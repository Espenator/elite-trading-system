from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.services.channels.base_channel_agent import BaseChannelAgent
from app.services.channels.schemas import SensoryEvent

logger = logging.getLogger(__name__)


class AlpacaChannelAgent(BaseChannelAgent):
    """Normalizes existing market_data.bar events into SensoryEvent + anomaly ideas."""

    def __init__(self, *, message_bus: Any, router: Any) -> None:
        super().__init__(
            name="alpaca_firehose",
            router=router,
            message_bus=message_bus,
            max_queue_size=int(os.getenv("ALPACA_FIREHOSE_QUEUE", "5000")),
        )
        self._bus = message_bus
        self._subscribed = False

    async def start(self) -> None:
        await super().start()
        if not self._subscribed:
            await self._bus.subscribe("market_data.bar", self._on_bar)
            self._subscribed = True
            logger.info("AlpacaChannelAgent subscribed to market_data.bar")

    async def _on_bar(self, bar: Dict[str, Any]) -> None:
        aq = os.getenv("ALPACA_ENV", "").strip().lower()
        data_quality = "paper" if aq in ("paper", "sandbox") else "live"

        ev = SensoryEvent.from_alpaca_bar(
            bar,
            data_quality=data_quality,
            provenance={"topic": "market_data.bar"},
        )

        if bar.get("source") == "alpaca_websocket":
            ev.tags.append("stream")
        elif isinstance(bar.get("source"), str) and "snapshot" in str(bar.get("source")):
            ev.tags.append("snapshot")

        await self.enqueue(ev)
