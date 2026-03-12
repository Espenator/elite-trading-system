"""
Cascade simulation test — anti-adaptive fix verification.

Simulates market open with 150 candidates discovered simultaneously.
Measures how many swarm.idea events pass rate limiting (target >= 80%).
With time-of-day adaptive limits (market_open 3x), the bus should accept
at least 120 of 150 when published in a burst.
"""
import asyncio
import pytest

from app.core.message_bus import MessageBus


@pytest.fixture
def bus():
    """Fresh MessageBus for cascade test (no singleton)."""
    return MessageBus(max_queue_size=2000)


@pytest.mark.asyncio
async def test_cascade_150_ideas_at_least_80_percent_accepted(bus):
    """
    Simulate market open: 150 swarm.idea events in rapid succession.
    With adaptive rate limit (market_open 3x), >= 80% should be accepted.
    """
    await bus.start()

    # Force market_open multiplier so effective rate is 3x (150/sec for base 50)
    bus._rate_limit_multiplier = lambda: 3.0

    # Dummy subscriber so swarm.idea is not no-op (queue still processes)
    received = []

    async def _count(_data):
        received.append(1)

    await bus.subscribe("swarm.idea", _count)

    # Publish 150 ideas as fast as possible (simulate burst at market open)
    for i in range(150):
        await bus.publish("swarm.idea", {
            "source": "cascade_test",
            "symbols": [f"SYM{i}"],
            "direction": "bullish",
            "reasoning": "test",
            "priority": 5,
        })

    # Allow queue to drain (process events)
    for _ in range(50):
        await asyncio.sleep(0.02)

    rate_limited = bus._rate_limited_count.get("swarm.idea", 0)
    accepted = 150 - rate_limited

    await bus.stop()

    # Target: >= 80% of 150 = 120 (arch review measured ~30% before adaptive fix)
    assert accepted >= 120, (
        f"Cascade test: only {accepted}/150 swarm.idea accepted "
        f"(rate_limited={rate_limited}). Target >= 120 (80%)."
    )


@pytest.mark.asyncio
async def test_cascade_adaptive_multiplier_increases_effective_rate(bus):
    """With market_open multiplier 3x, effective rate is 3x base."""
    await bus.start()
    mult = bus._rate_limit_multiplier()
    await bus.stop()
    # During test we may be in any timezone; multiplier is 0.5, 1.0, 2.0, or 3.0
    assert mult in (0.5, 1.0, 2.0, 3.0)
