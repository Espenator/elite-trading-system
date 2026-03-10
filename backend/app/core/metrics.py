"""Minimal Prometheus-compatible metrics for pipeline gates and events.

Counters and gauges are in-memory; use get_metrics() for scraping or /metrics endpoint.
Labels are stored as sorted tuple for stable keys. Thread-safe via lock.
"""
import threading
from typing import Any, Dict, List, Optional

_lock = threading.Lock()
_counters: Dict[tuple, int] = {}  # (name, label_key1, label_val1, ...) -> value
_gauges: Dict[tuple, float] = {}


def _key(name: str, labels: Dict[str, str]) -> tuple:
    if not labels:
        return (name,)
    parts = [name]
    for k in sorted(labels.keys()):
        parts.append(k)
        parts.append(str(labels[k]))
    return tuple(parts)


def counter_inc(name: str, labels: Optional[Dict[str, str]] = None, value: int = 1) -> None:
    """Increment a counter. Labels must be string key/value pairs."""
    labels = labels or {}
    key = _key(name, labels)
    with _lock:
        _counters[key] = _counters.get(key, 0) + value


def gauge_set(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """Set a gauge value."""
    labels = labels or {}
    key = _key(name, labels)
    with _lock:
        _gauges[key] = value


def get_counters() -> Dict[tuple, int]:
    """Return current counter snapshot (for tests and export)."""
    with _lock:
        return dict(_counters)


def get_gauges() -> Dict[tuple, float]:
    """Return current gauge snapshot."""
    with _lock:
        return dict(_gauges)


def get_metrics() -> Dict[str, Any]:
    """Return all metrics as a dict suitable for JSON export."""
    with _lock:
        counters_list = []
        for key, val in _counters.items():
            name = key[0]
            labels = {}
            i = 1
            while i < len(key):
                labels[key[i]] = key[i + 1]
                i += 2
            counters_list.append({"name": name, "labels": labels, "value": val})
        gauges_list = []
        for key, val in _gauges.items():
            name = key[0]
            labels = {}
            i = 1
            while i < len(key):
                labels[key[i]] = key[i + 1]
                i += 2
            gauges_list.append({"name": name, "labels": labels, "value": val})
        return {"counters": counters_list, "gauges": gauges_list}


def format_prometheus() -> str:
    """Format metrics in Prometheus text exposition format."""
    lines = []
    with _lock:
        for key, val in _counters.items():
            name = key[0].replace(".", "_")
            label_str = ""
            if len(key) > 1:
                pairs = [f'{key[i]}="{key[i+1]}"' for i in range(1, len(key), 2)]
                label_str = "{" + ",".join(pairs) + "}"
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{label_str} {val}")
        for key, val in _gauges.items():
            name = key[0].replace(".", "_")
            label_str = ""
            if len(key) > 1:
                pairs = [f'{key[i]}="{key[i+1]}"' for i in range(1, len(key), 2)]
                label_str = "{" + ",".join(pairs) + "}"
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{label_str} {val}")
    return "\n".join(lines) + "\n"
