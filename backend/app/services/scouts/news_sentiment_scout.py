"""NewsSentimentScout — aggregates news sentiment across multiple RSS feeds.

Scan cadence: 60 s
Source: RSS feeds (CNBC, Reuters, MarketWatch, Benzinga)
Signal types: news_catalyst

Discovery criteria
------------------
* Headline matches a known ticker symbol.
* Aggregate bullish or bearish keyword score > threshold.
* Deduplication by headline hash to avoid re-processing.
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict, deque
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_NEWS_CATALYST,
    SOURCE_NEWS,
)

logger = logging.getLogger(__name__)

_BULLISH = {"beat", "beats", "raises", "upgrade", "buy", "outperform", "record",
            "surge", "surges", "jumps", "acquisition", "merger", "approval",
            "approved", "breakthrough", "expands", "growth", "profit", "bull",
            "rally", "gains", "strong", "rebound"}
_BEARISH = {"miss", "misses", "cuts", "downgrade", "sell", "underperform",
            "recall", "plunges", "drops", "lawsuit", "investigation", "fraud",
            "bankruptcy", "loss", "layoffs", "warning", "disappoints", "bear",
            "decline", "slump", "weak", "crash"}

# Simple ticker mention pattern: $AAPL or standalone AAPL (3-5 uppercase letters)
_TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{2,5})(?!\w)")

# Known tickers to avoid false positives from common words
_KNOWN_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
    "NFLX", "JPM", "BAC", "GS", "SPY", "QQQ", "COIN", "MSTR", "INTC",
    "CRM", "ORCL", "ADBE", "PYPL", "SQ", "AVGO", "QCOM", "TXN",
}

_MIN_SCORE = 2   # minimum keyword hits to flag


class NewsSentimentScout(BaseScout):
    """Scout that aggregates RSS news sentiment for known ticker symbols."""

    scout_id = "news_sentiment"
    source = "RSS News Sentiment"
    source_type = SOURCE_NEWS
    scan_interval = 60.0
    timeout = 30.0

    def __init__(self) -> None:
        super().__init__()
        self._seen_hashes: deque = deque(maxlen=3000)
        self._seen_hashes_set: set = set()

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            articles = await self._fetch_articles()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        # Aggregate by ticker
        ticker_bull: Dict[str, int] = defaultdict(int)
        ticker_bear: Dict[str, int] = defaultdict(int)
        ticker_headlines: Dict[str, List[str]] = defaultdict(list)

        for article in articles:
            headline = str(article.get("title", article.get("headline", "")) or "")
            if not headline:
                continue
            h = hashlib.md5(headline.encode()).hexdigest()
            if h in self._seen_hashes_set:
                continue
            # Evict oldest entry when deque is full
            if len(self._seen_hashes) == self._seen_hashes.maxlen:
                evicted = self._seen_hashes[0]
                self._seen_hashes_set.discard(evicted)
            self._seen_hashes.append(h)
            self._seen_hashes_set.add(h)

            words = set(headline.lower().split())
            tickers = self._extract_tickers(headline)
            bull_hits = len(words & _BULLISH)
            bear_hits = len(words & _BEARISH)

            for ticker in tickers:
                ticker_bull[ticker] += bull_hits
                ticker_bear[ticker] += bear_hits
                ticker_headlines[ticker].append(headline[:100])

        for ticker, bull in ticker_bull.items():
            bear = ticker_bear[ticker]
            total = bull + bear
            if total < _MIN_SCORE:
                continue

            direction = (
                DIRECTION_BULLISH if bull > bear
                else DIRECTION_BEARISH if bear > bull
                else DIRECTION_NEUTRAL
            )
            score = min(100, total * 15)
            confidence = min(1.0, total * 0.1)
            headlines = ticker_headlines[ticker][:3]

            discoveries.append(DiscoveryPayload(
                scout_id=self.scout_id,
                source=self.source,
                source_type=self.source_type,
                symbol=ticker,
                direction=direction,
                signal_type=SIGNAL_NEWS_CATALYST,
                confidence=confidence,
                score=score,
                reasoning=(
                    f"News sentiment: {bull} bullish / {bear} bearish signals. "
                    f"Sample: {headlines[0] if headlines else 'N/A'}"
                ),
                priority=3,
                attributes={
                    "bullish_count": bull,
                    "bearish_count": bear,
                    "sample_headlines": headlines,
                },
            ))

        return discoveries

    async def _fetch_articles(self) -> List[Dict[str, Any]]:
        try:
            from app.services.news_aggregator import NewsAggregator
            agg = NewsAggregator()
            items = await agg.fetch_all_feeds()
            return items or []
        except Exception:
            return []

    def _extract_tickers(self, text: str) -> List[str]:
        tickers: List[str] = []
        for m in _TICKER_PATTERN.finditer(text):
            t = (m.group(1) or m.group(2) or "").upper()
            if t in _KNOWN_TICKERS:
                tickers.append(t)
        return list(set(tickers))
