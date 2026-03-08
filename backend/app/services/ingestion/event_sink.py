"""Event sink writer — idempotent DuckDB persistence for SourceEvent.

Subscribes to the MessageBus topic ``'source_event'`` and persists each
event to the ``source_events`` table, using ``dedupe_key`` to prevent
duplicate rows.  All DuckDB I/O is off-loaded to a thread pool so the
asyncio event loop is never blocked.

Usage (wired in main.py)::

    from app.services.ingestion.event_sink import EventSinkWriter
    sink = EventSinkWriter()
    await sink.start(message_bus)

    # Later:
    await sink.stop()
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TABLE = "source_events"


class EventSinkWriter:
    """MessageBus subscriber that persists SourceEvent payloads to DuckDB.

    Idempotency is achieved via a pre-check on ``dedupe_key`` before
    inserting, so replaying events is safe.  All writes go through the
    existing ``duckdb_store`` singleton to avoid concurrent-connection
    issues.
    """

    def __init__(self) -> None:
        self._events_written: int = 0
        self._events_skipped: int = 0
        self._events_failed: int = 0
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, message_bus) -> None:
        """Subscribe to 'source_event' on the given MessageBus."""
        self._running = True
        await message_bus.subscribe("source_event", self._handle_event)
        logger.info("EventSinkWriter started — listening on source_event")

    async def stop(self) -> None:
        self._running = False
        logger.info(
            "EventSinkWriter stopped — written=%d skipped=%d failed=%d",
            self._events_written,
            self._events_skipped,
            self._events_failed,
        )

    # ------------------------------------------------------------------
    # Internal write
    # ------------------------------------------------------------------

    def _write_sync(self, data: Dict[str, Any]) -> str:
        """Execute the INSERT and return 'written' or 'skipped'."""
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        with duckdb_store._lock:
            rows_before = conn.execute(
                f"SELECT COUNT(*) FROM {_TABLE} WHERE dedupe_key = ?",
                [data["dedupe_key"]],
            ).fetchone()[0]

            if rows_before > 0:
                return "skipped"

            conn.execute(
                f"""
                INSERT INTO {_TABLE}
                    (event_id, dedupe_key, schema_version, source, source_version,
                     feed, event_ts, ingested_at, symbols, entity_id,
                     payload, raw_payload, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    data.get("event_id", ""),
                    data["dedupe_key"],
                    data.get("schema_version", "1.0"),
                    data.get("source", ""),
                    data.get("source_version", "1"),
                    data.get("feed", ""),
                    data.get("event_ts", datetime.now(timezone.utc).isoformat()),
                    data.get("ingested_at", datetime.now(timezone.utc).isoformat()),
                    json.dumps(data.get("symbols", []), default=str),
                    data.get("entity_id", ""),
                    json.dumps(data.get("payload", {}), default=str),
                    data.get("raw_payload"),
                    bool(data.get("is_deleted", False)),
                ],
            )
        return "written"

    # ------------------------------------------------------------------
    # MessageBus handler
    # ------------------------------------------------------------------

    async def _handle_event(self, data: Dict[str, Any]) -> None:
        if not self._running:
            return
        if "dedupe_key" not in data:
            logger.warning("EventSinkWriter: received event without dedupe_key — dropping")
            self._events_failed += 1
            return

        try:
            result = await asyncio.to_thread(self._write_sync, data)
            if result == "written":
                self._events_written += 1
                logger.debug(
                    "EventSink wrote event dedupe_key=%s source=%s",
                    data["dedupe_key"], data.get("source", "?"),
                )
            else:
                self._events_skipped += 1
        except Exception:
            self._events_failed += 1
            logger.exception(
                "EventSinkWriter: failed to persist event dedupe_key=%s",
                data.get("dedupe_key", "unknown"),
            )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "events_written": self._events_written,
            "events_skipped": self._events_skipped,
            "events_failed": self._events_failed,
        }
