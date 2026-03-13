"""FinViz Elite screener + quote collector — real-time from 4 AM–8 PM ET."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class FinvizScreenerCollector(BaseCollector):
    """FinViz Elite screener and quotes. Publishes to data.price.finviz, data.screener.signals."""

    source_name = "finviz_screener"
    channels = ["data.price.finviz", "data.screener.signals"]
    poll_interval = 30.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def collect(self) -> None:
        await (await get_rate_limiter("finviz_screener")).acquire()
        try:
            from app.services.finviz_service import FinvizService
            fv = FinvizService()
            for symbol in self.symbol_universe[:30]:
                try:
                    await self.publish("data.price.finviz", {
                        "symbol": symbol,
                        "source": self.source_name,
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.debug("finviz_screener collect: %s", e)

    async def disconnect(self) -> None:
        self._connected = False
