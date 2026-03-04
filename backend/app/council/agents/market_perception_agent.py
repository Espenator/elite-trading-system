"""Market Perception Agent — OHLCV/volume features analysis."""
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "market_perception"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze OHLCV price action and volume to determine market direction."""
    cfg = get_agent_thresholds()
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

    if ret_1d > cfg["return_1d_threshold"]:
        bull_score += 1
    elif ret_1d < -cfg["return_1d_threshold"]:
        bear_score += 1

    if ret_5d > cfg["return_5d_threshold"]:
        bull_score += 1
    elif ret_5d < -cfg["return_5d_threshold"]:
        bear_score += 1

    if ret_20d > cfg["return_20d_threshold"]:
        bull_score += 1
    elif ret_20d < -cfg["return_20d_threshold"]:
        bear_score += 1

    # Volume confirmation
    if vol_surge > cfg["volume_surge_threshold"]:
        if ret_1d > 0:
            bull_score += 1
        else:
            bear_score += 1

    # Near highs/lows
    if pct_from_high > cfg["near_high_threshold"]:
        bull_score += 1
    if pct_from_low < cfg["near_low_threshold"]:
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

    # Enrich with intelligence package if available
    intel_meta = {}
    blackboard = context.get("blackboard")
    if blackboard:
        intel = blackboard.metadata.get("intelligence", {})
        news = intel.get("cortex_news", {})
        if isinstance(news, dict) and news.get("data"):
            news_data = news["data"]
            sentiment = news_data.get("overall_sentiment")
            catalyst_score = news_data.get("catalyst_score", 0)
            if sentiment and catalyst_score > 50:
                if sentiment == "bullish" and direction != "sell":
                    confidence = min(0.95, confidence + 0.05)
                    reasoning += f" | News: {sentiment} (catalyst={catalyst_score})"
                elif sentiment == "bearish" and direction != "buy":
                    confidence = min(0.95, confidence + 0.05)
                    reasoning += f" | News: {sentiment} (catalyst={catalyst_score})"
            intel_meta["news_sentiment"] = sentiment
            intel_meta["catalyst_score"] = catalyst_score

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg["weight_market_perception"],
        metadata=intel_meta if intel_meta else None,
    )
