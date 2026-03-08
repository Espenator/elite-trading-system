"""StreamingDiscoveryEngine — continuous, event-driven discovery path (Issue #38, E1).

Subscribes to ``market_data.bar`` events from the existing Alpaca stream and
detects real-time anomalies *without* polling.  Every confirmed anomaly is
published as a ``DiscoveryEvent`` on the ``swarm.idea`` MessageBus topic so the
existing HyperSwarm / SwarmSpawner council pipeline can triage and escalate it.

Design goals
============
* **Continuous** — one discovery path per incoming bar, not periodic.
* **Non-duplicate** — respects existing EventDrivenSignalEngine pipeline;
  does NOT publish ``signal.generated`` or touch the order/trade path.
* **Composable** — plugs in alongside TurboScanner, AutonomousScoutService, and
  all other ``swarm.idea`` producers without requiring changes to consumers.
* **Backpressure-safe** — global rate cap + per-symbol cooldown prevent flooding
  HyperSwarm when many symbols move simultaneously.
* **Observable** — ``get_status()`` mirrors the convention used by all other
  services (TurboScanner, HyperSwarm, etc.) for uniform health monitoring.

Event schema (``swarm.idea``)
==============================
Fields follow the schema consumed by ``SwarmSpawner._on_idea_event`` and
``HyperSwarm._on_signal``:

    source      : "streaming_discovery:<discovery_type>"
    symbols     : List[str]   — typically one symbol
    direction   : "bullish" | "bearish" | "unknown"
    reasoning   : str         — human-readable explanation
    priority    : int         — 1 (highest) – 10 (lowest)
    metadata    : {
        discovery_type  : str   — "volume_spike" | "price_breakout" | ...
        confidence      : float — 0.0–1.0
        volume_ratio    : float — bars volume / 20-bar avg volume
        price_change_pct: float — close vs open for the triggering bar
        bar_timestamp   : str   — ISO-8601 bar timestamp
    }

Backpressure / throttling / deduplication / health
===================================================
* ``DEDUP_TTL_SECONDS``      — minimum seconds between same (symbol, type) event.
* ``MAX_DISCOVERIES_PER_SEC``— global publish rate cap (token bucket, 1s window).
* ``SYMBOL_COOLDOWN_SECONDS``— per-symbol minimum gap between *any* discovery.
* ``_dedup_cache``           — ``{f"{symbol}:{dtype}": last_emit_ts}`` dict.
* ``_symbol_last_emit``      — ``{symbol: last_emit_ts}`` per-symbol gate.
* ``get_status()``           — exposes bars_processed, discoveries_emitted,
                               discoveries_skipped, dedup_cache_size, uptime.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration constants (tunable via env in a later iteration)
# ═══════════════════════════════════════════════════════════════════════════════

#: Rolling bar history maintained per symbol for indicator calculation.
MAX_BAR_HISTORY: int = 50

#: Minimum volume multiple over 20-bar average to trigger a volume_spike.
VOLUME_SPIKE_RATIO: float = 2.0

#: Minimum number of consecutive same-direction closes to trigger momentum_surge.
MOMENTUM_RUN_MIN: int = 4

#: Minimum bar price range multiple over 20-bar average to trigger range_expansion.
RANGE_EXPANSION_RATIO: float = 2.5

#: Minimum VWAP deviation percentage (|close - vwap| / vwap) for vwap_deviation.
VWAP_DEVIATION_PCT: float = 0.012  # 1.2 %

#: Deduplication TTL — same (symbol, type) pair is suppressed for this many seconds.
DEDUP_TTL_SECONDS: int = 300  # 5 minutes

#: Per-symbol cooldown — any discovery for a symbol is suppressed within this window.
SYMBOL_COOLDOWN_SECONDS: int = 60  # 1 minute

#: Maximum discoveries emitted globally per second (token-bucket gate).
MAX_DISCOVERIES_PER_SEC: int = 20

#: Minimum bars needed before running detectors on a symbol.
MIN_BARS_REQUIRED: int = 20

#: Discovery type priorities (lower = more urgent; matches TurboScanner convention).
_DISCOVERY_PRIORITIES: Dict[str, int] = {
    "volume_spike": 2,
    "price_breakout": 3,
    "momentum_surge": 3,
    "vwap_deviation": 4,
    "range_expansion": 3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Event schema
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DiscoveryEvent:
    """Typed wrapper for a discovery published to ``swarm.idea``.

    Serialised to a plain dict via ``to_bus_payload()`` before publishing so
    downstream consumers (SwarmSpawner, HyperSwarm) require zero changes.
    """

    discovery_type: str
    symbol: str
    direction: str                  # "bullish" | "bearish" | "unknown"
    reasoning: str
    confidence: float               # 0.0–1.0
    volume_ratio: float = 0.0
    price_change_pct: float = 0.0
    bar_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: Dict[str, Any] = field(default_factory=dict)

    # Derived / set by engine after construction
    priority: int = 5

    def to_bus_payload(self) -> Dict[str, Any]:
        """Return the ``swarm.idea`` wire format consumed by HyperSwarm / SwarmSpawner."""
        return {
            "source": f"streaming_discovery:{self.discovery_type}",
            "symbols": [self.symbol],
            "direction": self.direction,
            "reasoning": self.reasoning,
            "priority": self.priority,
            "metadata": {
                "discovery_type": self.discovery_type,
                "confidence": round(self.confidence, 3),
                "volume_ratio": round(self.volume_ratio, 3),
                "price_change_pct": round(self.price_change_pct, 4),
                "bar_timestamp": self.bar_timestamp,
                **self.extra,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════


class StreamingDiscoveryEngine:
    """Continuous, event-driven discovery engine for the swarm idea pipeline.

    Lifecycle
    ---------
    1. ``await engine.start()``  — subscribes to ``market_data.bar``
    2. Each incoming bar triggers ``_on_new_bar()``
    3. Anomaly detectors run synchronously against rolling per-symbol history
    4. Confirmed discoveries are deduped, rate-limited, then published to ``swarm.idea``
    5. ``await engine.stop()``  — unsubscribes and cancels cleanup task

    All anomaly detection is intentionally lightweight (O(history_size) math)
    so it completes within the same event-loop tick as the bar arrival.
    """

    def __init__(self, message_bus) -> None:
        self._bus = message_bus
        self._running: bool = False
        self._start_time: Optional[float] = None

        # Per-symbol rolling bar history (deque capped at MAX_BAR_HISTORY)
        self._bar_history: Dict[str, deque] = {}

        # Deduplication cache: f"{symbol}:{discovery_type}" -> last publish timestamp
        self._dedup_cache: Dict[str, float] = {}

        # Per-symbol gate: symbol -> last publish timestamp
        self._symbol_last_emit: Dict[str, float] = {}

        # Global rate limiter: sliding window of publish timestamps in the last second
        self._recent_publish_times: deque = deque()

        # Cleanup task handle
        self._cleanup_task: Optional[asyncio.Task] = None

        # Health counters
        self._bars_processed: int = 0
        self._discoveries_emitted: int = 0
        self._discoveries_skipped_dedup: int = 0
        self._discoveries_skipped_rate: int = 0
        self._discoveries_skipped_cooldown: int = 0
        self._errors: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to ``market_data.bar`` and begin continuous discovery."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        await self._bus.subscribe("market_data.bar", self._on_new_bar)
        self._cleanup_task = asyncio.create_task(self._dedup_cleanup_loop())
        logger.info(
            "StreamingDiscoveryEngine started — "
            "subscribed to market_data.bar (dedup_ttl=%ds, rate_cap=%d/s)",
            DEDUP_TTL_SECONDS,
            MAX_DISCOVERIES_PER_SEC,
        )

    async def stop(self) -> None:
        """Unsubscribe and shut down the cleanup background task."""
        self._running = False
        await self._bus.unsubscribe("market_data.bar", self._on_new_bar)
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "StreamingDiscoveryEngine stopped — "
            "%d bars processed, %d discoveries emitted",
            self._bars_processed,
            self._discoveries_emitted,
        )

    # ------------------------------------------------------------------
    # Bar handler
    # ------------------------------------------------------------------

    async def _on_new_bar(self, data: Dict[str, Any]) -> None:
        """Process a single ``market_data.bar`` event.

        Maintains rolling history then runs all detectors.  Any confirmed
        ``DiscoveryEvent`` is passed to ``_emit_discovery``.
        """
        if not self._running:
            return

        symbol: str = data.get("symbol", "")
        if not symbol:
            return

        try:
            self._bars_processed += 1

            # Maintain rolling bar history
            if symbol not in self._bar_history:
                self._bar_history[symbol] = deque(maxlen=MAX_BAR_HISTORY)
            self._bar_history[symbol].append(data)

            history = self._bar_history[symbol]
            if len(history) < MIN_BARS_REQUIRED:
                return

            bars: List[Dict[str, Any]] = list(history)

            # Run all detectors — first confirmed result wins per bar to avoid
            # publishing multiple discoveries for the same bar.
            discovery = (
                self._detect_volume_spike(symbol, bars)
                or self._detect_price_breakout(symbol, bars)
                or self._detect_momentum_surge(symbol, bars)
                or self._detect_vwap_deviation(symbol, bars)
                or self._detect_range_expansion(symbol, bars)
            )

            if discovery:
                await self._emit_discovery(discovery)

        except Exception:
            self._errors += 1
            logger.debug("StreamingDiscoveryEngine bar error for %s", symbol, exc_info=True)

    # ------------------------------------------------------------------
    # Anomaly detectors
    # ------------------------------------------------------------------

    def _detect_volume_spike(
        self, symbol: str, bars: List[Dict[str, Any]]
    ) -> Optional[DiscoveryEvent]:
        """Return a discovery if the latest bar's volume is >= VOLUME_SPIKE_RATIO × avg."""
        latest = bars[-1]
        current_vol = float(latest.get("volume") or 0)
        if current_vol <= 0:
            return None

        avg_vol = self._avg_volume(bars[:-1])
        if avg_vol <= 0:
            return None

        ratio = current_vol / avg_vol
        if ratio < VOLUME_SPIKE_RATIO:
            return None

        close = float(latest.get("close") or 0)
        open_ = float(latest.get("open") or close)
        pct_change = ((close - open_) / open_) if open_ > 0 else 0.0
        direction = "bullish" if pct_change >= 0 else "bearish"

        confidence = min(1.0, (ratio - VOLUME_SPIKE_RATIO) / VOLUME_SPIKE_RATIO * 0.5 + 0.5)
        return DiscoveryEvent(
            discovery_type="volume_spike",
            symbol=symbol,
            direction=direction,
            reasoning=(
                f"{symbol} volume {ratio:.1f}x avg — "
                f"price {'up' if pct_change >= 0 else 'down'} "
                f"{abs(pct_change) * 100:.2f}%"
            ),
            confidence=confidence,
            volume_ratio=round(ratio, 3),
            price_change_pct=round(pct_change, 4),
            bar_timestamp=latest.get("timestamp", ""),
        )

    def _detect_price_breakout(
        self, symbol: str, bars: List[Dict[str, Any]]
    ) -> Optional[DiscoveryEvent]:
        """Return a discovery if the latest close breaks the 10-bar prior high/low."""
        if len(bars) < 12:
            return None

        latest = bars[-1]
        prior = bars[-11:-1]  # 10 bars before the current one

        close = float(latest.get("close") or 0)
        if close <= 0:
            return None

        prior_high = max((float(b.get("high") or 0) for b in prior), default=0)
        prior_low = min(
            (float(b.get("low") or float("inf")) for b in prior if b.get("low")),
            default=float("inf"),
        )

        pct_change = 0.0
        if close > prior_high > 0:
            pct_change = (close - prior_high) / prior_high
            direction = "bullish"
            reasoning = f"{symbol} broke 10-bar high ${prior_high:.2f} → ${close:.2f} (+{pct_change*100:.2f}%)"
        elif close < prior_low < float("inf"):
            pct_change = (close - prior_low) / prior_low
            direction = "bearish"
            reasoning = f"{symbol} broke 10-bar low ${prior_low:.2f} → ${close:.2f} ({pct_change*100:.2f}%)"
        else:
            return None

        avg_vol = self._avg_volume(bars[:-1])
        current_vol = float(latest.get("volume") or 0)
        vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        confidence = min(1.0, abs(pct_change) * 50 + 0.4)
        return DiscoveryEvent(
            discovery_type="price_breakout",
            symbol=symbol,
            direction=direction,
            reasoning=reasoning,
            confidence=confidence,
            volume_ratio=round(vol_ratio, 3),
            price_change_pct=round(pct_change, 4),
            bar_timestamp=latest.get("timestamp", ""),
        )

    def _detect_momentum_surge(
        self, symbol: str, bars: List[Dict[str, Any]]
    ) -> Optional[DiscoveryEvent]:
        """Return a discovery if the last N consecutive bars all close in the same direction."""
        if len(bars) < MOMENTUM_RUN_MIN + 1:
            return None

        recent = bars[-(MOMENTUM_RUN_MIN + 1):]
        closes = [float(b.get("close") or 0) for b in recent]
        if any(c <= 0 for c in closes):
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        if all(d > 0 for d in deltas):
            direction = "bullish"
        elif all(d < 0 for d in deltas):
            direction = "bearish"
        else:
            return None

        total_move = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0.0
        latest = bars[-1]
        avg_vol = self._avg_volume(bars[:-1])
        current_vol = float(latest.get("volume") or 0)
        vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        confidence = min(1.0, abs(total_move) * 30 + 0.4)
        return DiscoveryEvent(
            discovery_type="momentum_surge",
            symbol=symbol,
            direction=direction,
            reasoning=(
                f"{symbol} {MOMENTUM_RUN_MIN}-bar momentum run "
                f"({'up' if direction == 'bullish' else 'down'} "
                f"{abs(total_move)*100:.2f}% total)"
            ),
            confidence=confidence,
            volume_ratio=round(vol_ratio, 3),
            price_change_pct=round(total_move, 4),
            bar_timestamp=latest.get("timestamp", ""),
        )

    def _detect_vwap_deviation(
        self, symbol: str, bars: List[Dict[str, Any]]
    ) -> Optional[DiscoveryEvent]:
        """Return a discovery if close deviates from VWAP by >= VWAP_DEVIATION_PCT."""
        latest = bars[-1]
        close = float(latest.get("close") or 0)
        vwap = float(latest.get("vwap") or 0)
        if close <= 0 or vwap <= 0:
            return None

        deviation = (close - vwap) / vwap
        if abs(deviation) < VWAP_DEVIATION_PCT:
            return None

        direction = "bullish" if deviation > 0 else "bearish"
        avg_vol = self._avg_volume(bars[:-1])
        current_vol = float(latest.get("volume") or 0)
        vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        confidence = min(1.0, abs(deviation) / VWAP_DEVIATION_PCT * 0.3 + 0.4)
        return DiscoveryEvent(
            discovery_type="vwap_deviation",
            symbol=symbol,
            direction=direction,
            reasoning=(
                f"{symbol} {'above' if deviation > 0 else 'below'} VWAP by "
                f"{abs(deviation)*100:.2f}% "
                f"(close=${close:.2f}, vwap=${vwap:.2f})"
            ),
            confidence=confidence,
            volume_ratio=round(vol_ratio, 3),
            price_change_pct=round(deviation, 4),
            bar_timestamp=latest.get("timestamp", ""),
        )

    def _detect_range_expansion(
        self, symbol: str, bars: List[Dict[str, Any]]
    ) -> Optional[DiscoveryEvent]:
        """Return a discovery if the current bar's high-low range >> avg range."""
        latest = bars[-1]
        high = float(latest.get("high") or 0)
        low = float(latest.get("low") or 0)
        if high <= 0 or low <= 0 or high <= low:
            return None

        current_range = high - low
        avg_range = self._avg_range(bars[:-1])
        if avg_range <= 0:
            return None

        ratio = current_range / avg_range
        if ratio < RANGE_EXPANSION_RATIO:
            return None

        close = float(latest.get("close") or 0)
        open_ = float(latest.get("open") or close)
        pct_change = ((close - open_) / open_) if open_ > 0 else 0.0
        direction = "bullish" if pct_change >= 0 else "bearish"

        avg_vol = self._avg_volume(bars[:-1])
        current_vol = float(latest.get("volume") or 0)
        vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        confidence = min(1.0, (ratio - RANGE_EXPANSION_RATIO) / RANGE_EXPANSION_RATIO * 0.4 + 0.4)
        return DiscoveryEvent(
            discovery_type="range_expansion",
            symbol=symbol,
            direction=direction,
            reasoning=(
                f"{symbol} bar range {ratio:.1f}x avg "
                f"(H=${high:.2f} L=${low:.2f}, range=${current_range:.2f})"
            ),
            confidence=confidence,
            volume_ratio=round(vol_ratio, 3),
            price_change_pct=round(pct_change, 4),
            bar_timestamp=latest.get("timestamp", ""),
        )

    # ------------------------------------------------------------------
    # Emission with backpressure / dedup / rate-limiting
    # ------------------------------------------------------------------

    async def _emit_discovery(self, event: DiscoveryEvent) -> None:
        """Gate and publish a ``DiscoveryEvent`` to ``swarm.idea``.

        Gates (applied in order):
        1. **Per-symbol cooldown** — SYMBOL_COOLDOWN_SECONDS between any two
           discoveries for the same symbol.
        2. **Deduplication** — DEDUP_TTL_SECONDS between same (symbol, type).
        3. **Global rate cap** — MAX_DISCOVERIES_PER_SEC across all symbols.
        """
        now = time.time()

        # 1. Per-symbol cooldown
        last_symbol_emit = self._symbol_last_emit.get(event.symbol, 0.0)
        if now - last_symbol_emit < SYMBOL_COOLDOWN_SECONDS:
            self._discoveries_skipped_cooldown += 1
            return

        # 2. Deduplication
        dedup_key = f"{event.symbol}:{event.discovery_type}"
        last_dedup_emit = self._dedup_cache.get(dedup_key, 0.0)
        if now - last_dedup_emit < DEDUP_TTL_SECONDS:
            self._discoveries_skipped_dedup += 1
            return

        # 3. Global rate cap (sliding 1-second window)
        cutoff = now - 1.0
        while self._recent_publish_times and self._recent_publish_times[0] < cutoff:
            self._recent_publish_times.popleft()
        if len(self._recent_publish_times) >= MAX_DISCOVERIES_PER_SEC:
            self._discoveries_skipped_rate += 1
            return

        # Set priority from lookup table
        event.priority = _DISCOVERY_PRIORITIES.get(event.discovery_type, 5)

        # Record timestamps before publish (optimistic — avoids double-emit on error)
        self._dedup_cache[dedup_key] = now
        self._symbol_last_emit[event.symbol] = now
        self._recent_publish_times.append(now)
        self._discoveries_emitted += 1

        await self._bus.publish("swarm.idea", event.to_bus_payload())

        logger.debug(
            "Discovery emitted: %s %s (%s, conf=%.2f)",
            event.symbol,
            event.discovery_type,
            event.direction,
            event.confidence,
        )

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    async def _dedup_cleanup_loop(self) -> None:
        """Periodically evict stale entries from the dedup cache (every 5 min)."""
        while self._running:
            try:
                await asyncio.sleep(DEDUP_TTL_SECONDS)
                now = time.time()
                stale_keys = [
                    k for k, ts in self._dedup_cache.items()
                    if now - ts > DEDUP_TTL_SECONDS
                ]
                for k in stale_keys:
                    del self._dedup_cache[k]
                stale_sym = [
                    s for s, ts in self._symbol_last_emit.items()
                    if now - ts > SYMBOL_COOLDOWN_SECONDS * 10
                ]
                for s in stale_sym:
                    del self._symbol_last_emit[s]
                if stale_keys or stale_sym:
                    logger.debug(
                        "Dedup cache cleanup: evicted %d keys, %d symbol entries",
                        len(stale_keys), len(stale_sym),
                    )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.debug("Dedup cleanup error", exc_info=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _avg_volume(bars: List[Dict[str, Any]], window: int = 20) -> float:
        """Mean volume over the last ``window`` bars (or all bars if fewer)."""
        recent = bars[-window:] if len(bars) >= window else bars
        vols = [float(b.get("volume") or 0) for b in recent]
        valid = [v for v in vols if v > 0]
        return sum(valid) / len(valid) if valid else 0.0

    @staticmethod
    def _avg_range(bars: List[Dict[str, Any]], window: int = 20) -> float:
        """Mean high-low range over the last ``window`` bars."""
        recent = bars[-window:] if len(bars) >= window else bars
        ranges = []
        for b in recent:
            h = float(b.get("high") or 0)
            lo = float(b.get("low") or 0)
            if h > 0 and lo > 0 and h > lo:
                ranges.append(h - lo)
        return sum(ranges) / len(ranges) if ranges else 0.0

    # ------------------------------------------------------------------
    # Health / observability
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a health snapshot compatible with the monitoring dashboard."""
        uptime = time.time() - self._start_time if self._start_time else 0.0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "symbols_tracked": len(self._bar_history),
            "bars_processed": self._bars_processed,
            "discoveries_emitted": self._discoveries_emitted,
            "discoveries_skipped_dedup": self._discoveries_skipped_dedup,
            "discoveries_skipped_rate": self._discoveries_skipped_rate,
            "discoveries_skipped_cooldown": self._discoveries_skipped_cooldown,
            "errors": self._errors,
            "dedup_cache_size": len(self._dedup_cache),
            "config": {
                "max_bar_history": MAX_BAR_HISTORY,
                "volume_spike_ratio": VOLUME_SPIKE_RATIO,
                "momentum_run_min": MOMENTUM_RUN_MIN,
                "range_expansion_ratio": RANGE_EXPANSION_RATIO,
                "vwap_deviation_pct": VWAP_DEVIATION_PCT,
                "dedup_ttl_seconds": DEDUP_TTL_SECONDS,
                "symbol_cooldown_seconds": SYMBOL_COOLDOWN_SECONDS,
                "max_discoveries_per_sec": MAX_DISCOVERIES_PER_SEC,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singleton factory
# ═══════════════════════════════════════════════════════════════════════════════

_instance: Optional[StreamingDiscoveryEngine] = None


def get_streaming_discovery(message_bus=None) -> StreamingDiscoveryEngine:
    """Return (or create) the module-level ``StreamingDiscoveryEngine`` singleton.

    On first call, ``message_bus`` must be provided.  Subsequent calls may
    omit it to retrieve the cached instance.
    """
    global _instance
    if _instance is None:
        if message_bus is None:
            raise RuntimeError(
                "get_streaming_discovery() called before engine was initialised. "
                "Pass a MessageBus instance on the first call."
            )
        _instance = StreamingDiscoveryEngine(message_bus)
    return _instance
