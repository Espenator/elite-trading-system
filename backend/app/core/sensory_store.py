"""Sensory store — last-value cache for MessageBus perception/orphan topics.

Subscribers in main.py lifespan write to this store so council agents can read
the latest perception data via blackboard.raw_features["features"]["sensory"].

Topics stored: perception.finviz.screener, perception.macro, perception.edgar,
perception.gex, perception.insider, perception.squeezemetrics, perception.earnings,
perception.congressional, macro.fred, perception.flow.uw_analysis, etc.
"""
import threading
from typing import Any, Dict

_lock = threading.Lock()
_store: Dict[str, Dict[str, Any]] = {}


def update(topic: str, data: Dict[str, Any]) -> None:
    """Store the latest payload for a topic (thread-safe)."""
    with _lock:
        _store[topic] = dict(data)


def get(topic: str) -> Dict[str, Any]:
    """Return the latest payload for a topic, or empty dict."""
    with _lock:
        return dict(_store.get(topic, {}))


def get_snapshot() -> Dict[str, Dict[str, Any]]:
    """Return a copy of all stored topic data for merging into council features."""
    with _lock:
        return {k: dict(v) for k, v in _store.items()}


def clear() -> None:
    """Clear all stored data (for tests)."""
    with _lock:
        _store.clear()
