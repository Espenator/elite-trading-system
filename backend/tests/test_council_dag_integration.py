"""Integration tests for full council DAG pipeline.

Tests: bar → signal.generated → council invocation → verdict;
      RED regime → HOLD / max_pos=0; signal below threshold → council NOT invoked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.schemas import AgentVote, DecisionPacket


def _make_vote(name: str, direction: str = "buy", confidence: float = 0.7) -> AgentVote:
    return AgentVote(agent_name=name, direction=direction, confidence=confidence,
                    reasoning=f"{name} vote", weight=1.0)


@pytest.mark.anyio
@patch("app.council.reflexes.circuit_breaker.circuit_breaker")
async def test_run_council_returns_decision_packet(mock_cb):
    """Council invocation returns a valid DecisionPacket (mocked agents)."""
    mock_cb.check_all = AsyncMock(return_value=None)

    stage1 = [_make_vote("market_perception"), _make_vote("regime")]
    stage2 = [_make_vote("rsi")]
    stage3 = [_make_vote("hypothesis"), _make_vote("layered_memory_agent")]
    stage4 = _make_vote("strategy")
    stage5 = [_make_vote("risk"), _make_vote("execution"), _make_vote("portfolio_optimizer_agent")]
    stage6 = _make_vote("critic")

    mock_spawner = MagicMock()
    mock_spawner.spawn_parallel = AsyncMock(side_effect=[stage1, stage2, stage3, stage5])
    mock_spawner.spawn = AsyncMock(side_effect=[stage4, stage6])
    mock_spawner.register_all_agents = MagicMock()
    mock_spawner.registered_agents = set()

    with patch("app.council.runner.TaskSpawner", return_value=mock_spawner):
        from app.council.runner import run_council
        decision = await run_council("AAPL", "1d", features={"features": {"regime": "GREEN"}}, context={})

    assert isinstance(decision, DecisionPacket)
    assert decision.symbol == "AAPL"
    assert decision.final_direction in ("buy", "sell", "hold")
    assert 0 <= decision.final_confidence <= 1.0


@pytest.mark.anyio
async def test_red_regime_has_max_pos_zero():
    """RED regime params enforce max_pos=0 (blocks new entries)."""
    from app.api.v1.strategy import REGIME_PARAMS
    red_params = REGIME_PARAMS.get("RED", {})
    assert red_params.get("max_pos") == 0
    assert red_params.get("kelly_scale", 1) <= 0.25


@pytest.mark.anyio
async def test_signal_below_threshold_does_not_invoke_council():
    """Signal score below gate threshold does not increment councils_invoked."""
    from app.council.council_gate import CouncilGate

    mock_bus = MagicMock()
    gate = CouncilGate(message_bus=mock_bus, gate_threshold=65.0)
    gate._running = True
    gate._current_regime = "NEUTRAL"
    gate._councils_invoked = 0
    gate._semaphore = __import__("asyncio").Semaphore(2)
    gate._priority_queue = []
    gate._symbol_direction_last_eval = {}
    gate._symbol_last_eval = {}

    await gate._on_signal({"symbol": "TEST", "score": 50.0, "direction": "buy"})
    assert gate._councils_invoked == 0
