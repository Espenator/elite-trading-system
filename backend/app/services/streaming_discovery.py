"""StreamingDiscoveryEngine — real-time anomaly detection from live market bars.

E1 of the Continuous Discovery Architecture (Issue #38).

Architecture:
    market_data.bar → 5 anomaly detectors → 3-gate emit → swarm.idea
                                                         → scout.heartbeat (health)

Detectors (5 total):
    1. VolumeSurge     — bar volume ≥ 2.5× rolling average
    2. PriceBreakout   — close breaks above/below rolling high/low
    3. MomentumSpike   — |return| ≥ momentum threshold vs recent range
    4. VelocityBurst   — VWAP deviation or intra-bar range expansion
    5. VolatilityShift — bar range ≥ 2× recent average bar range

Emit rule (3-gate):
    ≥ 3 of 5 detectors must fire on the same bar for the engine to
    publish a DiscoveryEvent to ``swarm.idea``.  Fewer than 3 fires
    are silently discarded to suppress noise.

DiscoveryEvent fields (matches swarm.idea schema):
    source    — "streaming_discovery:<symbol>"
    symbols   — [symbol]
    direction — "bullish" | "bearish" | "neutral"
    reasoning — human-readable summary of which detectors fired
    priority  — 1 (highest) – 5; derived from detector count
    metadata  — dict with raw detector outputs and bar data
"""
import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tunable constants
# ─────────────────────────────────────────────────────────────────────────────

LOOKBACK_BARS = 20           # Rolling window for averages
VOLUME_SURGE_MULT = 2.5      # Volume ≥ 2.5× rolling avg → detector fires
MOMENTUM_THRESHOLD = 0.015   # 1.5% move vs recent range → detector fires
VELOCITY_THRESHOLD = 0.5     # Intra-bar range ≥ 50% of recent avg range
VOLATILITY_MULT = 2.0        # Bar range ≥ 2× rolling avg range → detector fires
MIN_GATES = 3                # Minimum detectors that must fire to emit
MIN_PRICE = 1.0              # Skip penny stocks (price < $1)
MIN_VOLUME = 100             # Skip illiquid bars
MAX_TRACKED_SYMBOLS = 2000   # Evict LRU states above this to cap memory


@dataclass
class BarState:
    """Rolling state for a single symbol."""
    symbol: str
    volumes: Deque[float] = field(default_factory=lambda: deque(maxlen=LOOKBACK_BARS))
    ranges: Deque[float] = field(default_factory=lambda: deque(maxlen=LOOKBACK_BARS))
    closes: Deque[float] = field(default_factory=lambda: deque(maxlen=LOOKBACK_BARS))
    highs: Deque[float] = field(default_factory=lambda: deque(maxlen=LOOKBACK_BARS))
    lows: Deque[float] = field(default_factory=lambda: deque(maxlen=LOOKBACK_BARS))
    total_bars: int = 0

    def update(self, bar: Dict[str, Any]) -> None:
        close = float(bar.get("close", bar.get("c", 0)))
        high = float(bar.get("high", bar.get("h", close)))
        low = float(bar.get("low", bar.get("l", close)))
        volume = float(bar.get("volume", bar.get("v", 0)))
        self.closes.append(close)
        self.highs.append(high)
        self.lows.append(low)
        self.volumes.append(volume)
        self.ranges.append(high - low)
        self.total_bars += 1

    @property
    def has_baseline(self) -> bool:
        return self.total_bars >= max(5, LOOKBACK_BARS // 4)


@dataclass
class DetectionResult:
    """Output of a single detector pass."""
    name: str
    fired: bool
    direction: str = "neutral"  # bullish / bearish / neutral
    detail: str = ""


@dataclass
class DiscoveryEvent:
    """A discovery that passed the 3-gate filter."""
    symbol: str
    direction: str
    reasoning: str
    priority: int
    detector_names: List[str]
    bar: Dict[str, Any]
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_swarm_idea(self) -> Dict[str, Any]:
        return {
            "source": f"streaming_discovery:{self.symbol}",
            "symbols": [self.symbol],
            "direction": self.direction,
            "reasoning": self.reasoning,
            "priority": self.priority,
            "metadata": {
                "detectors": self.detector_names,
                "bar": self.bar,
                "detected_at": self.detected_at,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Individual detectors
# ─────────────────────────────────────────────────────────────────────────────

def detect_volume_surge(state: BarState, bar: Dict[str, Any]) -> DetectionResult:
    """Detector 1 — volume ≥ VOLUME_SURGE_MULT × rolling average."""
    if len(state.volumes) < 2:
        return DetectionResult("volume_surge", False)
    current_vol = float(bar.get("volume", bar.get("v", 0)))
    avg_vol = sum(list(state.volumes)[:-1]) / max(len(state.volumes) - 1, 1)
    if avg_vol == 0:
        return DetectionResult("volume_surge", False)
    ratio = current_vol / avg_vol
    fired = ratio >= VOLUME_SURGE_MULT
    return DetectionResult(
        "volume_surge",
        fired=fired,
        direction="neutral",
        detail=f"vol_ratio={ratio:.2f}",
    )


def detect_price_breakout(state: BarState, bar: Dict[str, Any]) -> DetectionResult:
    """Detector 2 — close breaks above rolling high or below rolling low."""
    if len(state.highs) < 2 or len(state.lows) < 2:
        return DetectionResult("price_breakout", False)
    close = float(bar.get("close", bar.get("c", 0)))
    prior_highs = list(state.highs)[:-1]
    prior_lows = list(state.lows)[:-1]
    rolling_high = max(prior_highs)
    rolling_low = min(prior_lows)
    if close > rolling_high:
        return DetectionResult("price_breakout", True, "bullish",
                               f"close={close:.2f} > rolling_high={rolling_high:.2f}")
    if close < rolling_low:
        return DetectionResult("price_breakout", True, "bearish",
                               f"close={close:.2f} < rolling_low={rolling_low:.2f}")
    return DetectionResult("price_breakout", False)


def detect_momentum_spike(state: BarState, bar: Dict[str, Any]) -> DetectionResult:
    """Detector 3 — |return| ≥ MOMENTUM_THRESHOLD vs prior close."""
    if len(state.closes) < 2:
        return DetectionResult("momentum_spike", False)
    close = float(bar.get("close", bar.get("c", 0)))
    prior_close = list(state.closes)[-2]
    if prior_close == 0:
        return DetectionResult("momentum_spike", False)
    ret = (close - prior_close) / prior_close
    fired = abs(ret) >= MOMENTUM_THRESHOLD
    direction = "bullish" if ret > 0 else "bearish"
    return DetectionResult(
        "momentum_spike",
        fired=fired,
        direction=direction if fired else "neutral",
        detail=f"return={ret:.4f}",
    )


def detect_velocity_burst(state: BarState, bar: Dict[str, Any]) -> DetectionResult:
    """Detector 4 — intra-bar range ≥ VELOCITY_THRESHOLD × rolling avg range."""
    if len(state.ranges) < 2:
        return DetectionResult("velocity_burst", False)
    high = float(bar.get("high", bar.get("h", 0)))
    low = float(bar.get("low", bar.get("l", 0)))
    close = float(bar.get("close", bar.get("c", 0)))
    current_range = high - low
    avg_range = sum(list(state.ranges)[:-1]) / max(len(state.ranges) - 1, 1)
    if avg_range == 0:
        return DetectionResult("velocity_burst", False)
    ratio = current_range / avg_range
    fired = ratio >= (1.0 + VELOCITY_THRESHOLD)
    # Direction: bullish if close is in upper half of bar
    midpoint = (high + low) / 2.0
    direction = "bullish" if close >= midpoint else "bearish"
    return DetectionResult(
        "velocity_burst",
        fired=fired,
        direction=direction if fired else "neutral",
        detail=f"range_ratio={ratio:.2f}",
    )


def detect_volatility_shift(state: BarState, bar: Dict[str, Any]) -> DetectionResult:
    """Detector 5 — bar range ≥ VOLATILITY_MULT × rolling average range."""
    if len(state.ranges) < 2:
        return DetectionResult("volatility_shift", False)
    high = float(bar.get("high", bar.get("h", 0)))
    low = float(bar.get("low", bar.get("l", 0)))
    current_range = high - low
    avg_range = sum(list(state.ranges)[:-1]) / max(len(state.ranges) - 1, 1)
    if avg_range == 0:
        return DetectionResult("volatility_shift", False)
    ratio = current_range / avg_range
    fired = ratio >= VOLATILITY_MULT
    return DetectionResult(
        "volatility_shift",
        fired=fired,
        direction="neutral",
        detail=f"vol_ratio={ratio:.2f}",
    )


_DETECTORS = [
    detect_volume_surge,
    detect_price_breakout,
    detect_momentum_spike,
    detect_velocity_burst,
    detect_volatility_shift,
]


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class StreamingDiscoveryEngine:
    """Real-time anomaly detection engine.

    Subscribes to ``market_data.bar``, runs 5 detectors per bar, and
    emits a DiscoveryEvent to ``swarm.idea`` when ≥ MIN_GATES detectors fire.
    """

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._states: Dict[str, BarState] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats = {
            "bars_processed": 0,
            "detections_fired": 0,
            "events_emitted": 0,
            "events_suppressed": 0,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("market_data.bar", self._on_bar)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "StreamingDiscoveryEngine started: %d detectors, %d-gate emit",
            len(_DETECTORS), MIN_GATES,
        )

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("StreamingDiscoveryEngine stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Bar handler
    # ──────────────────────────────────────────────────────────────────────

    async def _on_bar(self, data: Dict[str, Any]) -> None:
        symbol = data.get("symbol", data.get("S", ""))
        if not symbol:
            return
        close = float(data.get("close", data.get("c", 0)))
        volume = float(data.get("volume", data.get("v", 0)))
        if close < MIN_PRICE or volume < MIN_VOLUME:
            return

        state = self._states.setdefault(symbol, BarState(symbol=symbol))

        # Hard cap: evict the first-inserted (oldest by insertion order) symbol
        # when the table exceeds MAX_TRACKED_SYMBOLS.  setdefault() always appends
        # new symbols to the end, so next(iter(_states)) is the symbol seen
        # least recently for the first time — suitable for FIFO eviction of
        # delisted / one-off tickers that will never return.
        if len(self._states) > MAX_TRACKED_SYMBOLS:
            oldest = next(iter(self._states))
            del self._states[oldest]

        results = self._run_detectors(state, data)
        state.update(data)
        self._stats["bars_processed"] += 1

        fired = [r for r in results if r.fired]
        self._stats["detections_fired"] += len(fired)

        if len(fired) >= MIN_GATES:
            event = self._build_event(symbol, data, fired)
            self._stats["events_emitted"] += 1
            await self._emit(event)
        else:
            self._stats["events_suppressed"] += 1

    def _run_detectors(
        self, state: BarState, bar: Dict[str, Any]
    ) -> List[DetectionResult]:
        if not state.has_baseline:
            return []
        results = []
        for detector_fn in _DETECTORS:
            try:
                results.append(detector_fn(state, bar))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Detector %s error: %s", detector_fn.__name__, exc)
        return results

    def _build_event(
        self, symbol: str, bar: Dict[str, Any], fired: List[DetectionResult]
    ) -> DiscoveryEvent:
        # Aggregate direction by majority vote
        directions = [r.direction for r in fired if r.direction != "neutral"]
        bullish = directions.count("bullish")
        bearish = directions.count("bearish")
        if bullish > bearish:
            direction = "bullish"
        elif bearish > bullish:
            direction = "bearish"
        else:
            direction = "neutral"

        reasoning = (
            f"StreamingDiscovery: {len(fired)}/{len(_DETECTORS)} detectors fired on {symbol}. "
            + " | ".join(f"{r.name}({r.detail})" for r in fired)
        )
        # Priority: 5 detectors → 1, 4 → 2, 3 → 3
        priority = max(1, MIN_GATES + len(_DETECTORS) - len(fired))

        return DiscoveryEvent(
            symbol=symbol,
            direction=direction,
            reasoning=reasoning,
            priority=priority,
            detector_names=[r.name for r in fired],
            bar={
                "close": float(bar.get("close", bar.get("c", 0))),
                "high": float(bar.get("high", bar.get("h", 0))),
                "low": float(bar.get("low", bar.get("l", 0))),
                "volume": float(bar.get("volume", bar.get("v", 0))),
                "symbol": symbol,
            },
        )

    async def _emit(self, event: DiscoveryEvent) -> None:
        if not self._bus:
            return
        try:
            await self._bus.publish("swarm.idea", event.to_swarm_idea())
            logger.debug(
                "Emitted discovery: symbol=%s direction=%s gates=%d",
                event.symbol, event.direction, len(event.detector_names),
            )
        except Exception as exc:
            logger.warning("StreamingDiscoveryEngine emit failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Health heartbeat
    # ──────────────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(30)
            if not self._running:
                break
            if self._bus:
                try:
                    await self._bus.publish("scout.heartbeat", {
                        "source": "streaming_discovery_engine",
                        "status": "healthy",
                        "stats": dict(self._stats),
                        "tracked_symbols": len(self._states),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as exc:
                    logger.debug("Heartbeat publish failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Public helpers
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_tracked_symbols(self) -> List[str]:
        return list(self._states.keys())


_engine: Optional[StreamingDiscoveryEngine] = None


def get_streaming_discovery_engine(
    message_bus=None,
) -> StreamingDiscoveryEngine:
    global _engine
    if _engine is None:
        _engine = StreamingDiscoveryEngine(message_bus)
    return _engine
