"""OpenClawAdapter — ingests real-time signals from the OpenClaw bridge.

Schedule: every 10 minutes (supplemental; primary path is the real-time
          WebSocket/HTTP bridge in openclaw_bridge_service.py).

Drains the OpenClaw ring-buffer and emits one
:class:`~app.models.source_event.SourceEvent` per signal not yet seen.
Deduplication leverages the bridge's own ``signal_id`` field AND the
``SourceEvent.dedupe_key`` hash so replayed signals are silently dropped.

CheckpointStore key: ``openclaw.seen_ids`` — set of recently seen signal IDs
Topic: ``ingestion.signal``
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent
from app.services.ingestion.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

_CHECKPOINT_KEY = "openclaw.seen_ids"
_MAX_SEEN_IDS = 2000   # Bound the checkpoint size


class OpenClawAdapter(BaseSourceAdapter):
    """Drains buffered OpenClaw signals and emits SourceEvents.

    Args:
        max_signals: Maximum number of signals to emit per poll (default 200).
    """

    name = "openclaw"
    source_kind = "poll"

    def __init__(self, max_signals: int = 200) -> None:
        super().__init__()
        self._max_signals = max_signals

    async def fetch(self) -> List[SourceEvent]:
        from app.services.openclaw_bridge_service import openclaw_bridge

        raw_signals: List[Dict[str, Any]] = openclaw_bridge.get_realtime_signals(
            limit=self._max_signals
        )

        if not raw_signals:
            logger.debug("OpenClawAdapter: buffer empty")
            return []

        seen_ids: List[str] = self.checkpoint.get(_CHECKPOINT_KEY) or []
        seen_set = set(seen_ids)

        events: List[SourceEvent] = []
        new_ids: List[str] = []
        seq = 0

        for sig in raw_signals:
            sig_id: str = str(
                sig.get("signal_id") or sig.get("id") or sig.get("hash") or ""
            )
            if sig_id and sig_id in seen_set:
                continue

            ticker = (sig.get("ticker") or sig.get("symbol") or "").upper()
            traded_at = sig.get("timestamp") or sig.get("created_at") or ""

            events.append(
                SourceEvent(
                    source=self.name,
                    source_kind=self.source_kind,
                    topic="ingestion.signal",
                    payload=dict(sig),
                    symbol=ticker or None,
                    occurred_at=datetime.fromisoformat(str(traded_at)[:19])
                    if traded_at
                    else None,
                    sequence=seq,
                )
            )
            seq += 1

            if sig_id:
                new_ids.append(sig_id)
                seen_set.add(sig_id)

        if new_ids:
            combined = (seen_ids + new_ids)[-_MAX_SEEN_IDS:]
            self.checkpoint.set(_CHECKPOINT_KEY, combined)

        logger.info(
            "OpenClawAdapter: %d new signals (skipped %d seen)",
            len(events), len(raw_signals) - len(events),
        )
        return events

    async def close(self) -> None:
        pass  # Bridge service manages its own lifecycle
