"""Finviz channel agent: normalizes screener results into SensoryEvent."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.services.channels.base_channel_agent import BaseChannelAgent
from app.services.channels.schemas import SensoryEvent

logger = logging.getLogger(__name__)

FINVIZ_TOPICS = ("finviz.screener", "perception.finviz.screener")


class FinvizChannelAgent(BaseChannelAgent):
    """Subscribes to Finviz screener bus topics and enqueues SensoryEvents."""

    def __init__(self, *, message_bus: Any, router: Any) -> None:
        super().__init__(
            name="finviz_firehose",
            router=router,
            message_bus=message_bus,
            max_queue_size=int(os.getenv("FINVIZ_FIREHOSE_QUEUE", "2000")),
            batch_size=int(os.getenv("FINVIZ_FIREHOSE_BATCH", "16")),
        )
        self._bus = message_bus
        self._subscribed = False

    async def start(self) -> None:
        await super().start()
        if not self._subscribed:
            for topic in FINVIZ_TOPICS:
                await self._bus.subscribe(topic, self._on_finviz_event)
            self._subscribed = True
            logger.info("FinvizChannelAgent subscribed to %s", list(FINVIZ_TOPICS))

    async def _on_finviz_event(self, payload: Dict[str, Any]) -> None:
        try:
            if (payload.get("topic") or "").strip() == "finviz.screener" or "symbol" in payload:
                ev = SensoryEvent.from_finviz_source_event(payload, data_quality="live")
                await self.enqueue(ev)
            elif payload.get("type") == "finviz_screener_results" and "results" in payload:
                for row in payload.get("results") or []:
                    sym = (row.get("Ticker") or row.get("ticker") or "").strip().upper()
                    if not sym:
                        continue
                    ev = SensoryEvent.from_finviz_source_event(
                        {
                            "topic": "perception.finviz.screener",
                            "source": "finviz",
                            "source_kind": "screener",
                            "symbol": sym,
                            "payload_json": row,
                        },
                        data_quality="live",
                    )
                    await self.enqueue(ev)
        except Exception as e:
            logger.debug("FinvizChannelAgent skip event: %s", e)
