"""Market Perception Agent — OHLCV/volume features analysis."""
import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "market_perception"
WEIGHT = 1.0


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze OHLCV price action and volume to determine market direction."""
    f = features.get("features", features)

    # Price momentum signals
    ret_1d = f.get("return_1d", 0)
    ret_5d = f.get("return_5d", 0)
    ret_20d = f.get("return_20d", 0)
    vol_surge = f.get("volume_surge_ratio", 1.0)
    pct_from_high = f.get("pct_from_20d_high", 0)
    pct_from_low = f.get("pct_from_20d_low", 0)

    # Scoring
    bull_score = 0
    bear_score = 0

    if ret_1d > 0.005:
        bull_score += 1
    elif ret_1d < -0.005:
        bear_score += 1

    if ret_5d > 0.01:
        bull_score += 1
    elif ret_5d < -0.01:
        bear_score += 1

    if ret_20d > 0.03:
        bull_score += 1
    elif ret_20d < -0.03:
        bear_score += 1

    # Volume confirmation
    if vol_surge > 1.5:
        if ret_1d > 0:
            bull_score += 1
        else:
            bear_score += 1

    # Near highs/lows
    if pct_from_high > -0.02:
        bull_score += 1
    if pct_from_low < 0.02:
        bear_score += 1

    total = bull_score + bear_score
    if total == 0:
        direction = "hold"
        confidence = 0.3
    elif bull_score > bear_score:
        direction = "buy"
        confidence = min(0.9, 0.4 + bull_score * 0.1)
    elif bear_score > bull_score:
        direction = "sell"
        confidence = min(0.9, 0.4 + bear_score * 0.1)
    else:
        direction = "hold"
        confidence = 0.4

    reasoning = (
        f"Price: 1d={ret_1d:+.2%} 5d={ret_5d:+.2%} 20d={ret_20d:+.2%}, "
        f"Volume surge={vol_surge:.1f}x, "
        f"Bull/Bear={bull_score}/{bear_score}"
    )

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=WEIGHT,
    )
