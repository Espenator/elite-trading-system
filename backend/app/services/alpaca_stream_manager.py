"""AlpacaStreamManager — Orchestrate WebSocket streams per PC role.

Two-PC Architecture (prevents WebSocket conflicts):
    PC1 (PC_ROLE=primary):   Key 1 WebSocket → portfolio symbols
    PC2 (PC_ROLE=secondary): Key 2 WebSocket → discovery universe

Each PC opens exactly ONE WebSocket on ITS OWN Alpaca account.
Alpaca allows 1 WS per account per endpoint — this prevents disconnects.

All streams publish to the SAME MessageBus topic 'market_data.bar'.

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
        """Start WebSocket stream using THIS PC's assigned key only.

        PC1 (primary)   → Key 1 WS for portfolio symbols
        PC2 (secondary) → Key 2 WS for discovery universe

        Each PC opens exactly ONE WebSocket. No conflicts.
        """
        from app.services.alpaca_key_pool import get_alpaca_key_pool
        from app.services.alpaca_stream_service import AlpacaStreamService

        pool = get_alpaca_key_pool()
        ws_key = pool.get_ws_key()

        if not ws_key:
            logger.warning("AlpacaStreamManager: no WebSocket key for PC_ROLE=%s, skipping", pool.pc_role)
            return

        self._running = True
        self._start_time = time.time()

        # Determine symbols based on PC role
        if pool.pc_role == "secondary":
            # PC2: stream discovery universe symbols
            syms = self._symbols
            role_label = "discovery"
        else:
            # PC1: stream portfolio symbols (watched + positions)
            portfolio = await self._get_portfolio_symbols()
            syms = portfolio if portfolio else self._symbols[:50]
            role_label = "trading"

        stream = AlpacaStreamService(
            self.message_bus,
            symbols=syms,
            api_key=ws_key.api_key,
            secret_key=ws_key.secret_key,
        )
        self._streams[role_label] = stream
        self._stream_tasks[role_label] = asyncio.create_task(stream.start())
        logger.info(
            "AlpacaStreamManager: PC_ROLE=%s, %s stream (%d symbols), key=%s***",
            pool.pc_role, role_label, len(syms),
            ws_key.api_key[:4] if len(ws_key.api_key) >= 4 else "****",
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

        from app.services.alpaca_key_pool import get_alpaca_key_pool
        pool = get_alpaca_key_pool()

        return {
            "running": self._running,
            "pc_role": pool.pc_role,
            "stream_count": len(self._streams),
            "total_bars_received": total_bars,
            "uptime_seconds": round(uptime, 1),
            "streams": stream_statuses,
        }
