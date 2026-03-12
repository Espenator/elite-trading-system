"""Council DAG latency tracking for P50/P95/P99 percentiles.

Stores recent total and per-stage latencies; metrics endpoint reads percentiles.
Thread-safe; used by runner.py after each council evaluation.
"""
import threading
from collections import deque
from typing import Any, Dict, List

# Rolling window of last N council total latencies (ms)
MAX_SAMPLES = 500
_total_latencies: deque = deque(maxlen=MAX_SAMPLES)
_stage_latencies: Dict[str, deque] = {}  # stage_name -> deque of ms
_lock = threading.Lock()

# Stage names for consistent keys
STAGE_NAMES = ("stage1", "stage2", "stage3", "stage4", "stage5", "stage5.5", "stage6")


def _ensure_stage_deques():
    for name in STAGE_NAMES:
        if name not in _stage_latencies:
            _stage_latencies[name] = deque(maxlen=MAX_SAMPLES)


def record(total_ms: float, stage_latencies: Dict[str, float]) -> None:
    """Record one council run: total latency and per-stage latencies (ms)."""
    with _lock:
        _total_latencies.append(total_ms)
        _ensure_stage_deques()
        for stage, ms in (stage_latencies or {}).items():
            if stage in _stage_latencies and isinstance(ms, (int, float)):
                _stage_latencies[stage].append(float(ms))


def _percentiles(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_s = sorted(samples)
    n = len(sorted_s)
    return {
        "p50": round(sorted_s[min(int(n * 0.5), n - 1)], 2),
        "p95": round(sorted_s[min(int(n * 0.95), n - 1)], 2),
        "p99": round(sorted_s[min(int(n * 0.99), n - 1)], 2),
    }


def get_total_percentiles() -> Dict[str, Any]:
    """Return P50/P95/P99 for total council latency and sample count."""
    with _lock:
        samples = list(_total_latencies)
    p = _percentiles(samples)
    p["sample_count"] = len(samples)
    return p


def get_stage_percentiles() -> Dict[str, Dict[str, Any]]:
    """Return P50/P95/P99 per stage."""
    with _lock:
        _ensure_stage_deques()
        snap = {k: list(v) for k, v in _stage_latencies.items() if v}
    return {
        stage: {"sample_count": len(s), **_percentiles(s)}
        for stage, s in snap.items()
    }


def get_all() -> Dict[str, Any]:
    """Return total percentiles + per-stage percentiles for metrics endpoint."""
    return {
        "total_ms": get_total_percentiles(),
        "by_stage": get_stage_percentiles(),
    }
