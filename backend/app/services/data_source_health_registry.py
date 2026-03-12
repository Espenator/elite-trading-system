"""Data source health registry — track last fetch and error count per source for GET /data-sources/health.

CLAUDE.md Section 10: Alpaca, Unusual Whales, Finviz, FRED, SEC EDGAR, NewsAPI,
Benzinga, SqueezeMetrics, Capitol Trades, Senate Stock Watcher.
Arch review: SEC EDGAR, SqueezeMetrics, Benzinga, Capitol Trades do NOT publish to MessageBus.
"""
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Canonical 10 data sources (CLAUDE.md Section 10) + whether they publish to MessageBus
SOURCES = [
    {"name": "alpaca", "publishes_to_messagebus": True},
    {"name": "unusual_whales", "publishes_to_messagebus": True},
    {"name": "finviz", "publishes_to_messagebus": True},
    {"name": "fred", "publishes_to_messagebus": True},  # partial per arch review
    {"name": "sec_edgar", "publishes_to_messagebus": False},
    {"name": "news_api", "publishes_to_messagebus": True},
    {"name": "benzinga", "publishes_to_messagebus": False},
    {"name": "squeeze_metrics", "publishes_to_messagebus": False},
    {"name": "capitol_trades", "publishes_to_messagebus": False},
    {"name": "senate_stock_watcher", "publishes_to_messagebus": True},
]

# Per-source: last_success_ts, deque of error timestamps (last 1h)
_store: Dict[str, Dict[str, Any]] = {}
for s in SOURCES:
    _store[s["name"]] = {
        "last_success_ts": 0.0,
        "error_timestamps": deque(maxlen=500),
    }
_lock = threading.Lock()
ONE_HOUR = 3600.0


def record_success(source_name: str) -> None:
    """Call when a data source fetch succeeds."""
    with _lock:
        key = source_name.lower().replace("-", "_").replace(" ", "_")
        if key not in _store:
            _store[key] = {"last_success_ts": 0.0, "error_timestamps": deque(maxlen=500)}
        _store[key]["last_success_ts"] = time.time()


def record_error(source_name: str) -> None:
    """Call when a data source fetch fails."""
    with _lock:
        key = source_name.lower().replace("-", "_").replace(" ", "_")
        if key not in _store:
            _store[key] = {"last_success_ts": 0.0, "error_timestamps": deque(maxlen=500)}
        _store[key]["error_timestamps"].append(time.time())


def get_health() -> Dict[str, Any]:
    """Return health matrix for GET /api/v1/data-sources/health."""
    now = time.time()
    cutoff_1h = now - ONE_HOUR
    sources_list = []
    with _lock:
        for s in SOURCES:
            name = s["name"]
            publishes = s["publishes_to_messagebus"]
            entry = _store.get(name, {"last_success_ts": 0.0, "error_timestamps": deque()})
            last_ts = entry["last_success_ts"]
            errors_1h = sum(1 for t in entry["error_timestamps"] if t >= cutoff_1h)
            freshness = (now - last_ts) if last_ts else 999999
            if last_ts == 0:
                status = "UNKNOWN"
            elif freshness > 3600:  # > 1h
                status = "STALE"
            elif errors_1h >= 3:
                status = "DEGRADED"
            else:
                status = "HEALTHY"
            last_iso = datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat() if last_ts else None
            if last_iso and last_ts == 0:
                last_iso = None
            sources_list.append({
                "name": name,
                "status": status,
                "last_successful_fetch": last_iso,
                "data_freshness_seconds": round(freshness, 0) if last_ts else None,
                "error_count_1h": errors_1h,
                "publishes_to_messagebus": publishes,
            })
    return {"sources": sources_list}
