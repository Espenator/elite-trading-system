"""CheckpointStore — durable key/value store for adapter resume cursors.

Each source adapter uses a CheckpointStore entry to remember where it left
off (e.g. last polled timestamp, last page token, last sequence number) so
that restarts don't cause full re-fetches or data gaps.

Backed by a lightweight SQLite database (``data/checkpoints.db``) that is
separate from DuckDB analytics so there is no write-amplification risk.

Usage::

    from app.data.checkpoint_store import checkpoint_store

    # Save the last-polled timestamp for the UW adapter
    checkpoint_store.set("unusual_whales.last_ts", "2026-01-10T14:30:00Z")

    # Retrieve it on next startup
    last_ts = checkpoint_store.get("unusual_whales.last_ts")
"""

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Store checkpoints next to the DuckDB analytics file
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DEFAULT_PATH = _DATA_DIR / "checkpoints.db"


class CheckpointStore:
    """Thread-safe, durable key/value checkpoint store backed by SQLite.

    All values are JSON-serialized so the store accepts any JSON-compatible
    Python object (str, int, float, list, dict, None).

    Args:
        path: Path to the SQLite file.  Defaults to ``data/checkpoints.db``
              next to the DuckDB analytics database.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = str(path or _DEFAULT_PATH)
        self._lock = threading.Lock()
        self._init_schema()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    key        TEXT    PRIMARY KEY,
                    value      TEXT    NOT NULL,
                    updated_at REAL    NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        logger.debug("CheckpointStore initialized at %s", self._path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Persist ``value`` under ``key``.

        Overwrites any existing value.  Raises ``TypeError`` if ``value``
        is not JSON-serializable.
        """
        serialized = json.dumps(value, default=str)
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (key, value, updated_at) VALUES (?, ?, ?)",
                (key, serialized, time.time()),
            )
            conn.commit()
            conn.close()
        logger.debug("Checkpoint set: %s", key)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key``, or ``default`` if absent."""
        with self._lock:
            conn = self._connect()
            row = conn.execute(
                "SELECT value FROM checkpoints WHERE key = ?", (key,)
            ).fetchone()
            conn.close()
        if row is None:
            return default
        return json.loads(row[0])

    def delete(self, key: str) -> None:
        """Remove checkpoint ``key``.  No-op if it doesn't exist."""
        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM checkpoints WHERE key = ?", (key,))
            conn.commit()
            conn.close()
        logger.debug("Checkpoint deleted: %s", key)

    def all(self) -> Dict[str, Any]:
        """Return a dict of all stored checkpoints (key → deserialized value)."""
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT key, value FROM checkpoints ORDER BY key"
            ).fetchall()
            conn.close()
        return {k: json.loads(v) for k, v in rows}

    def keys(self) -> list:
        """Return a sorted list of all checkpoint keys."""
        with self._lock:
            conn = self._connect()
            rows = conn.execute("SELECT key FROM checkpoints ORDER BY key").fetchall()
            conn.close()
        return [r[0] for r in rows]

    def clear(self) -> int:
        """Delete ALL checkpoints.  Returns number of rows deleted."""
        with self._lock:
            conn = self._connect()
            cur = conn.execute("DELETE FROM checkpoints")
            count = cur.rowcount
            conn.commit()
            conn.close()
        logger.info("CheckpointStore cleared (%d keys removed)", count)
        return count


# ---------------------------------------------------------------------------
# Global singleton — import and use directly
# ---------------------------------------------------------------------------
checkpoint_store = CheckpointStore()
