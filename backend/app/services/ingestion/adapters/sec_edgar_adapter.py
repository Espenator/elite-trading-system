"""SEC EDGAR adapter — low-frequency poller with per-symbol filing cursor.

Polls SEC EDGAR for recent filings of tracked symbols and publishes
``perception.edgar`` events.  Checkpoints the most recent form type + date
per ticker so that already-seen filings are not re-emitted.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)


class SecEdgarAdapter(BaseSourceAdapter):
    source_name = "sec_edgar"
    source_kind = SourceKind.LOW_FREQ
    poll_interval_seconds = 3600.0  # 1 hour

    def __init__(self, message_bus=None, max_symbols: int = 5):
        super().__init__(message_bus)
        self._max_symbols = max_symbols

    def _get_symbols(self) -> List[str]:
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            return get_tracked_symbols() or ["AAPL"]
        except Exception:
            return ["AAPL"]

    async def poll_once(self) -> None:
        from app.services.sec_edgar_service import SecEdgarService

        svc = SecEdgarService()
        symbols = self._get_symbols()[: self._max_symbols]

        cursor: Dict[str, str] = self._checkpoint.get("cursors", {})

        for symbol in symbols:
            try:
                forms = await svc.get_recent_forms(symbol, limit=5)
                if not forms:
                    continue

                # Build a simple key from the first form for change detection
                form_key = f"{symbol}:{','.join(forms[:3])}"
                prev_key = cursor.get(symbol, "")

                if form_key == prev_key:
                    continue  # No new filings

                cursor[symbol] = form_key

                event = SourceEvent(
                    source=self.source_name,
                    source_kind=self.source_kind,
                    topic="perception.edgar",
                    symbol=symbol,
                    entity_id=symbol,
                    payload={
                        "type": "sec_filing",
                        "data": {"symbol": symbol, "forms": forms},
                        "source": "sec_edgar_adapter",
                        "timestamp": time.time(),
                    },
                    dedupe_key=f"edgar-{form_key}",
                )
                await self.publish_event(event)

            except Exception as exc:
                logger.warning("SEC EDGAR %s failed: %s", symbol, exc)

        self._checkpoint["cursors"] = cursor
        self._checkpoint["last_poll_at"] = time.time()
