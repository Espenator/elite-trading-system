"""Firehose metrics: counters, latency, queue depth."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict

_metrics: Dict[str, Any] = defaultdict(lambda: {"count": 0, "last_ts": 0.0, "queue_depth": 0})


def record_published(agent_id: str, topic: str) -> None:
    _key = f"{agent_id}:{topic}"
    _metrics[_key]["count"] += 1
    _metrics[_key]["last_ts"] = time.time()


def record_latency(agent_id: str, latency_sec: float) -> None:
    _metrics[agent_id]["last_latency"] = latency_sec
    _metrics[agent_id]["last_ts"] = time.time()


def set_queue_depth(agent_id: str, depth: int) -> None:
    _metrics[agent_id]["queue_depth"] = depth


def get_metrics() -> Dict[str, Any]:
    return dict(_metrics)
