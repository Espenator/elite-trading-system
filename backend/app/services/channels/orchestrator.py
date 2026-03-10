from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from app.services.channels.alpaca_channel_agent import AlpacaChannelAgent
from app.services.channels.discord_channel_agent import DiscordChannelAgent
from app.services.channels.uw_channel_agent import UWChannelAgent
from app.services.channels.finviz_channel_agent import FinvizChannelAgent
from app.services.channels.news_channel_agent import NewsChannelAgent
from app.services.channels.router import SensoryRouter

logger = logging.getLogger(__name__)


class ChannelsOrchestrator:
    def __init__(self, *, message_bus: Any) -> None:
        self._bus = message_bus
        self._router = SensoryRouter(message_bus)
        self._agents: Dict[str, Any] = {}
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        alpaca = AlpacaChannelAgent(message_bus=self._bus, router=self._router)
        discord = DiscordChannelAgent(message_bus=self._bus, router=self._router)
        uw = UWChannelAgent(message_bus=self._bus, router=self._router)
        finviz = FinvizChannelAgent(message_bus=self._bus, router=self._router)
        news = NewsChannelAgent(message_bus=self._bus, router=self._router)

        self._agents = {
            alpaca.name: alpaca,
            discord.name: discord,
            uw.name: uw,
            finviz.name: finviz,
            news.name: news,
        }

        for agent in self._agents.values():
            await agent.start()

        logger.info("ChannelsOrchestrator started (%d agents)", len(self._agents))

    async def stop(self) -> None:
        self._running = False
        for agent in self._agents.values():
            try:
                await agent.stop()
            except Exception:
                pass
        logger.info("ChannelsOrchestrator stopped")

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "agents": {name: agent.get_status() for name, agent in self._agents.items()},
            "router_metrics": self._router.get_metrics(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "router": self._router.get_metrics(),
            "agents": {name: agent.get_metrics() for name, agent in self._agents.items()},
            "bus": self._bus.get_metrics() if hasattr(self._bus, "get_metrics") else {},
        }

    async def pause(self, agent_name: str) -> bool:
        agent = self._agents.get(agent_name)
        if not agent:
            return False
        await agent.pause()
        return True

    async def resume(self, agent_name: str) -> bool:
        agent = self._agents.get(agent_name)
        if not agent:
            return False
        await agent.resume()
        return True


_orchestrator: Optional[ChannelsOrchestrator] = None


def get_channels_orchestrator(message_bus: Any | None = None) -> ChannelsOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        if message_bus is None:
            raise RuntimeError("ChannelsOrchestrator not initialized (message_bus required)")
        _orchestrator = ChannelsOrchestrator(message_bus=message_bus)
    return _orchestrator


async def ensure_orchestrator_started(message_bus: Any) -> ChannelsOrchestrator:
    orch = get_channels_orchestrator(message_bus)
    if not orch.is_running():
        await orch.start()
    return orch
