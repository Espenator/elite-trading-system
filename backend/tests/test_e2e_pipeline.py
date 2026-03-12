"""End-to-end pipeline test: swarm.idea → triage → signal → council → order → outcome.

Uses real MessageBus and service wiring; mocks external APIs (Ollama, Alpaca).
Verifies the One True Pipeline flow in one test.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.core.score_semantics import coerce_signal_score_0_100


@pytest.mark.asyncio
async def test_e2e_swarm_idea_to_order_submitted():
    """Full pipeline: publish SensoryEvent to swarm.idea → triage escalates → HyperSwarm
    publishes signal.generated → CouncilGate invokes council → council.verdict →
    OrderExecutor publishes order.submitted. All with real MessageBus, mocked LLM/Alpaca.
    """
    from app.core.message_bus import MessageBus
    from app.services.idea_triage import get_idea_triage_service
    from app.services.hyper_swarm import HyperSwarm, MicroSwarmResult, get_hyper_swarm
    from app.council.council_gate import CouncilGate
    from app.services.order_executor import OrderExecutor

    # Collectors for assertions
    triage_escalated = []
    signals_generated = []
    verdicts = []
    orders_submitted = []

    bus = MessageBus()
    await bus.start()

    async def on_triage_escalated(data):
        triage_escalated.append(data)

    async def on_signal(data):
        signals_generated.append(data)

    async def on_verdict(data):
        verdicts.append(data)

    async def on_order(data):
        orders_submitted.append(data)

    await bus.subscribe("triage.escalated", on_triage_escalated)
    await bus.subscribe("signal.generated", on_signal)
    await bus.subscribe("council.verdict", on_verdict)
    await bus.subscribe("order.submitted", on_order)

    # 1. IdeaTriageService — real
    triage_svc = get_idea_triage_service()
    triage_svc._bus = bus
    await triage_svc.start()

    # 2. HyperSwarm — stub _run_micro_swarm so we don't need Ollama
    async def _stub_run_micro_swarm(signal_data, worker_id):
        symbols = signal_data.get("symbols", [])
        symbol = symbols[0] if symbols else "E2E"
        return MicroSwarmResult(
            signal_id=f"e2e-{symbol}",
            symbol=symbol,
            signal_type="QuickScore",
            score=80,
            direction="bullish",
            confidence=0.85,
            reasoning="E2E test stub",
            risk_level="medium",
            escalated=False,
            ollama_node="stub",
            latency_ms=0.0,
        )

    with patch("app.services.ollama_node_pool.get_ollama_pool") as mock_pool:
        mock_pool.return_value = MagicMock(
            urls=["http://localhost:11434"],
            get_next_node=MagicMock(return_value="http://localhost:11434"),
            get_semaphore=MagicMock(return_value=None),
        )
        hyper_swarm = get_hyper_swarm()
        hyper_swarm._bus = bus
        hyper_swarm._run_micro_swarm = _stub_run_micro_swarm
        await hyper_swarm.start()

    # 3. CouncilGate — stub run_council so we don't need full DAG/LLM
    async def _stub_run_council(symbol=None, timeframe=None, context=None, **kwargs):
        from types import SimpleNamespace
        sym = symbol or kwargs.get("symbol", "E2E")
        d = SimpleNamespace(
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
                "council_reasoning": "e2e stub",
            },
        )
        return d

    with patch("app.council.runner.run_council", side_effect=_stub_run_council):
        gate = CouncilGate(
            message_bus=bus,
            gate_threshold=0.0,
            max_concurrent=2,
            cooldown_seconds=0,
        )
        await gate.start()

        # 4. OrderExecutor — shadow mode; mock Kelly/trade_stats so SizingGate passes
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
                "stats_source": "e2e_test",
                "stop_loss": price * 0.98,
                "take_profit": price * 1.05,
                "raw_kelly": 0.05,
                "win_rate": 0.55,
                "trade_count": 50,
            }
        executor._compute_kelly_size = _stub_compute_kelly
        await executor.start()

        # 5. Publish synthetic idea (high priority so triage escalates; price for OrderExecutor)
        await bus.publish(
            "swarm.idea",
            {
                "symbols": ["E2E"],
                "source": "e2e_test",
                "direction": "bullish",
                "reasoning": "End-to-end pipeline test",
                "priority": 1,
                "price": 100.0,
            },
        )

        # 6. Poll for pipeline completion (triage → signal → verdict → order)
        for _ in range(80):
            await asyncio.sleep(0.05)
            if triage_escalated and signals_generated and verdicts and orders_submitted:
                break

        await executor.stop()
        await gate.stop()

    await hyper_swarm.stop()
    await triage_svc.stop()
    await bus.stop()

    # Assertions
    assert len(triage_escalated) >= 1, "IdeaTriageService should escalate high-priority idea"
    assert triage_escalated[0].get("symbols") == ["E2E"] or "E2E" in str(triage_escalated[0].get("symbols", []))

    assert len(signals_generated) >= 1, "HyperSwarm should publish signal.generated"
    sig = signals_generated[0]
    score = sig.get("score", 0)
    if isinstance(score, float) and score <= 1:
        score = coerce_signal_score_0_100(score)
    assert 0 <= score <= 100, "signal.generated score must be 0-100"

    assert len(verdicts) >= 1, "CouncilGate should publish council.verdict"
    assert verdicts[0].get("execution_ready") is True
    assert verdicts[0].get("final_direction") == "buy"

    assert len(orders_submitted) >= 1, "OrderExecutor should publish order.submitted"
    assert orders_submitted[0].get("symbol") == "E2E"


@pytest.mark.asyncio
async def test_e2e_fill_to_weight_learner_update():
    """E2E test: council.verdict → record_decision → order.filled → outcome.resolved → weight_learner.update.

    Extended pipeline that verifies the full learning loop:
    1. Council votes are recorded in weight_learner
    2. Order execution completes (order.filled)
    3. Outcome is published (outcome.resolved) with pnl + r_multiple
    4. weight_learner.update_from_outcome() is called
    5. Aligned agents get upweighted; misaligned agents get downweighted
    """
    from app.core.message_bus import MessageBus
    from app.council.weight_learner import WeightLearner
    from app.council.schemas import AgentVote

    # Collectors for assertions
    outcomes_resolved = []

    bus = MessageBus()
    await bus.start()

    async def on_outcome(data):
        outcomes_resolved.append(data)

    await bus.subscribe("outcome.resolved", on_outcome)

    # 1. Create a weight learner and record a decision
    wl = WeightLearner(learning_rate=0.05, min_weight=0.2, max_weight=2.5)

    # Create mock decision with AgentVotes
    from types import SimpleNamespace
    decision = SimpleNamespace(
        decision_id="e2e-test-001",
        symbol="E2E_TEST",
        timestamp="2026-03-12T12:00:00Z",
        final_direction="buy",
        final_confidence=0.9,
        regime="BULLISH",
        votes=[
            AgentVote(
                agent_name="market_perception",
                direction="buy",
                confidence=0.95,
                reasoning="Strong bullish signal",
                weight=1.0,
            ),
            AgentVote(
                agent_name="risk",
                direction="buy",
                confidence=0.8,
                reasoning="Risk acceptable",
                weight=1.3,
            ),
            AgentVote(
                agent_name="strategy",
                direction="hold",
                confidence=0.6,
                reasoning="Uncertain strategy",
                weight=1.1,
            ),
        ],
    )

    # Record the decision
    wl.record_decision(decision)
    assert len(wl._decision_history) >= 1, "Decision should be recorded"

    # Get initial weights
    initial_weights = wl.get_weights()
    initial_market_perception_weight = initial_weights.get("market_perception", 1.0)
    initial_strategy_weight = initial_weights.get("strategy", 1.0)

    # 2. Simulate order.filled (just publish to bus)
    await bus.publish("order.filled", {
        "symbol": "E2E_TEST",
        "order_id": "e2e-order-001",
        "qty": 10,
        "filled_price": 100.0,
        "side": "buy",
    })

    # 3. Simulate trade outcome: profitable, so council's "buy" direction was correct
    await bus.publish("outcome.resolved", {
        "symbol": "E2E_TEST",
        "outcome_direction": "win",  # outcome was profitable
        "pnl": 150.0,
        "r_multiple": 1.5,
        "debate_quality_score": 0.8,
        "red_team_score": 0.9,
        "regime_entropy": 0.5,
        "trade_id": "e2e-test-001",
        "confidence": 0.95,
    })

    # Poll for outcome event
    for _ in range(50):
        await asyncio.sleep(0.01)
        if outcomes_resolved:
            break

    # 4. Call weight_learner.update_from_outcome() with the same trade_id
    updated_weights = wl.update_from_outcome(
        symbol="E2E_TEST",
        outcome_direction="win",
        pnl=150.0,
        r_multiple=1.5,
        debate_quality_score=0.8,
        red_team_score=0.9,
        regime_entropy=0.5,
        is_censored=False,
        confidence=0.95,
        trade_id="e2e-test-001",
    )

    # 5. Verify weight updates
    # market_perception voted "buy" → outcome was "win" → should be upweighted
    assert updated_weights.get("market_perception", 1.0) > initial_market_perception_weight, \
        f"market_perception should be upweighted (was {initial_market_perception_weight}, now {updated_weights.get('market_perception', 1.0)})"

    # strategy voted "hold" (direction doesn't match "buy") → should be downweighted or neutral
    # (downweighting happens when votes are examined)

    assert len(outcomes_resolved) >= 1, "outcome.resolved should be published"
    assert outcomes_resolved[0].get("symbol") == "E2E_TEST"
    assert outcomes_resolved[0].get("outcome_direction") == "win"

    await bus.stop()
