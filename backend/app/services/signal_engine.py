"""
Signal Generation Agent -- technical analysis and composite scores (0-100).

Takes raw data from Market Data Agent (symbol_universe). Optionally uses Finviz
quote data for price. Merges OpenClaw regime + 5-pillar candidate scores when available.
Applies momentum and simple pattern logic; outputs composite signal scores
0-100 for logging and downstream (ML, alerts).

v2: Added EventDrivenSignalEngine class that subscribes to MessageBus events
for <1s latency signal generation. Original run_tick() preserved for backward
compatibility with the Agent Command Center polling loop.
"""
import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from app.modules.symbol_universe import get_tracked_symbols

logger = logging.getLogger(__name__)

AGENT_NAME = "Signal Generation Agent"

# Max symbols to score per tick (avoid rate limits and latency)
DEFAULT_MAX_SYMBOLS = 20
# Min composite score to mention in log (e.g. "above 70")
MIN_SCORE_TO_REPORT = 70

# Regime multipliers: scale final score by market regime from OpenClaw
_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 1.10,
    "RISK_ON": 1.05,
    "NEUTRAL": 1.00,
    "RISK_OFF": 0.90,
    "BEARISH": 0.80,
    "CRISIS": 0.65,
    "UNKNOWN": 1.00,
}

# Bear regime multipliers: boost short signals in bearish conditions
_BEAR_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 0.65,
    "RISK_ON": 0.80,
    "NEUTRAL": 1.00,
    "RISK_OFF": 1.05,
    "BEARISH": 1.10,
    "CRISIS": 1.35,
    "UNKNOWN": 1.00,
}


def _numeric(val, default: float = 0.0) -> float:
    """Parse a value to float; strip commas and $."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("$", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default



def _compute_rsi(closes: List[float], period: int = 14) -> float:
    """Compute RSI (0-100) from close prices. Returns 50 if insufficient data."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_macd(closes: List[float]) -> Tuple[float, float, float]:
    """Compute MACD line, signal line, histogram. Returns (0,0,0) if insufficient data."""
    if len(closes) < 26:
        return 0.0, 0.0, 0.0

    def ema(data, period):
        k = 2.0 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * k + result[-1] * (1 - k))
        return result

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal = ema(macd_line, 9)
    hist = macd_line[-1] - signal[-1]
    return macd_line[-1], signal[-1], hist


def _compute_volume_score(volumes: List[float]) -> float:
    """Score volume relative to 20-period average. >1.5x = bullish confirmation."""
    if not volumes or len(volumes) < 5:
        return 0.0
    avg_vol = sum(volumes[:-1]) / max(1, len(volumes) - 1)
    if avg_vol == 0:
        return 0.0
    rel_vol = volumes[-1] / avg_vol
    return max(-10, min(15, (rel_vol - 1.0) * 20))


def _detect_divergence(closes: List[float], rsi_values: List[float]) -> Tuple[float, str]:
    """Detect bullish/bearish RSI divergence. Returns (score_adjustment, label)."""
    if len(closes) < 10 or len(rsi_values) < 10:
        return 0.0, ""
    price_low1, price_low2 = min(closes[-10:-5]), min(closes[-5:])
    rsi_low1, rsi_low2 = min(rsi_values[-10:-5]), min(rsi_values[-5:])
    if price_low2 < price_low1 and rsi_low2 > rsi_low1:
        return 10.0, "BullDiv"
    price_hi1, price_hi2 = max(closes[-10:-5]), max(closes[-5:])
    rsi_hi1, rsi_hi2 = max(rsi_values[-10:-5]), max(rsi_values[-5:])
    if price_hi2 > price_hi1 and rsi_hi2 < rsi_hi1:
        return -10.0, "BearDiv"
    return 0.0, ""


def _compute_composite_score(quotes: List[dict]) -> Tuple[float, str]:
    """Compute composite signal score 0-100 from quote rows.

    AUDIT NOTE (Task 14): These weights are heuristic, not calibrated against
    historical trade outcomes. The signal engine should cast a wide net — the
    17-agent council is the real intelligence layer. Consider:
    - Lowering the gate threshold (currently 65) to ~55 to avoid filtering out
      opportunities the council would have approved
    - Running a backtest sweep over thresholds 45-75 to find optimal gate
    - Normalizing scores so they have consistent statistical properties
    - Eventually replacing additive weights with a trained classifier

    Current weight breakdown (additive from base 50.0):
      momentum:  ±25 (50% of max movement)
      pattern:   ±15 (bullish/bearish candle)
      range:     ±5  (volatility)
      RSI:       ±10 (oversold/overbought)
      MACD:      ±5  (trend confirmation)
      volume:    ±10 (participation)
    """
    if not quotes or not isinstance(quotes, list):
        return 50.0, "No data"

    rows = []
    for r in quotes:
        if not isinstance(r, dict):
            continue
        row = {}
        for k, v in r.items():
            row[k.strip().lower() if isinstance(k, str) else k] = v
        rows.append(row)

    if not rows:
        return 50.0, "No data"

    last = rows[-1]
    open_val = _numeric(last.get("open"))
    close_val = _numeric(last.get("close"))
    high_val = _numeric(last.get("high"))
    low_val = _numeric(last.get("low"))

    if open_val and open_val > 0:
        momentum_pct = (close_val - open_val) / open_val * 100
        momentum_score = max(-25, min(25, momentum_pct * 0.5))
    else:
        momentum_score = 0.0

    if close_val > open_val:
        pattern_score = 15
        pattern_label = "Bull"
    elif close_val < open_val:
        pattern_score = -15
        pattern_label = "Bear"
    else:
        pattern_score = 0
        pattern_label = "Doji"

    if low_val and low_val > 0 and high_val > low_val:
        range_pct = (high_val - low_val) / low_val * 100
        range_score = max(-5, min(5, (range_pct - 2) * 0.5))
    else:
        range_score = 0.0

    closes = [_numeric(r.get("close")) for r in rows if _numeric(r.get("close")) > 0]
    volumes = [_numeric(r.get("volume")) for r in rows]

    rsi = _compute_rsi(closes) if len(closes) >= 15 else 50.0
    rsi_score = 0.0
    if rsi < 30:
        rsi_score = 10.0
    elif rsi > 70:
        rsi_score = -10.0
    elif rsi < 40:
        rsi_score = 5.0
    elif rsi > 60:
        rsi_score = -5.0

    _, _, macd_hist = _compute_macd(closes)
    macd_score = max(-10, min(10, macd_hist * 100))

    vol_score = _compute_volume_score(volumes)

    rsi_series = []
    if len(closes) >= 15:
        for i in range(14, len(closes)):
            rsi_series.append(_compute_rsi(closes[:i + 1]))
    div_score, div_label = _detect_divergence(closes, rsi_series)

    composite = 50.0 + momentum_score + pattern_score + range_score + rsi_score + macd_score + vol_score + div_score
    composite = max(0.0, min(100.0, composite))

    if pattern_label != "No data":
        label = pattern_label + (f"+{div_label}" if div_label else "") + " candle"
    else:
        label = "Neutral"

    return round(composite, 1), label


def _compute_short_composite_score(quotes: List[dict]) -> Tuple[float, str]:
    """Compute independent short signal score 0-100 from quote rows.

    Unlike the long score, this scores BEARISH setups directly:
    - RSI overbought = short opportunity (not bearish penalty)
    - Bearish candles = confirmation of selling pressure
    - Negative momentum = trend continuation for shorts
    - Bearish divergence = high-conviction reversal short
    - High volume on down bars = distribution signal
    """
    if not quotes or not isinstance(quotes, list):
        return 0.0, "No data"

    rows = []
    for r in quotes:
        if not isinstance(r, dict):
            continue
        row = {}
        for k, v in r.items():
            row[k.strip().lower() if isinstance(k, str) else k] = v
        rows.append(row)

    if not rows:
        return 0.0, "No data"

    last = rows[-1]
    open_val = _numeric(last.get("open"))
    close_val = _numeric(last.get("close"))
    high_val = _numeric(last.get("high"))
    low_val = _numeric(last.get("low"))

    # Negative momentum = bullish for shorts (score increases)
    if open_val and open_val > 0:
        momentum_pct = (close_val - open_val) / open_val * 100
        # Flip: negative momentum = positive short score
        short_momentum = max(-20, min(25, -momentum_pct * 0.5))
    else:
        short_momentum = 0.0

    # Bearish candle patterns = confirmation
    if close_val < open_val:
        pattern_score = 15
        pattern_label = "BearCandle"
    elif close_val > open_val:
        pattern_score = -10  # Bullish candle = bad for shorts
        pattern_label = "BullCandle"
    else:
        pattern_score = 0
        pattern_label = "Doji"

    # Volatility expansion on downside
    if low_val and low_val > 0 and high_val > low_val:
        range_pct = (high_val - low_val) / low_val * 100
        # Wide range + bearish = good for shorts
        range_score = max(-3, min(5, (range_pct - 2) * 0.4))
        if close_val < open_val:
            range_score = abs(range_score)  # Boost if bearish
    else:
        range_score = 0.0

    closes = [_numeric(r.get("close")) for r in rows if _numeric(r.get("close")) > 0]
    volumes = [_numeric(r.get("volume")) for r in rows]

    # RSI: overbought = short opportunity
    rsi = _compute_rsi(closes) if len(closes) >= 15 else 50.0
    rsi_score = 0.0
    if rsi > 75:
        rsi_score = 15.0  # Extreme overbought = strong short signal
    elif rsi > 70:
        rsi_score = 10.0
    elif rsi > 60:
        rsi_score = 3.0
    elif rsi < 30:
        rsi_score = -15.0  # Oversold = bad for shorts

    # MACD: negative histogram = trend confirmation for shorts
    _, _, macd_hist = _compute_macd(closes)
    macd_score = max(-8, min(10, -macd_hist * 80))  # Flip sign

    # Volume on down bars = distribution
    vol_score = 0.0
    if len(volumes) >= 5:
        avg_vol = sum(volumes[:-1]) / max(1, len(volumes) - 1)
        if avg_vol > 0:
            rel_vol = volumes[-1] / avg_vol
            if close_val < open_val:
                # High volume + bearish = distribution
                vol_score = max(0, min(12, (rel_vol - 1.0) * 15))
            else:
                # High volume + bullish = bad for shorts
                vol_score = min(0, max(-8, -(rel_vol - 1.0) * 10))

    # Bearish divergence (price making highs, RSI making lows)
    rsi_series = []
    if len(closes) >= 15:
        for i in range(14, len(closes)):
            rsi_series.append(_compute_rsi(closes[:i + 1]))
    div_score = 0.0
    div_label = ""
    if rsi_series:
        _, dl = _detect_divergence(closes, rsi_series)
        if dl == "BearDiv":
            div_score = 12.0
            div_label = "+BearDiv"

    composite = 50.0 + short_momentum + pattern_score + range_score + rsi_score + macd_score + vol_score + div_score
    composite = max(0.0, min(100.0, composite))

    label = f"SHORT:{pattern_label}{div_label}"
    return round(composite, 1), label


async def _get_openclaw_context() -> Tuple[str, Dict[str, Dict[str, float]]]:
    """Fetch OpenClaw regime + 5-pillar candidate scores."""
    try:
        from app.services.openclaw_bridge_service import openclaw_bridge

        health = await openclaw_bridge.get_health()
        if not health.get("connected"):
            return "UNKNOWN", {}

        regime = await openclaw_bridge.get_regime()
        candidates = await openclaw_bridge.get_top_candidates(n=50)

        regime_state = regime.get("state", "UNKNOWN")
        claw_scores: Dict[str, Dict[str, float]] = {}
        for c in candidates:
            ticker = c.get("ticker")
            score = c.get("composite_score")
            pillars = c.get("pillars", {})
            if ticker and score is not None:
                claw_scores[ticker] = {
                    "score": float(score),
                    "regime": float(pillars.get("regime", 50.0)),
                    "trend": float(pillars.get("trend", 50.0)),
                    "pullback": float(pillars.get("pullback", 50.0)),
                    "momentum": float(pillars.get("momentum", 50.0)),
                    "pattern": float(pillars.get("pattern", 50.0)),
                }

        return regime_state, claw_scores
    except Exception as e:
        logger.debug("OpenClaw context unavailable: %s", e)
        return "UNKNOWN", {}


# =========================================================================
# ORIGINAL POLLING-BASED run_tick() — preserved for Agent Command Center
# =========================================================================

async def run_tick(
    *,
    max_symbols: int = DEFAULT_MAX_SYMBOLS,
    use_quote_data: bool = True,
    use_openclaw: bool = True,
) -> List[Tuple[str, str]]:
    """Run one Signal Generation tick (polling mode — backward compatible)."""
    entries: List[Tuple[str, str]] = []

    symbols = get_tracked_symbols()
    if not symbols:
        entries.append(
            (
                "No symbols from Market Data Agent -- run Agent 1 first or check symbol_universe",
                "warning",
            )
        )
        return entries

    regime_state = "UNKNOWN"
    claw_scores: Dict[str, Dict[str, float]] = {}
    if use_openclaw:
        regime_state, claw_scores = await _get_openclaw_context()
        if claw_scores:
            entries.append(
                (
                    f"OpenClaw overlay: regime={regime_state}, {len(claw_scores)} 5-pillar candidate scores loaded",
                    "info",
                )
            )

    sample = symbols[:max_symbols]
    scored = []
    errors = 0

    finviz_svc = None
    if use_quote_data:
        try:
            from app.services.finviz_service import FinvizService
            finviz_svc = FinvizService()
        except Exception as e:
            logger.warning("Finviz not available for signal engine: %s", e)
            entries.append(
                ("Finviz quote data unavailable (check FINVIZ_API_KEY)", "info")
            )
            use_quote_data = False

    regime_mult = _REGIME_MULTIPLIERS.get(regime_state, 1.0)

    for symbol in sample:
        quotes = []
        if use_quote_data and finviz_svc:
            try:
                quotes = await finviz_svc.get_quote_data(
                    ticker=symbol, timeframe="d", duration="d5",
                )
            except Exception as e:
                logger.debug("Quote fetch failed for %s: %s", symbol, e)
                errors += 1

        ta_score, label = _compute_composite_score(quotes)

        claw_data = claw_scores.get(symbol)
        if claw_data is not None:
            pillar_score = (
                claw_data["regime"] * 0.2
                + claw_data["trend"] * 0.3
                + claw_data["pullback"] * 0.2
                + claw_data["momentum"] * 0.2
                + claw_data["pattern"] * 0.1
            )
            blended = (ta_score * 0.4) + (pillar_score * 0.6)
            label = f"{label}+5Pillars"
        else:
            blended = ta_score

        final_score = max(0.0, min(100.0, blended * regime_mult))
        scored.append((symbol, round(final_score, 1), label))

    scored.sort(key=lambda x: -x[1])
    above = [t for t in scored if t[1] >= MIN_SCORE_TO_REPORT]

    if above:
        top = above[0]
        entries.append(
            (
                f"Generated composite score {int(top[1])} for {top[0]} ({top[2]})",
                "success",
            )
        )

    entries.append(
        (
            f"Momentum algo applied to {len(sample)} symbols, {len(above)} above {MIN_SCORE_TO_REPORT}"
            + (f" ({errors} quote errors)" if errors else "")
            + (f" [regime={regime_state}, mult={regime_mult:.2f}]" if use_openclaw else ""),
            "info",
        )
    )
    return entries


# =========================================================================
# EVENT-DRIVEN SIGNAL ENGINE — subscribes to MessageBus events
# =========================================================================

class EventDrivenSignalEngine:
    """Real-time signal engine that reacts to market_data.bar events.

    Maintains a rolling window of bars per symbol and generates signals
    within <1s of receiving a new bar from the Alpaca WebSocket.

    Publishes signals to 'signal.generated' topic when score >= threshold.
    """

    SIGNAL_THRESHOLD = 65  # Minimum score to publish a signal
    MAX_BAR_HISTORY = 50   # Rolling window per symbol

    def __init__(self, message_bus):
        self.message_bus = message_bus
        self._bar_history: Dict[str, deque] = {}  # symbol -> deque of bar dicts
        self._running = False
        self._signals_generated = 0
        self._bars_processed = 0
        self._start_time: Optional[float] = None
        self._regime_state = "UNKNOWN"
        self._regime_mult = 1.0
        self._claw_scores: Dict[str, Dict[str, float]] = {}
        self._last_regime_refresh: float = 0
        self._regime_refresh_interval = 300  # Refresh OpenClaw every 5 min
        self._bear_regime_mult = 1.0

    async def start(self) -> None:
        """Subscribe to MessageBus events and start processing."""
        self._running = True
        self._start_time = time.time()
        await self.message_bus.subscribe("market_data.bar", self._on_new_bar)
        logger.info(
            "EventDrivenSignalEngine started — subscribed to market_data.bar "
            "(threshold=%d, history=%d bars)",
            self.SIGNAL_THRESHOLD,
            self.MAX_BAR_HISTORY,
        )

    async def stop(self) -> None:
        """Stop processing."""
        self._running = False
        await self.message_bus.unsubscribe("market_data.bar", self._on_new_bar)
        logger.info(
            "EventDrivenSignalEngine stopped — %d signals from %d bars",
            self._signals_generated,
            self._bars_processed,
        )

    async def _on_new_bar(self, data: Dict[str, Any]) -> None:
        """Process a new bar event and generate signal if conditions met."""
        if not self._running:
            return

        symbol = data.get("symbol", "")
        if not symbol:
            return

        self._bars_processed += 1

        # Maintain rolling bar history per symbol
        if symbol not in self._bar_history:
            self._bar_history[symbol] = deque(maxlen=self.MAX_BAR_HISTORY)
        self._bar_history[symbol].append(data)

        # Need at least 5 bars for meaningful analysis
        history = self._bar_history[symbol]
        if len(history) < 5:
            return

        # Periodically refresh OpenClaw regime (every 5 min, not per bar)
        now = time.time()
        if now - self._last_regime_refresh > self._regime_refresh_interval:
            asyncio.create_task(self._refresh_regime())
            self._last_regime_refresh = now

        # Build quote rows from bar history (same format _compute_composite_score expects)
        quote_rows = [
            {
                "open": bar.get("open", 0),
                "high": bar.get("high", 0),
                "low": bar.get("low", 0),
                "close": bar.get("close", 0),
                "volume": bar.get("volume", 0),
            }
            for bar in history
        ]

        ta_score, label = _compute_composite_score(quote_rows)

        # Blend with OpenClaw 5-pillar score if available
        claw_data = self._claw_scores.get(symbol)
        if claw_data is not None:
            pillar_score = (
                claw_data["regime"] * 0.2
                + claw_data["trend"] * 0.3
                + claw_data["pullback"] * 0.2
                + claw_data["momentum"] * 0.2
                + claw_data["pattern"] * 0.1
            )
            blended = (ta_score * 0.4) + (pillar_score * 0.6)
            label = f"{label}+5Pillars"
        else:
            blended = ta_score

        # Blend with ML XGBoost score if model is loaded
        try:
            from app.services.ml_scorer import get_ml_scorer
            ml = get_ml_scorer()
            if ml.is_loaded:
                ml_result = ml.score(symbol, list(history))
                if ml_result:
                    ml_score = ml_result["ml_score"]
                    ml_conf = ml_result["confidence"]
                    # Weight ML by its confidence: high-confidence ML dominates
                    ml_weight = min(0.5, 0.2 + ml_conf * 0.3)  # 0.2-0.5
                    blended = blended * (1 - ml_weight) + ml_score * ml_weight
                    label = f"{label}+ML({ml_result['probability']:.0%})"
        except Exception:
            pass

        final_score = max(0.0, min(100.0, blended * self._regime_mult))

        # Only publish signals above threshold
        if final_score >= self.SIGNAL_THRESHOLD:
            self._signals_generated += 1
            signal_data = {
                "symbol": symbol,
                "score": round(final_score, 1),
                "label": label,
                                "direction": "buy",
                "price": data.get("close", 0),
                "volume": data.get("volume", 0),
                "regime": self._regime_state,
                "regime_mult": self._regime_mult,
                "bar_count": len(history),
                "timestamp": data.get("timestamp", ""),
                "source": "event_driven_signal_engine",
            }
            await self.message_bus.publish("signal.generated", signal_data)

            if final_score >= 80:
                logger.info(
                    "\u26a1 HIGH signal: %s score=%.1f (%s) @ $%.2f [regime=%s]",
                    symbol, final_score, label, data.get("close", 0), self._regime_state,
                )

        # SHORT signal: independent bearish scoring (B2 fix — replaces naive 100-blended inversion)
        short_score_raw, short_label = _compute_short_composite_score(history)
        bear_score = max(0.0, min(100.0, short_score_raw * self._bear_regime_mult))
        if bear_score >= self.SIGNAL_THRESHOLD:
            self._signals_generated += 1
            short_signal_data = {
                "symbol": symbol,
                "score": round(bear_score, 1),
                "label": short_label,
                "direction": "sell",
                "price": data.get("close", 0),
                "volume": data.get("volume", 0),
                "regime": self._regime_state,
                "regime_mult": self._bear_regime_mult,
                "bar_count": len(history),
                "timestamp": data.get("timestamp", ""),
                "source": "event_driven_signal_engine",
            }
            await self.message_bus.publish("signal.generated", short_signal_data)

            if bear_score >= 80:
                logger.info(
                    "\u26a1 HIGH SHORT signal: %s score=%.1f (%s) @ $%.2f [regime=%s]",
                    symbol, bear_score, short_label, data.get("close", 0), self._regime_state,
                )

    async def _refresh_regime(self) -> None:
        """Background refresh of OpenClaw regime context."""
        try:
            self._regime_state, self._claw_scores = await _get_openclaw_context()
            self._regime_mult = _REGIME_MULTIPLIERS.get(self._regime_state, 1.0)
            self._bear_regime_mult = _BEAR_REGIME_MULTIPLIERS.get(self._regime_state, 1.0)
            if self._claw_scores:
                logger.debug(
                    "Regime refreshed: %s (mult=%.2f, %d candidates)",
                    self._regime_state, self._regime_mult, len(self._claw_scores),
                            
                )
        except Exception as e:
            logger.debug("Regime refresh failed: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Return engine status for monitoring."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "bars_processed": self._bars_processed,
            "signals_generated": self._signals_generated,
            "symbols_tracked": len(self._bar_history),
            "signal_threshold": self.SIGNAL_THRESHOLD,
            "regime": self._regime_state,
            "regime_multiplier": self._regime_mult,
            "openclaw_candidates": len(self._claw_scores),
        }
