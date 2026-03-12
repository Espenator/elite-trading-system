from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from app.services.channels.schemas import SensoryEvent

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RetryPolicy:
    max_retries: int = 5
    base_delay_s: float = 0.25
    max_delay_s: float = 10.0
    jitter_s: float = 0.25


@dataclass
class CircuitBreaker:
    failure_threshold: int = 10
    reset_timeout_s: float = 30.0


class BaseChannelAgent:
    """Base ingestion agent with bounded queue, retry/backoff, circuit breaker, and health."""

    def __init__(
        self,
        *,
        name: str,
        router: Any,
        message_bus: Any,
        max_queue_size: int = 2000,
        num_workers: int = 1,
        retry: Optional[RetryPolicy] = None,
        breaker: Optional[CircuitBreaker] = None,
        heartbeat_topic: str = "ingest.health",
        dlq_topic: str = "ingest.dlq",
        on_enqueue: Optional[Callable[[SensoryEvent], Awaitable[None]]] = None,
    ) -> None:
        self.name = name
        self._router = router
        self._bus = message_bus
        self._queue: asyncio.Queue[SensoryEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._num_workers = max(1, num_workers)
        self._retry = retry or RetryPolicy()
        self._breaker = breaker or CircuitBreaker()
        self._heartbeat_topic = heartbeat_topic
        self._dlq_topic = dlq_topic
        self._on_enqueue = on_enqueue

        self._running = False
        self._paused = False
        self._worker_tasks: list[asyncio.Task] = []
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._consecutive_failures = 0
        self._circuit_opened_at: Optional[float] = None

        self._metrics: Dict[str, int] = {
            "events_in": 0,
            "events_out": 0,
            "events_dropped_queue_full": 0,
            "events_failed": 0,
            "events_dlq": 0,
        }
        self._last_event_ts: Optional[str] = None
        self._last_error_ts: Optional[str] = None
        self._last_error: Optional[str] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop())
            for _ in range(self._num_workers)
        ]
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "ChannelAgent started: %s (%d workers, queue=%d)",
            self.name, self._num_workers, self._queue.maxsize,
        )

    async def stop(self) -> None:
        self._running = False
        all_tasks = self._worker_tasks + ([self._heartbeat_task] if self._heartbeat_task else [])
        for t in all_tasks:
            t.cancel()
        await asyncio.gather(*all_tasks, return_exceptions=True)
        self._worker_tasks = []
        logger.info("ChannelAgent stopped: %s", self.name)

    async def pause(self) -> None:
        self._paused = True

    async def resume(self) -> None:
        self._paused = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "running": self._running,
            "paused": self._paused,
            "queue_depth": self._queue.qsize(),
            "queue_max": self._queue.maxsize,
            "circuit_open": self._is_circuit_open(),
            "consecutive_failures": self._consecutive_failures,
            "last_event_ts": self._last_event_ts,
            "last_error_ts": self._last_error_ts,
            "last_error": self._last_error,
            "metrics": dict(self._metrics),
        }

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)

    async def enqueue(self, event: SensoryEvent) -> bool:
        if not self._running:
            return False
        self._metrics["events_in"] += 1
        if self._on_enqueue:
            try:
                await self._on_enqueue(event)
            except Exception:
                pass
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self._metrics["events_dropped_queue_full"] += 1
            self._last_error_ts = _utc_iso()
            self._last_error = "queue_full"
            return False

    def _is_circuit_open(self) -> bool:
        if self._circuit_opened_at is None:
            return False
        if (time.time() - self._circuit_opened_at) >= self._breaker.reset_timeout_s:
            self._circuit_opened_at = None
            self._consecutive_failures = 0
            return False
        return True

    def _open_circuit(self) -> None:
        if self._circuit_opened_at is None:
            self._circuit_opened_at = time.time()

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                ev = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                if self._paused:
                    try:
                        self._queue.put_nowait(ev)
                    except asyncio.QueueFull:
                        pass
                    self._queue.task_done()
                    continue
                if self._is_circuit_open():
                    await self._publish_dlq(ev, "circuit_open")
                    self._queue.task_done()
                    continue
                await self._process_with_retries(ev)
                self._metrics["events_out"] += 1
                self._last_event_ts = _utc_iso()
            except Exception as exc:
                self._metrics["events_failed"] += 1
                self._last_error_ts = _utc_iso()
                self._last_error = str(exc)[:300]
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass

    async def _process_with_retries(self, ev: SensoryEvent) -> None:
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry.max_retries + 1):
            try:
                await self._router.route_and_publish(ev)
                self._consecutive_failures = 0
                return
            except Exception as exc:
                last_exc = exc
                self._consecutive_failures += 1
                self._metrics["events_failed"] += 1
                self._last_error_ts = _utc_iso()
                self._last_error = str(exc)[:300]
                if self._consecutive_failures >= self._breaker.failure_threshold:
                    self._open_circuit()
                    break
                if attempt >= self._retry.max_retries:
                    break
                delay = min(
                    self._retry.max_delay_s,
                    (self._retry.base_delay_s * (2**attempt)) + random.random() * self._retry.jitter_s,
                )
                await asyncio.sleep(delay)

        await self._publish_dlq(ev, str(last_exc) if last_exc else "publish_failed")

    async def _publish_dlq(self, ev: SensoryEvent, error: str) -> None:
        self._metrics["events_dlq"] += 1
        self._last_error_ts = _utc_iso()
        self._last_error = error[:300]
        try:
            await self._bus.publish(
                self._dlq_topic,
                {
                    "agent": self.name,
                    "error": error[:500],
                    "event": ev.model_dump(mode="json"),
                    "ts": _utc_iso(),
                },
            )
        except Exception:
            pass

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(10)
                if not self._running:
                    break
                await self._bus.publish(
                    self._heartbeat_topic,
                    {
                        "agent": self.name,
                        "status": "paused" if self._paused else "running",
                        "queue_depth": self._queue.qsize(),
                        "circuit_open": self._is_circuit_open(),
                        "metrics": dict(self._metrics),
                        "last_event_ts": self._last_event_ts,
                        "last_error_ts": self._last_error_ts,
                        "ts": _utc_iso(),
                    },
                )
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)
