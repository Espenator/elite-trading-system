"""Tests for canonical Blackboard service — single source of truth for OpenClaw/CNS."""

import asyncio
import pytest

from app.services.blackboard_service import (
    Blackboard,
    BlackboardMessage,
    Topic,
    get_blackboard,
    set_blackboard,
)


def test_blackboard_singleton_is_single_instance():
    """There is exactly one blackboard at runtime from get_blackboard()."""
    bb1 = get_blackboard()
    bb2 = get_blackboard()
    assert bb1 is bb2


def test_blackboard_read_write_visible():
    """Writes to the blackboard are visible to read() and to subscribers."""
    # Use a fresh instance so we don't pollute the global singleton
    bb = Blackboard()
    payload = [{"symbol": "AAPL", "score": 80}]
    bb.publish(Topic.SCORED_CANDIDATES, payload)
    assert bb.read(Topic.SCORED_CANDIDATES, []) == payload

    received = []
    bb.subscribe(Topic.ML_PREDICTIONS, lambda msg: received.append(msg.payload))
    bb.publish(Topic.ML_PREDICTIONS, {"symbol": "MSFT", "win_prob": 0.7})
    assert len(received) == 1
    assert received[0]["win_prob"] == 0.7


def test_blackboard_accepts_blackboard_message():
    """publish(BlackboardMessage) is accepted and stored."""
    bb = Blackboard()
    msg = BlackboardMessage(
        topic=Topic.WHALE_SIGNALS,
        payload={"ticker": "GOOG", "premium": 100},
        source="whale_flow",
    )
    bb.publish(msg)
    assert bb.read(Topic.WHALE_SIGNALS) == {"ticker": "GOOG", "premium": 100}


@pytest.mark.asyncio
async def test_blackboard_subscribe_async_returns_queue():
    """Async subscribers get a queue that receives published messages."""
    bb = Blackboard()
    queue = await bb.subscribe_async(Topic.TRADE_OUTCOMES, "test_sub")
    bb.publish(Topic.TRADE_OUTCOMES, {"ticker": "AAPL", "action": "buy"})
    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert isinstance(msg, BlackboardMessage)
    assert msg.payload["ticker"] == "AAPL"
