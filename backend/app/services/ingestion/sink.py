"""IngestionEventSink — write SourceEvents to DuckDB ingestion_events table.

The sink is the final step of the adapter pipeline:

    Adapter.run_fetch() → List[SourceEvent] → IngestionEventSink.write()

Features:

* **Async-safe** — uses ``asyncio.to_thread`` so the FastAPI event loop is
  never blocked by DuckDB writes.
* **Batch writes** — ``write_many`` inserts events one-by-one within a single
  connection lock, minimising overhead.
* **Dedupe on insert** — the DuckDB ``ingestion_events`` table has a
  ``UNIQUE (dedupe_key)`` constraint; the sink uses ``INSERT OR IGNORE`` so
  duplicate events are silently discarded without raising.
* **Metrics** — ``total_written`` / ``total_skipped`` counters available for
  health endpoints.

Usage::

    from app.services.ingestion.sink import ingestion_sink

    events = await adapter.run_fetch()
    written, skipped = await ingestion_sink.write_many(events)
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from app.models.source_event import SourceEvent

logger = logging.getLogger(__name__)


class IngestionEventSink:
    """Async writer for :class:`~app.models.source_event.SourceEvent` objects.

    Args:
        store: Optional :class:`~app.data.duckdb_storage.DuckDBStorage`
               instance.  Defaults to the global ``duckdb_store`` singleton.
    """

    def __init__(self, store=None) -> None:
        self._store = store
        self._total_written: int = 0
        self._total_skipped: int = 0

    @property
    def store(self):
        if self._store is None:
            from app.data.duckdb_storage import duckdb_store
            self._store = duckdb_store
        return self._store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def write(self, event: SourceEvent) -> bool:
        """Persist a single event.  Returns ``True`` if written, ``False`` if skipped."""
        written, _ = await self.write_many([event])
        return written == 1

    async def write_many(self, events: List[SourceEvent]) -> Tuple[int, int]:
        """Persist a batch of events.

        Returns:
            ``(written_count, skipped_count)`` tuple.
        """
        if not events:
            return 0, 0

        written = await self.store.write_ingestion_events_async(events)
        skipped = len(events) - written
        self._total_written += written
        self._total_skipped += skipped
        return written, skipped

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def total_written(self) -> int:
        return self._total_written

    @property
    def total_skipped(self) -> int:
        return self._total_skipped

    def health(self) -> dict:
        return {
            "total_written": self._total_written,
            "total_skipped": self._total_skipped,
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
ingestion_sink = IngestionEventSink()
