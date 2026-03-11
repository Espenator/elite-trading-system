from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.services.channels.base_channel_agent import BaseChannelAgent
from app.services.channels.schemas import SensoryEvent
from app.services.discord_swarm_bridge import DiscordSwarmBridge

logger = logging.getLogger(__name__)


class DiscordChannelAgent(BaseChannelAgent):
    """Discord ingestion agent that emits SensoryEvent instead of direct swarm.publish()."""

    def __init__(self, *, message_bus: Any, router: Any) -> None:
        super().__init__(
            name="discord_firehose",
            router=router,
            message_bus=message_bus,
            max_queue_size=int(os.getenv("DISCORD_FIREHOSE_QUEUE", "2000")),
        )
        self._bus = message_bus
        self._bridge = DiscordSwarmBridge(message_bus=message_bus)

    async def start(self) -> None:
        await super().start()
        await self._bridge.start()
        logger.info("DiscordChannelAgent started (bridge polling active)")

    async def stop(self) -> None:
        try:
            await self._bridge.stop()
        except Exception:
            pass
        await super().stop()

    async def _on_discord_signal(self, payload: Dict[str, Any]) -> None:
        symbols = payload.get("symbols") or []
        ev = SensoryEvent.from_discord_signal(
            symbols=symbols,
            direction=payload.get("direction", "unknown"),
            text=payload.get("raw_content", payload.get("reasoning", "")) or "",
            channel=((payload.get("metadata") or {}).get("channel") or "unknown"),
            source_type=((payload.get("metadata") or {}).get("source_type") or "unknown"),
            message_id=str(((payload.get("provenance") or {}).get("message_id") or "")),
            author=str(((payload.get("provenance") or {}).get("author") or "")),
            data_quality="live",
        )

        channel = (ev.normalized.get("channel") or "").lower()
        if "alert" in channel or "options" in channel or "flow" in channel:
            ev.priority = min(95, max(ev.priority, 75))
            ev.tags = list(dict.fromkeys(ev.tags + ["alert"]))

        await self.enqueue(ev)
