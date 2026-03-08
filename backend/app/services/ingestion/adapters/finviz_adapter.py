"""FinvizAdapter — polls Finviz screener for equity snapshot data.

Schedule: every 5 minutes during market hours (market_hours=True).

Uses :func:`~app.services.ingestion.snapshot_diff.compute_snapshot_diff` to
emit a ``SourceEvent`` only for symbols whose screener data has changed
since the last poll, avoiding redundant downstream processing.

CheckpointStore key: ``finviz.last_snapshot_hash``
Topic: ``ingestion.screener``
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.models.source_event import SourceEvent
from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.snapshot_diff import compute_snapshot_diff, snapshot_hash

logger = logging.getLogger(__name__)

_CHECKPOINT_HASH_KEY = "finviz.last_snapshot_hash"
_CHECKPOINT_SNAPSHOT_KEY = "finviz.last_snapshot"


class FinvizAdapter(BaseSourceAdapter):
    """Polls the Finviz screener and emits change events for each symbol.

    Only symbols whose values changed since the previous poll are emitted,
    keeping downstream event volume low during quiet market periods.

    Args:
        screener_params: Dict of Finviz screener params forwarded to
                         :class:`~app.services.finviz_service.FinvizService`.
    """

    name = "finviz"
    source_kind = "poll"

    def __init__(self, screener_params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self._screener_params = screener_params or {}

    async def fetch(self) -> List[SourceEvent]:
        """Fetch screener data, diff against last snapshot, return change events."""
        from app.services.finviz_service import FinvizService

        svc = FinvizService()
        # get_screener returns a list of dicts, one per ticker
        raw: List[Dict[str, Any]] = await svc.get_screener(**self._screener_params)

        # Key snapshot by ticker
        new_snapshot: Dict[str, Dict[str, Any]] = {
            item["ticker"]: item
            for item in (raw or [])
            if item.get("ticker")
        }

        if not new_snapshot:
            logger.debug("FinvizAdapter: empty screener response")
            return []

        # Load previous snapshot from checkpoint store
        old_snapshot: Optional[Dict[str, Any]] = self.checkpoint.get(_CHECKPOINT_SNAPSHOT_KEY)

        events: List[SourceEvent] = []
        for seq, (ticker, new_data) in enumerate(new_snapshot.items()):
            old_data = old_snapshot.get(ticker) if old_snapshot else None
            diff = compute_snapshot_diff(old_data, new_data)
            if not diff.has_changes:
                continue

            events.append(
                SourceEvent(
                    source=self.name,
                    source_kind=self.source_kind,
                    topic="ingestion.screener",
                    payload={
                        "ticker": ticker,
                        "data": new_data,
                        "diff": diff.to_dict(),
                    },
                    symbol=ticker,
                    sequence=seq,
                )
            )

        # Persist snapshot and its hash for next poll
        new_hash = snapshot_hash(new_snapshot)
        self.checkpoint.set(_CHECKPOINT_HASH_KEY, new_hash)
        self.checkpoint.set(_CHECKPOINT_SNAPSHOT_KEY, new_snapshot)

        logger.info(
            "FinvizAdapter: %d/%d symbols changed",
            len(events), len(new_snapshot),
        )
        return events

    async def close(self) -> None:
        pass  # Stateless HTTP poller — nothing to close
