"""Unusual Whales agent: flow, dark pool, congress → swarm.idea + perception topics."""
from __future__ import annotations

import logging
import os
from typing import Any, List

from app.services.firehose.base_agent import BaseFirehoseAgent
from app.services.firehose.schemas import SensoryEvent, SensorySource

logger = logging.getLogger(__name__)


class UnusualWhalesAgent(BaseFirehoseAgent):
    """Polls Unusual Whales API; publishes flow/darkpool/congress to swarm.idea + perception.*."""

    agent_id = "unusual_whales"
    poll_interval_sec = 120.0

    async def fetch(self) -> List[SensoryEvent]:
        events: List[SensoryEvent] = []
        if not os.getenv("UNUSUAL_WHALES_API_KEY"):
            return events
        try:
            from app.services.unusual_whales_service import UnusualWhalesService
            uw = UnusualWhalesService()
            data = await uw.get_flow_alerts()
            items = data if isinstance(data, list) else (data.get("items") or data.get("data") or [data] if isinstance(data, dict) else [])
            for a in (items or [])[:10]:
                if not isinstance(a, dict):
                    continue
                sym = a.get("ticker") or a.get("symbol") or ""
                events.append(
                    SensoryEvent(
                        source=SensorySource.UNUSUAL_WHALES,
                        symbol=sym,
                        symbols=[sym] if sym else [],
                        payload=a,
                        direction="bullish" if a.get("sentiment") == "bullish" else "bearish",
                        priority=2,
                        topic_hint="swarm.idea",
                    )
                )
        except Exception as e:
            logger.debug("Unusual Whales fetch: %s", e)
        return events
