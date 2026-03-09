"""News Catalyst Agent — breaking news detection via council spawner.

Fetches recent headlines from News API for the target symbol, scores them
for catalyst potential (FDA, M&A, earnings surprises, analyst changes),
and votes on whether a price-moving catalyst exists.

Runs in Stage 1 parallel with the other perception agents.
"""
import logging
import re
from typing import Any, Dict, List

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "news_catalyst"

# High-impact catalyst keywords and their bullish/bearish bias
_BULLISH_CATALYSTS = {
    "fda approval", "fda approves", "beat expectations", "earnings beat",
    "raised guidance", "upgraded", "upgrade", "outperform", "buy rating",
    "acquisition", "acquires", "merger", "partnership", "deal",
    "dividend increase", "buyback", "share repurchase", "record revenue",
    "strong demand", "price target raised", "analyst upgrade",
}
_BEARISH_CATALYSTS = {
    "fda reject", "fda rejects", "missed expectations", "earnings miss",
    "lowered guidance", "downgraded", "downgrade", "underperform", "sell rating",
    "layoffs", "restructuring", "investigation", "lawsuit", "recall",
    "dividend cut", "warning", "going concern", "debt concern",
    "weak demand", "price target cut", "analyst downgrade", "sec probe",
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Fetch recent news for symbol and assess catalyst potential."""
    cfg = get_agent_thresholds()

    headlines = _fetch_headlines(symbol)
    if not headlines:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No news headlines available (set NEWS_API_KEY)",
            weight=cfg.get("weight_news_catalyst", 0.6),
            metadata={"data_available": False, "headline_count": 0},
        )

    # Score each headline for catalyst potential
    bull_catalysts = []
    bear_catalysts = []
    for headline in headlines:
        text_lower = headline.get("text", "").lower()
        for kw in _BULLISH_CATALYSTS:
            if kw in text_lower:
                bull_catalysts.append({"keyword": kw, "headline": headline["text"][:200]})
                break
        for kw in _BEARISH_CATALYSTS:
            if kw in text_lower:
                bear_catalysts.append({"keyword": kw, "headline": headline["text"][:200]})
                break

    total_catalysts = len(bull_catalysts) + len(bear_catalysts)
    headline_count = len(headlines)

    # Determine direction based on catalyst balance
    if total_catalysts == 0:
        direction = "hold"
        confidence = 0.2
        reasoning = f"No catalysts in {headline_count} headlines for {symbol}"
    elif len(bull_catalysts) > len(bear_catalysts):
        direction = "buy"
        confidence = min(0.85, 0.45 + len(bull_catalysts) * 0.1)
        top = bull_catalysts[0]["keyword"]
        reasoning = (
            f"{len(bull_catalysts)} bullish catalysts in {headline_count} headlines "
            f"(top: '{top}')"
        )
    elif len(bear_catalysts) > len(bull_catalysts):
        direction = "sell"
        confidence = min(0.85, 0.45 + len(bear_catalysts) * 0.1)
        top = bear_catalysts[0]["keyword"]
        reasoning = (
            f"{len(bear_catalysts)} bearish catalysts in {headline_count} headlines "
            f"(top: '{top}')"
        )
    else:
        direction = "hold"
        confidence = 0.35
        reasoning = (
            f"Mixed catalysts: {len(bull_catalysts)} bull vs {len(bear_catalysts)} bear "
            f"in {headline_count} headlines"
        )

    # Enrich with Perplexity breaking news if available on blackboard
    blackboard = context.get("blackboard")
    if blackboard:
        intel = blackboard.metadata.get("intelligence", {})
        cortex_news = intel.get("cortex_news", {})
        if isinstance(cortex_news, dict) and cortex_news.get("data"):
            news_data = cortex_news["data"]
            perplexity_sentiment = news_data.get("overall_sentiment")
            catalyst_score = news_data.get("catalyst_score", 0)
            if perplexity_sentiment and catalyst_score > 60:
                # Perplexity confirms catalyst direction
                if perplexity_sentiment == "bullish" and direction in ("buy", "hold"):
                    confidence = min(0.9, confidence + 0.1)
                    reasoning += f" | Perplexity confirms: {perplexity_sentiment} (score={catalyst_score})"
                elif perplexity_sentiment == "bearish" and direction in ("sell", "hold"):
                    confidence = min(0.9, confidence + 0.1)
                    reasoning += f" | Perplexity confirms: {perplexity_sentiment} (score={catalyst_score})"

        # Write catalyst data to blackboard for downstream agents
        await blackboard.set("metadata", "news_catalysts", {
            "direction": direction,
            "confidence": confidence,
            "bullish_count": len(bull_catalysts),
            "bearish_count": len(bear_catalysts),
            "headline_count": headline_count,
            "top_bullish": bull_catalysts[:3],
            "top_bearish": bear_catalysts[:3],
        })

    meta = {
        "data_available": True,
        "headline_count": headline_count,
        "bullish_catalysts": len(bull_catalysts),
        "bearish_catalysts": len(bear_catalysts),
        "top_catalyst": (bull_catalysts or bear_catalysts or [{}])[0].get("keyword"),
    }

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_news_catalyst", 0.6),
        metadata=meta,
    )


def _fetch_headlines(symbol: str) -> List[Dict[str, str]]:
    """Fetch recent headlines from News API for a single symbol."""
    try:
        from app.modules.social_news_engine.aggregators import fetch_news_api
        items = fetch_news_api([symbol], limit_per_symbol=10)
        return [{"text": item.get("text", ""), "timestamp": item.get("timestamp", "")}
                for item in items if item.get("text")]
    except Exception as e:
        logger.debug("News fetch failed for %s: %s", symbol, e)
        return []
