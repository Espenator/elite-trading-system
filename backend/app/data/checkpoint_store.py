"""Lightweight per-source checkpoint store backed by DuckDB.

Checkpoints let adapters resume after a restart without re-ingesting
data they have already processed.

Usage::

    from app.data.checkpoint_store import checkpoint_store

    # Persist progress
    await checkpoint_store.save("finviz", "screener", {"cursor": "2026-03-08T12:00:00"})

    # Resume on restart
    cp = await checkpoint_store.load("finviz", "screener")
    last_cursor = (cp or {}).get("cursor")
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TABLE = "ingestion_checkpoints"


class CheckpointStore:
    """Per-source, per-scope checkpoint persistence backed by DuckDB.

    Uses the module-level ``duckdb_store`` singleton so all I/O goes
    through the same serialised connection and asyncio.to_thread pool.
    """

    # ------------------------------------------------------------------
    # Sync helpers (used in tests / sync startup code)
    # ------------------------------------------------------------------

    def _load_sync(self, source: str, scope: str) -> Optional[Dict[str, Any]]:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        with duckdb_store._lock:
            rows = conn.execute(
                f"SELECT data FROM {_TABLE} WHERE source = ? AND scope = ?",
                [source, scope],
            ).fetchall()
        if not rows:
            return None
        return json.loads(rows[0][0])

    def _save_sync(self, source: str, scope: str, data: Dict[str, Any]) -> None:
        from app.data.duckdb_storage import duckdb_store
        payload = json.dumps(data, default=str)
        now = datetime.now(timezone.utc).isoformat()
        conn = duckdb_store._get_conn()
        with duckdb_store._lock:
            conn.execute(
                f"""
                INSERT INTO {_TABLE} (source, scope, data, saved_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (source, scope)
                DO UPDATE SET data = excluded.data, saved_at = excluded.saved_at
                """,
                [source, scope, payload, now],
            )

    def _delete_sync(self, source: str, scope: str) -> None:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        with duckdb_store._lock:
            conn.execute(
                f"DELETE FROM {_TABLE} WHERE source = ? AND scope = ?",
                [source, scope],
            )

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def load(self, source: str, scope: str) -> Optional[Dict[str, Any]]:
        """Return the stored checkpoint dict, or None if not found."""
        return await asyncio.to_thread(self._load_sync, source, scope)

    async def save(self, source: str, scope: str, data: Dict[str, Any]) -> None:
        """Persist a checkpoint, overwriting any previous value for this key."""
        await asyncio.to_thread(self._save_sync, source, scope, data)
        logger.debug("Checkpoint saved: source=%s scope=%s", source, scope)

    async def delete(self, source: str, scope: str) -> None:
        """Remove a checkpoint (e.g. on deliberate reset)."""
        await asyncio.to_thread(self._delete_sync, source, scope)
        logger.debug("Checkpoint deleted: source=%s scope=%s", source, scope)


# ---------------------------------------------------------------------------
# Module-level singleton — mirrors duckdb_store pattern
# ---------------------------------------------------------------------------
checkpoint_store = CheckpointStore()
