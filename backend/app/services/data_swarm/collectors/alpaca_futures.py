"""Alpaca futures data collector — ES, NQ, YM, RTY, CL, GC, etc."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

FUTURES_SYMBOLS = ["ES", "NQ", "YM", "RTY", "CL", "GC", "SI", "ZB", "DX", "VX"]


class AlpacaFuturesCollector(BaseCollector):
    """Futures data. Publishes to data.futures, data.market_pulse."""

    source_name = "alpaca_futures"
    channels = ["data.futures", "data.market_pulse"]
    poll_interval = 60.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def collect(self) -> None:
        await (await get_rate_limiter("alpaca_rest")).acquire()
        # Alpaca stock data API; futures may require different endpoint. Placeholder publish.
        await self.publish("data.futures", {
            "symbols": FUTURES_SYMBOLS,
            "source": self.source_name,
        })

    async def disconnect(self) -> None:
        self._connected = False
