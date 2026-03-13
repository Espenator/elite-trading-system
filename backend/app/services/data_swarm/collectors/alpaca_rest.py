"""Alpaca REST snapshot collector — fallback when WebSocket is down."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.rate_limiter import get_rate_limiter
from app.services.data_swarm.session_clock import get_session_clock, TradingSession

logger = logging.getLogger(__name__)


class AlpacaRestCollector(BaseCollector):
    """REST snapshot polling. GET /v2/stocks/snapshots. Publishes to data.price.snapshot, data.bars.history."""

    source_name = "alpaca_rest"
    channels = ["data.price.snapshot", "data.bars.history"]
    poll_interval = 60.0
    is_streaming = False

    def __init__(self, symbol_universe: List[str]) -> None:
        super().__init__(symbol_universe)
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return
        self._connected = True

    async def collect(self) -> None:
        limiter = await get_rate_limiter("alpaca_rest")
        await limiter.acquire()
        try:
            from app.services.alpaca_service import alpaca_service
            alpaca = alpaca_service
            symbols = self.symbol_universe[:100]
            snapshots = await alpaca.get_snapshots(symbols)
            if not snapshots:
                return
            session = get_session_clock().get_current_session()
            for symbol, snap in snapshots.items():
                if not isinstance(snap, dict):
                    continue
                quote = (snap.get("quote") or {}) if isinstance(snap.get("quote"), dict) else {}
                trade = (snap.get("trade") or {}) if isinstance(snap.get("trade"), dict) else {}
                price = float(trade.get("p") or quote.get("ap") or quote.get("bp") or 0)
                if price <= 0:
                    continue
                await self.publish("data.price.snapshot", {
                    "symbol": symbol,
                    "price": price,
                    "bid": float(quote.get("bp", 0)) or None,
                    "ask": float(quote.get("ap", 0)) or None,
                    "volume": int(trade.get("s", 0) or 0),
                    "session": session.value if hasattr(session, "value") else str(session),
                    "is_realtime": False,
                })
        except Exception as e:
            logger.debug("alpaca_rest collect: %s", e)
        # Base run() sleeps poll_interval after each collect()

    async def disconnect(self) -> None:
        self._connected = False
