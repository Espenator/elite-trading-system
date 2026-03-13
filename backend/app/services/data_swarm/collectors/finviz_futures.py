"""FinViz futures collector — 20min delayed, gap filler only."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class FinvizFuturesCollector(BaseCollector):
    """FinViz futures (delayed). Publishes to data.futures.finviz."""

    source_name = "finviz_futures"
    channels = ["data.futures.finviz"]
    poll_interval = 300.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def collect(self) -> None:
        await (await get_rate_limiter("finviz_futures")).acquire()
        await self.publish("data.futures.finviz", {
            "source": self.source_name,
            "is_delayed": True,
        })

    async def disconnect(self) -> None:
        self._connected = False
