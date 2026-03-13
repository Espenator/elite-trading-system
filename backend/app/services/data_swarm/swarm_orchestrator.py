"""Swarm orchestrator — spawns and kills data collectors by session. Integrates with circuit_breaker for emergency shutdown."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from app.core.message_bus import get_message_bus
from app.services.data_swarm.session_clock import get_session_clock, TradingSession
from app.services.data_swarm.health_monitor import get_health_monitor

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """
    Spawns and manages data collector agents based on current trading session.
    Publishes swarm health to system.swarm.health channel.
    Integrates with council/reflexes/circuit_breaker for emergency shutdown.
    """

    def __init__(self, symbol_universe: List[str]) -> None:
        self.symbol_universe = symbol_universe
        self.clock = get_session_clock()
        self.health = get_health_monitor()
        self.collectors: Dict[str, "BaseCollector"] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def _create_collector(self, source_name: str) -> "BaseCollector":
        """Create collector instance by name."""
        from app.services.data_swarm.collectors import COLLECTOR_REGISTRY
        cls = COLLECTOR_REGISTRY.get(source_name)
        if cls is None:
            raise ValueError(f"Unknown collector: {source_name}")
        return cls(self.symbol_universe)

    async def run(self) -> None:
        """Main loop: check session every 60s, spawn/kill collectors, publish swarm health."""
        self._running = True
        bus = get_message_bus()
        while self._running:
            try:
                session = self.clock.get_current_session()
                active_sources = self.clock.get_active_sources()

                for source_name, should_run in active_sources.items():
                    if should_run and source_name not in self.tasks:
                        await self.spawn(source_name)
                    elif not should_run and source_name in self.tasks:
                        await self.kill(source_name)

                await bus.publish("system.swarm.health", {
                    "session": session.value if isinstance(session, TradingSession) else str(session),
                    "active_collectors": list(self.tasks.keys()),
                    "collector_health": self.health.get_status(),
                    "data_freshness": self.health.get_freshness(),
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("SwarmOrchestrator loop error: %s", e)
            await asyncio.sleep(60)

        await self.emergency_shutdown()

    async def spawn(self, source_name: str) -> None:
        """Create collector instance and start as asyncio task."""
        try:
            collector = self._create_collector(source_name)
            self.collectors[source_name] = collector
            self.tasks[source_name] = asyncio.create_task(
                collector.run(),
                name=f"collector_{source_name}",
            )
            logger.info("SWARM SPAWNED: %s", source_name)
        except Exception as e:
            logger.warning("SWARM spawn %s failed: %s", source_name, e)

    async def kill(self, source_name: str) -> None:
        """Gracefully shutdown collector."""
        if source_name not in self.collectors:
            return
        collector = self.collectors[source_name]
        collector.request_stop()
        task = self.tasks.get(source_name)
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        await collector.disconnect()
        self.collectors.pop(source_name, None)
        self.tasks.pop(source_name, None)
        logger.info("SWARM KILLED: %s", source_name)

    async def emergency_shutdown(self) -> None:
        """Circuit breaker triggered — kill everything."""
        for name in list(self.tasks.keys()):
            await self.kill(name)
        self._running = False
        logger.info("SWARM emergency shutdown complete")

    def request_stop(self) -> None:
        """Signal the orchestrator loop to exit."""
        self._running = False


def get_swarm_orchestrator(symbol_universe: Optional[List[str]] = None) -> SwarmOrchestrator:
    """Factory with default symbol universe if not provided."""
    default_universe = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "CRM",
        "NFLX", "ORCL", "ADBE", "INTC", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
        "JPM", "GS", "MS", "BAC", "WFC", "V", "MA", "AXP", "UNH",
        "XOM", "CVX", "COP", "SLB", "LMT", "RTX", "BA", "CAT", "DE", "GE",
        "PG", "KO", "PEP", "JNJ", "MRK", "LLY", "ABBV", "TMO", "DHR", "ABT",
        "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "ARKK", "TLT", "GLD", "SLV",
    ]
    return SwarmOrchestrator(symbol_universe or default_universe)
