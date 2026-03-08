"""UnusualWhalesAdapter — polls Unusual Whales options flow.

Schedule: every 2 minutes during market hours.

Wraps the existing :class:`~app.services.unusual_whales_service.UnusualWhalesService`
and converts raw alerts into typed :class:`~app.models.source_event.SourceEvent`
objects.  Deduplication is handled by the ``SourceEvent.dedupe_key`` (SHA-256
of source+topic+symbol+payload) so replayed or overlapping pages are
automatically discarded by the DuckDB ``INSERT OR IGNORE`` sink.

CheckpointStore key: ``unusual_whales.last_ts`` — ISO timestamp of the most
                     recent alert ingested.
Topic: ``ingestion.options_flow``
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent
from app.services.ingestion.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

_CHECKPOINT_KEY = "unusual_whales.last_ts"


class UnusualWhalesAdapter(BaseSourceAdapter):
    """Polls Unusual Whales for options flow alerts.

    Args:
        limit: Max alerts per poll request (default 50).
    """

    name = "unusual_whales"
    source_kind = "poll"

    def __init__(self, limit: int = 50) -> None:
        super().__init__()
        self._limit = limit

    async def fetch(self) -> List[SourceEvent]:
        from app.services.unusual_whales_service import UnusualWhalesService

        svc = UnusualWhalesService()
        raw = await svc.get_flow_alerts(limit=self._limit)

        alerts: List[Dict[str, Any]] = (
            raw if isinstance(raw, list) else raw.get("data", raw.get("items", []))
        ) if raw else []

        if not alerts:
            logger.debug("UnusualWhalesAdapter: no alerts returned")
            return []

        last_ts: Optional[str] = self.checkpoint.get(_CHECKPOINT_KEY)
        events: List[SourceEvent] = []
        newest_ts: Optional[str] = last_ts
        seq = 0

        for alert in alerts:
            traded_at: str = (
                alert.get("traded_at")
                or alert.get("date")
                or datetime.utcnow().isoformat()
            )
            # Only process alerts newer than last checkpoint
            if last_ts and traded_at <= last_ts:
                continue

            ticker = (alert.get("ticker") or alert.get("symbol") or "").upper()
            if not ticker:
                continue

            events.append(
                SourceEvent(
                    source=self.name,
                    source_kind=self.source_kind,
                    topic="ingestion.options_flow",
                    payload=dict(alert),
                    symbol=ticker,
                    occurred_at=datetime.fromisoformat(traded_at[:19])
                    if traded_at
                    else None,
                    sequence=seq,
                )
            )
            seq += 1

            if newest_ts is None or traded_at > newest_ts:
                newest_ts = traded_at

        if newest_ts and newest_ts != last_ts:
            self.checkpoint.set(_CHECKPOINT_KEY, newest_ts)

        logger.info(
            "UnusualWhalesAdapter: %d new alerts (last_ts: %s → %s)",
            len(events), last_ts, newest_ts,
        )
        return events

    async def close(self) -> None:
        pass  # Stateless HTTP poller — nothing to close
