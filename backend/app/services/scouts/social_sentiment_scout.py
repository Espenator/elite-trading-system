"""SocialSentimentScout — monitors social media momentum (Reddit/StockGeist).

Scan cadence: 120 s
Source: Social sentiment (Reddit, StockGeist, news_aggregator social feeds)
Signal types: social_momentum

Discovery criteria
------------------
* Spike in mention count compared to 7-day rolling average (>= 2x).
* Net sentiment (bull - bear) >= 0.2.
* Only tickers with >= 10 mentions per scan.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_SOCIAL_MOMENTUM,
    SOURCE_SOCIAL,
)

logger = logging.getLogger(__name__)

_MIN_MENTIONS = 10
_MENTION_SPIKE_RATIO = 2.0
_NET_SENTIMENT_THRESHOLD = 0.2


class SocialSentimentScout(BaseScout):
    """Scout that surfaces social sentiment spikes from Reddit and StockGeist."""

    scout_id = "social_sentiment"
    source = "Social Sentiment Monitor"
    source_type = SOURCE_SOCIAL
    scan_interval = 120.0
    timeout = 30.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            data = await self._fetch_social_data()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for entry in data:
            payload = self._evaluate_entry(entry)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_social_data(self) -> List[Dict[str, Any]]:
        # Use the existing social_news_engine if available
        try:
            from app.modules.social_news_engine.sentiment import get_social_sentiment
            return await get_social_sentiment() or []
        except Exception:
            pass
        # Fallback: use news_aggregator's social scraper
        try:
            from app.services.news_aggregator import NewsAggregator
            agg = NewsAggregator()
            items = await agg.fetch_reddit_sentiment()
            return items or []
        except Exception:
            return []

    def _evaluate_entry(self, entry: Dict[str, Any]) -> "DiscoveryPayload | None":
        symbol = str(entry.get("ticker", entry.get("symbol", "")) or "").upper()
        if not symbol:
            return None

        mentions = int(entry.get("mentions", entry.get("count", 0)) or 0)
        avg_mentions = float(entry.get("avg_mentions", entry.get("rolling_avg", mentions)) or 1)
        bull_score = float(entry.get("bullish", entry.get("bull_score", 0)) or 0)
        bear_score = float(entry.get("bearish", entry.get("bear_score", 0)) or 0)

        if mentions < _MIN_MENTIONS:
            return None

        mention_ratio = mentions / max(avg_mentions, 1)
        total = bull_score + bear_score
        net_sentiment = (bull_score - bear_score) / total if total > 0 else 0.0

        if mention_ratio < _MENTION_SPIKE_RATIO and abs(net_sentiment) < _NET_SENTIMENT_THRESHOLD:
            return None

        direction = (
            DIRECTION_BULLISH if net_sentiment > 0
            else DIRECTION_BEARISH if net_sentiment < 0
            else DIRECTION_NEUTRAL
        )
        score = min(100, int(mention_ratio * 20 + abs(net_sentiment) * 50))
        confidence = min(1.0, mention_ratio / 10 * 0.5 + abs(net_sentiment) * 0.5)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_SOCIAL_MOMENTUM,
            confidence=confidence,
            score=score,
            reasoning=(
                f"Social spike: {mentions} mentions ({mention_ratio:.1f}x avg); "
                f"net sentiment {net_sentiment:+.2f}"
            ),
            priority=3,
            attributes={
                "mentions": mentions,
                "avg_mentions": avg_mentions,
                "mention_ratio": round(mention_ratio, 2),
                "bull_score": bull_score,
                "bear_score": bear_score,
                "net_sentiment": round(net_sentiment, 4),
                "source_platform": entry.get("platform", "social"),
            },
        )
