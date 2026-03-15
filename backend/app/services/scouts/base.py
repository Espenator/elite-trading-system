"""BaseScout — abstract base for all 12 dedicated scout agents (E2).

Each scout:
  - Runs on a configurable interval in the background
  - Publishes DiscoveryPayload events to ``swarm.idea``
  - Publishes health ticks to ``scout.heartbeat`` every 30 s
  - Is stateless between runs (idempotent)
  - Handles its own errors without crashing the task loop
  - Applies backpressure when the MessageBus queue is congested (B-fix)
  - Session-aware: runs 3x slower on weekends/overnight to free resources
"""
import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Backpressure thresholds (configurable via env)
_BACKPRESSURE_PCT = float(os.getenv("SCOUT_BACKPRESSURE_PCT", "90"))   # Pause at 90% (raised from 60% to avoid pausing during high-signal periods)
_MAX_PER_CYCLE = int(os.getenv("SCOUT_MAX_PER_CYCLE", "20"))           # Max discoveries per cycle


@dataclass
class DiscoveryPayload:
    """Standardised discovery event published to ``swarm.idea``."""

    source: str                     # e.g. "flow_hunter_scout"
    symbols: List[str]              # symbols of interest
    direction: str                  # bullish | bearish | neutral
    reasoning: str                  # human-readable explanation
    priority: int = 5               # 1 (highest) – 5 (lowest)
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_swarm_idea(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "symbols": self.symbols,
            "direction": self.direction,
            "reasoning": self.reasoning,
            "priority": self.priority,
            "metadata": {
                **self.metadata,
                "discovered_at": self.discovered_at,
            },
        }

    def to_heartbeat(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "status": "discovery",
            "symbols_count": len(self.symbols),
            "direction": self.direction,
            "priority": self.priority,
            "timestamp": self.discovered_at,
        }


class BaseScout(ABC):
    """Abstract base for all scout agents.

    Subclasses must implement:
        ``name``      — unique string identifier
        ``interval``  — seconds between scout cycles
        ``scout()``   — single-cycle discovery logic; returns list of payloads
    """

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats = {
            "cycles_run": 0,
            "discoveries_made": 0,
            "errors": 0,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Abstract interface
    # ──────────────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this scout (e.g. 'flow_hunter_scout')."""

    @property
    @abstractmethod
    def interval(self) -> float:
        """Seconds between scout cycles."""

    @abstractmethod
    async def scout(self) -> List[DiscoveryPayload]:
        """Run one discovery cycle and return zero or more payloads."""

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Scout started: %s (interval=%.0fs)", self.name, self.interval)

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._heartbeat_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        logger.info("Scout stopped: %s", self.name)

    # ──────────────────────────────────────────────────────────────────────
    # Internal loops
    # ──────────────────────────────────────────────────────────────────────

    def _get_effective_interval(self) -> float:
        """Return session-aware interval: 3x slower on weekends/overnight."""
        try:
            from app.services.session_manager import get_current_session, WEEKEND, OVERNIGHT
            session = get_current_session()
            if session == WEEKEND:
                return max(self.interval * 3, 300)  # At least 5 min on weekends
            if session == OVERNIGHT:
                return max(self.interval * 2, 120)  # At least 2 min overnight
        except Exception:
            pass
        return self.interval

    async def _run_loop(self) -> None:
        while self._running:
            try:
                # Backpressure: wait if queue is congested before even running cycle
                await self._wait_for_backpressure()

                payloads = await self.scout()
                self._stats["cycles_run"] += 1
                published = 0
                for payload in payloads or []:
                    if published >= _MAX_PER_CYCLE:
                        self._stats["throttled"] = self._stats.get("throttled", 0) + 1
                        logger.debug(
                            "Scout %s hit per-cycle cap (%d), deferring remaining",
                            self.name, _MAX_PER_CYCLE,
                        )
                        break
                    # Re-check backpressure between publishes
                    if self._is_queue_congested():
                        self._stats["backpressure_skips"] = (
                            self._stats.get("backpressure_skips", 0) + 1
                        )
                        logger.info(
                            "Scout %s pausing mid-cycle — queue congested", self.name
                        )
                        break
                    await self._publish(payload)
                    published += 1
                    self._stats["discoveries_made"] += 1
                    # Yield to event loop between publishes to avoid starving consumers
                    await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("Scout %s error: %s", self.name, exc)
            await asyncio.sleep(self._get_effective_interval())

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(30)
            if not self._running:
                break
            if self._bus:
                try:
                    await self._bus.publish("scout.heartbeat", {
                        "source": self.name,
                        "status": "healthy",
                        "stats": dict(self._stats),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as exc:
                    logger.debug("%s heartbeat failed: %s", self.name, exc)

    def _is_queue_congested(self) -> bool:
        """Return True if MessageBus queue is above backpressure threshold."""
        if not self._bus:
            return False
        try:
            return self._bus.queue_usage_pct >= _BACKPRESSURE_PCT
        except Exception:
            return False

    async def _wait_for_backpressure(self, max_wait: float = 30.0) -> None:
        """Block until queue drops below backpressure threshold (or timeout)."""
        if not self._is_queue_congested():
            return
        logger.info(
            "Scout %s waiting — MessageBus queue at %.0f%% (threshold %.0f%%)",
            self.name, self._bus.queue_usage_pct, _BACKPRESSURE_PCT,
        )
        waited = 0.0
        while self._running and self._is_queue_congested() and waited < max_wait:
            await asyncio.sleep(1.0)
            waited += 1.0
        if waited >= max_wait:
            logger.warning(
                "Scout %s backpressure timeout (%.0fs) — skipping cycle", self.name, max_wait
            )

    async def _publish(self, payload: DiscoveryPayload) -> None:
        if not self._bus:
            return
        try:
            await self._bus.publish("swarm.idea", payload.to_swarm_idea())
            logger.debug(
                "Scout %s discovered: symbols=%s direction=%s",
                self.name, payload.symbols, payload.direction,
            )
        except Exception as exc:
            logger.warning("Scout %s publish failed: %s", self.name, exc)

    # ──────────────────────────────────────────────────────────────────────
    # Public helpers
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        if self._bus:
            try:
                stats["queue_usage_pct"] = round(self._bus.queue_usage_pct, 1)
            except Exception:
                pass
        return stats
