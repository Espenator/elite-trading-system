"""Scout discovery pipeline: swarm.idea → triage → DiscoverySignalBridge → signal.generated → council path.

Verifies that mock DiscoveryPayload published to swarm.idea is consumed by IdeaTriageService,
escalated to triage.escalated, and DiscoverySignalBridge publishes signal.generated so
the idea reaches CouncilGate (and thus council/OrderExecutor) without requiring HyperSwarm/Ollama.
"""
import asyncio
from unittest.mock import patch

import pytest

from app.core.score_semantics import coerce_signal_score_0_100


@pytest.mark.asyncio
async def test_swarm_idea_reaches_signal_generated_via_bridge():
    """Publish mock DiscoveryPayload to swarm.idea → triage escalates → bridge → signal.generated."""
    from app.core.message_bus import MessageBus
    from app.services.idea_triage import get_idea_triage_service
    from app.services.discovery_signal_bridge import get_discovery_signal_bridge

    triage_escalated = []
    signals_generated = []

    bus = MessageBus()
    await bus.start()

    async def on_escalated(data):
        triage_escalated.append(data)

    async def on_signal(data):
        signals_generated.append(data)

    await bus.subscribe("triage.escalated", on_escalated)
    await bus.subscribe("signal.generated", on_signal)

    triage_svc = get_idea_triage_service()
    triage_svc._bus = bus
    await triage_svc.start()

    bridge = get_discovery_signal_bridge()
    bridge._bus = bus
    await bridge.start()

    # Mock DiscoveryPayload as swarm.idea dict (high priority + flow_hunter so triage score passes)
    await bus.publish(
        "swarm.idea",
        {
            "source": "flow_hunter_scout",
            "symbols": ["SCOUT_TEST"],
            "direction": "bullish",
            "reasoning": "Unusual options flow test",
            "priority": 1,
            "metadata": {},
        },
    )

    for _ in range(60):
        await asyncio.sleep(0.05)
        if triage_escalated and signals_generated:
            break

    await bridge.stop()
    await triage_svc.stop()
    await bus.stop()

    assert len(triage_escalated) >= 1, "IdeaTriage should escalate scout idea"
    assert triage_escalated[0].get("symbols") == ["SCOUT_TEST"] or "SCOUT_TEST" in str(
        triage_escalated[0].get("symbols", [])
    )

    assert len(signals_generated) >= 1, "DiscoverySignalBridge should publish signal.generated"
    sig = signals_generated[0]
    assert sig.get("symbol") == "SCOUT_TEST"
    score = sig.get("score", 0)
    if isinstance(score, (int, float)) and score <= 1:
        score = coerce_signal_score_0_100(score)
    assert 55 <= score <= 100, "Bridge score should pass gate (>= 55)"


@pytest.mark.asyncio
async def test_swarm_idea_to_council_verdict_with_bridge():
    """Full path: DiscoveryPayload → swarm.idea → triage → bridge → signal.generated → CouncilGate → council.verdict."""
    from app.core.message_bus import MessageBus
    from app.services.idea_triage import get_idea_triage_service
    from app.services.discovery_signal_bridge import get_discovery_signal_bridge
    from app.council.council_gate import CouncilGate
    from app.services.order_executor import OrderExecutor

    triage_escalated = []
    signals_generated = []
    verdicts = []
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_escalated(data):
        triage_escalated.append(data)

    async def on_signal(data):
        signals_generated.append(data)

    async def on_verdict(data):
        verdicts.append(data)

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("triage.escalated", on_escalated)
    await bus.subscribe("signal.generated", on_signal)
    await bus.subscribe("council.verdict", on_verdict)
    await bus.subscribe("order.submitted", on_order)

    triage_svc = get_idea_triage_service()
    triage_svc._bus = bus
    await triage_svc.start()

    bridge = get_discovery_signal_bridge()
    bridge._bus = bus
    await bridge.start()

    async def _stub_run_council(symbol=None, timeframe=None, context=None, **kwargs):
        from types import SimpleNamespace
        sym = symbol or kwargs.get("symbol", "SCOUT_E2E")
        return SimpleNamespace(
            vetoed=False,
            veto_reasons=[],
            final_direction="buy",
            final_confidence=0.9,
            execution_ready=True,
            votes=[1],
            symbol=sym,
            to_dict=lambda: {
                "symbol": sym,
                "vetoed": False,
                "veto_reasons": [],
                "final_direction": "buy",
                "final_confidence": 0.9,
                "execution_ready": True,
                "votes": [1],
                "council_reasoning": "scout_e2e stub",
            },
        )

    with patch("app.council.runner.run_council", side_effect=_stub_run_council):
        gate = CouncilGate(
            message_bus=bus,
            gate_threshold=0.0,
            max_concurrent=2,
            cooldown_seconds=0,
        )
        await gate.start()

        executor = OrderExecutor(
            message_bus=bus,
            auto_execute=False,
            min_score=0,
            max_daily_trades=100,
            cooldown_seconds=0,
        )

        async def _stub_compute_kelly(symbol, score, regime, price, direction):
            return {
                "action": "TRADE",
                "kelly_pct": 0.05,
                "qty": 10,
                "edge": 0.1,
                "stats_source": "scout_e2e",
                "stop_loss": (price or 100) * 0.98,
                "take_profit": (price or 100) * 1.05,
                "raw_kelly": 0.05,
                "win_rate": 0.55,
                "trade_count": 50,
            }

        executor._compute_kelly_size = _stub_compute_kelly
        await executor.start()

        await bus.publish(
            "swarm.idea",
            {
                "source": "flow_hunter_scout",
                "symbols": ["SCOUT_E2E"],
                "direction": "bullish",
                "reasoning": "Scout E2E test",
                "priority": 1,
                "metadata": {"price": 100.0},
            },
        )

        for _ in range(100):
            await asyncio.sleep(0.05)
            if verdicts and orders_submitted:
                break

        await executor.stop()
        await gate.stop()

    await bridge.stop()
    await triage_svc.stop()
    await bus.stop()

    assert len(signals_generated) >= 1, "Bridge should emit signal.generated"
    assert signals_generated[0].get("symbol") == "SCOUT_E2E"
    assert len(verdicts) >= 1, "CouncilGate should publish council.verdict"
    assert verdicts[0].get("execution_ready") is True
    assert len(orders_submitted) >= 1, "OrderExecutor should publish order.submitted"
    assert orders_submitted[0].get("symbol") == "SCOUT_E2E"
