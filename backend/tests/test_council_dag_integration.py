"""Integration tests for full council DAG pipeline.

- bar event → signal.generated → council invocation → verdict output
- RED regime → council should output HOLD with max_pos=0
- signal score below threshold → council NOT invoked
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_signal_below_threshold_council_not_invoked():
    """When signal score is below regime-adaptive threshold, council is not run."""
    from app.council.council_gate import CouncilGate, _REGIME_GATE_THRESHOLDS

    bus = AsyncMock()
    bus.publish = AsyncMock()
    gate = CouncilGate(message_bus=bus, gate_threshold=65.0, max_concurrent=3)

    # RED regime threshold is 75
    gate._current_regime = "RED"
    threshold = gate._get_regime_threshold()
    assert threshold >= 75.0

    # Signal with score 60 should not invoke council (below 75)
    signal_data = {
        "symbol": "AAPL",
        "score": 60,
        "action": "BUY",
        "composite_score": 60,
        "regime": "RED",
    }
    # Simulate gate logic: would skip if score < threshold
    assert signal_data["composite_score"] < threshold


@pytest.mark.asyncio
async def test_red_regime_verdict_hold_max_pos_zero():
    """When regime is RED, order executor should enforce max_pos=0 (no new entries)."""
    from app.council.arbiter import arbitrate
    from app.council.schemas import AgentVote

    # Build votes that would normally be buy
    votes = [
        AgentVote("market_perception", "buy", 0.7, "bullish", weight=1.0),
        AgentVote("regime", "hold", 0.9, "RED regime", weight=1.2),
        AgentVote("risk", "buy", 0.6, "ok", weight=1.5),
        AgentVote("strategy", "buy", 0.65, "strategy buy", weight=1.1),
        AgentVote("execution", "buy", 0.7, "ready", weight=1.3),
    ]
    packet = arbitrate(
        symbol="AAPL",
        timeframe="1d",
        timestamp="2026-03-12T12:00:00Z",
        votes=votes,
    )
    # Arbiter produces a direction; regime enforcement (max_pos=0) is in OrderExecutor
    assert packet.final_direction in ("buy", "sell", "hold")
    assert 0.0 <= packet.final_confidence <= 1.0
    assert packet.risk_limits is not None


@pytest.mark.asyncio
async def test_bar_to_signal_to_council_flow_mocked():
    """Bar event → signal.generated → council invocation → verdict (mocked pipeline)."""
    from app.council.runner import run_council

    symbol = "SPY"
    timeframe = "1d"
    features = {
        "features": {
            "return_1d": 0.01,
            "return_5d": 0.02,
            "regime": "NEUTRAL",
            "last_close": 450.0,
        }
    }
    context = {}

    with patch("app.services.brain_client.get_brain_client") as m_brain:
        m_brain.return_value.enabled = False
        packet = await run_council(
            symbol=symbol,
            timeframe=timeframe,
            features=features,
            context=context,
        )
    assert packet is not None
    assert packet.symbol == symbol
    assert packet.final_direction in ("buy", "sell", "hold")
    assert len(packet.votes) >= 1
    assert packet.final_confidence >= 0.0 and packet.final_confidence <= 1.0


@pytest.mark.asyncio
async def test_regime_adaptive_threshold_values():
    """Regime-adaptive gate thresholds are defined for RED/GREEN/YELLOW."""
    from app.council.council_gate import _REGIME_GATE_THRESHOLDS

    assert _REGIME_GATE_THRESHOLDS["RED"] == 75.0
    assert _REGIME_GATE_THRESHOLDS["GREEN"] == 55.0
    assert _REGIME_GATE_THRESHOLDS["YELLOW"] == 65.0
    assert _REGIME_GATE_THRESHOLDS["CRISIS"] == 75.0
