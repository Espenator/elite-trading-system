"""Durable checkpoint store for incremental pollers.

Persists adapter cursors and seen-event sets to a JSON file so that
pollers resume from where they left off across restarts.  All
operations are thread-safe via a threading.Lock.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class CheckpointStore:
    """Thread-safe, JSON-file-backed checkpoint store.

    Keys are arbitrary strings (e.g. "unusual_whales:last_ts").
    Values must be JSON-serialisable (str, int, float, list, dict).
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or (_CHECKPOINT_DIR / "ingestion_checkpoints.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load persisted state from disk (best-effort)."""
        try:
            if self._path.exists():
                with open(self._path) as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        self._data = loaded
        except Exception as exc:  # pragma: no cover
            logger.warning("CheckpointStore: failed to load %s: %s", self._path, exc)
            self._data = {}

    def _flush(self) -> None:
        """Persist current state to disk (best-effort)."""
        try:
            with open(self._path, "w") as fh:
                json.dump(self._data, fh, indent=2)
        except Exception as exc:  # pragma: no cover
            logger.error("CheckpointStore: failed to flush %s: %s", self._path, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for *key*, or *default* if absent."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* and flush to disk."""
        with self._lock:
            self._data[key] = value
            self._flush()

    def delete(self, key: str) -> None:
        """Remove *key* and flush to disk."""
        with self._lock:
            self._data.pop(key, None)
            self._flush()

    def all_keys(self) -> list:
        """Return all stored keys (for diagnostics)."""
        with self._lock:
            return list(self._data.keys())
