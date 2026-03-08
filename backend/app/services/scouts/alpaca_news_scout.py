"""AlpacaNewsScout — monitors Alpaca news stream for earnings/catalyst headlines.

Scan cadence: 60 s
Source: Alpaca Markets News API
Signal types: news_catalyst

Discovery criteria
------------------
* News headline contains bullish or bearish catalyst keywords.
* Sentiment scoring applied to headline text.
* Deduplication by headline ID to avoid reprocessing.
"""
from __future__ import annotations

import hashlib
import logging
from collections import deque
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_NEWS_CATALYST,
    SOURCE_ALPACA,
)

logger = logging.getLogger(__name__)

_BULLISH_KEYWORDS = {
    "beat", "beats", "raises", "upgrade", "buy", "outperform", "record",
    "surges", "jumps", "acquisition", "merger", "approval", "approved",
    "breakthrough", "expands", "growth", "profit",
}
_BEARISH_KEYWORDS = {
    "miss", "misses", "cuts", "downgrade", "sell", "underperform", "recall",
    "plunges", "drops", "lawsuit", "investigation", "fraud", "bankruptcy",
    "loss", "layoffs", "warning", "disappoints",
}


class AlpacaNewsScout(BaseScout):
    """Scout that monitors Alpaca's news stream for high-impact catalysts."""

    scout_id = "alpaca_news"
    source = "Alpaca News Stream"
    source_type = SOURCE_ALPACA
    scan_interval = 60.0
    timeout = 25.0

    def __init__(self) -> None:
        super().__init__()
        self._seen_ids: deque = deque(maxlen=2000)
        self._seen_ids_set: set = set()

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            articles = await self._fetch_news()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for article in articles:
            payload = self._evaluate_article(article)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_news(self) -> List[Dict[str, Any]]:
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            news = await svc.get_news(limit=50)
            return news or []
        except Exception:
            return []

    def _evaluate_article(self, article: Dict[str, Any]) -> "DiscoveryPayload | None":
        art_id = str(article.get("id", ""))
        headline = str(article.get("headline", article.get("title", "")) or "")
        symbols = article.get("symbols", []) or []

        if not headline or not symbols:
            return None

        # Dedup using a bounded deque for insertion-ordered eviction
        h = hashlib.md5((art_id or headline).encode()).hexdigest()
        if h in self._seen_ids_set:
            return None
        # Evict oldest entry when the deque is full
        if len(self._seen_ids) == self._seen_ids.maxlen:
            evicted = self._seen_ids[0]
            self._seen_ids_set.discard(evicted)
        self._seen_ids.append(h)
        self._seen_ids_set.add(h)

        words = set(headline.lower().split())
        bull_hits = words & _BULLISH_KEYWORDS
        bear_hits = words & _BEARISH_KEYWORDS
        if not bull_hits and not bear_hits:
            return None

        direction = (
            DIRECTION_BULLISH if len(bull_hits) > len(bear_hits)
            else DIRECTION_BEARISH if len(bear_hits) > len(bull_hits)
            else DIRECTION_NEUTRAL
        )
        score = min(100, (len(bull_hits) + len(bear_hits)) * 20)
        confidence = min(1.0, (len(bull_hits) + len(bear_hits)) * 0.2)
        symbol = symbols[0].upper()

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_NEWS_CATALYST,
            confidence=confidence,
            score=score,
            reasoning=f"News catalyst: {headline[:100]}",
            priority=2,
            related_symbols=[s.upper() for s in symbols[1:5]],
            attributes={
                "headline": headline[:200],
                "bullish_keywords": list(bull_hits),
                "bearish_keywords": list(bear_hits),
                "article_id": art_id,
            },
        )
