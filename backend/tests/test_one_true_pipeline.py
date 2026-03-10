"""Audit: One True Pipeline — swarm.idea must not directly trigger council/spawn; only triage.escalated does."""
import asyncio

import pytest


@pytest.mark.asyncio
async def test_swarm_idea_does_not_directly_trigger_spawn():
    """Publishing to swarm.idea must NOT cause SwarmSpawner to queue work (no bypass)."""
    from app.core.message_bus import MessageBus
    from app.services.swarm_spawner import SwarmSpawner

    bus = MessageBus()
    await bus.start()
    spawner = SwarmSpawner(message_bus=bus)
    await spawner.start()

    # Publish raw idea to swarm.idea (no triage in between)
    await bus.publish(
        "swarm.idea",
        {
            "symbols": ["AAPL"],
            "source": "test",
            "direction": "bullish",
            "reasoning": "test",
            "priority": 1,
        },
    )

    # Give handlers time to run
    await asyncio.sleep(0.1)

    # SwarmSpawner subscribes to triage.escalated only — so queue must still be empty
    assert spawner._queue.qsize() == 0, "swarm.idea must not directly trigger SwarmSpawner"

    await spawner.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_triage_escalated_triggers_spawn():
    """Only triage.escalated must cause SwarmSpawner to queue work."""
    from app.core.message_bus import MessageBus
    from app.services.swarm_spawner import SwarmSpawner

    bus = MessageBus()
    await bus.start()
    spawner = SwarmSpawner(message_bus=bus)
    await spawner.start()

    # Publish escalated payload (as IdeaTriageService would)
    await bus.publish(
        "triage.escalated",
        {
            "symbols": ["MSFT"],
            "source": "test",
            "direction": "bullish",
            "reasoning": "test",
            "priority": 1,
            "triage": {"symbol": "MSFT", "escalated": True},
        },
    )

    await asyncio.sleep(0.15)

    # SwarmSpawner should have queued one idea
    assert spawner._queue.qsize() >= 1 or spawner._stats["total_spawned"] >= 1, (
        "triage.escalated must trigger SwarmSpawner"
    )

    await spawner.stop()
    await bus.stop()
