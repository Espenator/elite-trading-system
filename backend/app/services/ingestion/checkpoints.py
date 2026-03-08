"""Durable checkpoint store for ingestion adapters.

Checkpoints are simple JSON dicts keyed by source name.  The default
implementation writes to a JSON file on disk so that adapter state survives
process restarts without requiring DuckDB (which may not be initialised yet
during early startup).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.getenv(
    "INGESTION_CHECKPOINT_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "ingestion_checkpoints.json"),
)


class CheckpointStore:
    """Thread-safe JSON-file checkpoint store."""

    def __init__(self, path: str = _DEFAULT_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r") as f:
                    self._data = json.load(f)
        except Exception as exc:
            logger.debug("checkpoint load error: %s", exc)
            self._data = {}

    def _flush(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("checkpoint flush error: %s", exc)

    def load(self, source_name: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data.get(source_name, {}))

    def save(self, source_name: str, checkpoint: Dict[str, Any]) -> None:
        with self._lock:
            self._data[source_name] = dict(checkpoint)
            self._flush()

    def delete(self, source_name: str) -> None:
        with self._lock:
            self._data.pop(source_name, None)
            self._flush()

    def all_checkpoints(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
_store: CheckpointStore | None = None


def get_checkpoint_store(path: str | None = None) -> CheckpointStore:
    global _store
    if _store is None:
        _store = CheckpointStore(path or _DEFAULT_PATH)
    return _store
