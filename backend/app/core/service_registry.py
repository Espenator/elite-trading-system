"""
Service Registry — tracks which services started successfully.

AUDIT FIX (Task 8): Each service starts with independent error handling.
Failed services don't prevent subsequent services from starting.
The registry is exposed in /readyz so operators and the HITL gate know
which intelligence layers are actually active.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ServiceInfo:
    name: str
    status: ServiceStatus = ServiceStatus.PENDING
    started_at: Optional[float] = None
    error: Optional[str] = None
    category: str = "core"  # core, intelligence, data, monitoring


_registry: Dict[str, ServiceInfo] = {}


def register_service(name: str, category: str = "core") -> ServiceInfo:
    """Register a service for tracking."""
    info = ServiceInfo(name=name, category=category)
    _registry[name] = info
    return info


def mark_started(name: str):
    """Mark a service as successfully started."""
    if name in _registry:
        _registry[name].status = ServiceStatus.STARTED
        _registry[name].started_at = time.time()


def mark_failed(name: str, error: str):
    """Mark a service as failed to start."""
    if name in _registry:
        _registry[name].status = ServiceStatus.FAILED
        _registry[name].error = error
    logger.error("Service %s failed to start: %s", name, error)


def mark_stopped(name: str):
    """Mark a service as stopped."""
    if name in _registry:
        _registry[name].status = ServiceStatus.STOPPED


def get_health_summary() -> Dict:
    """Get a summary of all service states for /readyz."""
    started = [n for n, s in _registry.items() if s.status == ServiceStatus.STARTED]
    failed = [n for n, s in _registry.items() if s.status == ServiceStatus.FAILED]
    pending = [n for n, s in _registry.items() if s.status == ServiceStatus.PENDING]

    return {
        "total_services": len(_registry),
        "started": len(started),
        "failed": len(failed),
        "pending": len(pending),
        "services": {
            name: {
                "status": info.status.value,
                "category": info.category,
                "error": info.error,
            }
            for name, info in _registry.items()
        },
        "failed_services": failed,
        "intelligence_degraded": any(
            _registry[n].status == ServiceStatus.FAILED
            for n in _registry
            if _registry[n].category == "intelligence"
        ),
    }
