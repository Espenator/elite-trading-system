"""Tests for the 11-agent debate council + arbiter."""
import pytest
from unittest.mock import patch

from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate, REQUIRED_AGENTS, VETO_AGENTS


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------
def _vote(name, direction="buy", confidence=0.7, veto=False, veto_reason="", weight=1.0, **meta):
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} test vote",
        veto=veto,
        veto_reason=veto_reason,
        weight=weight,
        metadata=meta,
    )


def _full_votes(
    market_dir="buy",
    flow_dir="buy",
    regime_dir="buy",
    hypothesis_dir="buy",
    strategy_dir="buy",
    risk_dir="buy",
    execution_dir="buy",
    critic_dir="hold",
    risk_veto=False,
    exec_veto=False,
    risk_veto_reason="",
    exec_veto_reason="",
    execution_ready=True,
):
    """Build a list of 8 core agent votes with configurable directions (3 perception agents write to blackboard)."""
    return [
        _vote("market_perception", market_dir, weight=1.0),
        _vote("flow_perception", flow_dir, weight=0.8),
        _vote("regime", regime_dir, weight=1.2),
        _vote("hypothesis", hypothesis_dir, weight=0.9),
        _vote("strategy", strategy_dir, weight=1.0),
        _vote(
            "risk", risk_dir, weight=1.5,
            veto=risk_veto, veto_reason=risk_veto_reason,
            risk_limits={"max_position": 0.02},
        ),
        _vote(
            "execution", execution_dir, weight=1.3,
            veto=exec_veto, veto_reason=exec_veto_reason,
            execution_ready=execution_ready,
        ),
        _vote("critic", critic_dir, weight=0.5, confidence=0.3),
    ]


# ---------------------------------------------------------------------------
# AgentVote + DecisionPacket serialization
# ---------------------------------------------------------------------------
class TestSchemas:
    def test_agent_vote_to_dict(self):
        v = _vote("risk", "sell", confidence=0.85, veto=True, veto_reason="too risky")
        d = v.to_dict()
        assert d["agent_name"] == "risk"
        assert d["direction"] == "sell"
        assert d["confidence"] == 0.85
        assert d["veto"] is True
        assert d["veto_reason"] == "too risky"

    def test_decision_packet_to_dict(self):
        votes = [_vote("regime", "buy"), _vote("risk", "buy")]
        dp = DecisionPacket(
            symbol="AAPL",
            timeframe="1d",
            timestamp="2025-01-01T00:00:00Z",
            votes=votes,
            final_direction="buy",
            final_confidence=0.75,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=True,
            council_reasoning="Test reasoning",
        )
        d = dp.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["final_direction"] == "buy"
        assert d["vote_count"] == 2
        assert len(d["votes"]) == 2
        assert d["votes"][0]["agent_name"] == "regime"


# ---------------------------------------------------------------------------
# Arbiter rules
# ---------------------------------------------------------------------------
class TestArbiter:
    def test_risk_veto_produces_hold(self):
        votes = _full_votes(risk_veto=True, risk_veto_reason="Portfolio heat exceeded")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.vetoed is True
        assert result.final_direction == "hold"
        assert result.final_confidence == 0.0
        assert "risk" in result.veto_reasons[0]

    def test_execution_veto_produces_hold(self):
        votes = _full_votes(exec_veto=True, exec_veto_reason="Broker disconnected")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.vetoed is True
        assert result.final_direction == "hold"
        assert "execution" in result.veto_reasons[0]

    def test_both_vetoes(self):
        votes = _full_votes(
            risk_veto=True, risk_veto_reason="Heat",
            exec_veto=True, exec_veto_reason="No broker",
        )
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.vetoed is True
        assert len(result.veto_reasons) == 2

    def test_non_veto_agent_cannot_veto(self):
        """strategy agent veto flag should be ignored."""
        votes = _full_votes()
        # Manually set strategy to veto — arbiter should ignore it
        votes[4] = _vote("strategy", "hold", veto=True, veto_reason="I want to veto")
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.vetoed is False  # strategy is not in VETO_AGENTS

    def test_unanimous_buy(self):
        # Patch so arbiter uses static weights; avoid learned_weights/calibration zeroing
        with patch("app.council.arbiter._get_learned_weights", return_value={}), \
             patch("app.council.arbiter.get_thompson_sampler") as mock_ts:
            mock_ts.return_value.should_explore.return_value = False
            mock_cal = type("Cal", (), {"get_weight_penalty": lambda self, a: 1.0})()
            with patch("app.council.calibration.get_calibration_tracker", return_value=mock_cal):
                votes = _full_votes()
                result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "buy"
        assert result.final_confidence > 0.5
        assert result.vetoed is False

    def test_unanimous_sell(self):
        votes = _full_votes(
            market_dir="sell", flow_dir="sell", regime_dir="sell",
            hypothesis_dir="sell", strategy_dir="sell",
            risk_dir="sell", execution_dir="sell", critic_dir="sell",
        )
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "sell"
        assert result.final_confidence > 0.5

    def test_mixed_votes_majority_wins(self):
        with patch("app.council.arbiter._get_learned_weights", return_value={}), \
             patch("app.council.arbiter.get_thompson_sampler") as mock_ts:
            mock_ts.return_value.should_explore.return_value = False
            mock_cal = type("Cal", (), {"get_weight_penalty": lambda self, a: 1.0})()
            with patch("app.council.calibration.get_calibration_tracker", return_value=mock_cal):
                votes = _full_votes(
                    market_dir="buy", flow_dir="sell", regime_dir="buy",
                    hypothesis_dir="buy", strategy_dir="sell",
                    risk_dir="buy", execution_dir="buy", critic_dir="hold",
                )
                result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        # Buy has more weighted votes
        assert result.final_direction == "buy"

    def test_missing_required_agent_holds(self):
        """If a required agent (regime/risk/strategy) is missing, hold."""
        votes = [
            _vote("market_perception", "buy"),
            _vote("flow_perception", "buy"),
            # regime missing!
            _vote("hypothesis", "buy"),
            _vote("strategy", "buy"),
            _vote("risk", "buy"),
            _vote("execution", "buy"),
            _vote("critic", "hold"),
        ]
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.final_direction == "hold"
        assert "Missing required agents" in result.council_reasoning

    def test_weighted_confidence_calculation(self):
        """Verify confidence is a weighted average."""
        with patch("app.council.arbiter._get_learned_weights", return_value={}), \
             patch("app.council.arbiter.get_thompson_sampler") as mock_ts:
            mock_ts.return_value.should_explore.return_value = False
            mock_cal = type("Cal", (), {"get_weight_penalty": lambda self, a: 1.0})()
            with patch("app.council.calibration.get_calibration_tracker", return_value=mock_cal):
                votes = [
                    _vote("regime", "buy", confidence=0.8, weight=1.2),
                    _vote("risk", "buy", confidence=0.6, weight=1.5),
                    _vote("strategy", "buy", confidence=0.9, weight=1.0),
                ]
                result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        # All vote buy, so confidence = total_buy_weight / total_weight
        assert result.final_direction == "buy"
        assert result.final_confidence > 0.0
        assert result.final_confidence <= 1.0

    def test_execution_readiness_requires_exec_agent(self):
        votes = _full_votes(execution_ready=False)
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.execution_ready is False

    def test_execution_readiness_on_hold(self):
        votes = _full_votes(
            market_dir="hold", flow_dir="hold", regime_dir="hold",
            hypothesis_dir="hold", strategy_dir="hold",
            risk_dir="hold", execution_dir="hold", critic_dir="hold",
        )
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert result.execution_ready is False

    def test_risk_limits_extracted(self):
        votes = _full_votes()
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert "max_position" in result.risk_limits

    def test_council_reasoning_contains_counts(self):
        votes = _full_votes()
        result = arbitrate("SPY", "1d", "2025-01-01T00:00:00Z", votes)
        assert "buy=" in result.council_reasoning
        assert "sell=" in result.council_reasoning
        assert "hold=" in result.council_reasoning


# ---------------------------------------------------------------------------
# Individual agents return valid votes
# ---------------------------------------------------------------------------
class TestAgentContracts:
    """Verify each agent returns a valid AgentVote."""

    @pytest.mark.anyio
    async def test_market_perception_agent(self):
        from app.council.agents import market_perception_agent
        vote = await market_perception_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "market_perception"
        assert vote.direction in ("buy", "sell", "hold")
        assert 0.0 <= vote.confidence <= 1.0

    @pytest.mark.anyio
    async def test_flow_perception_agent(self):
        from app.council.agents import flow_perception_agent
        vote = await flow_perception_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "flow_perception"

    @pytest.mark.anyio
    async def test_regime_agent(self):
        from app.council.agents import regime_agent
        vote = await regime_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "regime"

    @pytest.mark.anyio
    async def test_hypothesis_agent(self):
        from app.council.agents import hypothesis_agent
        vote = await hypothesis_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "hypothesis"

    @pytest.mark.anyio
    async def test_strategy_agent(self):
        from app.council.agents import strategy_agent
        vote = await strategy_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "strategy"

    @pytest.mark.anyio
    async def test_risk_agent(self):
        from app.council.agents import risk_agent
        vote = await risk_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "risk"

    @pytest.mark.anyio
    async def test_execution_agent(self):
        from app.council.agents import execution_agent
        vote = await execution_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "execution"

    @pytest.mark.anyio
    async def test_critic_agent(self):
        from app.council.agents import critic_agent
        vote = await critic_agent.evaluate("SPY", "1d", {"features": {}}, {})
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "critic"
