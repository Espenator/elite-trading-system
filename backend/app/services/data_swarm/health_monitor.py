"""Health monitor for data swarm collectors — heartbeats, freshness, failover."""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

HEARTBEAT_EXPECT_INTERVAL = 30.0
UNHEALTHY_THRESHOLD = 90.0   # seconds without heartbeat
DEAD_THRESHOLD = 180.0       # seconds — notify orchestrator to respawn
STALE_DATA_THRESHOLD = 120.0 # seconds during regular hours — STALE warning


class HealthMonitor:
    """Tracks last_heartbeat per collector; data_freshness per symbol."""

    def __init__(self) -> None:
        self._last_heartbeat: Dict[str, float] = {}
        self._last_price_time: Dict[str, float] = {}  # symbol -> timestamp
        self._status: Dict[str, str] = {}  # collector -> "healthy" | "unhealthy" | "dead"

    def record_heartbeat(self, source: str) -> None:
        """Called when a collector publishes system.collector.health heartbeat."""
        now = time.monotonic()
        self._last_heartbeat[source] = now
        self._status[source] = "healthy"

    def record_price(self, symbol: str) -> None:
        """Record that we got a price update for symbol (for freshness)."""
        self._last_price_time[symbol] = time.monotonic()

    def get_status(self) -> Dict[str, str]:
        """Return current status per collector: healthy, unhealthy, dead."""
        now = time.monotonic()
        for source, t in list(self._last_heartbeat.items()):
            age = now - t
            if age > DEAD_THRESHOLD:
                self._status[source] = "dead"
            elif age > UNHEALTHY_THRESHOLD:
                self._status[source] = "unhealthy"
            else:
                self._status[source] = "healthy"
        return dict(self._status)

    def get_freshness(self) -> Dict[str, float]:
        """Return seconds since last price update per symbol."""
        now = time.monotonic()
        return {s: now - t for s, t in self._last_price_time.items()}

    def get_stale_symbols(self, threshold_sec: float = STALE_DATA_THRESHOLD) -> list:
        """Symbols with no update in threshold_sec (for regular-hours STALE warning)."""
        now = time.monotonic()
        return [s for s, t in self._last_price_time.items() if (now - t) > threshold_sec]


_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Singleton health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
