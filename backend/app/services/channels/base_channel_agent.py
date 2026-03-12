from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

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
    """Base ingestion agent with batch-drain processing, circuit breaker, and health.

    Instead of N workers competing on a single queue, uses one worker that
    drains up to ``batch_size`` events per cycle and processes them all
    concurrently via ``asyncio.gather``.  This eliminates queue contention
    and gives true parallelism proportional to batch size.
    """

    def __init__(
        self,
        *,
        name: str,
        router: Any,
        message_bus: Any,
        max_queue_size: int = 2000,
        batch_size: int = 1,
        retry: Optional[RetryPolicy] = None,
        breaker: Optional[CircuitBreaker] = None,
        heartbeat_topic: str = "ingest.health",
        dlq_topic: str = "ingest.dlq",
        on_enqueue: Optional[Callable[[SensoryEvent], Awaitable[None]]] = None,
        # Legacy compat — ignored, batch_size replaces num_workers
        num_workers: int = 1,
    ) -> None:
        self.name = name
        self._router = router
        self._bus = message_bus
        self._queue: asyncio.Queue[SensoryEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._batch_size = max(1, batch_size)
        self._retry = retry or RetryPolicy()
        self._breaker = breaker or CircuitBreaker()
        self._heartbeat_topic = heartbeat_topic
        self._dlq_topic = dlq_topic
        self._on_enqueue = on_enqueue

        self._running = False
        self._paused = False
        self._worker_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._consecutive_failures = 0
        self._circuit_opened_at: Optional[float] = None

        self._metrics: Dict[str, int] = {
            "events_in": 0,
            "events_out": 0,
            "events_dropped_queue_full": 0,
            "events_failed": 0,
            "events_dlq": 0,
            "batches_processed": 0,
            "max_batch_seen": 0,
        }
        self._last_event_ts: Optional[str] = None
        self._last_error_ts: Optional[str] = None
        self._last_error: Optional[str] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "ChannelAgent started: %s (batch=%d, queue=%d)",
            self.name, self._batch_size, self._queue.maxsize,
        )

    async def stop(self) -> None:
        self._running = False
        tasks = [t for t in (self._worker_task, self._heartbeat_task) if t]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._worker_task = None
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
            "batch_size": self._batch_size,
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

    # ------------------------------------------------------------------
    # Core worker — batch drain + parallel process
    # ------------------------------------------------------------------

    def _drain_batch(self) -> List[SensoryEvent]:
        """Non-blocking drain of up to batch_size events from the queue."""
        batch: List[SensoryEvent] = []
        for _ in range(self._batch_size):
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

    async def _worker_loop(self) -> None:
        while self._running:
            # Block on the first event (up to 1s) to avoid busy-spin
            try:
                first = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if self._paused:
                try:
                    self._queue.put_nowait(first)
                except asyncio.QueueFull:
                    pass
                self._queue.task_done()
                await asyncio.sleep(0.25)
                continue

            # Drain up to (batch_size - 1) more without blocking
            batch = [first] + self._drain_batch()

            if self._metrics["max_batch_seen"] < len(batch):
                self._metrics["max_batch_seen"] = len(batch)
            self._metrics["batches_processed"] += 1

            if self._is_circuit_open():
                for ev in batch:
                    await self._publish_dlq(ev, "circuit_open")
                    self._queue.task_done()
                continue

            # Fast path: use route_batch for the whole batch when no
            # retries are needed (common case).  Falls back to per-event
            # retry on failure.
            if hasattr(self._router, "route_batch") and len(batch) > 1:
                try:
                    await self._router.route_batch(batch)
                    self._consecutive_failures = 0
                    now = _utc_iso()
                    self._metrics["events_out"] += len(batch)
                    self._last_event_ts = now
                    for _ in batch:
                        try:
                            self._queue.task_done()
                        except Exception:
                            pass
                    continue
                except Exception:
                    # Batch failed — fall through to per-event retry
                    pass

            # Per-event processing with individual retry
            results = await asyncio.gather(
                *[self._process_one(ev) for ev in batch],
                return_exceptions=True,
            )

            now = _utc_iso()
            for ev, result in zip(batch, results):
                if isinstance(result, Exception):
                    self._metrics["events_failed"] += 1
                    self._last_error_ts = now
                    self._last_error = str(result)[:300]
                else:
                    self._metrics["events_out"] += 1
                    self._last_event_ts = now
                try:
                    self._queue.task_done()
                except Exception:
                    pass

    async def _process_one(self, ev: SensoryEvent) -> None:
        """Process a single event through the router with retry."""
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry.max_retries + 1):
            try:
                await self._router.route_and_publish(ev)
                self._consecutive_failures = 0
                return
            except Exception as exc:
                last_exc = exc
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._breaker.failure_threshold:
                    self._open_circuit()
                    break
                if attempt >= self._retry.max_retries:
                    break
                delay = min(
                    self._retry.max_delay_s,
                    (self._retry.base_delay_s * (2 ** attempt))
                    + random.random() * self._retry.jitter_s,
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
                        "batch_size": self._batch_size,
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
