"""Unusual Whales channel agent: normalizes UW flow/congress/insider/darkpool into SensoryEvent."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.services.channels.base_channel_agent import BaseChannelAgent
from app.services.channels.schemas import SensoryEvent

logger = logging.getLogger(__name__)

UW_TOPICS = (
    "unusual_whales.flow",
    "unusual_whales.congress",
    "unusual_whales.insider",
    "unusual_whales.darkpool",
)


class UWChannelAgent(BaseChannelAgent):
    """Subscribes to Unusual Whales bus topics and enqueues SensoryEvents for the router."""

    def __init__(self, *, message_bus: Any, router: Any) -> None:
        super().__init__(
            name="uw_firehose",
            router=router,
            message_bus=message_bus,
            max_queue_size=int(os.getenv("UW_FIREHOSE_QUEUE", "3000")),
            batch_size=int(os.getenv("UW_FIREHOSE_BATCH", "16")),
        )
        self._bus = message_bus
        self._subscribed = False

    async def start(self) -> None:
        await super().start()
        if not self._subscribed:
            for topic in UW_TOPICS:
                await self._bus.subscribe(topic, self._on_uw_event)
            self._subscribed = True
            logger.info("UWChannelAgent subscribed to %s", list(UW_TOPICS))

    async def _on_uw_event(self, payload: Dict[str, Any]) -> None:
        try:
            ev = SensoryEvent.from_uw_source_event(payload, data_quality="live")
            await self.enqueue(ev)
        except Exception as e:
            logger.debug("UWChannelAgent skip event: %s", e)
