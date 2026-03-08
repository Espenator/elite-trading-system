"""ScoutRegistry — orchestration hub for all 12 dedicated discovery scouts.

The registry is the single control plane for the scout fleet:
  * Registers all 12 concrete scouts at import time.
  * Starts / stops all scouts as a unit during app lifespan.
  * Provides per-scout restart without full fleet restart.
  * Exposes aggregate health for the status API.

Usage (wired in ``main.py``)::

    from app.services.scouts.registry import get_scout_registry

    registry = get_scout_registry()

    # startup
    await registry.start_all(message_bus)

    # shutdown
    await registry.stop_all()

    # health check
    status = registry.get_status()

Individual scouts may also be restarted::

    await registry.restart_scout("finviz_momentum")
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.services.scouts.base_scout import BaseScout

if TYPE_CHECKING:
    from app.core.message_bus import MessageBus

logger = logging.getLogger(__name__)


def _build_scout_fleet() -> List[BaseScout]:
    """Instantiate all 12 dedicated scout agents.

    Import order determines startup order.  Each import is protected so a
    broken scout never prevents the others from loading.
    """
    scouts: List[BaseScout] = []
    scout_classes = [
        ("app.services.scouts.alpaca_trade_scout", "AlpacaTradeScout"),
        ("app.services.scouts.alpaca_news_scout", "AlpacaNewsScout"),
        ("app.services.scouts.alpaca_premarket_scout", "AlpacaPremarketScout"),
        ("app.services.scouts.unusual_whales_flow_scout", "UnusualWhalesFlowScout"),
        ("app.services.scouts.unusual_whales_darkpool_scout", "UnusualWhalesDarkpoolScout"),
        ("app.services.scouts.finviz_momentum_scout", "FinvizMomentumScout"),
        ("app.services.scouts.finviz_breakout_scout", "FinvizBreakoutScout"),
        ("app.services.scouts.fred_macro_scout", "FredMacroScout"),
        ("app.services.scouts.sec_edgar_scout", "SecEdgarScout"),
        ("app.services.scouts.news_sentiment_scout", "NewsSentimentScout"),
        ("app.services.scouts.social_sentiment_scout", "SocialSentimentScout"),
        ("app.services.scouts.sector_rotation_scout", "SectorRotationScout"),
    ]
    for module_path, class_name in scout_classes:
        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            scouts.append(cls())
            logger.debug("Registered scout: %s", class_name)
        except Exception as exc:
            logger.error("Failed to load scout %s.%s: %s", module_path, class_name, exc)
    return scouts


class ScoutRegistry:
    """Central registry and lifecycle manager for the 12 scout fleet.

    Thread-safety note: all public methods are coroutines and must be
    called from the same event loop as the FastAPI application.
    """

    def __init__(self) -> None:
        self._scouts: Dict[str, BaseScout] = {}
        self._bus: Optional["MessageBus"] = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Registration (used internally by _build_scout_fleet)
    # ------------------------------------------------------------------

    def register(self, scout: BaseScout) -> None:
        """Add a scout to the registry.  Raises if ``scout_id`` is duplicate."""
        if scout.scout_id in self._scouts:
            raise ValueError(f"Scout '{scout.scout_id}' already registered")
        self._scouts[scout.scout_id] = scout

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_all(self, bus: "MessageBus") -> None:
        """Start all registered scouts against the given message bus.

        Safe to call multiple times — already-running scouts are skipped.
        """
        self._bus = bus

        # Lazy-load fleet on first start
        if not self._scouts:
            for scout in _build_scout_fleet():
                if scout.scout_id not in self._scouts:
                    self._scouts[scout.scout_id] = scout

        self._running = True
        started = 0
        for scout_id, scout in self._scouts.items():
            if scout._running:
                continue
            try:
                await scout.start(bus)
                started += 1
            except Exception as exc:
                logger.error("Failed to start scout '%s': %s", scout_id, exc)

        logger.info(
            "ScoutRegistry: %d/%d scouts started",
            started, len(self._scouts),
        )

    async def stop_all(self) -> None:
        """Stop all running scouts gracefully."""
        self._running = False
        stop_tasks = [
            scout.stop()
            for scout in self._scouts.values()
            if scout._running
        ]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        logger.info("ScoutRegistry: all scouts stopped")

    async def restart_scout(self, scout_id: str) -> None:
        """Stop and restart a single scout by ID."""
        scout = self._scouts.get(scout_id)
        if scout is None:
            raise KeyError(f"Scout '{scout_id}' not found in registry")
        if scout._running:
            await scout.stop()
        if self._bus:
            await scout.start(self._bus)
            logger.info("ScoutRegistry: restarted scout '%s'", scout_id)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate fleet status suitable for the /status API."""
        scouts_status = {}
        running_count = 0
        error_count = 0
        total_discoveries = 0

        for scout_id, scout in self._scouts.items():
            health = scout.get_health()
            scouts_status[scout_id] = health.to_dict()
            if health.status == "running":
                running_count += 1
            elif health.status == "error":
                error_count += 1
            total_discoveries += health.total_discoveries

        return {
            "fleet_running": self._running,
            "total_scouts": len(self._scouts),
            "running_scouts": running_count,
            "error_scouts": error_count,
            "total_discoveries": total_discoveries,
            "scouts": scouts_status,
        }

    def get_scout_ids(self) -> List[str]:
        """Return list of all registered scout IDs."""
        return list(self._scouts.keys())

    def get_scout(self, scout_id: str) -> Optional[BaseScout]:
        """Return a specific scout by ID, or None."""
        return self._scouts.get(scout_id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: Optional[ScoutRegistry] = None


def get_scout_registry() -> ScoutRegistry:
    """Return the application-wide ScoutRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = ScoutRegistry()
    return _registry
