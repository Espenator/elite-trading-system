"""Social Perception Agent — real-time social sentiment via council spawner.

Aggregates sentiment from StockGeist, News API, Discord, and X/Twitter
using the existing social_news_engine, then votes in the council DAG.

Runs in Stage 1 parallel with market_perception, flow_perception, and regime.
Writes social sentiment context to blackboard for downstream agents.
"""
import logging
from collections import defaultdict
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "social_perception"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Aggregate social sentiment for symbol and vote on market direction."""
    cfg = get_agent_thresholds()

    # Fetch raw social data from all configured sources
    items = _fetch_social_data(symbol)
    if not items:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No social data available (set API keys for StockGeist/News/Discord/X)",
            weight=cfg.get("weight_social_perception", 0.7),
            metadata={"data_available": False, "sources": [], "item_count": 0},
        )

    # Score sentiment
    score, source_breakdown = _score_items(items, symbol)

    # Detect spike from historical data
    spike_msg = _check_spike(symbol, score)

    # Map 0-100 score to direction + confidence
    direction, confidence = _score_to_vote(score, cfg)

    # Spike detection boosts confidence
    if spike_msg:
        if "bullish" in spike_msg and direction == "buy":
            confidence = min(0.9, confidence + 0.1)
        elif "bearish" in spike_msg and direction == "sell":
            confidence = min(0.9, confidence + 0.1)

    sources_used = list(source_breakdown.keys())
    item_count = sum(source_breakdown.values())
    reasoning = (
        f"Social sentiment={score}/100, "
        f"sources={','.join(sources_used)}, "
        f"items={item_count}"
    )
    if spike_msg:
        reasoning += f" | SPIKE: {spike_msg}"

    meta = {
        "data_available": True,
        "sentiment_score": score,
        "sources": sources_used,
        "source_breakdown": source_breakdown,
        "item_count": item_count,
        "spike": spike_msg,
    }

    # Write social context to blackboard for downstream agents
    blackboard = context.get("blackboard")
    if blackboard:
        blackboard.metadata["social_sentiment"] = {
            "score": score,
            "direction": direction,
            "confidence": confidence,
            "sources": sources_used,
            "spike": spike_msg,
            "item_count": item_count,
        }

    # Publish sentiment to message bus for persistence
    try:
        from app.core.message_bus import get_message_bus
        from datetime import datetime
        bus = get_message_bus()
        if bus and items:
            await bus.publish("sentiment.update", {
                "symbol": symbol,
                "source": "social_perception",
                "score": score,
                "headlines_count": item_count,
                "sources": sources_used,
                "spike": spike_msg,
                "timestamp": datetime.utcnow().isoformat(),
            })
    except Exception:
        pass  # Never break council voting

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_social_perception", 0.7),
        metadata=meta,
    )


def _fetch_social_data(symbol: str):
    """Fetch social data for a single symbol from all configured sources."""
    try:
        from app.modules.social_news_engine.aggregators import aggregate_all
        from app.modules.social_news_engine.config import DEFAULT_SOURCES
        return aggregate_all([symbol], DEFAULT_SOURCES)
    except Exception as e:
        logger.debug("Social data fetch failed for %s: %s", symbol, e)
        return []


def _score_items(items, symbol: str):
    """Score sentiment and return (score_0_100, source_breakdown)."""
    from app.modules.social_news_engine.sentiment import score_text, score_to_0_100

    source_breakdown: Dict[str, int] = defaultdict(int)
    texts = []
    sym_upper = symbol.upper()

    for item in items:
        ticker = (item.get("ticker") or "").upper()
        if ticker != sym_upper:
            continue
        text = item.get("text") or ""
        if text:
            texts.append(text)
            source_breakdown[item.get("source", "unknown")] += 1

    if not texts:
        # Use all items if none match the exact symbol (cross-symbol intel)
        for item in items:
            text = item.get("text") or ""
            if text:
                texts.append(text)
                source_breakdown[item.get("source", "unknown")] += 1

    if not texts:
        return 50, dict(source_breakdown)

    combined = " ".join(texts)
    raw = score_text(combined, use_vader=True)
    score = score_to_0_100(raw)
    return score, dict(source_breakdown)


def _check_spike(symbol: str, score: int):
    """Check for unusual sentiment spike using historical data."""
    try:
        from app.modules.social_news_engine.spike import append_score, check_spike
        append_score(symbol, score)
        return check_spike(symbol, score)
    except Exception:
        return None


def _score_to_vote(score: int, cfg: Dict[str, Any]):
    """Map 0-100 sentiment score to (direction, confidence)."""
    bullish_threshold = cfg.get("social_bullish_threshold", 62)
    bearish_threshold = cfg.get("social_bearish_threshold", 38)
    strong_bullish = cfg.get("social_strong_bullish_threshold", 75)
    strong_bearish = cfg.get("social_strong_bearish_threshold", 25)

    if score >= strong_bullish:
        return "buy", 0.75
    elif score >= bullish_threshold:
        return "buy", 0.55
    elif score <= strong_bearish:
        return "sell", 0.75
    elif score <= bearish_threshold:
        return "sell", 0.55
    else:
        return "hold", 0.35
