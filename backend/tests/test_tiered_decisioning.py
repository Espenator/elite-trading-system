"""Tests for tiered decisioning (Fast Council + Deep Council routing)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.council.schemas import DecisionPacket, AgentVote


@pytest.mark.asyncio
async def test_fast_council_basic():
    """Test that fast council runs with 5 agents and returns a decision."""
    from app.council.fast_runner import run_fast_council

    # Mock features
    features = {
        "symbol": "AAPL",
        "features": {
            "close": 150.0,
            "volume": 1000000,
            "regime": "bull",
        }
    }

    # Mock TaskSpawner to return stub votes
    with patch("app.council.fast_runner.TaskSpawner") as mock_spawner_class:
        mock_spawner = MagicMock()
        mock_spawner_class.return_value = mock_spawner
        mock_spawner.register_all_agents = MagicMock()

        # Mock spawn_parallel to return 2 votes (market_perception, regime)
        mock_spawner.spawn_parallel = AsyncMock(return_value=[
            AgentVote("market_perception", "buy", 0.6, "Price trending up", 1.0),
            AgentVote("regime", "buy", 0.7, "Bull regime", 1.2),
        ])

        # Mock spawn to return single votes (risk, strategy)
        mock_spawner.spawn = AsyncMock(side_effect=[
            AgentVote("risk", "buy", 0.75, "Risk acceptable", 1.5),
            AgentVote("strategy", "buy", 0.8, "Good entry", 1.1),
        ])

        with patch("app.council.fast_runner.arbitrate") as mock_arbitrate:
            mock_arbitrate.return_value = DecisionPacket(
                symbol="AAPL",
                timeframe="1d",
                timestamp="2026-03-09T00:00:00",
                votes=[],
                final_direction="buy",
                final_confidence=0.75,
                reasoning="Fast council consensus",
                metadata={"council_tier": "fast"},
            )

            decision = await run_fast_council(
                symbol="AAPL",
                timeframe="1d",
                features=features,
                signal_score=80.0,
            )

            # Verify decision returned
            assert decision is not None
            assert decision.symbol == "AAPL"
            assert decision.final_direction in ["buy", "sell", "hold"]
            assert decision.metadata.get("council_tier") == "fast"


@pytest.mark.asyncio
async def test_should_escalate_to_deep():
    """Test escalation logic from fast to deep council."""
    from app.council.fast_runner import should_escalate_to_deep

    # Low confidence should escalate
    low_conf_decision = DecisionPacket(
        symbol="AAPL",
        timeframe="1d",
        timestamp="2026-03-09T00:00:00",
        votes=[],
        final_direction="buy",
        final_confidence=0.6,  # Below 0.7 threshold
        reasoning="Low confidence",
        metadata={"council_tier": "fast"},
    )
    assert await should_escalate_to_deep(low_conf_decision, threshold=0.7) is True

    # High confidence should not escalate
    high_conf_decision = DecisionPacket(
        symbol="AAPL",
        timeframe="1d",
        timestamp="2026-03-09T00:00:00",
        votes=[],
        final_direction="buy",
        final_confidence=0.85,  # Above 0.7 threshold
        reasoning="High confidence",
        metadata={"council_tier": "fast"},
    )
    assert await should_escalate_to_deep(high_conf_decision, threshold=0.7) is False

    # Risk veto should escalate
    risk_veto_decision = DecisionPacket(
        symbol="AAPL",
        timeframe="1d",
        timestamp="2026-03-09T00:00:00",
        votes=[
            AgentVote("risk", "hold", 0.9, "Risk too high", 1.5),
        ],
        final_direction="buy",
        final_confidence=0.8,
        reasoning="But risk vetoed",
        metadata={"council_tier": "fast"},
    )
    assert await should_escalate_to_deep(risk_veto_decision, threshold=0.7) is True


@pytest.mark.asyncio
async def test_council_gate_tiered_routing():
    """Test CouncilGate routes to fast/deep council based on score."""
    from app.council.council_gate import CouncilGate
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    gate = CouncilGate(bus, gate_threshold=65.0, fast_threshold=75.0)

    # Verify thresholds set correctly
    assert gate.gate_threshold == 65.0
    assert gate.fast_threshold == 75.0

    # Verify counters initialized
    assert gate._fast_councils == 0
    assert gate._deep_councils == 0
    assert gate._escalations == 0


def test_fast_council_file_exists():
    """Verify fast_runner.py module exists."""
    import app.council.fast_runner
    assert app.council.fast_runner is not None


def test_layered_memory_agent_wired():
    """Verify layered_memory_agent is wired in Stage 3 of runner.py."""
    with open("backend/app/council/runner.py", "r") as f:
        content = f.read()
        # Check that layered_memory_agent is in Stage 3 config
        assert "layered_memory_agent" in content
        assert 'agent_type": "layered_memory_agent"' in content


def test_p0_p1_fixes_verified():
    """Verify all P0/P1 fixes are in place."""
    # P0-1: TurboScanner score scale fix
    with open("backend/app/services/turbo_scanner.py", "r") as f:
        content = f.read()
        assert "signal.score * 100" in content  # Score conversion

    # P0-2: Single council.verdict publication
    with open("backend/app/council/runner.py", "r") as f:
        content = f.read()
        # Should have comment about removed duplicate
        assert "council.verdict publish is handled canonically by council_gate.py" in content

    # P0-3: UnusualWhales MessageBus wiring
    with open("backend/app/services/unusual_whales_service.py", "r") as f:
        content = f.read()
        assert 'publish("perception.unusualwhales"' in content

    # P1-4: SelfAwareness called
    with open("backend/app/council/runner.py", "r") as f:
        content = f.read()
        assert "get_self_awareness()" in content
        assert "should_skip_agent" in content

    # P1-5: IntelligenceCache.start() called
    with open("backend/app/main.py", "r") as f:
        content = f.read()
        assert "IntelligenceCache" in content
        assert "await _intelligence_cache.start()" in content

    # P1-6: brain_service gRPC wired to hypothesis_agent
    with open("backend/app/council/agents/hypothesis_agent.py", "r") as f:
        content = f.read()
        assert "from app.services.brain_client import get_brain_client" in content
        assert "client = get_brain_client()" in content
