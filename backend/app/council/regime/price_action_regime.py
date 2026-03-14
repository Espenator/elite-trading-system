"""Price-Action Regime Fallback — classifies market regime using SPY OHLCV data.

When the Bayesian engine lacks VIX/macro inputs and the HMM model hasn't been
trained, this module provides a simple but effective regime classification
using only SPY daily bars from DuckDB.

Metrics used:
    - Trend: price vs 20 SMA and 50 SMA
    - Volatility: ATR percentile over lookback window
    - Drawdown: % from rolling 252-day high
    - Breadth proxy: % of recent bars that closed up

Returns one of: BULLISH, BEARISH, SIDEWAYS, CRISIS, UNKNOWN

Issue #60: Market regime stuck at UNKNOWN — this is the fallback.
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Regime labels compatible with the rest of the system
REGIMES = ("BULLISH", "BEARISH", "SIDEWAYS", "CRISIS", "UNKNOWN")

# Map price-action regimes to Bayesian-style state names for beliefs dict
_PA_TO_BAYESIAN = {
    "BULLISH": "trending_bull",
    "BEARISH": "trending_bear",
    "SIDEWAYS": "mean_revert",
    "CRISIS": "high_vol_crisis",
    "UNKNOWN": "transition",
}

# Map price-action regimes to OpenClaw color codes
_PA_TO_OPENCLAW = {
    "BULLISH": "GREEN",
    "BEARISH": "RED",
    "SIDEWAYS": "YELLOW",
    "CRISIS": "RED",
    "UNKNOWN": "YELLOW",
}


def _fetch_spy_bars_from_duckdb(limit: int = 260) -> Optional[list]:
    """Fetch recent SPY daily bars from DuckDB (synchronous — call via to_thread).

    Returns list of dicts with keys: date, open, high, low, close, volume.
    Returns None if data is unavailable.
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        cur = duckdb_store.get_thread_cursor()
        try:
            rows = cur.execute(
                """
                SELECT date, open, high, low, close, volume
                FROM daily_ohlcv
                WHERE symbol = 'SPY'
                ORDER BY date DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        finally:
            cur.close()

        if not rows:
            return None

        # Reverse to chronological order (oldest first)
        rows = rows[::-1]
        return [
            {
                "date": r[0],
                "open": float(r[1]) if r[1] is not None else 0.0,
                "high": float(r[2]) if r[2] is not None else 0.0,
                "low": float(r[3]) if r[3] is not None else 0.0,
                "close": float(r[4]) if r[4] is not None else 0.0,
                "volume": int(r[5]) if r[5] is not None else 0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error("price_action_regime: DuckDB query failed: %s", e)
        return None


def classify_regime_from_price_action(
    bars: list,
) -> Tuple[str, float, Dict]:
    """Classify market regime from SPY OHLCV bars.

    Args:
        bars: List of dicts with keys: open, high, low, close, volume.
              Must be in chronological order (oldest first).
              Needs at least 50 bars for reliable classification.

    Returns:
        Tuple of (regime_label, confidence, details_dict)
    """
    if not bars or len(bars) < 20:
        return "UNKNOWN", 0.0, {"error": "insufficient data", "bar_count": len(bars) if bars else 0}

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    n = len(closes)

    # ── 1. Trend: price vs 20 SMA and 50 SMA ──────────────────────────
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes[-min(50, n):]) / min(50, n)
    current_price = closes[-1]

    above_sma20 = current_price > sma_20
    above_sma50 = current_price > sma_50
    sma20_above_sma50 = sma_20 > sma_50

    # Trend score: -1 (strong bearish) to +1 (strong bullish)
    trend_score = 0.0
    if above_sma20:
        trend_score += 0.33
    else:
        trend_score -= 0.33
    if above_sma50:
        trend_score += 0.33
    else:
        trend_score -= 0.33
    if sma20_above_sma50:
        trend_score += 0.34
    else:
        trend_score -= 0.34

    # ── 2. Volatility: ATR percentile ──────────────────────────────────
    # Calculate 14-period ATR for the full history
    atrs = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        atrs.append(tr)

    if len(atrs) >= 14:
        # Current ATR (14-period average)
        current_atr = sum(atrs[-14:]) / 14
        # ATR as percentage of price
        atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0

        # Percentile rank of current ATR vs all ATRs
        atr_pcts = [(a / closes[i + 1]) * 100 if closes[i + 1] > 0 else 0 for i, a in enumerate(atrs)]
        below_count = sum(1 for a in atr_pcts if a <= atr_pct)
        atr_percentile = below_count / len(atr_pcts) if atr_pcts else 0.5
    else:
        atr_pct = 0.0
        atr_percentile = 0.5

    # ── 3. Drawdown from rolling high ──────────────────────────────────
    lookback_252 = min(252, n)
    rolling_high = max(highs[-lookback_252:])
    drawdown_pct = ((current_price - rolling_high) / rolling_high) * 100 if rolling_high > 0 else 0

    # ── 4. Breadth proxy: % of last 20 bars that closed up ────────────
    recent_n = min(20, n - 1)
    up_bars = sum(1 for i in range(n - recent_n, n) if closes[i] > closes[i - 1])
    up_ratio = up_bars / recent_n if recent_n > 0 else 0.5

    # ── Classification logic ───────────────────────────────────────────
    regime = "SIDEWAYS"
    confidence = 0.5

    # CRISIS: deep drawdown + high volatility
    if drawdown_pct < -10 and atr_percentile > 0.80:
        regime = "CRISIS"
        confidence = min(0.95, 0.6 + abs(drawdown_pct) / 100 + (atr_percentile - 0.8))
    # BEARISH: negative trend + drawdown
    elif trend_score < -0.3 and drawdown_pct < -5:
        regime = "BEARISH"
        confidence = min(0.90, 0.5 + abs(trend_score) * 0.3 + abs(drawdown_pct) / 50)
    # BULLISH: positive trend + limited drawdown + decent breadth
    elif trend_score > 0.3 and drawdown_pct > -5 and up_ratio > 0.45:
        regime = "BULLISH"
        confidence = min(0.90, 0.5 + trend_score * 0.3 + up_ratio * 0.2)
    # SIDEWAYS: weak trend, moderate everything
    else:
        regime = "SIDEWAYS"
        # Confidence is higher when metrics are truly mixed
        confidence = 0.5 + (1.0 - abs(trend_score)) * 0.2

    confidence = round(max(0.1, min(confidence, 0.95)), 4)

    details = {
        "source": "price_action_fallback",
        "bar_count": n,
        "current_price": round(current_price, 2),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "trend_score": round(trend_score, 4),
        "atr_pct": round(atr_pct, 4),
        "atr_percentile": round(atr_percentile, 4),
        "drawdown_pct": round(drawdown_pct, 2),
        "up_ratio_20": round(up_ratio, 4),
        "rolling_high_252": round(rolling_high, 2),
    }

    return regime, confidence, details


async def get_price_action_regime() -> Dict:
    """Async entry point: fetch SPY bars from DuckDB and classify regime.

    Uses asyncio.to_thread for the DuckDB query to avoid blocking the event loop.

    Returns:
        Dict with regime, confidence, beliefs, details, and source info.
    """
    try:
        bars = await asyncio.to_thread(_fetch_spy_bars_from_duckdb, 260)
        if not bars or len(bars) < 20:
            logger.warning(
                "price_action_regime: insufficient SPY bars (%d) — need at least 20",
                len(bars) if bars else 0,
            )
            return {
                "regime": "UNKNOWN",
                "confidence": 0.0,
                "beliefs": {},
                "details": {"error": "insufficient SPY data in DuckDB"},
                "source": "price_action_fallback",
            }

        regime, confidence, details = classify_regime_from_price_action(bars)

        # Build beliefs dict compatible with BayesianRegime format
        beliefs = {
            "trending_bull": 0.0,
            "trending_bear": 0.0,
            "mean_revert": 0.0,
            "high_vol_crisis": 0.0,
            "low_vol_grind": 0.0,
            "transition": 0.0,
        }
        # Assign confidence to the matching Bayesian state
        bayesian_state = _PA_TO_BAYESIAN.get(regime, "transition")
        beliefs[bayesian_state] = confidence
        # Distribute remaining probability
        remaining = 1.0 - confidence
        other_states = [s for s in beliefs if s != bayesian_state]
        for s in other_states:
            beliefs[s] = round(remaining / len(other_states), 4)

        openclaw_color = _PA_TO_OPENCLAW.get(regime, "YELLOW")

        logger.info(
            "price_action_regime: %s (conf=%.1f%%) | SPY=%.2f | dd=%.1f%% | trend=%.2f | atr_pctl=%.0f%%",
            regime,
            confidence * 100,
            details.get("current_price", 0),
            details.get("drawdown_pct", 0),
            details.get("trend_score", 0),
            details.get("atr_percentile", 0) * 100,
        )

        return {
            "regime": regime,
            "confidence": confidence,
            "beliefs": beliefs,
            "details": details,
            "source": "price_action_fallback",
            "openclaw_color": openclaw_color,
        }

    except Exception as e:
        logger.error("price_action_regime: failed: %s", e)
        return {
            "regime": "UNKNOWN",
            "confidence": 0.0,
            "beliefs": {},
            "details": {"error": str(e)},
            "source": "price_action_fallback",
        }
