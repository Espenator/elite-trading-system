"""SentimentScout — social sentiment spikes, 60-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

SENTIMENT_SPIKE_THRESHOLD = 0.7   # Compound score magnitude
MENTION_SPIKE_MULTIPLIER = 3.0    # 3× normal mention velocity


class SentimentScout(BaseScout):
    """Monitors StockGeist, Reddit, and social sentiment spikes."""

    @property
    def name(self) -> str:
        return "sentiment_scout"

    @property
    def interval(self) -> float:
        return 60.0

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.finviz_service import get_finviz_service
            svc = get_finviz_service()
            trending = await svc.get_trending_tickers(limit=10)
        except Exception as exc:
            logger.debug("SentimentScout: finviz error: %s", exc)
            trending = []

        for item in trending or []:
            symbol = item.get("ticker", item.get("symbol", ""))
            if not symbol:
                continue
            score = float(item.get("sentiment", item.get("score", 0)))
            mention_change = float(item.get("mention_change", 0))
            if abs(score) < SENTIMENT_SPIKE_THRESHOLD and mention_change < MENTION_SPIKE_MULTIPLIER:
                continue
            direction = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=(
                    f"Sentiment spike: {symbol} score={score:.2f}, "
                    f"mention_change={mention_change:.1f}×"
                ),
                priority=3,
                metadata={"sentiment_score": score, "mention_change": mention_change},
            ))
        return payloads
