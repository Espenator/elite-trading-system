"""Lightweight in-memory sentiment store for real-time dashboard access."""
from datetime import datetime
from collections import defaultdict
import threading

_lock = threading.Lock()
_store: dict = {}  # symbol -> latest sentiment data
_history: dict = defaultdict(list)  # symbol -> time series


def update(symbol: str, data: dict):
    with _lock:
        data["updated_at"] = datetime.utcnow().isoformat()
        _store[symbol] = data
        _history[symbol].append(data)
        # Keep last 100 entries per symbol
        if len(_history[symbol]) > 100:
            _history[symbol] = _history[symbol][-100:]


def get(symbol: str) -> dict:
    with _lock:
        return _store.get(symbol, {})


def get_all() -> dict:
    with _lock:
        return dict(_store)


def get_count() -> int:
    with _lock:
        return sum(len(v) for v in _history.values())
