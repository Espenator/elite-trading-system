"""Finviz screener agent: screener results → swarm.idea + idea escalation."""
from __future__ import annotations

import logging
import os
from typing import Any, List

from app.services.firehose.base_agent import BaseFirehoseAgent
from app.services.firehose.schemas import SensoryEvent, SensorySource

logger = logging.getLogger(__name__)


class FinvizScreenerAgent(BaseFirehoseAgent):
    """Polls Finviz screener; publishes results to swarm.idea."""

    agent_id = "finviz_screener"
    poll_interval_sec = 300.0

    async def fetch(self) -> List[SensoryEvent]:
        events: List[SensoryEvent] = []
        try:
            from app.services.finviz_service import FinvizService
            svc = FinvizService()
            rows = await svc.get_screener()
            for r in (rows or [])[:15]:
                sym = (r.get("Ticker") or r.get("symbol") or r.get("Symbol") or "").strip()
                if not sym:
                    continue
                events.append(
                    SensoryEvent(
                        source=SensorySource.FINVIZ,
                        symbol=sym,
                        symbols=[sym],
                        payload=dict(r),
                        direction="bullish",
                        priority=4,
                        topic_hint="swarm.idea",
                    )
                )
        except Exception as e:
            logger.debug("Finviz screener fetch: %s", e)
        return events
