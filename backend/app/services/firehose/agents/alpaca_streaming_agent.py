"""Alpaca streaming agent: subscribes to market_data.bar, forwards anomalies to swarm.idea."""
from __future__ import annotations

import logging
from typing import Any, List

from app.services.firehose.base_agent import BaseFirehoseAgent
from app.services.firehose.schemas import SensoryEvent, SensorySource

logger = logging.getLogger(__name__)


class AlpacaStreamingAgent(BaseFirehoseAgent):
    """Listens to market_data.bar (from AlpacaStreamManager), emits swarm.idea for anomalies."""

    agent_id = "alpaca_streaming"

    def __init__(self, message_bus: Any):
        super().__init__(message_bus)
        self._subscribed = False
        self._bars_seen = 0

    async def start(self) -> None:
        self._running = True
        if self.message_bus:
            await self.message_bus.subscribe("market_data.bar", self._on_bar)
            self._subscribed = True
        logger.info("Firehose AlpacaStreamingAgent started (subscribed to market_data.bar)")

    async def stop(self) -> None:
        if self._subscribed and self.message_bus:
            await self.message_bus.unsubscribe("market_data.bar", self._on_bar)
            self._subscribed = False
        self._running = False

    async def _on_bar(self, bar_data: dict) -> None:
        self._bars_seen += 1
        vol = bar_data.get("volume") or 0
        high = float(bar_data.get("high") or 0)
        low = float(bar_data.get("low") or 0)
        close = float(bar_data.get("close") or 0)
        if high <= 0:
            return
        range_pct = (high - low) / high * 100 if high else 0
        if range_pct >= 5.0 or (vol and vol > 500_000):
            event = SensoryEvent(
                source=SensorySource.ALPACA_STREAM,
                symbol=bar_data.get("symbol"),
                symbols=[bar_data["symbol"]] if bar_data.get("symbol") else [],
                payload=dict(bar_data),
                direction="unknown",
                priority=4,
                topic_hint="swarm.idea",
            )
            event.payload["reasoning"] = f"Bar range {range_pct:.1f}% or high volume"
            self.enqueue(event)

    async def fetch(self) -> List[SensoryEvent]:
        return []

    def get_status(self) -> dict:
        s = super().get_status()
        s["bars_seen"] = self._bars_seen
        s["subscribed"] = self._subscribed
        return s
