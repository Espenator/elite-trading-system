"""Discord ingest agent: polls Discord channels, publishes social/alerts to swarm.idea."""
from __future__ import annotations

import logging
import os
from typing import Any, List

from app.services.firehose.base_agent import BaseFirehoseAgent
from app.services.firehose.schemas import SensoryEvent, SensorySource

logger = logging.getLogger(__name__)


class DiscordIngestAgent(BaseFirehoseAgent):
    """Polls Discord (or stub); publishes alerts as swarm.idea + perception topic."""

    agent_id = "discord_ingest"
    poll_interval_sec = 60.0

    async def fetch(self) -> List[SensoryEvent]:
        events: List[SensoryEvent] = []
        if not os.getenv("DISCORD_BOT_TOKEN"):
            return events
        try:
            from app.services.discord_swarm_bridge import get_discord_bridge
            bridge = get_discord_bridge()
            if not hasattr(bridge, "_last_messages"):
                return events
            for msg in getattr(bridge, "_last_messages", [])[-20:]:
                text = (msg.get("content") or msg.get("text") or "")[:500]
                if not text:
                    continue
                events.append(
                    SensoryEvent(
                        source=SensorySource.DISCORD,
                        symbols=[],
                        payload={"raw_content": text, "channel": msg.get("channel_id", "")},
                        direction="unknown",
                        priority=5,
                        topic_hint="swarm.idea",
                    )
                )
        except Exception as e:
            logger.debug("Discord ingest fetch: %s", e)
        return events
