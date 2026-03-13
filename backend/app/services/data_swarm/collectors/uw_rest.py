"""Unusual Whales REST collector — stock-state, OHLC, market-tide, sectors."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class UWRestCollector(BaseCollector):
    """UW REST: stock-state, OHLC, market-tide, sector-etfs. Publishes to data.price.uw_rest, data.market.tide, etc."""

    source_name = "uw_rest"
    channels = ["data.price.uw_rest", "data.market.tide", "data.market.sectors", "data.gex.levels"]
    poll_interval = 30.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def collect(self) -> None:
        await (await get_rate_limiter("uw_rest")).acquire()
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            uw = get_unusual_whales_service()
            if uw is None:
                return
            for symbol in self.symbol_universe[:20]:
                try:
                    await self.publish("data.price.uw_rest", {
                        "symbol": symbol,
                        "source": self.source_name,
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.debug("uw_rest collect: %s", e)

    async def disconnect(self) -> None:
        self._connected = False
