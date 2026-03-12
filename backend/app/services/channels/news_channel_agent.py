"""News channel agent: wraps NewsAggregator and normalizes items into SensoryEvent."""
from __future__ import annotations

import logging
import os
from typing import Any

from app.services.channels.base_channel_agent import BaseChannelAgent
from app.services.channels.schemas import SensoryEvent
from app.services.news_aggregator import NewsAggregator, NewsItem

logger = logging.getLogger(__name__)


class NewsChannelAgent(BaseChannelAgent):
    """Runs NewsAggregator with a callback that enqueues each actionable item as SensoryEvent."""

    def __init__(self, *, message_bus: Any, router: Any) -> None:
        super().__init__(
            name="news_firehose",
            router=router,
            message_bus=message_bus,
            max_queue_size=int(os.getenv("NEWS_FIREHOSE_QUEUE", "2000")),
            batch_size=int(os.getenv("NEWS_FIREHOSE_BATCH", "8")),
        )
        self._bus = message_bus
        self._aggregator = NewsAggregator(
            message_bus=message_bus,
            on_news_item=self._on_news_item,
            publish_to_bus=False,
        )

    async def start(self) -> None:
        await super().start()
        self._aggregator._bus = self._bus
        await self._aggregator.start()
        logger.info("NewsChannelAgent started (aggregator polling active)")

    async def stop(self) -> None:
        try:
            await self._aggregator.stop()
        except Exception:
            pass
        await super().stop()

    async def _on_news_item(self, item: NewsItem) -> None:
        try:
            ev = SensoryEvent.from_news_item(
                headline=item.headline,
                source=item.source,
                symbols=item.symbols,
                url=item.url,
                sentiment=item.sentiment,
                urgency=item.urgency,
                sentiment_score=item.sentiment_score,
                published_at=item.published_at,
                hash_id=item.hash_id,
                data_quality="live",
            )
            await self.enqueue(ev)
        except Exception as e:
            logger.debug("NewsChannelAgent skip item: %s", e)
