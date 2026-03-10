"""Firehose orchestrator: registry, start/stop, pause/resume, status."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.services.firehose.metrics import get_metrics

logger = logging.getLogger(__name__)


class FirehoseOrchestrator:
    """Registry and lifecycle for firehose spine agents."""

    def __init__(self, message_bus: Any):
        self.message_bus = message_bus
        self._agents: Dict[str, Any] = {}
        self._running = False
        self._paused = False

    def register(self, agent: Any) -> None:
        aid = getattr(agent, "agent_id", agent.__class__.__name__)
        self._agents[aid] = agent
        logger.info("Firehose registered agent: %s", aid)

    async def start(self) -> None:
        self._running = True
        for aid, agent in self._agents.items():
            if hasattr(agent, "start"):
                await agent.start()
        logger.info("Firehose orchestrator started (%d agents)", len(self._agents))

    async def stop(self) -> None:
        self._running = False
        for aid, agent in self._agents.items():
            if hasattr(agent, "stop"):
                try:
                    await agent.stop()
                except Exception as e:
                    logger.warning("Firehose agent %s stop error: %s", aid, e)
        logger.info("Firehose orchestrator stopped")

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def get_status(self) -> Dict[str, Any]:
        agents = {}
        for aid, agent in self._agents.items():
            agents[aid] = agent.get_status() if hasattr(agent, "get_status") else {"agent_id": aid}
        return {
            "running": self._running,
            "paused": self._paused,
            "agents": agents,
            "metrics": get_metrics(),
        }


_orchestrator: Optional[FirehoseOrchestrator] = None


async def ensure_orchestrator_started(message_bus: Any) -> FirehoseOrchestrator:
    """Create orchestrator, register spine agents, start. Idempotent."""
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator
    from app.services.firehose.agents.alpaca_streaming_agent import AlpacaStreamingAgent
    from app.services.firehose.agents.discord_ingest_agent import DiscordIngestAgent
    from app.services.firehose.agents.finviz_screener_agent import FinvizScreenerAgent
    from app.services.firehose.agents.unusual_whales_agent import UnusualWhalesAgent

    orch = FirehoseOrchestrator(message_bus)
    orch.register(AlpacaStreamingAgent(message_bus))
    orch.register(DiscordIngestAgent(message_bus))
    orch.register(UnusualWhalesAgent(message_bus))
    orch.register(FinvizScreenerAgent(message_bus))
    await orch.start()
    _orchestrator = orch
    return orch
