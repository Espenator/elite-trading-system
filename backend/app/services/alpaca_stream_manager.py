"""AlpacaStreamManager — Orchestrate multiple WebSocket streams.

Manages one AlpacaStreamService per API key, each covering a different
symbol universe. Replaces the single AlpacaStreamService as the top-level
stream coordinator in main.py.

Architecture:
    trading      key → portfolio symbols only (from Alpaca positions API)
    discovery_a  key → top 500 high-priority symbols
    discovery_b  key → next 500 symbols (rotating universe)

All streams publish to the SAME MessageBus topic 'market_data.bar'.

If only 1 key is configured, behaves exactly like the current
AlpacaStreamService (backward compatible).

Part of #39 — E0.2
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlpacaStreamManager:
    """Multi-stream orchestrator using AlpacaKeyPool."""

    def __init__(self, message_bus, symbols: Optional[List[str]] = None):
        self.message_bus = message_bus
        self._symbols = symbols or []
        self._streams: Dict[str, Any] = {}  # role -> AlpacaStreamService
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._start_time: Optional[float] = None

    async def start(self) -> None:
        """Start all streams based on configured keys."""
        from app.services.alpaca_key_pool import get_alpaca_key_pool
        from app.services.alpaca_stream_service import AlpacaStreamService

        pool = get_alpaca_key_pool()
        keys = pool.get_all_keys()

        if not keys:
            logger.warning("AlpacaStreamManager: no API keys configured, skipping")
            return

        self._running = True
        self._start_time = time.time()

        if pool.is_multi_key:
            # Multi-key mode: distribute symbols across streams
            await self._start_multi_key(keys)
        else:
            # Single-key mode: behave exactly like the old AlpacaStreamService
            key = keys[0]
            stream = AlpacaStreamService(
                self.message_bus,
                symbols=self._symbols,
                api_key=key.api_key,
                secret_key=key.secret_key,
            )
            self._streams[key.role] = stream
            self._stream_tasks[key.role] = asyncio.create_task(stream.start())
            logger.info(
                "AlpacaStreamManager: single-key mode (%d symbols)",
                len(self._symbols),
            )

    async def _start_multi_key(self, keys: List) -> None:
        """Start streams with symbol distribution across multiple keys."""
        from app.services.alpaca_stream_service import AlpacaStreamService

        # Get portfolio symbols for trading key
        portfolio_symbols = await self._get_portfolio_symbols()

        # Distribute discovery symbols
        discovery_symbols = [s for s in self._symbols if s not in portfolio_symbols]

        for key in keys:
            if key.role == "trading":
                syms = portfolio_symbols or self._symbols[:10]
            elif key.role == "discovery_a":
                mid = len(discovery_symbols) // 2
                syms = discovery_symbols[:mid] if discovery_symbols else []
            elif key.role == "discovery_b":
                mid = len(discovery_symbols) // 2
                syms = discovery_symbols[mid:] if discovery_symbols else []
            else:
                syms = []

            if not syms:
                logger.info(
                    "AlpacaStreamManager: skipping stream '%s' (no symbols)",
                    key.role,
                )
                continue

            stream = AlpacaStreamService(
                self.message_bus,
                symbols=syms,
                api_key=key.api_key,
                secret_key=key.secret_key,
            )
            self._streams[key.role] = stream
            self._stream_tasks[key.role] = asyncio.create_task(stream.start())
            logger.info(
                "AlpacaStreamManager: started '%s' stream (%d symbols)",
                key.role, len(syms),
            )

    async def _get_portfolio_symbols(self) -> List[str]:
        """Fetch current portfolio symbols from Alpaca positions API."""
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            if positions:
                return [p.get("symbol", "") for p in positions if p.get("symbol")]
        except Exception as e:
            logger.debug("AlpacaStreamManager: portfolio fetch failed: %s", e)
        return []

    async def stop(self) -> None:
        """Graceful shutdown of all streams."""
        self._running = False
        for role, stream in self._streams.items():
            try:
                await stream.stop()
            except Exception as e:
                logger.debug("Error stopping stream '%s': %s", role, e)

        for role, task in self._stream_tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        self._streams.clear()
        self._stream_tasks.clear()
        logger.info("AlpacaStreamManager: all streams stopped")

    def rebalance_symbols(self, universe: List[str]) -> None:
        """Redistribute symbols across streams.

        Takes effect on next reconnect cycle.
        """
        self._symbols = universe

        if len(self._streams) <= 1:
            # Single-key mode: update the one stream
            for stream in self._streams.values():
                stream.update_symbols(universe)
            return

        # Multi-key: split across discovery streams
        discovery_streams = {
            role: stream
            for role, stream in self._streams.items()
            if role.startswith("discovery_")
        }
        if not discovery_streams:
            return

        # Simple even split
        roles = sorted(discovery_streams.keys())
        chunk_size = len(universe) // len(roles) if roles else len(universe)
        for i, role in enumerate(roles):
            start = i * chunk_size
            end = start + chunk_size if i < len(roles) - 1 else len(universe)
            discovery_streams[role].update_symbols(universe[start:end])

        logger.info(
            "AlpacaStreamManager: rebalanced %d symbols across %d streams",
            len(universe), len(discovery_streams),
        )

    def get_status(self) -> Dict[str, Any]:
        """Per-stream stats (symbols count, bars received, errors)."""
        uptime = time.time() - self._start_time if self._start_time else 0
        stream_statuses = {}
        total_bars = 0

        for role, stream in self._streams.items():
            try:
                s = stream.get_status()
                stream_statuses[role] = s
                total_bars += s.get("bars_received", 0)
            except Exception:
                stream_statuses[role] = {"error": "status unavailable"}

        return {
            "running": self._running,
            "stream_count": len(self._streams),
            "total_bars_received": total_bars,
            "uptime_seconds": round(uptime, 1),
            "streams": stream_statuses,
        }
