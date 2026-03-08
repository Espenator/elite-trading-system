"""Health and metrics primitives for source adapters."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class HealthStatus(str, Enum):
    """Health status of a source adapter."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILURE = "auth_failure"
    OFFLINE = "offline"


@dataclass
class HealthMetrics:
    """Health and performance metrics for a source adapter.

    Attributes:
        status: Current health status
        last_success: Timestamp of last successful operation
        last_error: Timestamp of last error
        consecutive_errors: Number of consecutive errors
        total_events: Total events emitted
        events_last_hour: Events in the last hour
        average_latency_ms: Average latency in milliseconds
        error_rate: Error rate (0.0 to 1.0)
        metadata: Additional metrics (rate limit info, etc.)
    """

    status: HealthStatus = HealthStatus.HEALTHY
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    consecutive_errors: int = 0
    total_events: int = 0
    events_last_hour: int = 0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error.isoformat() if self.last_error else None,
            "consecutive_errors": self.consecutive_errors,
            "total_events": self.total_events,
            "events_last_hour": self.events_last_hour,
            "average_latency_ms": self.average_latency_ms,
            "error_rate": self.error_rate,
            "metadata": self.metadata,
        }

    def is_healthy(self) -> bool:
        """Check if the adapter is healthy."""
        return self.status == HealthStatus.HEALTHY

    def is_degraded(self) -> bool:
        """Check if the adapter is degraded but still operational."""
        return self.status == HealthStatus.DEGRADED

    def is_available(self) -> bool:
        """Check if the adapter is available (healthy or degraded)."""
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
