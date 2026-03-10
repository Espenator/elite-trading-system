import asyncio

import pytest


@pytest.mark.asyncio
async def test_council_gate_publishes_single_verdict_per_signal(monkeypatch):
    """Regression: ensure we don't have multiple invokers double-publishing verdicts."""
    from app.core.message_bus import MessageBus
    from app.council.council_gate import CouncilGate

    verdicts = []

    async def on_verdict(data):
        verdicts.append(data)

    bus = MessageBus()
    await bus.start()
    await bus.subscribe("council.verdict", on_verdict)

    # Stub run_council so the test doesn't depend on the full DAG/LLM stack.
    class _Decision:
        vetoed = False
        veto_reasons = []
        final_direction = "buy"
        final_confidence = 0.9
        execution_ready = True
        votes = [1]

        def to_dict(self):
            return {
                "symbol": "AAPL",
                "vetoed": False,
                "veto_reasons": [],
                "final_direction": "buy",
                "final_confidence": 0.9,
                "execution_ready": True,
                "votes": [1],
                "council_reasoning": "stub",
            }

    async def _stub_run_council(*args, **kwargs):
        return _Decision()

    monkeypatch.setattr("app.council.runner.run_council", _stub_run_council)

    gate = CouncilGate(message_bus=bus, gate_threshold=0.0, max_concurrent=1, cooldown_seconds=0)
    await gate.start()

    await bus.publish(
        "signal.generated",
        {"symbol": "AAPL", "score": 90, "direction": "buy", "price": 123.45, "source": "unit_test"},
    )

    # Allow background task to run.
    for _ in range(50):
        if verdicts:
            break
        await asyncio.sleep(0.01)

    await gate.stop()
    await bus.stop()

    assert len(verdicts) == 1
    assert verdicts[0].get("symbol") == "AAPL"


@pytest.mark.asyncio
async def test_council_fallback_is_safe_and_non_executable_by_default(monkeypatch):
    from app.core.message_bus import MessageBus
    from app.services.council_invocation import setup_council_invocation

    monkeypatch.setenv("COUNCIL_VERDICT_FALLBACK_ENABLED", "true")
    monkeypatch.delenv("COUNCIL_GATE_ENABLED", raising=False)
    monkeypatch.setenv("AUTO_EXECUTE_TRADES", "false")
    monkeypatch.delenv("COUNCIL_FALLBACK_EXECUTION_READY", raising=False)

    verdicts = []

    async def on_verdict(data):
        verdicts.append(data)

    bus = MessageBus()
    await bus.start()
    await bus.subscribe("council.verdict", on_verdict)

    setup = await setup_council_invocation(bus, llm_enabled=False, council_enabled=False)
    assert setup["mode"] == "fallback"

    await bus.publish(
        "signal.generated",
        {"symbol": "AAPL", "score": 90, "direction": "buy", "price": 100.0, "source": "unit_test"},
    )

    for _ in range(50):
        if verdicts:
            break
        await asyncio.sleep(0.01)

    await bus.stop()

    assert len(verdicts) == 1
    assert verdicts[0]["execution_ready"] is False
    assert verdicts[0]["vetoed"] is True
    assert verdicts[0]["source"] == "council_fallback"

