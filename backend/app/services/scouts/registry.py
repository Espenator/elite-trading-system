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

        # Stagger startup: each scout gets an initial delay to avoid thundering herd.
        # 2-second spacing means all 12 scouts fire their first cycle within ~24s.
        _stagger_seconds = float(__import__("os").getenv("SCOUT_STAGGER_DELAY", "2.0"))
        for idx, cls in enumerate(scout_classes):
            scout = cls(message_bus=message_bus, initial_delay=idx * _stagger_seconds)
            self._scouts.append(scout)
            await scout.start()

        self._started = True
        logger.info("ScoutRegistry started %d scouts (stagger=%.1fs)", len(self._scouts), _stagger_seconds)

    async def stop(self) -> None:
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
