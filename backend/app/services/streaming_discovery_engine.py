"""StreamingDiscoveryEngine — real-time anomaly detection on market data bars.

Issue #38 — E1: Streaming Discovery Architecture.

Subscribes to ``market_data.bar`` events on the MessageBus and detects
in-bar anomalies within a rolling window per symbol.  High-score events
are published as ``swarm.idea`` messages for immediate HyperSwarm triage,
bridging the gap between real-time market data and the scout/council
pipeline without waiting for the 60-second TurboScanner cycle.

Anomaly detectors (each contributes 0-100 sub-score):
    1. **Volume spike** — current volume vs N-bar average.
    2. **Price surge** — absolute intra-bar % change exceeds threshold.
    3. **VWAP deviation** — price diverges from rolling VWAP estimate.
    4. **RSI extreme** — fast RSI (7-period) in overbought / oversold zone.
    5. **Bollinger squeeze + expansion** — BB width collapse followed by breakout.

Composite score = weighted average of triggered sub-scores.  Events with
``composite >= PUBLISH_THRESHOLD`` are emitted as ``swarm.idea``.

Event contract (``swarm.idea``)::

    {
      "source":            "streaming_discovery",
      "symbol":            "AAPL",
      "discovery_type":    "volume_spike",          # primary detector
      "score":             78.5,                    # composite 0-100
      "price":             195.32,
      "volume":            4200000,
      "anomaly_details":   {...},                   # detector-specific payload
      "bar_timestamp":     "2026-03-08T14:31:00Z",
      "reason":            "Volume spike 4.3x avg; RSI extreme (28.1)",
    }

Usage::

    engine = StreamingDiscoveryEngine(message_bus)
    await engine.start()
    # Runs until:
    await engine.stop()

Singleton accessor::

    from app.services.streaming_discovery_engine import get_streaming_discovery
    engine = get_streaming_discovery()
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tunable constants
# ─────────────────────────────────────────────────────────────────────────────

ROLLING_WINDOW = 50          # Bars kept per symbol for rolling stats
VOLUME_SPIKE_RATIO = 2.5     # vol > ratio × avg_vol → spike
PRICE_SURGE_PCT = 0.015      # |Δ% in bar| > 1.5% → surge
VWAP_DEVIATION_PCT = 0.008   # |price − vwap| / vwap > 0.8% → deviation
RSI_OVERBOUGHT = 75.0        # RSI > 75 → overbought
RSI_OVERSOLD = 25.0          # RSI < 25 → oversold
BB_SQUEEZE_PCT = 0.01        # BB width / price < 1% → squeeze
BB_EXPAND_RATIO = 1.5        # current BB width > ratio × squeeze width → expansion
PUBLISH_THRESHOLD = 55.0     # Composite score to emit swarm.idea
COOLDOWN_SECONDS = 90        # Min seconds between discoveries per symbol

# Sub-score weights (must sum to 1.0)
_WEIGHTS: Dict[str, float] = {
    "volume_spike": 0.30,
    "price_surge": 0.25,
    "vwap_deviation": 0.20,
    "rsi_extreme": 0.15,
    "bb_expansion": 0.10,
}


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Bar:
    """Compact bar snapshot stored in the rolling window."""
    close: float
    open: float
    high: float
    low: float
    volume: float
    timestamp: str = ""


@dataclass
class _SymbolState:
    """Per-symbol rolling state maintained by the engine."""
    bars: Deque[_Bar] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    last_discovery_ts: float = 0.0   # time.time() of last published swarm.idea

    # Bollinger squeeze tracking
    bb_squeeze_width: float = 0.0    # Width at squeeze point (to detect expansion)


# ─────────────────────────────────────────────────────────────────────────────
# Detector helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_rsi(closes: List[float], period: int = 7) -> float:
    """Compute RSI from a list of close prices (fast, period-period).

    Returns 50.0 when insufficient data or when there are no price moves.
    """
    if len(closes) < period + 1:
        return 50.0
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_gain == 0.0 and avg_loss == 0.0:
        return 50.0  # No movement at all — neutral
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_vwap(bars: List[_Bar]) -> float:
    """Compute rolling VWAP estimate from available bars."""
    total_pv = 0.0
    total_vol = 0.0
    for b in bars:
        typical = (b.high + b.low + b.close) / 3.0
        total_pv += typical * b.volume
        total_vol += b.volume
    return total_pv / total_vol if total_vol > 0 else 0.0


def _compute_bb_width(closes: List[float], period: int = 20) -> Tuple[float, float]:
    """Return (middle_band, band_width) using *period* most-recent closes."""
    if len(closes) < period:
        return (0.0, 0.0)
    window = closes[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / period
    std = variance ** 0.5
    return mean, 4.0 * std  # 4σ = 2 std each side


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class StreamingDiscoveryEngine:
    """Listens to market_data.bar and emits swarm.idea for anomalous bars.

    Parameters
    ----------
    message_bus:
        The shared MessageBus instance.
    publish_threshold:
        Minimum composite score (0-100) to emit a swarm.idea event.
    cooldown_seconds:
        Minimum seconds between discoveries for the same symbol.
    """

    def __init__(
        self,
        message_bus,
        publish_threshold: float = PUBLISH_THRESHOLD,
        cooldown_seconds: float = COOLDOWN_SECONDS,
    ) -> None:
        self._bus = message_bus
        self._publish_threshold = publish_threshold
        self._cooldown_seconds = cooldown_seconds

        self._running = False
        self._start_time: Optional[float] = None

        # Per-symbol state
        self._symbols: Dict[str, _SymbolState] = {}

        # Metrics
        self._bars_processed = 0
        self._discoveries_made = 0
        self._cooldowns_skipped = 0
        self._errors = 0

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to market_data.bar and begin anomaly detection."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        await self._bus.subscribe("market_data.bar", self._on_bar)
        logger.info(
            "StreamingDiscoveryEngine started "
            "(threshold=%.0f, cooldown=%ds, window=%d bars)",
            self._publish_threshold,
            self._cooldown_seconds,
            ROLLING_WINDOW,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop."""
        self._running = False
        await self._bus.unsubscribe("market_data.bar", self._on_bar)
        logger.info(
            "StreamingDiscoveryEngine stopped — bars=%d, discoveries=%d, cooldowns=%d",
            self._bars_processed,
            self._discoveries_made,
            self._cooldowns_skipped,
        )

    # ── Core event handler ───────────────────────────────────────────────────

    async def _on_bar(self, bar_data: Dict[str, Any]) -> None:
        """Handle a single market_data.bar event."""
        if not self._running:
            return
        try:
            self._bars_processed += 1
            symbol = bar_data.get("symbol", "")
            if not symbol:
                return

            # Reject bars from mock/simulated sources
            source = bar_data.get("source", "")
            if source and "mock" in source.lower():
                return

            bar = _Bar(
                close=float(bar_data.get("close") or bar_data.get("price") or 0),
                open=float(bar_data.get("open") or bar_data.get("close") or 0),
                high=float(bar_data.get("high") or bar_data.get("close") or 0),
                low=float(bar_data.get("low") or bar_data.get("close") or 0),
                volume=float(bar_data.get("volume") or 0),
                timestamp=str(bar_data.get("timestamp", "")),
            )

            if bar.close <= 0:
                return

            # Update rolling state
            state = self._symbols.setdefault(symbol, _SymbolState())
            state.bars.append(bar)

            # Need a minimum history before scoring
            if len(state.bars) < 5:
                return

            # Per-symbol cooldown check
            now = time.time()
            if now - state.last_discovery_ts < self._cooldown_seconds:
                self._cooldowns_skipped += 1
                return

            # Detect anomalies and compute composite score
            composite, anomaly_details, primary_type, reason_parts = self._detect(
                bar, state
            )

            if composite >= self._publish_threshold:
                state.last_discovery_ts = now
                self._discoveries_made += 1
                await self._publish_discovery(
                    symbol=symbol,
                    bar=bar,
                    composite=composite,
                    primary_type=primary_type,
                    anomaly_details=anomaly_details,
                    reason_parts=reason_parts,
                )
        except Exception as exc:
            self._errors += 1
            logger.debug("StreamingDiscoveryEngine bar error: %s", exc)

    def _detect(
        self,
        bar: _Bar,
        state: _SymbolState,
    ) -> Tuple[float, Dict[str, Any], str, List[str]]:
        """Run all detectors and return (composite, details, primary_type, reasons)."""
        bars_list = list(state.bars)
        closes = [b.close for b in bars_list]
        volumes = [b.volume for b in bars_list]

        sub_scores: Dict[str, float] = {}
        details: Dict[str, Any] = {}
        reason_parts: List[str] = []

        # 1. Volume spike
        avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
        if avg_vol > 0:
            ratio = bar.volume / avg_vol
            if ratio >= VOLUME_SPIKE_RATIO:
                sub_scores["volume_spike"] = min(100.0, (ratio / VOLUME_SPIKE_RATIO) * 60.0)
                details["volume_spike"] = {"ratio": round(ratio, 2), "avg_vol": int(avg_vol)}
                reason_parts.append(f"Volume spike {ratio:.1f}x avg")

        # 2. Price surge
        prev_close = closes[-2] if len(closes) >= 2 else bar.close
        if prev_close > 0:
            pct_change = (bar.close - prev_close) / prev_close
            abs_change = abs(pct_change)
            if abs_change >= PRICE_SURGE_PCT:
                sub_scores["price_surge"] = min(100.0, (abs_change / PRICE_SURGE_PCT) * 55.0)
                details["price_surge"] = {
                    "pct_change": round(pct_change, 4),
                    "direction": "up" if pct_change > 0 else "down",
                }
                reason_parts.append(f"Price surge {pct_change:+.2%}")

        # 3. VWAP deviation
        if len(bars_list) >= 10:
            vwap = _compute_vwap(bars_list[-10:])
            if vwap > 0:
                deviation = abs(bar.close - vwap) / vwap
                if deviation >= VWAP_DEVIATION_PCT:
                    sub_scores["vwap_deviation"] = min(100.0, (deviation / VWAP_DEVIATION_PCT) * 50.0)
                    details["vwap_deviation"] = {
                        "vwap": round(vwap, 2),
                        "deviation_pct": round(deviation, 4),
                        "direction": "above" if bar.close > vwap else "below",
                    }
                    reason_parts.append(f"VWAP deviation {deviation:.2%}")

        # 4. RSI extreme
        rsi = _compute_rsi(closes[-15:] if len(closes) >= 15 else closes)
        if rsi <= RSI_OVERSOLD:
            sub_scores["rsi_extreme"] = min(100.0, (RSI_OVERSOLD - rsi) / RSI_OVERSOLD * 100.0)
            details["rsi_extreme"] = {"rsi": round(rsi, 1), "zone": "oversold"}
            reason_parts.append(f"RSI extreme ({rsi:.1f} oversold)")
        elif rsi >= RSI_OVERBOUGHT:
            sub_scores["rsi_extreme"] = min(100.0, (rsi - RSI_OVERBOUGHT) / (100.0 - RSI_OVERBOUGHT) * 100.0)
            details["rsi_extreme"] = {"rsi": round(rsi, 1), "zone": "overbought"}
            reason_parts.append(f"RSI extreme ({rsi:.1f} overbought)")

        # 5. Bollinger squeeze + expansion
        if len(closes) >= 20:
            mid, width = _compute_bb_width(closes)
            if mid > 0:
                width_pct = width / mid
                if width_pct < BB_SQUEEZE_PCT:
                    state.bb_squeeze_width = width_pct
                elif (
                    state.bb_squeeze_width > 0
                    and width_pct > state.bb_squeeze_width * BB_EXPAND_RATIO
                ):
                    # Expansion after a squeeze
                    expand_ratio = width_pct / state.bb_squeeze_width
                    sub_scores["bb_expansion"] = min(100.0, (expand_ratio - 1.0) * 60.0)
                    details["bb_expansion"] = {
                        "squeeze_width_pct": round(state.bb_squeeze_width, 4),
                        "current_width_pct": round(width_pct, 4),
                        "expand_ratio": round(expand_ratio, 2),
                    }
                    reason_parts.append(f"BB expansion {expand_ratio:.1f}x squeeze")
                    state.bb_squeeze_width = 0.0  # Reset after expansion detected

        if not sub_scores:
            return (0.0, {}, "none", [])

        # Composite score: weight only the triggered detectors proportionally
        total_weight = sum(_WEIGHTS[k] for k in sub_scores)
        composite = sum(sub_scores[k] * _WEIGHTS[k] for k in sub_scores) / total_weight

        # Primary type = highest-scoring detector
        primary_type = max(sub_scores, key=lambda k: sub_scores[k])

        return composite, details, primary_type, reason_parts

    async def _publish_discovery(
        self,
        symbol: str,
        bar: _Bar,
        composite: float,
        primary_type: str,
        anomaly_details: Dict[str, Any],
        reason_parts: List[str],
    ) -> None:
        """Publish a swarm.idea event to the MessageBus."""
        reason = "; ".join(reason_parts) if reason_parts else primary_type
        payload: Dict[str, Any] = {
            "source": "streaming_discovery",
            "symbol": symbol,
            "discovery_type": primary_type,
            "score": round(composite, 1),
            "price": bar.close,
            "volume": int(bar.volume),
            "anomaly_details": anomaly_details,
            "bar_timestamp": bar.timestamp,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self._bus.publish("swarm.idea", payload)
            logger.info(
                "🔍 StreamingDiscovery: %s → %s (score=%.1f) — %s",
                symbol,
                primary_type,
                composite,
                reason,
            )
        except Exception as exc:
            logger.debug("StreamingDiscoveryEngine publish failed: %s", exc)

    # ── Public API ───────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return engine status for monitoring / health checks."""
        uptime = time.time() - self._start_time if self._start_time else 0.0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "symbols_tracked": len(self._symbols),
            "bars_processed": self._bars_processed,
            "discoveries_made": self._discoveries_made,
            "cooldowns_skipped": self._cooldowns_skipped,
            "errors": self._errors,
            "publish_threshold": self._publish_threshold,
            "cooldown_seconds": self._cooldown_seconds,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_status() — consistent with other service naming."""
        return self.get_status()

    @property
    def symbols_tracked(self) -> int:
        return len(self._symbols)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────

_engine_instance: Optional[StreamingDiscoveryEngine] = None


def get_streaming_discovery(message_bus=None) -> StreamingDiscoveryEngine:
    """Return the process-wide StreamingDiscoveryEngine singleton.

    On first call, *message_bus* must be provided.  Subsequent calls
    may omit it.
    """
    global _engine_instance
    if _engine_instance is None:
        if message_bus is None:
            from app.core.message_bus import get_message_bus
            message_bus = get_message_bus()
        _engine_instance = StreamingDiscoveryEngine(message_bus)
    return _engine_instance
