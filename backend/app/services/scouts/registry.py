"""ScoutRegistry — manages all 12 scout agents (E2).

Usage:
    registry = get_scout_registry()
    await registry.start(message_bus)
    ...
    await registry.stop()
"""
import logging
from typing import Dict, List, Optional, Type

from app.services.scouts.base import BaseScout

logger = logging.getLogger(__name__)


class ScoutRegistry:
    """Manages the lifecycle of all registered scout agents."""

    def __init__(self):
        self._scouts: List[BaseScout] = []
        self._started = False
        self._health_aggregator = None

    # ──────────────────────────────────────────────────────────────────────
    # Registration
    # ──────────────────────────────────────────────────────────────────────

    def register(self, scout_class: Type[BaseScout], message_bus=None) -> BaseScout:
        scout = scout_class(message_bus=message_bus)
        self._scouts.append(scout)
        return scout

    def register_instance(self, scout: BaseScout) -> None:
        self._scouts.append(scout)

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def start(self, message_bus=None) -> None:
        """Instantiate all 12 scouts and start them."""
        if self._started:
            return

        from app.services.scouts.flow_hunter import FlowHunterScout
        from app.services.scouts.insider import InsiderScout
        from app.services.scouts.congress import CongressScout
        from app.services.scouts.gamma import GammaScout
        from app.services.scouts.news import NewsScout
        from app.services.scouts.sentiment import SentimentScout
        from app.services.scouts.macro import MacroScout
        from app.services.scouts.earnings import EarningsScout
        from app.services.scouts.sector_rotation import SectorRotationScout
        from app.services.scouts.short_squeeze import ShortSqueezeScout
        from app.services.scouts.ipo import IPOScout
        from app.services.scouts.correlation_break import CorrelationBreakScout

        scout_classes = [
            FlowHunterScout,
            InsiderScout,
            CongressScout,
            GammaScout,
            NewsScout,
            SentimentScout,
            MacroScout,
            EarningsScout,
            SectorRotationScout,
            ShortSqueezeScout,
            IPOScout,
            CorrelationBreakScout,
        ]

        for cls in scout_classes:
            scout = cls(message_bus=message_bus)
            self._scouts.append(scout)
            await scout.start()

        # Start the HealthAggregator — subscribes to scout.heartbeat from all
        # individual scouts and publishes a single consolidated heartbeat every
        # 60 seconds instead of 28 individual events per minute.
        from app.services.scouts.health_aggregator import HealthAggregator
        self._health_aggregator = HealthAggregator(message_bus=message_bus)
        await self._health_aggregator.start()

        self._started = True
        logger.info("ScoutRegistry started %d scouts", len(self._scouts))

    async def stop(self) -> None:
        if self._health_aggregator:
            try:
                await self._health_aggregator.stop()
            except Exception as exc:
                logger.warning("Error stopping HealthAggregator: %s", exc)
            self._health_aggregator = None
        for scout in self._scouts:
            try:
                await scout.stop()
            except Exception as exc:
                logger.warning("Error stopping scout %s: %s", scout.name, exc)
        self._scouts.clear()
        self._started = False
        logger.info("ScoutRegistry stopped all scouts")

    # ──────────────────────────────────────────────────────────────────────
    # Introspection
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, dict]:
        return {s.name: s.get_stats() for s in self._scouts}

    def get_health(self) -> Dict:
        """Return aggregated health status from the HealthAggregator."""
        if self._health_aggregator:
            return self._health_aggregator.get_status()
        return {"scout_count": len(self._scouts), "scouts": {}, "aggregated_at": None}

    @property
    def scout_count(self) -> int:
        return len(self._scouts)

    @property
    def scouts(self) -> List[BaseScout]:
        return list(self._scouts)


_registry: Optional[ScoutRegistry] = None


def get_scout_registry() -> ScoutRegistry:
    global _registry
    if _registry is None:
        _registry = ScoutRegistry()
    return _registry
