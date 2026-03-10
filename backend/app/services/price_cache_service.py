"""PriceCacheService — in-memory last price per symbol from market_data.bar / market_data.quote.

Primary price source for OutcomeTracker shadow exit evaluation (SL/TP).
Avoids flaky REST price fetch; subscribes to MessageBus bar/quote events.
"""
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PriceCacheService:
    """Cache last price per symbol from MessageBus market_data.bar and market_data.quote."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._prices: Dict[str, float] = {}
        self._last_update_ts: Optional[float] = None  # global last update time (for degraded check)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("market_data.bar", self._on_bar)
            await self._bus.subscribe("market_data.quote", self._on_quote)
        logger.info("PriceCacheService started (subscribed to market_data.bar, market_data.quote)")

    async def stop(self) -> None:
        self._running = False
        if self._bus:
            try:
                await self._bus.unsubscribe("market_data.bar", self._on_bar)
                await self._bus.unsubscribe("market_data.quote", self._on_quote)
            except Exception:
                pass
        logger.info("PriceCacheService stopped")

    async def _on_bar(self, data: Dict[str, Any]) -> None:
        symbol = data.get("symbol")
        close = data.get("close")
        if symbol and close is not None:
            try:
                self._prices[symbol.upper()] = float(close)
                self._last_update_ts = time.time()
            except (TypeError, ValueError):
                pass

    async def _on_quote(self, data: Dict[str, Any]) -> None:
        symbol = data.get("symbol")
        ap = data.get("ap")  # ask price
        bp = data.get("bp")  # bid price
        if symbol and (ap is not None or bp is not None):
            try:
                if ap is not None and bp is not None:
                    mid = (float(ap) + float(bp)) / 2.0
                else:
                    mid = float(ap if ap is not None else bp)
                self._prices[symbol.upper()] = mid
                self._last_update_ts = time.time()
            except (TypeError, ValueError):
                pass

    def get_price(self, symbol: str) -> Optional[float]:
        """Return last known price for symbol, or None."""
        if not symbol:
            return None
        return self._prices.get(symbol.upper())

    def get_prices(self, symbols: list) -> Dict[str, float]:
        """Return dict of symbol -> last price for symbols that have a cached price."""
        return {s: self._prices[s.upper()] for s in symbols if s and s.upper() in self._prices}

    def get_last_update_time(self) -> Optional[float]:
        """Return timestamp of last bar/quote update (for brain degraded check)."""
        return self._last_update_ts

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "symbols_cached": len(self._prices),
            "last_update_ts": self._last_update_ts,
        }


_price_cache: Optional[PriceCacheService] = None


def get_price_cache(message_bus=None) -> PriceCacheService:
    global _price_cache
    if _price_cache is None:
        _price_cache = PriceCacheService(message_bus)
    return _price_cache
