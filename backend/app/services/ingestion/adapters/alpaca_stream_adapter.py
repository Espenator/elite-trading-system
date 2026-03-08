"""Alpaca stream adapter — thin wrapper around the existing AlpacaStreamManager.

This adapter does NOT replace the existing streaming infrastructure.  Instead
it delegates to ``AlpacaStreamManager`` while conforming to the
``BaseSourceAdapter`` interface so the ingestion registry can track its
lifecycle and health uniformly.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceKind

logger = logging.getLogger(__name__)


class AlpacaStreamAdapter(BaseSourceAdapter):
    source_name = "alpaca_stream"
    source_kind = SourceKind.STREAM
    poll_interval_seconds = 0  # Not polled

    def __init__(self, message_bus=None, symbols: Optional[List[str]] = None):
        super().__init__(message_bus)
        self._symbols = symbols or []
        self._manager = None

    async def start(self) -> None:
        """Override start() to delegate entirely to AlpacaStreamManager."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        if os.getenv("DISABLE_ALPACA_DATA_STREAM", "").strip().lower() in ("1", "true", "yes"):
            logger.info("AlpacaStreamAdapter skipped (DISABLE_ALPACA_DATA_STREAM=1)")
            return

        from app.services.alpaca_stream_manager import AlpacaStreamManager
        self._manager = AlpacaStreamManager(self._bus, self._symbols)
        self._task = asyncio.create_task(self._manager.start())

    async def stop(self) -> None:
        """Stop the underlying AlpacaStreamManager."""
        self._running = False
        if self._manager:
            await self._manager.stop()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("%s adapter stopped", self.source_name)

    async def _run_stream(self) -> None:
        """Not used — the manager runs its own tasks."""
        while self._running:
            await asyncio.sleep(5)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        if self._manager:
            base["manager_status"] = self._manager.get_status()
        return base
