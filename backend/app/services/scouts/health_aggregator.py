"""HealthAggregator — batches ``scout.heartbeat`` events from all sources.

Problem
───────
14 services (12 scouts + StreamingDiscoveryEngine + IdeaTriageService) each
publish an independent ``scout.heartbeat`` event every 30–60 seconds.  That
produces ≈28 events/minute on a topic with zero subscribers — pure overhead
on the MessageBus dispatch loop.

Solution
────────
``HealthAggregator`` subscribes to ``scout.heartbeat`` and merges every
incoming pulse into a single in-memory registry keyed by ``source``.  The
ScoutRegistry calls it every 60 seconds to publish one **consolidated**
``scout.heartbeat`` payload that carries all scouts' stats.

A service is considered *stale* after ``stale_after_secs`` seconds without
a heartbeat (default 120 s — 4× the 30-second base interval).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STALE_AFTER_SECS = 120  # 4× the 30-second scout heartbeat interval


class HealthAggregator:
    """Subscribes to ``scout.heartbeat`` and provides a consolidated view.

    Wire-up:
        aggregator = HealthAggregator(message_bus)
        await aggregator.start()
        ...
        status = aggregator.get_status()   # call from API / dashboard
        await aggregator.stop()
    """

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        # source → {status, stats, timestamp, last_seen_epoch}
        self._latest: Dict[str, Dict[str, Any]] = {}
        self._publish_task: Optional[asyncio.Task] = None

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("scout.heartbeat", self._on_heartbeat)
        self._publish_task = asyncio.create_task(self._publish_loop())
        logger.info("HealthAggregator started (stale_after=%ds)", STALE_AFTER_SECS)

    async def stop(self) -> None:
        self._running = False
        if self._publish_task:
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass
        logger.info("HealthAggregator stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Handler
    # ──────────────────────────────────────────────────────────────────────

    async def _on_heartbeat(self, data: Dict[str, Any]) -> None:
        """Merge an incoming heartbeat pulse into the in-memory registry."""
        source = data.get("source", "unknown")
        import time
        self._latest[source] = {
            "source": source,
            "status": data.get("status", "unknown"),
            "stats": data.get("stats", {}),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "last_seen_epoch": time.time(),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Publish loop — one consolidated heartbeat per minute
    # ──────────────────────────────────────────────────────────────────────

    async def _publish_loop(self) -> None:
        """Publish one aggregated ``scout.heartbeat`` per minute."""
        import time
        while self._running:
            await asyncio.sleep(60)
            if not self._running:
                break
            if not self._bus:
                continue
            try:
                now = time.time()
                sources = {}
                for src, entry in list(self._latest.items()):
                    age = now - entry["last_seen_epoch"]
                    sources[src] = {
                        "status": "stale" if age > STALE_AFTER_SECS else entry["status"],
                        "stats": entry["stats"],
                        "last_heartbeat": entry["timestamp"],
                        "age_secs": round(age, 1),
                    }
                await self._bus.publish("scout.heartbeat", {
                    "source": "health_aggregator",
                    "status": "healthy",
                    "scout_count": len(sources),
                    "scouts": sources,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as exc:
                logger.debug("HealthAggregator publish failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return the latest aggregated health snapshot (for dashboards/API)."""
        import time
        now = time.time()
        scouts = {}
        for src, entry in self._latest.items():
            age = now - entry["last_seen_epoch"]
            scouts[src] = {
                "status": "stale" if age > STALE_AFTER_SECS else entry["status"],
                "stats": entry["stats"],
                "last_heartbeat": entry["timestamp"],
                "age_secs": round(age, 1),
            }
        return {
            "scout_count": len(scouts),
            "scouts": scouts,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }
