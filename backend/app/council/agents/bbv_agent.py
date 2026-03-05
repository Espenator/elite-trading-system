"""BBV Agent -- Bollinger Band %B value for mean-reversion signals.

Inspired by smarttrading.club BBV (Bollinger Band Value) analysis.
Measures price position within bands on daily + hourly timeframes.
Generates mean-reversion signals at extreme band positions.
"""

import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "bbv"
WEIGHT = 0.9


async def evaluate(
    symbol: str,
    timeframe: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
) -> AgentVote:
    """Evaluate Bollinger Band position for mean-reversion opportunities."""
    f = features.get("features", features)

    last_close = float(f.get("last_close", 0))
    bb_upper = float(f.get("ind_bb_upper", 0) or f.get("bb_upper_20", 0))
    bb_lower = float(f.get("ind_bb_lower", 0) or f.get("bb_lower_20", 0))
    bb_mid = float(f.get("ind_bb_middle", 0) or f.get("ind_sma_20", 0))
    std_dev = float(f.get("ind_std_20", 0) or f.get("daily_std_dev", 0))

    ret_1d = float(f.get("return_1d", 0))
    ret_5d = float(f.get("return_5d", 0))
    rsi = float(f.get("ind_rsi_14", 50))

    # Calculate %B (position within Bollinger Bands)
    bb_width = bb_upper - bb_lower
    if bb_width > 0 and last_close > 0:
        pct_b = (last_close - bb_lower) / bb_width
    else:
        pct_b = 0.5

    # Bandwidth (volatility measure)
    bandwidth = bb_width / bb_mid if bb_mid > 0 else 0

    score = 0
    reasons = []

    # Extreme band positions (mean-reversion)
    if pct_b <= 0.0:
        score += 3
        reasons.append(f"%B={pct_b:.2f} (below lower band)")
    elif pct_b <= 0.15:
        score += 2
        reasons.append(f"%B={pct_b:.2f} (near lower band)")
    elif pct_b >= 1.0:
        score -= 3
        reasons.append(f"%B={pct_b:.2f} (above upper band)")
    elif pct_b >= 0.85:
        score -= 2
        reasons.append(f"%B={pct_b:.2f} (near upper band)")
    else:
        reasons.append(f"%B={pct_b:.2f} (mid-band)")

    # RSI confirmation for extremes
    if pct_b <= 0.15 and rsi <= 35:
        score += 1
        reasons.append("RSI confirms oversold")
    elif pct_b >= 0.85 and rsi >= 65:
        score -= 1
        reasons.append("RSI confirms overbought")

    # Bandwidth squeeze detection (low vol -> expansion coming)
    if bandwidth < 0.04:
        reasons.append(f"BB squeeze (bw={bandwidth:.3f}) - breakout pending")
    elif bandwidth > 0.12:
        reasons.append(f"Wide bands (bw={bandwidth:.3f}) - high volatility")

    # Trend context: don't fade strong trends
    if ret_5d > 0.05 and pct_b >= 0.85:
        score = max(score, -1)
        reasons.append("Strong uptrend - reduced sell signal")
    elif ret_5d < -0.05 and pct_b <= 0.15:
        score = min(score, 1)
        reasons.append("Strong downtrend - reduced buy signal")

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
            "pct_b": round(pct_b, 3),
            "bandwidth": round(bandwidth, 4),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "score": score,
        },
    )
