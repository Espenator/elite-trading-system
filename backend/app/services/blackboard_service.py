"""Canonical Blackboard service — single in-process pub/sub for OpenClaw and CNS.

Replaces the standalone Blackboard + Topic registry in OpenClaw so there is
exactly one blackboard implementation at runtime. Council evaluation uses
BlackboardState (per-evaluation context); this service is for long-lived
topic-based coordination (scored_candidates, ml_predictions, execution_orders, etc.).

Usage:
    from app.services.blackboard_service import get_blackboard, set_blackboard, Topic, BlackboardMessage

    bb = get_blackboard()
    bb.publish(Topic.ML_PREDICTIONS, result)
    candidates = bb.read(Topic.SCORED_CANDIDATES, [])
    bb.subscribe(Topic.WHALE_SIGNALS, callback)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Topic registry (unified: ensemble_scorer + streaming/clawbots)
# ─────────────────────────────────────────────────────────────────────────────

class Topic:
    """Canonical pub/sub topic names for the Blackboard."""
    # Ensemble scorer / ML pipeline
    SCORED_CANDIDATES = "scored_candidates"
    ML_PREDICTIONS = "ml_predictions"
    REGIME_STATE = "regime_state"
    WHALE_FLOW = "whale_flow"
    MODEL_METRICS = "model_metrics"
    TRADE_OUTCOMES = "trade_outcomes"
    RETRAIN_REQUEST = "retrain_request"
    # Streaming / clawbots / Tier 1–3
    EXECUTION_ORDERS = "execution_orders"
    WHALE_SIGNALS = "whale_signals"
    SCORED_SIGNALS = "scored_signals"
    REGIME_UPDATES = "regime_updates"
    ALPHA_SIGNALS = "alpha_signals"
    WATCHLIST_UPDATES = "watchlist_updates"
    BAR_UPDATES = "bar_updates"


# ─────────────────────────────────────────────────────────────────────────────
# BlackboardMessage — envelope for payload + TTL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BlackboardMessage:
    """Message envelope for blackboard pub/sub; supports TTL for expiry."""
    topic: str
    payload: Any
    source: Optional[str] = None
    source_agent: Optional[str] = None
    priority: int = 5
    ttl_seconds: float = 60.0
    _created_at: float = field(default_factory=time.monotonic, repr=False)

    def is_expired(self) -> bool:
        return (time.monotonic() - self._created_at) > self.ttl_seconds


# ─────────────────────────────────────────────────────────────────────────────
# Blackboard — single store + sync subscribers + optional async queues
# ─────────────────────────────────────────────────────────────────────────────

class Blackboard:
    """Single in-process blackboard: read, publish, subscribe (sync and async)."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._store_msg: Dict[str, BlackboardMessage] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queues: Dict[str, Dict[str, asyncio.Queue]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    def publish(self, topic_or_msg: Union[str, BlackboardMessage], data: Any = None) -> None:
        """Publish by (topic, data) or a single BlackboardMessage."""
        if isinstance(topic_or_msg, BlackboardMessage):
            msg = topic_or_msg
            topic = msg.topic
        else:
            topic = topic_or_msg
            msg = BlackboardMessage(topic=topic, payload=data if data is not None else {})

        self._store_msg[topic] = msg
        self._store[topic] = msg.payload

        for cb in self._subscribers.get(topic, []):
            try:
                cb(msg)
            except Exception as e:
                logger.debug("Blackboard subscriber error on %s: %s", topic, e)

        for sub_id, q in self._queues.get(topic, {}).items():
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                logger.debug("Blackboard queue full for %s/%s", topic, sub_id)

    def read(self, topic: str, default: Any = None) -> Any:
        """Return last payload for topic (or default)."""
        return self._store.get(topic, default)

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Register sync callback for topic. Callback receives BlackboardMessage."""
        self._subscribers[topic].append(callback)

    async def subscribe_async(self, topic: str, subscriber_id: str) -> asyncio.Queue:
        """Register async listener; returns a queue that receives BlackboardMessages."""
        async with self._lock:
            if topic not in self._queues:
                self._queues[topic] = {}
            if subscriber_id not in self._queues[topic]:
                self._queues[topic][subscriber_id] = asyncio.Queue(maxsize=500)
        return self._queues[topic][subscriber_id]

    def heartbeat(self, subscriber_id: str) -> None:
        """No-op for compatibility with memory_v3 listener."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Singleton + injection
# ─────────────────────────────────────────────────────────────────────────────

_blackboard: Optional[Blackboard] = None


def get_blackboard() -> Blackboard:
    """Return the canonical global Blackboard. Creates one if none set."""
    global _blackboard
    if _blackboard is None:
        _blackboard = Blackboard()
        logger.info("BlackboardService: created canonical Blackboard singleton")
    return _blackboard


def set_blackboard(bb: Blackboard) -> None:
    """Inject the Blackboard instance (e.g. for tests)."""
    global _blackboard
    _blackboard = bb
