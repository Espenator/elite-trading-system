import asyncio
import os
import pytest


class _StubBus:
    def __init__(self):
        self.published = []

    async def publish(self, topic: str, data: dict):
        self.published.append((topic, data))


@pytest.mark.asyncio
async def test_council_gate_threshold_70_passes_50_does_not(monkeypatch):
    from app.council.council_gate import CouncilGate

    bus = _StubBus()
    gate = CouncilGate(message_bus=bus, gate_threshold=65.0)
    gate._running = True

    called = []

    async def _fake_eval(symbol, signal_data):
        called.append((symbol, signal_data.get("score")))

    monkeypatch.setattr(gate, "_evaluate_with_council", _fake_eval)

    await gate._on_signal({"symbol": "AAPL", "score": 50.0, "source": "unit_test"})
    await asyncio.sleep(0)
    assert called == []

    await gate._on_signal({"symbol": "AAPL", "score": 70.0, "source": "unit_test"})
    await asyncio.sleep(0)
    assert called and called[-1][0] == "AAPL"


@pytest.mark.asyncio
async def test_signal_to_verdict_fallback_maps_confidence(monkeypatch):
    from app.core.score_semantics import (
        coerce_gate_threshold_0_100,
        coerce_signal_score_0_100,
        score_to_final_confidence_0_1,
    )

    monkeypatch.setenv("COUNCIL_GATE_THRESHOLD", "65.0")
    gate_threshold = coerce_gate_threshold_0_100(
        os.getenv("COUNCIL_GATE_THRESHOLD", "65.0"),
        context="test",
    )

    low = coerce_signal_score_0_100(50.0, context="test")
    high = coerce_signal_score_0_100(70.0, context="test")

    assert low < gate_threshold
    assert high >= gate_threshold
    assert abs(score_to_final_confidence_0_1(high, context="test") - 0.70) < 1e-9


@pytest.mark.asyncio
async def test_message_bus_coerces_signal_generated_score_to_0_100():
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    await bus.start()
    try:
        received = []

        async def _collector(data):
            received.append(data)

        await bus.subscribe("signal.generated", _collector)

        # Normalized score should be scaled 0..1 -> 0..100
        await bus.publish("signal.generated", {"symbol": "AAPL", "score": 0.7})
        await asyncio.sleep(0.01)
        assert received[-1]["score"] == 70.0

        # Out-of-range scores should be clamped
        await bus.publish("signal.generated", {"symbol": "AAPL", "score": 120})
        await asyncio.sleep(0.01)
        assert received[-1]["score"] == 100.0

        await bus.publish("signal.generated", {"symbol": "AAPL", "score": -5})
        await asyncio.sleep(0.01)
        assert received[-1]["score"] == 0.0
    finally:
        await bus.stop()

