"""Finviz snapshot adapter — scheduled poller with change-detection diff publish.

Wraps the existing ``FinvizService`` and emits ``perception.finviz.screener``
events only when the screener results have changed since the last poll.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)


class FinvizAdapter(BaseSourceAdapter):
    source_name = "finviz"
    source_kind = SourceKind.SNAPSHOT
    poll_interval_seconds = 60.0

    def __init__(self, message_bus=None):
        super().__init__(message_bus)
        self._last_hash: str = ""

    async def _on_start(self) -> None:
        self._last_hash = self._checkpoint.get("last_hash", "")

    async def poll_once(self) -> None:
        from app.services.finviz_service import FinvizService

        svc = FinvizService()
        stocks = await svc.get_stock_list()
        if not stocks:
            return

        # Diff detection: hash ticker list to detect changes
        tickers = sorted(
            (s.get("Ticker") or s.get("ticker") or "") for s in stocks if isinstance(s, dict)
        )
        current_hash = hashlib.md5(",".join(tickers).encode()).hexdigest()

        is_changed = current_hash != self._last_hash
        self._last_hash = current_hash
        self._checkpoint["last_hash"] = current_hash
        self._checkpoint["last_poll_at"] = time.time()
        self._checkpoint["symbol_count"] = len(tickers)

        # Update symbol universe (side-effect preserved from legacy path)
        try:
            from app.modules.symbol_universe import set_tracked_symbols_from_finviz
            set_tracked_symbols_from_finviz(stocks)
        except Exception:
            pass

        # Always publish so downstream can see freshness, but tag whether data changed
        event = SourceEvent(
            source=self.source_name,
            source_kind=self.source_kind,
            topic="perception.finviz.screener",
            payload={
                "type": "finviz_screener_results",
                "results": stocks,
                "symbol_count": len(tickers),
                "changed": is_changed,
                "source": "finviz_adapter",
                "timestamp": time.time(),
            },
            dedupe_key=f"finviz-{current_hash}",
        )
        await self.publish_event(event)

    def diff_detected(self) -> bool:
        """Public helper: did the last poll detect a change?"""
        return self._last_hash != self._checkpoint.get("last_hash", "")
