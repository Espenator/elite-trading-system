"""SubsystemHealth registry — explicit healthy/degraded/unavailable states.

Replaces silent failure patterns with structured health state, freshness,
and optional circuit-breaker behavior. Surface via health endpoint and metrics.
"""
import logging
import threading
import time
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


# Known subsystems for pipeline
SUBSYSTEM_MARKET_DATA = "market_data"
SUBSYSTEM_REGIME = "regime_detection"
SUBSYSTEM_LLM_COUNCIL = "llm_council"
SUBSYSTEM_RISK = "risk_service"
SUBSYSTEM_OUTCOME_LEARNER = "outcome_tracker_learner"

_registry: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# Default max staleness (seconds) for freshness checks
DEFAULT_STALENESS_SEC = 300


def set_health(
    subsystem: str,
    state: HealthState,
    reason: str = "",
    trace_id: Optional[str] = None,
) -> None:
    """Set explicit health state for a subsystem."""
    now = time.time()
    with _lock:
        _registry[subsystem] = {
            "state": state.value,
            "reason": reason,
            "updated_at": now,
            "trace_id": trace_id,
        }
    logger.info(
        "health_registry subsystem=%s state=%s reason=%s trace_id=%s",
        subsystem, state.value, reason or "-", trace_id or "-",
    )


def get_health(subsystem: str) -> Dict[str, Any]:
    """Return current health for subsystem."""
    with _lock:
        entry = _registry.get(subsystem, {})
    if not entry:
        return {"state": HealthState.HEALTHY.value, "reason": "", "updated_at": 0}
    return dict(entry)


def is_healthy(subsystem: str, max_staleness_sec: Optional[float] = None) -> bool:
    """Return True if subsystem is healthy and optionally within staleness."""
    with _lock:
        entry = _registry.get(subsystem, {})
    if not entry:
        return True
    if entry.get("state") != HealthState.HEALTHY.value:
        return False
    if max_staleness_sec is not None and max_staleness_sec > 0:
        updated = entry.get("updated_at", 0)
        if time.time() - updated > max_staleness_sec:
            return False
    return True


def get_all_health() -> Dict[str, Dict[str, Any]]:
    """Return full registry for health endpoint."""
    with _lock:
        return {k: dict(v) for k, v in _registry.items()}


def mark_degraded(subsystem: str, reason: str, trace_id: Optional[str] = None) -> None:
    """Convenience: mark subsystem degraded (e.g. after repeated failures)."""
    set_health(subsystem, HealthState.DEGRADED, reason=reason, trace_id=trace_id)


def mark_unavailable(subsystem: str, reason: str, trace_id: Optional[str] = None) -> None:
    """Convenience: mark subsystem unavailable."""
    set_health(subsystem, HealthState.UNAVAILABLE, reason=reason, trace_id=trace_id)


def mark_healthy(subsystem: str, trace_id: Optional[str] = None) -> None:
    """Convenience: mark subsystem healthy."""
    set_health(subsystem, HealthState.HEALTHY, reason="", trace_id=trace_id)
