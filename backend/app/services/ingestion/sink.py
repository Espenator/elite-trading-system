"""Append-only event sink — subscribes to source topics and persists to DuckDB.

The sink is the single writer for ingestion events.  It deduplicates on
``dedupe_key`` so that replay / double-publish is safe.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

# Maximum number of dedupe keys held in memory (LRU)
_MAX_DEDUPE_KEYS = 50_000


class EventSink:
    """Idempotent append-only writer that subscribes to MessageBus topics."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._seen: OrderedDict[str, float] = OrderedDict()  # dedupe_key -> ingested_at
        self._persisted: int = 0
        self._duplicates: int = 0
        self._errors: int = 0
        self._subscribed_topics: Set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def subscribe(self, topic: str) -> None:
        """Subscribe to a MessageBus topic and persist all events."""
        if self._bus is None:
            return
        if topic in self._subscribed_topics:
            return
        await self._bus.subscribe(topic, self._on_event)
        self._subscribed_topics.add(topic)
        logger.info("EventSink subscribed to %s", topic)

    async def _on_event(self, event_data: Dict[str, Any]) -> None:
        """Handle an incoming event from the bus."""
        dedupe_key = event_data.get("dedupe_key") or event_data.get("event_id", "")
        if not dedupe_key:
            # No dedupe key — persist unconditionally
            await self._persist(event_data)
            return

        if dedupe_key in self._seen:
            self._duplicates += 1
            return

        # Record in LRU
        self._seen[dedupe_key] = time.time()
        if len(self._seen) > _MAX_DEDUPE_KEYS:
            self._seen.popitem(last=False)

        await self._persist(event_data)

    async def _persist(self, event_data: Dict[str, Any]) -> None:
        """Write event to DuckDB ingestion_events table (non-blocking)."""
        try:
            from app.data.duckdb_storage import duckdb_store

            await duckdb_store.async_insert(
                """
                INSERT OR IGNORE INTO ingestion_events
                    (event_id, source, source_kind, topic, symbol, entity_id,
                     occurred_at, ingested_at, sequence, dedupe_key, schema_version,
                     payload_json, trace_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_data.get("event_id", ""),
                    event_data.get("source", ""),
                    event_data.get("source_kind", ""),
                    event_data.get("topic", ""),
                    event_data.get("symbol", ""),
                    event_data.get("entity_id", ""),
                    event_data.get("occurred_at", 0),
                    event_data.get("ingested_at", time.time()),
                    event_data.get("sequence", 0),
                    event_data.get("dedupe_key", ""),
                    event_data.get("schema_version", 1),
                    _safe_json(event_data.get("payload", {})),
                    event_data.get("trace_id", ""),
                ],
            )
            self._persisted += 1
        except Exception as exc:
            self._errors += 1
            logger.debug("EventSink persist error: %s", exc)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "persisted": self._persisted,
            "duplicates_skipped": self._duplicates,
            "errors": self._errors,
            "subscribed_topics": sorted(self._subscribed_topics),
            "dedupe_cache_size": len(self._seen),
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _safe_json(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return "{}"
