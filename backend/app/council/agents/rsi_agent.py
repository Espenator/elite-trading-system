"""RSI Agent -- multi-timeframe RSI oversold/overbought with divergence detection.

Inspired by smarttrading.club RSI analysis across daily + hourly timeframes.
Detects RSI slope divergence vs price for early reversal signals.
"""

import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "rsi"
WEIGHT = 1.0


async def evaluate(
    symbol: str,
    timeframe: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
) -> AgentVote:
    """Evaluate RSI across multiple timeframes with divergence detection."""
    f = features.get("features", features)

    rsi_daily = float(f.get("ind_rsi_14", 0) or f.get("rsi_14", 0) or 50)
    rsi_hourly = float(f.get("rsi_hourly", 0) or f.get("ind_rsi_14_1h", 0) or 50)

    ret_1d = float(f.get("return_1d", 0))
    ret_5d = float(f.get("return_5d", 0))

    # RSI slope approximation from context or features
    rsi_prev = float(f.get("rsi_14_prev", 0) or rsi_daily)
    rsi_slope = rsi_daily - rsi_prev if rsi_prev > 0 else 0

    # Divergence: price falling but RSI rising (bullish) or vice versa
    bullish_divergence = ret_5d < -0.01 and rsi_slope > 3
    bearish_divergence = ret_5d > 0.01 and rsi_slope < -3

    # Multi-timeframe scoring
    score = 0
    reasons = []

    # Daily RSI
    if rsi_daily <= 25:
        score += 3
        reasons.append(f"Daily RSI={rsi_daily:.0f} (deeply oversold)")
    elif rsi_daily <= 30:
        score += 2
        reasons.append(f"Daily RSI={rsi_daily:.0f} (oversold)")
    elif rsi_daily >= 75:
        score -= 3
        reasons.append(f"Daily RSI={rsi_daily:.0f} (deeply overbought)")
    elif rsi_daily >= 70:
        score -= 2
        reasons.append(f"Daily RSI={rsi_daily:.0f} (overbought)")
    else:
        reasons.append(f"Daily RSI={rsi_daily:.0f}")

    # Hourly RSI confirmation
    if rsi_hourly > 0 and rsi_hourly != 50:
        if rsi_hourly <= 30:
            score += 1
            reasons.append(f"Hourly RSI={rsi_hourly:.0f} (oversold)")
        elif rsi_hourly >= 70:
            score -= 1
            reasons.append(f"Hourly RSI={rsi_hourly:.0f} (overbought)")

    # Divergence signals (high conviction)
    if bullish_divergence:
        score += 2
        reasons.append("Bullish RSI divergence detected")
    elif bearish_divergence:
        score -= 2
        reasons.append("Bearish RSI divergence detected")

    # Mean-reversion from extremes with momentum confirmation
    if rsi_daily <= 30 and rsi_slope > 0:
        score += 1
        reasons.append("RSI turning up from oversold")
    elif rsi_daily >= 70 and rsi_slope < 0:
        score -= 1
        reasons.append("RSI turning down from overbought")

    # Direction and confidence
    if score >= 3:
        direction = "buy"
        confidence = min(0.85, 0.45 + score * 0.08)
    elif score <= -3:
        direction = "sell"
        confidence = min(0.85, 0.45 + abs(score) * 0.08)
    elif score >= 1:
        direction = "buy"
        confidence = 0.35 + score * 0.05
    elif score <= -1:
        direction = "sell"
        confidence = 0.35 + abs(score) * 0.05
    else:
        direction = "hold"
        confidence = 0.3

    reasoning = "; ".join(reasons[:5])

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning=reasoning,
        weight=WEIGHT,
        metadata={
            "rsi_daily": round(rsi_daily, 1),
            "rsi_hourly": round(rsi_hourly, 1),
            "rsi_slope": round(rsi_slope, 2),
            "score": score,
            "bullish_divergence": bullish_divergence,
            "bearish_divergence": bearish_divergence,
        },
    )
