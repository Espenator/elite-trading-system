"""Async pub/sub MessageBus for event-driven trading pipeline.

Supports two transport modes:
  1. LOCAL  — asyncio.Queue only (single process, zero deps)
  2. REDIS  — Redis pub/sub bridge for cross-PC cluster communication

When REDIS_URL is set in env/config, the bus automatically bridges
cluster-scoped topics through Redis so PC1 and PC2 share a nervous
system.  High-frequency local topics (market_data.*) stay on the
in-process queue for zero-overhead — they are NOT sent over the wire.

Topics:
  market_data.bar     - New 1-min bar from Alpaca WebSocket
  market_data.quote   - Real-time quote update
  signal.generated    - Trading signal created (score >= threshold)
  order.submitted     - Order sent to broker
  order.filled        - Order executed
  order.cancelled     - Order cancelled
  model.updated       - ML model learned from trade outcome
  risk.alert          - Risk limit breached

Usage (unchanged — all subscribers work exactly as before):
    bus = MessageBus()
    await bus.start()
    await bus.subscribe('market_data.bar', my_handler)
    await bus.publish('market_data.bar', {'symbol': 'AAPL', ...})
    await bus.stop()
"""
import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class MessageBus:
    """High-performance async event bus with topic-based pub/sub.

    Optionally bridges selected topics through Redis for multi-PC clusters.
    The public API (subscribe / publish / start / stop) is identical in both
    modes — callers never need to know which transport is active.
    """

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
        # Swarm intelligence topics
        "swarm.idea",           # New idea submitted for analysis
        "swarm.spawned",        # Swarm spawned and running
        "swarm.result",         # Swarm analysis complete
        "knowledge.ingested",   # New knowledge fed into the system
        "scout.discovery",      # Scout found an opportunity
        "scout.heartbeat",      # Scout agent health tick (E2)
        # Triage layer topics (E3)
        "triage.escalated",     # Idea passed quality gate → HyperSwarm
        "triage.dropped",       # Idea below threshold (audit trail)
        # Cluster telemetry topics
        "cluster.telemetry",    # GPU/VRAM/Ollama stats from cluster nodes
        "cluster.node_status",  # Node online/offline/degraded transitions
        # Outcome tracking
        "outcome.resolved",     # Position outcome resolved (win/loss/scratch)
        # Perception layer — data source topics
        "perception.unusualwhales",     # UnusualWhales alerts (options flow, dark pool, congress)
                        "unusual_whales.flow",           # UnusualWhales options flow alerts (agent-facing)
        "unusual_whales.congress",       # UnusualWhales congress trading activity
        "unusual_whales.darkpool",       # UnusualWhales dark pool transactions
        "perception.finviz.screener",   # Finviz screener results (bulk from service)
        "finviz.screener",              # Finviz adapter per-row SourceEvent
        "perception.macro",             # FRED macro data (CPI, unemployment, VIX, 10Y yield)
        "perception.edgar",             # SEC EDGAR filings
        # OpenClaw graduated scanner topics
        "perception.flow.uw_analysis",  # UW agents analysis
        "perception.flow.whale",        # Whale flow detection
        "perception.scanner.daily",     # Daily scanner results
        "perception.scanner.pullback",  # Pullback detector
        "perception.scanner.rebound",   # Rebound detector
        "perception.scanner.short_squeeze",  # Short squeeze detector
        "perception.scanner.accumulation",   # AMD accumulation detector
        "perception.scanner.sector",    # Sector rotation
        "perception.scanner.earnings",  # Earnings calendar
        "perception.scanner.expected_move",  # FOM expected moves
        "perception.world_intel",       # Sensorium world intelligence
        "perception.regime.openclaw",   # OpenClaw regime detection
        "perception.regime.hmm",        # HMM regime detection
        "perception.macro.openclaw",    # OpenClaw macro context
        "signal.openclaw.composite",    # OpenClaw composite scorer (0-100)
        "signal.openclaw.ensemble",     # OpenClaw ensemble scorer (ML)
        "signal.unified",               # UnifiedProfitEngine output
        # Firehose ingestion topics
        "ingest.raw",
        "ingest.health",
        "ingest.dlq",
        "ingest.to_awareness",
        "ingest.awareness_enriched",
        # Symbol prep (Phase 2 — hot-path purity)
        "symbol.prep.requested",
        "symbol.prep.ready",
    }

    # Topics bridged through Redis when cluster mode is active.
    # High-frequency market data stays local (thousands of events/sec).
    REDIS_BRIDGED_TOPICS: Set[str] = {
        "signal.generated",
        "council.verdict",
        "order.submitted",
        "order.filled",
        "order.cancelled",
        "risk.alert",
        "cluster.telemetry",
        "cluster.node_status",
        "swarm.idea",
        "swarm.result",
        "scout.discovery",
        "triage.escalated",
        "model.updated",
        "knowledge.ingested",
        "outcome.resolved",
        "hitl.approval_needed",
        "perception.unusualwhales",
        "perception.finviz.screener",
        "perception.macro",
        "perception.edgar",
        "ingest.health",
        "ingest.dlq",
        "ingest.to_awareness",
        "ingest.awareness_enriched",
    }

    # Redis channel prefix to avoid collisions with other apps
    REDIS_PREFIX = "etbus:"

    # Per-topic rate limits (events/second).  Topics not listed are unlimited.
    # Override via env: MSGBUS_RATE_LIMIT_SWARM_IDEA=50
    TOPIC_RATE_LIMITS: Dict[str, float] = {
        "swarm.idea": float(os.environ.get("MSGBUS_RATE_LIMIT_SWARM_IDEA", "50")),
        "scout.heartbeat": float(os.environ.get("MSGBUS_RATE_LIMIT_SCOUT_HEARTBEAT", "10")),
        "triage.dropped": float(os.environ.get("MSGBUS_RATE_LIMIT_TRIAGE_DROPPED", "20")),
        "cluster.telemetry": float(os.environ.get("MSGBUS_RATE_LIMIT_CLUSTER_TELEMETRY", "10")),
    }

    def __init__(self, max_queue_size: int = 10_000):
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, int] = defaultdict(int)
        self._error_count: int = 0
        self._start_time: Optional[float] = None

        # Per-topic token bucket state for rate limiting
        self._topic_tokens: Dict[str, float] = {}       # Available tokens
        self._topic_last_refill: Dict[str, float] = {}   # Last refill timestamp
        self._rate_limited_count: Dict[str, int] = defaultdict(int)  # Dropped by rate limit

        # D3: Dead-letter queue — stores events that failed all handler retries
        self._dlq: List[Dict[str, Any]] = []
        self._dlq_max = 500  # Cap DLQ to prevent unbounded growth
        self._capacity_alert_sent = False
        self._capacity_alert_threshold = 0.80  # Alert at 80% queue capacity
        self._handler_timeout = 10.0  # Per-handler timeout in seconds (D3)

        # Redis bridge state
        self._redis_url: str = ""
        self._redis_pub: Any = None       # redis.asyncio.Redis (publisher)
        self._redis_sub: Any = None       # redis.asyncio.client.PubSub
        self._redis_listen_task: Optional[asyncio.Task] = None
        self._redis_connected: bool = False
        self._redis_errors: int = 0
        self._node_id: str = ""           # Dedup — ignore own publishes

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the event processing loop (+ Redis bridge if configured)."""
        if self._running:
            logger.warning("MessageBus already running")
            return
        self._running = True
        self._start_time = time.time()

        # Start local queue processor
        self._process_task = asyncio.create_task(self._process_events())

        # Attempt Redis bridge connection
        await self._connect_redis()

        transport = "Redis-bridged" if self._redis_connected else "local-only"
        logger.info(
            "MessageBus started (queue_size=%d, transport=%s)",
            self._queue.maxsize, transport,
        )

    async def stop(self) -> None:
        """Graceful shutdown: drain queue, disconnect Redis, then stop."""
        if not self._running:
            return
        self._running = False
        logger.info("MessageBus stopping — draining %d remaining events...", self._queue.qsize())

        # Drain remaining local events with 5s timeout
        try:
            await asyncio.wait_for(self._drain(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("MessageBus drain timeout — %d events dropped", self._queue.qsize())

        # Stop Redis listener
        await self._disconnect_redis()

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

    # ------------------------------------------------------------------
    # Public API (unchanged interface)
    # ------------------------------------------------------------------

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
        """Publish an event to a topic. Non-blocking — events are queued.

        If Redis bridge is active and the topic is in REDIS_BRIDGED_TOPICS,
        the event is ALSO published to Redis so remote nodes receive it.
        Local delivery still happens via the asyncio queue regardless.
        """
        if not self._running:
            logger.debug("MessageBus not running — dropping event on '%s'", topic)
            return

        if topic not in self.VALID_TOPICS:
            logger.error("Invalid MessageBus topic '%s' — check for typos. Valid topics: %s",
                         topic, sorted(self.VALID_TOPICS))
            return

        # Per-topic rate limiting (token bucket)
        if topic in self.TOPIC_RATE_LIMITS:
            if not self._check_rate_limit(topic):
                self._rate_limited_count[topic] += 1
                self._metrics[topic] += 1  # Still count for observability
                # Log periodically to avoid log flooding
                if self._rate_limited_count[topic] % 100 == 1:
                    logger.warning(
                        "Rate-limiting topic '%s' — %d events dropped (limit: %.0f/s)",
                        topic, self._rate_limited_count[topic],
                        self.TOPIC_RATE_LIMITS[topic],
                    )
                return

        # Enforce canonical score semantics at the bus boundary so every publisher
        # (current + future) preserves the invariant:
        #   signal.generated.score ∈ [0, 100]
        if topic == "signal.generated" and isinstance(data, dict) and "score" in data:
            try:
                from app.core.score_semantics import coerce_signal_score_0_100

                data = dict(data)  # don't mutate caller-owned dict
                data["score"] = coerce_signal_score_0_100(
                    data.get("score"),
                    context=f"MessageBus publish(signal.generated) {data.get('symbol', '')}".strip(),
                )
            except Exception:
                # Never let score coercion break event delivery.
                pass

        event = {"topic": topic, "data": data, "timestamp": time.time()}

        # D3: Check capacity and alert at 80%
        queue_usage = self._queue.qsize() / max(self._queue.maxsize, 1)
        if queue_usage >= self._capacity_alert_threshold and not self._capacity_alert_sent:
            self._capacity_alert_sent = True
            logger.warning(
                "MessageBus queue at %.0f%% capacity (%d/%d) — backpressure risk",
                queue_usage * 100, self._queue.qsize(), self._queue.maxsize,
            )
            # Try Slack alert (fire-and-forget)
            asyncio.ensure_future(self._send_capacity_alert(queue_usage))
        elif queue_usage < 0.5 and self._capacity_alert_sent:
            self._capacity_alert_sent = False  # Reset alert when queue drains

        # Local delivery (always)
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._error_count += 1
            logger.error("MessageBus queue FULL — sending to DLQ on '%s'", topic)
            self._add_to_dlq(event, reason="queue_full")

        # Redis bridge (cross-PC delivery)
        if self._redis_connected and topic in self.REDIS_BRIDGED_TOPICS:
            await self._redis_publish(topic, data)

    # ------------------------------------------------------------------
    # Per-topic rate limiting (token bucket)
    # ------------------------------------------------------------------

    def _check_rate_limit(self, topic: str) -> bool:
        """Return True if this event is allowed under the topic rate limit.

        Uses a simple token-bucket algorithm: tokens refill at TOPIC_RATE_LIMITS[topic]
        per second, burst size equals the rate (1 second worth of tokens).
        """
        now = time.time()
        rate = self.TOPIC_RATE_LIMITS[topic]
        burst = max(rate, 10.0)  # Allow at least 10-event bursts

        # Initialize on first call
        if topic not in self._topic_tokens:
            self._topic_tokens[topic] = burst
            self._topic_last_refill[topic] = now

        # Refill tokens
        elapsed = now - self._topic_last_refill[topic]
        if elapsed > 0:
            self._topic_tokens[topic] = min(
                burst, self._topic_tokens[topic] + elapsed * rate
            )
            self._topic_last_refill[topic] = now

        # Consume one token
        if self._topic_tokens[topic] >= 1.0:
            self._topic_tokens[topic] -= 1.0
            return True
        return False

    # ------------------------------------------------------------------
    # Local event processor (unchanged logic)
    # ------------------------------------------------------------------

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
        """Call handler with error isolation + timeout (D3).

        Per-handler timeout prevents one slow handler from blocking all
        event processing. Failed events go to the dead-letter queue.
        """
        handler_name = handler.__qualname__ if hasattr(handler, '__qualname__') else str(handler)
        try:
            await asyncio.wait_for(handler(data), timeout=self._handler_timeout)
        except asyncio.TimeoutError:
            self._error_count += 1
            logger.warning(
                "Handler %s TIMED OUT on topic '%s' (limit=%.1fs)",
                handler_name, topic, self._handler_timeout,
            )
            self._add_to_dlq(
                {"topic": topic, "data": data, "timestamp": time.time()},
                reason=f"handler_timeout:{handler_name}",
            )
        except Exception:
            self._error_count += 1
            logger.exception(
                "Handler %s failed on topic '%s'",
                handler_name, topic,
            )
            self._add_to_dlq(
                {"topic": topic, "data": data, "timestamp": time.time()},
                reason=f"handler_error:{handler_name}",
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

    # ------------------------------------------------------------------
    # D3: Dead-letter queue + capacity alerting
    # ------------------------------------------------------------------

    def _add_to_dlq(self, event: Dict[str, Any], reason: str) -> None:
        """Add a failed event to the dead-letter queue."""
        dlq_entry = {
            "event": event,
            "reason": reason,
            "failed_at": time.time(),
        }
        self._dlq.append(dlq_entry)
        # Cap DLQ size — drop oldest entries
        while len(self._dlq) > self._dlq_max:
            self._dlq.pop(0)

    def get_dlq(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent DLQ entries for monitoring."""
        return self._dlq[-limit:]

    def clear_dlq(self) -> int:
        """Clear the DLQ. Returns count of cleared entries."""
        count = len(self._dlq)
        self._dlq.clear()
        return count

    async def _send_capacity_alert(self, usage: float) -> None:
        """Send Slack alert when queue capacity is high."""
        try:
            from app.services.slack_notification_service import get_slack_service
            slack = get_slack_service()
            await slack.send_alert(
                f"MessageBus queue at {usage:.0%} capacity "
                f"({self._queue.qsize()}/{self._queue.maxsize}). "
                f"Check for slow handlers or burst traffic."
            )
        except Exception:
            pass  # Never let alerting break the bus

    # ------------------------------------------------------------------
    # Redis bridge
    # ------------------------------------------------------------------

    async def _connect_redis(self) -> None:
        """Connect to Redis if REDIS_URL is configured. Never blocks startup."""
        # Read URL from settings or env
        redis_url = ""
        try:
            from app.core.config import settings
            redis_url = getattr(settings, "REDIS_URL", "") or ""
        except Exception:
            pass
        if not redis_url:
            redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            logger.info("MessageBus: no REDIS_URL — running in local-only mode")
            return

        self._redis_url = redis_url.strip()

        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.warning(
                "MessageBus: redis package not installed — running in local-only mode. "
                "Install with: pip install redis"
            )
            return

        try:
            # Generate unique node ID to prevent self-echo
            import socket
            self._node_id = f"{socket.gethostname()}-{os.getpid()}"

            # Publisher connection
            self._redis_pub = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Verify connectivity
            await self._redis_pub.ping()

            # Subscriber connection (separate connection required for pub/sub)
            sub_client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self._redis_sub = sub_client.pubsub()

            # Subscribe to all bridged topic channels
            channels = {
                f"{self.REDIS_PREFIX}{topic}": self._on_redis_message
                for topic in self.REDIS_BRIDGED_TOPICS
            }
            await self._redis_sub.subscribe(**channels)

            # Start listener loop
            self._redis_listen_task = asyncio.create_task(self._redis_listener())

            self._redis_connected = True
            logger.info(
                "MessageBus: Redis bridge CONNECTED at %s (node=%s, bridging %d topics)",
                self._redis_url, self._node_id, len(self.REDIS_BRIDGED_TOPICS),
            )

        except Exception as e:
            logger.warning(
                "MessageBus: Redis connection failed — falling back to local-only: %s", e
            )
            self._redis_connected = False
            self._redis_pub = None
            self._redis_sub = None

    async def _disconnect_redis(self) -> None:
        """Clean up Redis connections."""
        if self._redis_listen_task:
            self._redis_listen_task.cancel()
            try:
                await self._redis_listen_task
            except (asyncio.CancelledError, Exception):
                pass
            self._redis_listen_task = None

        if self._redis_sub:
            try:
                await self._redis_sub.unsubscribe()
                await self._redis_sub.close()
            except Exception:
                pass
            self._redis_sub = None

        if self._redis_pub:
            try:
                await self._redis_pub.close()
            except Exception:
                pass
            self._redis_pub = None

        self._redis_connected = False

    async def _redis_publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish event to Redis channel. Fire-and-forget — never blocks local delivery."""
        if not self._redis_pub:
            return
        try:
            envelope = json.dumps({
                "node_id": self._node_id,
                "topic": topic,
                "data": data,
                "timestamp": time.time(),
            })
            channel = f"{self.REDIS_PREFIX}{topic}"
            await self._redis_pub.publish(channel, envelope)
        except Exception as e:
            self._redis_errors += 1
            if self._redis_errors <= 5 or self._redis_errors % 100 == 0:
                logger.warning("MessageBus: Redis publish failed (%d total): %s", self._redis_errors, e)

            # If we've had too many consecutive errors, try reconnecting
            if self._redis_errors >= 10:
                logger.warning("MessageBus: Redis errors threshold reached — attempting reconnect")
                await self._disconnect_redis()
                await self._connect_redis()

    async def _redis_listener(self) -> None:
        """Background task: listen for messages from other nodes via Redis."""
        logger.info("MessageBus: Redis listener started")
        try:
            while self._running and self._redis_sub:
                try:
                    message = await asyncio.wait_for(
                        self._redis_sub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=2.0,
                    )
                    if message is None:
                        continue
                    if message["type"] != "message":
                        continue

                    await self._on_redis_message(message)

                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception:
                    logger.exception("MessageBus: Redis listener error")
                    await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            pass
        logger.info("MessageBus: Redis listener stopped")

    async def _on_redis_message(self, message: Any) -> None:
        """Handle incoming message from Redis — inject into local bus.

        Deduplication: messages from our own node_id are ignored
        (they were already delivered locally via the asyncio queue).
        """
        try:
            if isinstance(message, dict):
                raw = message.get("data", "")
            else:
                raw = str(message)

            if not raw or not isinstance(raw, str):
                return

            envelope = json.loads(raw)
            sender = envelope.get("node_id", "")
            topic = envelope.get("topic", "")
            data = envelope.get("data", {})

            # Skip our own messages (already handled locally)
            if sender == self._node_id:
                return

            # Deliver to local subscribers via the queue
            if topic and data:
                event = {"topic": topic, "data": data, "timestamp": time.time(), "_remote": True}
                try:
                    self._queue.put_nowait(event)
                except asyncio.QueueFull:
                    self._error_count += 1
                    logger.warning("MessageBus: queue full, dropping remote event on '%s'", topic)

        except json.JSONDecodeError:
            logger.debug("MessageBus: invalid JSON from Redis")
        except Exception:
            logger.exception("MessageBus: error processing Redis message")

    # ------------------------------------------------------------------
    # Queue introspection (used by publishers for backpressure)
    # ------------------------------------------------------------------

    @property
    def queue_depth(self) -> int:
        """Current number of events waiting in the queue."""
        return self._queue.qsize()

    @property
    def queue_max(self) -> int:
        """Maximum queue capacity."""
        return self._queue.maxsize

    @property
    def queue_usage_pct(self) -> float:
        """Queue usage as a percentage (0.0–100.0)."""
        return (self._queue.qsize() / max(self._queue.maxsize, 1)) * 100

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, Any]:
        """Return bus metrics for monitoring dashboard."""
        uptime = time.time() - self._start_time if self._start_time else 0
        queue_usage = self._queue.qsize() / max(self._queue.maxsize, 1)
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "queue_depth": self._queue.qsize(),
            "queue_max": self._queue.maxsize,
            "queue_usage_pct": round(queue_usage * 100, 1),
            "events_by_topic": dict(self._metrics),
            "total_events": sum(self._metrics.values()),
            "total_errors": self._error_count,
            "subscribers": {
                topic: len(handlers) for topic, handlers in self._subscribers.items()
            },
            # D3: Dead-letter queue
            "dlq": {
                "size": len(self._dlq),
                "max": self._dlq_max,
                "capacity_alert_active": self._capacity_alert_sent,
            },
            # Rate limiting stats
            "rate_limited": dict(self._rate_limited_count),
            # Redis bridge metrics
            "redis": {
                "connected": self._redis_connected,
                "url": self._redis_url or None,
                "node_id": self._node_id or None,
                "publish_errors": self._redis_errors,
                "bridged_topics": len(self.REDIS_BRIDGED_TOPICS),
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
