"""NewsScout — Alpaca real-time news stream, subscribes via MessageBus."""
import logging
from typing import List, Optional

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

# News keywords that raise priority
HIGH_PRIORITY_KEYWORDS = {
    "earnings", "beat", "miss", "guidance", "fda", "approval",
    "merger", "acquisition", "buyout", "takeover", "upgrade", "downgrade",
    "bankruptcy", "fraud", "recall", "lawsuit", "settlement",
}


class NewsScout(BaseScout):
    """Subscribes to market news events and converts them to discoveries.

    Unlike other scouts, this one doesn't poll — it receives news via
    the MessageBus ``market_data.bar`` channel and also via the news
    aggregator if available.  The ``interval`` is used for a fallback
    poll of the aggregator only.
    """

    def __init__(self, message_bus=None):
        super().__init__(message_bus)
        self._pending: List[DiscoveryPayload] = []
        self._subscribed = False

    @property
    def name(self) -> str:
        return "news_scout"

    @property
    def interval(self) -> float:
        return 60.0  # fallback poll interval

    async def start(self) -> None:
        # Subscribe to news topic before starting the loop
        if self._bus and not self._subscribed:
            try:
                await self._bus.subscribe("perception.unusualwhales", self._on_news_event)
                self._subscribed = True
            except Exception as exc:
                logger.debug("NewsScout: subscribe error: %s", exc)
        await super().start()

    async def _on_news_event(self, data: dict) -> None:
        """Handle incoming news events from the bus."""
        headline = data.get("headline", data.get("title", data.get("summary", "")))
        symbols = data.get("symbols", data.get("tickers", []))
        if not symbols or not headline:
            return
        if isinstance(symbols, str):
            symbols = [symbols]
        priority = self._score_headline(headline)
        payload = DiscoveryPayload(
            source=self.name,
            symbols=list(symbols)[:5],
            direction="neutral",
            reasoning=f"News catalyst: {headline[:120]}",
            priority=priority,
            metadata={"headline": headline[:300], "source": data.get("source", "news")},
        )
        self._pending.append(payload)

    def _score_headline(self, headline: str) -> int:
        lower = headline.lower()
        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw in lower:
                return 2
        return 4

    async def scout(self) -> List[DiscoveryPayload]:
        # Drain pending events collected via subscription
        payloads = list(self._pending)
        self._pending.clear()

        # Fallback: poll news aggregator
        try:
            from app.services.news_aggregator import get_news_aggregator
            agg = get_news_aggregator()
            items = await agg.get_latest(limit=10)
            for item in items or []:
                headline = item.get("headline", item.get("title", ""))
                symbols = item.get("symbols", item.get("tickers", []))
                if not headline or not symbols:
                    continue
                if isinstance(symbols, str):
                    symbols = [symbols]
                payloads.append(DiscoveryPayload(
                    source=self.name,
                    symbols=list(symbols)[:5],
                    direction="neutral",
                    reasoning=f"News: {headline[:120]}",
                    priority=self._score_headline(headline),
                    metadata={"headline": headline[:300]},
                ))
        except Exception as exc:
            logger.debug("NewsScout fallback poll failed: %s", exc)

        return payloads
