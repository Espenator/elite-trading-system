"""Relative Strength Agent — ticker vs benchmark performance ranking.

Inspired by smarttrading.club Strong/Weak ETFs, Quarterly Strength,
Top Gainers/Losers tables. Computes excess returns vs SPY,
relative strength trend, and momentum classification.
"""

import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "relative_strength"
WEIGHT = 1.0


async def evaluate(
    symbol: str,
    timeframe: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
) -> AgentVote:
    """Evaluate relative strength vs benchmark and peers."""
    f = features.get("features", features)

    ret_5d = float(f.get("return_5d", 0))
    ret_20d = float(f.get("return_20d", 0))
    ret_60d = float(f.get("return_60d", 0) or f.get("return_3m", 0))

    bench_ret_5d = float(f.get("spy_return_5d", 0) or f.get("bench_return_5d", 0))
    bench_ret_20d = float(f.get("spy_return_20d", 0) or f.get("bench_return_20d", 0))
    bench_ret_60d = float(f.get("spy_return_60d", 0) or f.get("bench_return_60d", 0))

    # Peer ranking (percentile 0-1 within sector/universe)
    peer_percentile = float(f.get("peer_percentile_20d", 0.5))

    # Relative strength line slope
    rs_slope = float(f.get("rs_line_slope", 0))

    # Excess returns
    excess_5d = ret_5d - bench_ret_5d
    excess_20d = ret_20d - bench_ret_20d
    excess_60d = ret_60d - bench_ret_60d

    # Momentum classification
    if ret_5d > 0 and ret_20d > 0 and ret_60d > 0:
        if ret_5d > ret_20d > ret_60d:
            momentum = "accelerating"
        else:
            momentum = "strong"
    elif ret_5d < 0 and ret_20d < 0 and ret_60d < 0:
        if ret_5d < ret_20d < ret_60d:
            momentum = "deteriorating"
        else:
            momentum = "weak"
    elif ret_5d > 0 and ret_60d < 0:
        momentum = "recovering"
    elif ret_5d < 0 and ret_60d > 0:
        momentum = "fading"
    else:
        momentum = "mixed"

    score = 0
    reasons = []

    # Top/bottom performer
    if peer_percentile >= 0.8:
        score += 2
        reasons.append(f"Top performer: {peer_percentile:.0%} percentile")
    elif peer_percentile >= 0.6:
        score += 1
        reasons.append(f"Above avg: {peer_percentile:.0%} percentile")
    elif peer_percentile <= 0.2:
        score -= 2
        reasons.append(f"Bottom performer: {peer_percentile:.0%} percentile")
    elif peer_percentile <= 0.4:
        score -= 1
        reasons.append(f"Below avg: {peer_percentile:.0%} percentile")

    # Excess returns
    if excess_20d > 0.03:
        score += 1
        reasons.append(f"Excess 20d={excess_20d:+.1%} (outperforming)")
    elif excess_20d < -0.03:
        score -= 1
        reasons.append(f"Excess 20d={excess_20d:+.1%} (underperforming)")

    # RS line trend
    if rs_slope > 0.001:
        score += 1
        reasons.append("RS line trending up")
    elif rs_slope < -0.001:
        score -= 1
        reasons.append("RS line trending down")

    # Momentum classification
    momentum_scores = {
        "accelerating": 2, "strong": 1, "recovering": 1,
        "deteriorating": -2, "weak": -1, "fading": -1,
        "mixed": 0,
    }
    m_score = momentum_scores.get(momentum, 0)
    score += m_score
    reasons.append(f"Momentum={momentum}")

    if score >= 3:
        direction = "buy"
        confidence = min(0.85, 0.4 + score * 0.07)
    elif score <= -3:
        direction = "sell"
        confidence = min(0.85, 0.4 + abs(score) * 0.07)
    elif score >= 1:
        direction = "buy"
        confidence = 0.35 + score * 0.05
    elif score <= -1:
        direction = "sell"
        confidence = 0.35 + abs(score) * 0.05
    else:
        direction = "hold"
        confidence = 0.3

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning="; ".join(reasons[:5]),
        weight=WEIGHT,
        metadata={
            "momentum": momentum,
            "peer_percentile": round(peer_percentile, 3),
            "excess_5d": round(excess_5d, 4),
            "excess_20d": round(excess_20d, 4),
            "excess_60d": round(excess_60d, 4),
            "rs_slope": round(rs_slope, 6),
            "score": score,
        },
    )
