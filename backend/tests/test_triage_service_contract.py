import asyncio
from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_triage_emits_drop_reasons_and_audit_trail(monkeypatch):
    from app.core.message_bus import MessageBus
    from app.services.idea_triage import IdeaTriageService

    # Make threshold deterministically high so we exercise below_threshold.
    monkeypatch.setattr("app.services.idea_triage.BASE_THRESHOLD", 80, raising=False)

    bus = MessageBus()
    await bus.start()
    triage = IdeaTriageService(message_bus=bus)

    escalated = []
    dropped = []

    async def on_escalated(data):
        escalated.append(data)

    async def on_dropped(data):
        dropped.append(data)

    await bus.subscribe("triage.escalated", on_escalated)
    await bus.subscribe("triage.dropped", on_dropped)
    await triage.start()

    # 1) Invalid payload → dropped with invalid_payload
    await bus.publish("swarm.idea", {"source": "unit_test", "priority": 5})

    # 2) Old/low-quality → below_threshold
    old_ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    await bus.publish(
        "swarm.idea",
        {"symbols": ["AAPL"], "source": "unit_test", "priority": 5, "metadata": {"detected_at": old_ts}},
    )

    # 3) High quality → escalated
    await bus.publish(
        "swarm.idea",
        {"symbols": ["MSFT"], "source": "insider_scout", "priority": 1, "metadata": {"detected_at": datetime.now(timezone.utc).isoformat()}},
    )

    # 4) Immediate repeat → cooldown
    await bus.publish(
        "swarm.idea",
        {"symbols": ["MSFT"], "source": "insider_scout", "priority": 1, "metadata": {"detected_at": datetime.now(timezone.utc).isoformat()}},
    )

    # Let async handlers run.
    for _ in range(100):
        if len(escalated) >= 1 and len(dropped) >= 3:
            break
        await asyncio.sleep(0.01)

    await triage.stop()
    await bus.stop()

    assert any(d.get("triage", {}).get("drop_reason") == "invalid_payload" for d in dropped)
    assert any(d.get("triage", {}).get("drop_reason") == "below_threshold" for d in dropped)
    assert any(d.get("triage", {}).get("drop_reason") == "cooldown" for d in dropped)
    assert len(escalated) == 1


@pytest.mark.asyncio
async def test_triage_drops_stale_ideas():
    """Stale ideas (age > MAX_IDEA_AGE_SECS) are dropped with drop_reason=stale."""
    from app.services.idea_triage import IdeaTriageService, MAX_IDEA_AGE_SECS
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    await bus.start()
    triage = IdeaTriageService(message_bus=bus)
    dropped = []

    async def on_dropped(data):
        dropped.append(data)

    await bus.subscribe("triage.dropped", on_dropped)
    await triage.start()

    # Idea with very old timestamp (stale)
    old_ts = (datetime.now(timezone.utc) - timedelta(seconds=MAX_IDEA_AGE_SECS + 60)).isoformat()
    await bus.publish(
        "swarm.idea",
        {
            "symbols": ["AAPL"],
            "source": "insider_scout",
            "priority": 1,
            "metadata": {"detected_at": old_ts},
        },
    )

    for _ in range(50):
        if dropped:
            break
        await asyncio.sleep(0.02)

    await triage.stop()
    await bus.stop()

    assert len(dropped) >= 1
    assert any(d.get("triage", {}).get("drop_reason") == "stale" for d in dropped)


@pytest.mark.anyio
async def test_triage_status_endpoint(client):
    r = await client.get("/api/v1/triage/status")
    assert r.status_code == 200
    body = r.json()
    assert "total_received" in body
    assert "dropped_by_reason" in body
    assert "recent_dropped" in body

