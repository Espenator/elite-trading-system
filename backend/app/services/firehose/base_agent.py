"""Base firehose agent: queue, backoff, circuit breaker."""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.services.firehose.metrics import record_latency, record_published, set_queue_depth
from app.services.firehose.router import route
from app.services.firehose.schemas import SensoryEvent

logger = logging.getLogger(__name__)


class BaseFirehoseAgent(ABC):
    """Base for spine agents: run loop, publish via router, backoff on failure."""

    agent_id: str = "base"
    max_retries: int = 3
    backoff_base_sec: float = 1.0
    circuit_failures: int = 5  # open circuit after this many consecutive failures
    circuit_reset_sec: float = 60.0
    poll_interval_sec: float = 0.0  # If > 0, call fetch() every N sec and enqueue

    def __init__(self, message_bus: Any):
        self.message_bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._failures = 0
        self._circuit_open_until: float = 0.0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Firehose agent %s started", self.agent_id)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("Firehose agent %s stopped", self.agent_id)

    def enqueue(self, event: SensoryEvent) -> bool:
        try:
            self._queue.put_nowait(event)
            set_queue_depth(self.agent_id, self._queue.qsize())
            return True
        except asyncio.QueueFull:
            return False

    poll_interval_sec: float = 0.0  # If > 0, call fetch() every N sec and enqueue

    async def _run_loop(self) -> None:
        last_poll = 0.0
        while self._running:
            try:
                if time.monotonic() < self._circuit_open_until:
                    await asyncio.sleep(1.0)
                    continue
                if getattr(self, "poll_interval_sec", 0) > 0 and time.monotonic() - last_poll >= self.poll_interval_sec:
                    last_poll = time.monotonic()
                    try:
                        for evt in await self.fetch():
                            self.enqueue(evt)
                    except Exception as e:
                        logger.warning("Firehose agent %s fetch error: %s", self.agent_id, e)
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    set_queue_depth(self.agent_id, self._queue.qsize())
                    continue
                set_queue_depth(self.agent_id, self._queue.qsize())
                start = time.perf_counter()
                ok = await self._process_and_publish(event)
                record_latency(self.agent_id, time.perf_counter() - start)
                if ok:
                    self._failures = 0
                else:
                    self._failures += 1
                    if self._failures >= self.circuit_failures:
                        self._circuit_open_until = time.monotonic() + self.circuit_reset_sec
                        logger.warning(
                            "Firehose agent %s circuit open for %.0fs",
                            self.agent_id,
                            self.circuit_reset_sec,
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Firehose agent %s run_loop error: %s", self.agent_id, e)
                self._failures += 1
                await asyncio.sleep(self.backoff_base_sec)

    async def _process_and_publish(self, event: SensoryEvent) -> bool:
        for topic, payload in route(event):
            try:
                await self.message_bus.publish(topic, payload)
                record_published(self.agent_id, topic)
            except Exception as e:
                logger.warning("Firehose %s publish %s failed: %s", self.agent_id, topic, e)
                return False
        return True

    @abstractmethod
    async def fetch(self) -> list[SensoryEvent]:
        """Produce sensory events (implemented by each agent)."""
        ...

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "queue_depth": self._queue.qsize(),
            "failures": self._failures,
            "circuit_open": time.monotonic() < self._circuit_open_until,
        }
