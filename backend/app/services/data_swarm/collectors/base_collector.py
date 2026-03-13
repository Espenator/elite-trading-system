"""Abstract base collector — publish to MessageBus, heartbeat, backoff, graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30.0
BACKOFF_INITIAL = 1.0
BACKOFF_MAX = 60.0
BACKOFF_MULTIPLIER = 2.0


def utc_now() -> str:
    """ISO timestamp in UTC for message bus payloads."""
    return datetime.now(timezone.utc).isoformat()


class BaseCollector(ABC):
    """Base for all data swarm collectors. Handles publish, heartbeat, backoff, shutdown."""

    source_name: str = ""
    channels: List[str] = []
    poll_interval: float = 60.0
    is_streaming: bool = False

    def __init__(self, symbol_universe: List[str]) -> None:
        self.symbol_universe = symbol_universe
        self._stop = asyncio.Event()
        self._backoff_secs = BACKOFF_INITIAL
        self._last_heartbeat = 0.0
        self._bus = None

    async def publish(self, channel: str, data: Dict[str, Any]) -> None:
        """Publish normalized data to message_bus."""
        if self._bus is None:
            self._bus = get_message_bus()
        payload = {
            "source": self.source_name,
            "timestamp": utc_now(),
            "data": data,
        }
        await self._bus.publish(channel, payload)

    async def _heartbeat(self) -> None:
        """Emit heartbeat for health_monitor (every 30s)."""
        if self._bus is None:
            self._bus = get_message_bus()
        await self._bus.publish("system.collector.health", {
            "source": self.source_name,
            "heartbeat": utc_now(),
            "type": "heartbeat",
        })

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection (WebSocket or session)."""
        ...

    @abstractmethod
    async def collect(self) -> None:
        """Fetch data and publish. For streaming, this runs in a loop; for REST, poll once."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection gracefully."""
        ...

    async def run(self) -> None:
        """Main loop: connect, collect (with backoff on failure), heartbeat every 30s."""
        self._bus = get_message_bus()
        self._stop.clear()
        self._backoff_secs = BACKOFF_INITIAL
        last_heartbeat = asyncio.get_event_loop().time()

        while not self._stop.is_set():
            try:
                await self.connect()
                self._backoff_secs = BACKOFF_INITIAL
                logger.info("Collector %s connected", self.source_name)

                while not self._stop.is_set():
                    now = asyncio.get_event_loop().time()
                    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                        await self._heartbeat()
                        last_heartbeat = now

                    await self.collect()

                    if self.is_streaming:
                        await asyncio.sleep(1.0)
                    else:
                        await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Collector %s error: %s — backoff %.1fs", self.source_name, e, self._backoff_secs)
                await self.disconnect()
                await asyncio.sleep(self._backoff_secs)
                self._backoff_secs = min(self._backoff_secs * BACKOFF_MULTIPLIER, BACKOFF_MAX)

        await self.disconnect()
        logger.info("Collector %s stopped", self.source_name)

    def request_stop(self) -> None:
        """Signal the run loop to exit."""
        self._stop.set()
