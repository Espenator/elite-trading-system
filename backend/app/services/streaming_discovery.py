"""StreamingDiscoveryEngine — real-time anomaly detection from market_data.bar events.

E1 of the Continuous Discovery Architecture (Issue #38).

Subscribes to market_data.bar events already flowing from AlpacaStreamManager
and detects volume spikes, price breakouts, and gap events in real-time.
Every detection is published to swarm.idea (→ HyperSwarm triage) and
scout.discovery (→ WebSocket monitoring).

Also manages a DynamicUniverseManager that scores each seen symbol and
recommends universe expansions when a symbol becomes consistently active.

Design principles:
- Zero new Alpaca connections — piggybacks on existing market_data.bar stream
- Pure in-process; no DB writes on the hot path (bar callback is fast)
- Cooldown per symbol to avoid flooding HyperSwarm
- All discoveries carry source="streaming_discovery" (never "mock")

Pipeline position:
    AlpacaStreamManager → market_data.bar → StreamingDiscoveryEngine
                                              → swarm.idea → HyperSwarm
                                              → scout.discovery → WebSocket
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROLLING_WINDOW = 20          # Bars kept per symbol for anomaly baseline
VOLUME_SPIKE_RATIO = 2.0     # x times avg volume → spike
PRICE_BREAKOUT_WINDOW = 20   # New N-bar high/low → breakout
GAP_THRESHOLD = 0.02         # 2% open vs prior close → gap event
COOLDOWN_SECONDS = 300       # Minimum seconds between discoveries for same symbol
MAX_SYMBOLS_TRACKED = 2000   # Cap memory usage
UNIVERSE_ACTIVITY_THRESHOLD = 5   # Anomalies before symbol is promoted to universe


@dataclass
class DiscoveryEvent:
    """A real-time anomaly detected in the market_data.bar stream."""

    symbol: str
    event_type: str          # volume_spike | price_breakout | gap_up | gap_down
    direction: str           # bullish | bearish | neutral
    score: float             # 0-100 urgency score
    reasoning: str
    bar: Dict[str, Any]
    source: str = "streaming_discovery"
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "event_type": self.event_type,
            "direction": self.direction,
            "score": round(self.score, 1),
            "reasoning": self.reasoning,
            "bar": self.bar,
            "source": self.source,
            "detected_at": self.detected_at,
        }


class _SymbolWindow:
    """Per-symbol rolling window for anomaly detection."""

    __slots__ = ("closes", "volumes", "opens", "highs", "lows", "anomaly_count")

    def __init__(self) -> None:
        self.closes: Deque[float] = deque(maxlen=ROLLING_WINDOW)
        self.volumes: Deque[float] = deque(maxlen=ROLLING_WINDOW)
        self.opens: Deque[float] = deque(maxlen=ROLLING_WINDOW)
        self.highs: Deque[float] = deque(maxlen=ROLLING_WINDOW)
        self.lows: Deque[float] = deque(maxlen=ROLLING_WINDOW)
        self.anomaly_count: int = 0

    def push(self, bar: Dict[str, Any]) -> None:
        self.closes.append(float(bar.get("close") or 0))
        self.volumes.append(float(bar.get("volume") or 0))
        self.opens.append(float(bar.get("open") or 0))
        self.highs.append(float(bar.get("high") or 0))
        self.lows.append(float(bar.get("low") or 0))

    @property
    def ready(self) -> bool:
        """True once we have enough bars to detect anomalies."""
        return len(self.volumes) >= max(5, ROLLING_WINDOW // 4)

    def avg_volume(self) -> float:
        """Avg of all but the most recent bar."""
        baseline = list(self.volumes)[:-1]
        return sum(baseline) / len(baseline) if baseline else 0.0

    def recent_close(self) -> float:
        return self.closes[-1] if self.closes else 0.0

    def prior_close(self) -> float:
        return self.closes[-2] if len(self.closes) >= 2 else 0.0

    def n_bar_high(self) -> float:
        return max(self.highs) if self.highs else 0.0

    def n_bar_low(self) -> float:
        return min(self.lows) if self.lows else float("inf")


class DynamicUniverseManager:
    """Tracks symbol activity and recommends universe expansions.

    Symbols seen repeatedly in anomaly events are promoted to the active
    universe so AlpacaStreamManager starts streaming them.
    """

    def __init__(self) -> None:
        self._activity: Dict[str, int] = defaultdict(int)  # symbol → anomaly count
        self._promoted: Set[str] = set()
        self._pending_additions: List[str] = []

    def record_anomaly(self, symbol: str) -> None:
        self._activity[symbol] += 1
        if (
            self._activity[symbol] >= UNIVERSE_ACTIVITY_THRESHOLD
            and symbol not in self._promoted
        ):
            self._promoted.add(symbol)
            self._pending_additions.append(symbol)
            logger.info(
                "DynamicUniverse: %s promoted after %d anomalies",
                symbol,
                self._activity[symbol],
            )

    def drain_pending(self) -> List[str]:
        """Return and clear the list of newly promoted symbols."""
        result, self._pending_additions = self._pending_additions, []
        return result

    def get_status(self) -> Dict[str, Any]:
        top = sorted(self._activity.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "tracked_symbols": len(self._activity),
            "promoted_symbols": len(self._promoted),
            "pending_additions": len(self._pending_additions),
            "top_active": [{"symbol": s, "count": c} for s, c in top],
        }


class StreamingDiscoveryEngine:
    """Real-time anomaly detector consuming market_data.bar events.

    Parameters
    ----------
    message_bus : MessageBus
        The shared event bus (already started before this service).
    cooldown_seconds : int
        Per-symbol cooldown between discovery events.
    volume_spike_ratio : float
        Volume multiplier above rolling avg to trigger spike alert.
    gap_threshold : float
        Open vs prior-close ratio to trigger gap event.
    """

    def __init__(
        self,
        message_bus,
        cooldown_seconds: int = COOLDOWN_SECONDS,
        volume_spike_ratio: float = VOLUME_SPIKE_RATIO,
        gap_threshold: float = GAP_THRESHOLD,
    ) -> None:
        self._bus = message_bus
        self._cooldown = cooldown_seconds
        self._volume_spike_ratio = volume_spike_ratio
        self._gap_threshold = gap_threshold

        self._windows: Dict[str, _SymbolWindow] = {}
        self._last_discovery: Dict[str, float] = {}  # symbol → timestamp
        self._universe = DynamicUniverseManager()
        self._running = False
        self._start_time: Optional[float] = None

        # Stats
        self._stats: Dict[str, int] = {
            "bars_processed": 0,
            "anomalies_detected": 0,
            "volume_spikes": 0,
            "price_breakouts": 0,
            "gap_events": 0,
            "swarm_ideas_published": 0,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to market_data.bar and begin real-time detection."""
        self._running = True
        self._start_time = time.time()
        await self._bus.subscribe("market_data.bar", self._on_bar)
        logger.info(
            "StreamingDiscoveryEngine started "
            "(cooldown=%ds, volume_spike=%.1fx, gap=%.1f%%)",
            self._cooldown,
            self._volume_spike_ratio,
            self._gap_threshold * 100,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop."""
        self._running = False
        await self._bus.unsubscribe("market_data.bar", self._on_bar)
        logger.info(
            "StreamingDiscoveryEngine stopped — bars=%d, anomalies=%d",
            self._stats["bars_processed"],
            self._stats["anomalies_detected"],
        )

    # ------------------------------------------------------------------
    # Bar processing (hot path — must be fast)
    # ------------------------------------------------------------------

    async def _on_bar(self, bar: Dict[str, Any]) -> None:
        if not self._running:
            return

        symbol = bar.get("symbol", "")
        if not symbol:
            return

        # Evict oldest symbol if we're at capacity
        if len(self._windows) >= MAX_SYMBOLS_TRACKED and symbol not in self._windows:
            return

        win = self._windows.setdefault(symbol, _SymbolWindow())
        win.push(bar)
        self._stats["bars_processed"] += 1

        if not win.ready:
            return

        # Run anomaly detectors
        events = self._detect_anomalies(symbol, win, bar)
        if not events:
            return

        # Apply per-symbol cooldown
        now = time.time()
        if now - self._last_discovery.get(symbol, 0) < self._cooldown:
            return
        self._last_discovery[symbol] = now

        # Take the highest-score event
        event = max(events, key=lambda e: e.score)
        win.anomaly_count += 1
        self._universe.record_anomaly(symbol)
        self._stats["anomalies_detected"] += 1

        # Publish asynchronously — fire-and-forget to keep bar processing fast
        asyncio.create_task(self._publish_discovery(event))

    def _detect_anomalies(
        self, symbol: str, win: _SymbolWindow, bar: Dict[str, Any]
    ) -> List[DiscoveryEvent]:
        events: List[DiscoveryEvent] = []

        current_vol = float(bar.get("volume") or 0)
        current_close = float(bar.get("close") or 0)
        current_open = float(bar.get("open") or 0)
        current_high = float(bar.get("high") or 0)
        current_low = float(bar.get("low") or 0)
        prior_close = win.prior_close()

        # --- Volume spike ---
        avg_vol = win.avg_volume()
        if avg_vol > 0 and current_vol >= avg_vol * self._volume_spike_ratio:
            ratio = current_vol / avg_vol
            pct_chg = (current_close - prior_close) / prior_close if prior_close else 0
            direction = "bullish" if pct_chg > 0 else ("bearish" if pct_chg < 0 else "neutral")
            score = min(60 + (ratio - self._volume_spike_ratio) * 10, 90)
            events.append(
                DiscoveryEvent(
                    symbol=symbol,
                    event_type="volume_spike",
                    direction=direction,
                    score=score,
                    reasoning=(
                        f"Volume {ratio:.1f}x avg ({current_vol:,.0f} vs "
                        f"{avg_vol:,.0f} avg), price {pct_chg:+.1%}"
                    ),
                    bar=bar,
                )
            )
            self._stats["volume_spikes"] += 1

        # --- Price breakout (new N-bar high/low) ---
        if len(win.highs) >= PRICE_BREAKOUT_WINDOW and current_high > 0:
            prior_highs = list(win.highs)[:-1]
            prior_lows = list(win.lows)[:-1]
            n_bar_high = max(prior_highs) if prior_highs else 0
            n_bar_low = min(prior_lows) if prior_lows else float("inf")

            if current_high > n_bar_high and n_bar_high > 0:
                breakout_pct = (current_high - n_bar_high) / n_bar_high
                score = min(55 + breakout_pct * 500, 85)
                events.append(
                    DiscoveryEvent(
                        symbol=symbol,
                        event_type="price_breakout",
                        direction="bullish",
                        score=score,
                        reasoning=(
                            f"New {PRICE_BREAKOUT_WINDOW}-bar high: "
                            f"${current_high:.2f} vs prior high ${n_bar_high:.2f} "
                            f"(+{breakout_pct:.1%})"
                        ),
                        bar=bar,
                    )
                )
                self._stats["price_breakouts"] += 1

            elif current_low < n_bar_low and n_bar_low < float("inf"):
                breakdown_pct = (n_bar_low - current_low) / n_bar_low
                score = min(55 + breakdown_pct * 500, 85)
                events.append(
                    DiscoveryEvent(
                        symbol=symbol,
                        event_type="price_breakout",
                        direction="bearish",
                        score=score,
                        reasoning=(
                            f"New {PRICE_BREAKOUT_WINDOW}-bar low: "
                            f"${current_low:.2f} vs prior low ${n_bar_low:.2f} "
                            f"(-{breakdown_pct:.1%})"
                        ),
                        bar=bar,
                    )
                )
                self._stats["price_breakouts"] += 1

        # --- Gap events ---
        if prior_close > 0 and current_open > 0:
            gap_pct = (current_open - prior_close) / prior_close
            if abs(gap_pct) >= self._gap_threshold:
                event_type = "gap_up" if gap_pct > 0 else "gap_down"
                direction = "bullish" if gap_pct > 0 else "bearish"
                score = min(50 + abs(gap_pct) * 500, 80)
                events.append(
                    DiscoveryEvent(
                        symbol=symbol,
                        event_type=event_type,
                        direction=direction,
                        score=score,
                        reasoning=(
                            f"Gap {gap_pct:+.1%} open: "
                            f"${current_open:.2f} vs prior close ${prior_close:.2f}"
                        ),
                        bar=bar,
                    )
                )
                self._stats["gap_events"] += 1

        return events

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def _publish_discovery(self, event: DiscoveryEvent) -> None:
        """Publish event to swarm.idea and scout.discovery topics."""
        try:
            event_dict = event.to_dict()

            # swarm.idea → picked up by HyperSwarm for rapid triage
            await self._bus.publish(
                "swarm.idea",
                {
                    "source": event.source,
                    "symbols": [event.symbol],
                    "direction": event.direction,
                    "reasoning": event.reasoning,
                    "priority": int(max(1, min(10, event.score / 10))),
                    "event_type": event.event_type,
                    "score": event.score,
                    "bar": event.bar,
                },
            )
            self._stats["swarm_ideas_published"] += 1

            # scout.discovery → WebSocket monitoring channel
            await self._bus.publish("scout.discovery", event_dict)

        except Exception as exc:
            logger.debug("StreamingDiscovery publish failed for %s: %s", event.symbol, exc)

    # ------------------------------------------------------------------
    # Status / monitoring
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "symbols_tracked": len(self._windows),
            "cooldown_seconds": self._cooldown,
            "volume_spike_ratio": self._volume_spike_ratio,
            "gap_threshold_pct": round(self._gap_threshold * 100, 1),
            "stats": dict(self._stats),
            "universe": self._universe.get_status(),
        }

    def get_universe_status(self) -> Dict[str, Any]:
        return self._universe.get_status()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_streaming_discovery: Optional[StreamingDiscoveryEngine] = None


def get_streaming_discovery(message_bus=None) -> StreamingDiscoveryEngine:
    """Return the singleton StreamingDiscoveryEngine, creating it if needed."""
    global _streaming_discovery
    if _streaming_discovery is None:
        if message_bus is None:
            from app.core.message_bus import get_message_bus
            message_bus = get_message_bus()
        _streaming_discovery = StreamingDiscoveryEngine(message_bus=message_bus)
    return _streaming_discovery
