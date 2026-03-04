"""Async pub/sub MessageBus for event-driven trading pipeline.

Topics:
  market_data.bar     - New 1-min bar from Alpaca WebSocket
  market_data.quote   - Real-time quote update
  signal.generated    - Trading signal created (score >= threshold)
  order.submitted     - Order sent to broker
  order.filled        - Order executed
  order.cancelled     - Order cancelled
  model.updated       - ML model learned from trade outcome
  risk.alert          - Risk limit breached

Usage:
    bus = MessageBus()
    await bus.start()
    await bus.subscribe('market_data.bar', my_handler)
    await bus.publish('market_data.bar', {'symbol': 'AAPL', ...})
    await bus.stop()
"""
import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class MessageBus:
    """High-performance async event bus with topic-based pub/sub."""

    VALID_TOPICS = {
        "market_data.bar",
        "market_data.quote",
        "signal.generated",
        "order.submitted",
        "order.filled",
        "order.cancelled",
        "model.updated",
        "risk.alert",
        "system.heartbeat",
        "council.verdict",
        "hitl.approval_needed",
    }

    def __init__(self, max_queue_size: int = 10_000):
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, int] = defaultdict(int)
        self._error_count: int = 0
        self._start_time: Optional[float] = None

    async def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            logger.warning("MessageBus already running")
            return
        self._running = True
        self._start_time = time.time()
        self._process_task = asyncio.create_task(self._process_events())
        logger.info("MessageBus started (queue_size=%d)", self._queue.maxsize)

    async def stop(self) -> None:
        """Graceful shutdown: drain queue then stop."""
        if not self._running:
            return
        self._running = False
        logger.info("MessageBus stopping — draining %d remaining events...", self._queue.qsize())
        # Drain remaining events with 5s timeout
        try:
            await asyncio.wait_for(self._drain(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("MessageBus drain timeout — %d events dropped", self._queue.qsize())
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "MessageBus stopped — processed %d total events, %d errors",
            sum(self._metrics.values()),
            self._error_count,
        )

    MAX_SUBSCRIBERS_PER_TOPIC = 50

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a coroutine handler to a topic."""
        if topic not in self.VALID_TOPICS:
            logger.warning("Subscribing to unregistered topic '%s' — consider adding to VALID_TOPICS", topic)
        if len(self._subscribers[topic]) >= self.MAX_SUBSCRIBERS_PER_TOPIC:
            logger.warning("Topic '%s' at subscriber limit (%d) — rejecting new handler", topic, self.MAX_SUBSCRIBERS_PER_TOPIC)
            return
        self._subscribers[topic].append(handler)
        logger.info(
            "Subscribed %s to '%s' (%d total handlers)",
            handler.__qualname__ if hasattr(handler, '__qualname__') else str(handler),
            topic,
            len(self._subscribers[topic]),
        )

    async def unsubscribe(self, topic: str, handler: EventHandler) -> bool:
        """Remove a handler from a topic. Returns True if found."""
        handlers = self._subscribers.get(topic, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish an event to a topic. Non-blocking — events are queued."""
        if not self._running:
            logger.debug("MessageBus not running — dropping event on '%s'", topic)
            return
        event = {"topic": topic, "data": data, "timestamp": time.time()}
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._error_count += 1
            logger.error("MessageBus queue FULL — dropping event on '%s'", topic)

    async def _process_events(self) -> None:
        """Main event processing loop — dispatches events to subscribers."""
        logger.info("MessageBus event loop started")
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            topic = event["topic"]
            data = event["data"]
            handlers = self._subscribers.get(topic, [])

            if not handlers:
                self._queue.task_done()
                continue

            # Fan-out: call all handlers concurrently
            tasks = []
            for handler in handlers:
                tasks.append(asyncio.create_task(self._safe_call(handler, data, topic)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self._metrics[topic] += 1
            self._queue.task_done()

    async def _safe_call(
        self, handler: EventHandler, data: Dict[str, Any], topic: str
    ) -> None:
        """Call handler with error isolation — one bad handler won't crash others."""
        try:
            await handler(data)
        except Exception:
            self._error_count += 1
            logger.exception(
                "Handler %s failed on topic '%s'",
                handler.__qualname__ if hasattr(handler, '__qualname__') else str(handler),
                topic,
            )

    async def _drain(self) -> None:
        """Process remaining queued events."""
        while not self._queue.empty():
            event = await self._queue.get()
            topic = event["topic"]
            data = event["data"]
            handlers = self._subscribers.get(topic, [])
            for handler in handlers:
                await self._safe_call(handler, data, topic)
            self._queue.task_done()

    def get_metrics(self) -> Dict[str, Any]:
        """Return bus metrics for monitoring dashboard."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "queue_depth": self._queue.qsize(),
            "queue_max": self._queue.maxsize,
            "events_by_topic": dict(self._metrics),
            "total_events": sum(self._metrics.values()),
            "total_errors": self._error_count,
            "subscribers": {
                topic: len(handlers) for topic, handlers in self._subscribers.items()
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton (lazy init)
# ---------------------------------------------------------------------------
_bus_instance: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create the global MessageBus singleton."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = MessageBus()
    return _bus_instance
