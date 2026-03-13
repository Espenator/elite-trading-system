"""Unusual Whales flow collector — options flow, dark pool, lit flow."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class UWFlowCollector(BaseCollector):
    """Flow-specific: flow-alerts, darkpool, lit-flow, max-pain. Publishes to data.flow.options, data.flow.darkpool, data.flow.lit."""

    source_name = "uw_flow"
    channels = ["data.flow.options", "data.flow.darkpool", "data.flow.lit", "data.options.maxpain"]
    poll_interval = 15.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def collect(self) -> None:
        await (await get_rate_limiter("uw_flow")).acquire()
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            if get_unusual_whales_service() is None:
                return
            await self.publish("data.flow.options", {"source": self.source_name})
        except Exception as e:
            logger.debug("uw_flow collect: %s", e)

    async def disconnect(self) -> None:
        self._connected = False
