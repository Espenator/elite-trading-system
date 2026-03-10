import asyncio

import pytest


@pytest.mark.asyncio
async def test_hyperswarm_consumes_triage_and_escalates_to_signal_generated(monkeypatch):
    from app.core.message_bus import MessageBus
    from app.services.hyper_swarm import HyperSwarm, ESCALATION_THRESHOLD

    # Avoid DuckDB + network calls.
    async def _fake_context(self, symbol):
        return {}

    async def _fake_call_ollama(self, base_url, prompt):
        return "\n".join(
            [
                f"SCORE: {max(ESCALATION_THRESHOLD, 70)}",
                "DIRECTION: bullish",
                "CONFIDENCE: 0.9",
                "RISK: low",
                "REASON: looks good",
            ]
        )

    monkeypatch.setattr(HyperSwarm, "_get_symbol_context", _fake_context, raising=True)
    monkeypatch.setattr(HyperSwarm, "_call_ollama", _fake_call_ollama, raising=True)

    bus = MessageBus()
    await bus.start()

    signals = []
    results = []

    async def on_signal(data):
        signals.append(data)

    async def on_result(data):
        results.append(data)

    await bus.subscribe("signal.generated", on_signal)
    await bus.subscribe("swarm.result", on_result)

    hs = HyperSwarm(message_bus=bus)
    await hs.start()

    await bus.publish(
        "triage.escalated",
        {"source": "unit_test", "symbols": ["AAPL"], "direction": "bullish", "reasoning": "x", "triage": {"idea_id": "t1"}},
    )

    for _ in range(200):
        if signals and results:
            break
        await asyncio.sleep(0.01)

    await hs.stop()
    await bus.stop()

    assert any(r.get("type") == "micro_swarm_result" for r in results)
    assert len(signals) == 1
    assert signals[0]["symbol"] == "AAPL"
    assert signals[0]["source"] == "hyper_swarm"
    assert 0 <= float(signals[0]["score"]) <= 100

