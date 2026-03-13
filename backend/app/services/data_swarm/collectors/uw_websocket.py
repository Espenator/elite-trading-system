"""Unusual Whales WebSocket collector — price, flow_alerts, gex, news."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class UWWebSocketCollector(BaseCollector):
    """UW WebSocket: price, flow_alerts, gex, news. Publishes to data.price.uw, data.flow.alerts, data.gex, data.news."""

    source_name = "uw_websocket"
    channels = ["data.price.uw", "data.flow.alerts", "data.gex", "data.news"]
    poll_interval = 1.0
    is_streaming = True

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        # TODO: connect to UW WebSocket when endpoint/API is confirmed
        self._connected = True

    async def collect(self) -> None:
        if not self._connected:
            await asyncio.sleep(5)
            return
        await asyncio.sleep(1)

    async def disconnect(self) -> None:
        self._connected = False
