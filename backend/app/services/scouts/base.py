"""BaseScout — abstract base for all 12 dedicated scout agents (E2).

Each scout:
  - Runs on a configurable interval in the background
  - Publishes DiscoveryPayload events to ``swarm.idea``
  - Publishes health ticks to ``scout.heartbeat`` every 30 s
  - Is stateless between runs (idempotent)
  - Handles its own errors without crashing the task loop
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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

    async def _run_loop(self) -> None:
        while self._running:
            try:
                payloads = await self.scout()
                self._stats["cycles_run"] += 1
                for payload in payloads or []:
                    await self._publish(payload)
                    self._stats["discoveries_made"] += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("Scout %s error: %s", self.name, exc)
            await asyncio.sleep(self.interval)

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
        return dict(self._stats)
