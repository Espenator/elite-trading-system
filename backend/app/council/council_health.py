"""Council health observability — last evaluation + rolling 24h + per-agent performance.

Updated by runner.py after each council evaluation. Exposed via GET /api/v1/council/health
and GET /api/v1/council/agents/performance. Adds <50ms to evaluation latency.
"""
import logging
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.council.registry import AGENTS, DAG_STAGES

logger = logging.getLogger(__name__)

# Rolling window: keep last N evaluations for 24h stats (assume ~1 eval/min → 1440)
ROLLING_MAX = 200
STALE_SEC = 86400  # 24h

# Agent name -> stage index (1-based) for display
def _agent_stage(name: str) -> int:
    for i, stage in enumerate(DAG_STAGES, 1):
        if name in stage:
            return i
    return 0


def _is_failure_hold(vote: Any) -> bool:
    """True if vote is a failure fallback (confidence <= 0.1 or error/timeout in reasoning)."""
    if vote.confidence > 0.1:
        return False
    r = (vote.reasoning or "").lower()
    return "error" in r or "timeout" in r or "exception" in r or vote.confidence <= 0.0


def _is_timeout(vote: Any) -> bool:
    """True if vote indicates agent timed out."""
    r = (vote.reasoning or "").lower()
    return "timeout" in r


def _is_real_vote(vote: Any) -> bool:
    """True if vote is a real decision (not failure hold, not timeout)."""
    return not _is_failure_hold(vote) and not _is_timeout(vote)


# In-memory store
_last_evaluation: Optional[Dict[str, Any]] = None
_rolling: deque = deque(maxlen=ROLLING_MAX)
_agent_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "vote_count": 0,
    "failure_count": 0,
    "veto_count": 0,
    "confidence_sum": 0.0,
    "direction_buy": 0,
    "direction_sell": 0,
    "direction_hold": 0,
})
_lock = threading.Lock()


def update_after_evaluation(
    decision_id: str,
    symbol: str,
    verdict: str,
    latency_ms: float,
    votes: List[Any],
    total_registered: int = 35,
) -> None:
    """Called by runner after each council evaluation. Kept lightweight (<50ms)."""
    if not votes:
        return
    now = datetime.now(timezone.utc).isoformat()
    real_conf_sum = 0.0
    real_count = 0
    failure_conf_sum = 0.0
    failure_count = 0
    timeout_count = 0
    for v in votes:
        if _is_timeout(v):
            timeout_count += 1
            failure_count += 1
            failure_conf_sum += v.confidence
        elif _is_failure_hold(v):
            failure_count += 1
            failure_conf_sum += v.confidence
        else:
            real_count += 1
            real_conf_sum += v.confidence
    avg_real = real_conf_sum / real_count if real_count else 0.0
    avg_failure = failure_conf_sum / failure_count if failure_count else 0.1

    failure_rate = failure_count / max(total_registered, 1)
    if failure_rate > 0.50:
        health_status = "CRITICAL"
    elif failure_rate > 0.20:
        health_status = "DEGRADED"
    else:
        health_status = "HEALTHY"

    last = {
        "timestamp": now,
        "symbol": symbol,
        "council_decision_id": decision_id,
        "latency_ms": round(latency_ms, 0),
        "agents": {
            "total_registered": total_registered,
            "voted_successfully": real_count,
            "failure_holds": failure_count - timeout_count,
            "timed_out": timeout_count,
            "avg_confidence_real": round(avg_real, 3),
            "avg_confidence_failure": round(avg_failure, 3),
        },
        "verdict": verdict.upper(),
        "health_status": health_status,
    }

    with _lock:
        global _last_evaluation
        _last_evaluation = last
        _rolling.append({
            "ts": time.time(),
            "healthy_agents": real_count,
            "latency_ms": latency_ms,
            "total": total_registered,
        })
        # Per-agent stats
        for v in votes:
            name = getattr(v, "agent_name", str(v))
            _agent_stats[name]["vote_count"] += 1
            if _is_failure_hold(v) or _is_timeout(v):
                _agent_stats[name]["failure_count"] += 1
            if getattr(v, "veto", False):
                _agent_stats[name]["veto_count"] += 1
            _agent_stats[name]["confidence_sum"] += getattr(v, "confidence", 0)
            d = getattr(v, "direction", "hold").lower()
            if d == "buy":
                _agent_stats[name]["direction_buy"] += 1
            elif d == "sell":
                _agent_stats[name]["direction_sell"] += 1
            else:
                _agent_stats[name]["direction_hold"] += 1


def get_rolling_24h() -> Dict[str, Any]:
    """Compute rolling 24h stats from _rolling deque."""
    with _lock:
        recent = [e for e in _rolling if (time.time() - e["ts"]) < STALE_SEC]
    if not recent:
        return {
            "evaluations": 0,
            "avg_healthy_agents": 0,
            "avg_latency_ms": 0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "worst_degradation": None,
        }
    latencies = [e["latency_ms"] for e in recent]
    healthy = [e["healthy_agents"] for e in recent]
    total_reg = recent[0].get("total", 35) if recent else 35
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    p50 = latencies_sorted[int(n * 0.50)] if n > 0 else 0
    p95_idx = max(0, int(n * 0.95) - 1)
    p95 = latencies_sorted[p95_idx] if latencies_sorted else 0
    p99_idx = max(0, int(n * 0.99) - 1)
    p99 = latencies_sorted[p99_idx] if latencies_sorted else 0
    worst = min(recent, key=lambda e: e["healthy_agents"])
    worst_ts = datetime.fromtimestamp(worst["ts"], tz=timezone.utc).isoformat()
    return {
        "evaluations": len(recent),
        "avg_healthy_agents": round(sum(healthy) / len(healthy), 1),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 0),
        "p50_latency_ms": round(p50, 0),
        "p95_latency_ms": round(p95, 0),
        "p99_latency_ms": round(p99, 0),
        "worst_degradation": f"{worst_ts} ({worst['healthy_agents']}/{total_reg} healthy)",
    }


def get_latency_percentiles() -> Dict[str, Any]:
    """Return council latency percentiles from rolling window for metrics API."""
    rolling = get_rolling_24h()
    recent_count = rolling.get("evaluations", 0)
    return {
        "p50": rolling.get("p50_latency_ms", 0),
        "p95": rolling.get("p95_latency_ms", 0),
        "p99": rolling.get("p99_latency_ms", 0),
        "sample_count": recent_count,
    }


def get_health() -> Dict[str, Any]:
    """Return full health payload for GET /api/v1/council/health."""
    with _lock:
        last = dict(_last_evaluation) if _last_evaluation else None
    rolling = get_rolling_24h()
    return {
        "last_evaluation": last,
        "rolling_24h": rolling,
    }


def get_agents_performance() -> Dict[str, Any]:
    """Return per-agent performance for GET /api/v1/council/agents/performance."""
    try:
        from app.council.calibration import get_calibration_tracker
        cal = get_calibration_tracker()
        calibration = cal.get_all_scores()
    except Exception:
        calibration = {}

    with _lock:
        stats = {k: dict(v) for k, v in _agent_stats.items()}

    agents_list: List[Dict[str, Any]] = []
    voting_agents = [a for a in AGENTS if a not in ("arbiter",)]
    for name in voting_agents:
        s = stats.get(name, {})
        vote_count = s.get("vote_count", 0)
        failure_count = s.get("failure_count", 0)
        conf_sum = s.get("confidence_sum", 0)
        n = vote_count - failure_count
        avg_conf = round(conf_sum / vote_count, 3) if vote_count else 0
        cal_data = calibration.get(name, {})
        brier = cal_data.get("brier_score")
        health = "HEALTHY"
        if vote_count >= 5 and failure_count / vote_count > 0.3:
            health = "DEGRADED"
        if vote_count >= 10 and failure_count == vote_count:
            health = "BROKEN"
        agents_list.append({
            "name": name,
            "stage": _agent_stage(name),
            "weight": 1.0,  # Could be merged from weight_learner if needed
            "stats_24h": {
                "vote_count": vote_count,
                "failure_count": failure_count,
                "veto_count": s.get("veto_count", 0),
                "avg_confidence": avg_conf,
                "direction_distribution": {
                    "buy": s.get("direction_buy", 0),
                    "sell": s.get("direction_sell", 0),
                    "hold": s.get("direction_hold", 0),
                },
                "brier_score": round(brier, 3) if brier is not None else None,
                "health": health,
            },
        })

    # Broken: high failure rate in last 24h
    broken = [a["name"] for a in agents_list if a["stats_24h"].get("health") == "BROKEN"]
    # Always-hold: voted but 100% hold (likely not producing signal)
    always_hold: List[str] = []
    for a in agents_list:
        dist = a["stats_24h"].get("direction_distribution", {})
        total = dist.get("buy", 0) + dist.get("sell", 0) + dist.get("hold", 0)
        if total >= 10 and dist.get("hold", 0) == total:
            always_hold.append(a["name"])

    return {
        "agents": agents_list,
        "broken_agents": broken,
        "always_hold_agents": always_hold,
    }


def classify_votes(votes: List[Any], total_registered: int = 35) -> Dict[str, Any]:
    """Classify votes into real / failure_hold / timed_out. Used by runner for alerting."""
    real_count = sum(1 for v in votes if _is_real_vote(v))
    timeout_count = sum(1 for v in votes if _is_timeout(v))
    failure_hold_count = sum(1 for v in votes if _is_failure_hold(v)) - timeout_count
    failure_rate = (timeout_count + failure_hold_count) / max(total_registered, 1)
    return {
        "voted_successfully": real_count,
        "failure_holds": failure_hold_count,
        "timed_out": timeout_count,
        "failure_rate": failure_rate,
        "is_degraded": failure_rate > 0.20,
        "is_critical": failure_rate > 0.50,
    }
