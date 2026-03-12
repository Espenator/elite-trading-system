"""Tests for BlackboardState and its integration with the council pipeline."""
import pytest
from datetime import datetime, timezone, timedelta

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote, DecisionPacket


class TestBlackboardState:
    def test_creation_defaults(self):
        bb = BlackboardState(symbol="AAPL")
        assert bb.symbol == "AAPL"
        assert bb.council_decision_id  # UUID generated
        assert len(bb.council_decision_id) == 36  # UUID format
        assert bb.ttl_seconds == 30
        assert bb.perceptions == {}
        assert bb.hypothesis is None
        assert bb.strategy is None
        assert bb.risk_assessment is None
        assert bb.execution_plan is None
        assert bb.critic_review is None

    def test_creation_with_features(self):
        features = {"features": {"return_1d": 0.02}}
        bb = BlackboardState(symbol="MSFT", raw_features=features)
        assert bb.raw_features == features
        assert bb.features == features  # property alias

    def test_is_expired(self):
        bb = BlackboardState(symbol="SPY", ttl_seconds=1)
        assert not bb.is_expired
        bb.created_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        assert bb.is_expired

    def test_to_dict(self):
        bb = BlackboardState(symbol="AAPL")
        bb.perceptions["market_perception"] = {"direction": "buy"}
        bb.hypothesis = {"direction": "buy", "confidence": 0.7}
        d = bb.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["council_decision_id"] == bb.council_decision_id
        assert d["perceptions"]["market_perception"]["direction"] == "buy"
        assert d["hypothesis"]["confidence"] == 0.7
        assert "created_at" in d
        assert "ttl_seconds" in d
        assert d["ttl_seconds"] == 30

    def test_remaining_ttl_seconds(self):
        bb = BlackboardState(symbol="SPY", ttl_seconds=60)
        remaining = bb.remaining_ttl_seconds()
        assert 59 <= remaining <= 61
        bb.created_at = datetime.now(timezone.utc) - timedelta(seconds=90)
        assert bb.remaining_ttl_seconds() <= 0
        assert bb.is_expired

    def test_to_log_safe(self):
        bb = BlackboardState(symbol="NVDA")
        bb.stage_latencies["stage1"] = 100.5
        log_safe = bb.to_log_safe()
        assert log_safe["symbol"] == "NVDA"
        assert log_safe["council_decision_id"] == bb.council_decision_id
        assert "remaining_ttl_seconds" in log_safe
        assert log_safe["stage_latencies"]["stage1"] == 100.5
        assert "perceptions" not in log_safe
        assert "raw_features" not in log_safe

    def test_to_snapshot_excludes_raw_features(self):
        bb = BlackboardState(symbol="TSLA", raw_features={"big": "data"})
        snap = bb.to_snapshot()
        assert "raw_features" not in snap
        assert snap["symbol"] == "TSLA"

    def test_unique_decision_ids(self):
        bb1 = BlackboardState(symbol="A")
        bb2 = BlackboardState(symbol="B")
        assert bb1.council_decision_id != bb2.council_decision_id

    def test_propagation_stage_outputs(self):
        """Stage outputs written to blackboard are visible in serialization (propagation)."""
        bb = BlackboardState(symbol="GOOG", raw_features={"features": {"rsi": 55}})
        bb.perceptions["regime"] = {"direction": "buy", "confidence": 0.8}
        bb.perceptions["risk"] = {"direction": "buy", "veto": False}
        bb.hypothesis = {"direction": "buy", "reasoning": "momentum"}
        bb.strategy = {"direction": "buy", "confidence": 0.7}
        bb.risk_assessment = {"direction": "buy", "risk_limits": {}}
        bb.execution_plan = {"execution_ready": True}
        bb.critic_review = {"direction": "buy"}
        d = bb.to_dict()
        assert d["perceptions"]["regime"]["direction"] == "buy"
        assert d["hypothesis"]["reasoning"] == "momentum"
        assert d["strategy"]["confidence"] == 0.7
        assert d["risk_assessment"]["risk_limits"] == {}
        assert d["execution_plan"]["execution_ready"] is True
        assert d["critic_review"]["direction"] == "buy"
        snap = bb.to_snapshot()
        assert snap["perceptions"]["risk"]["veto"] is False


class TestAgentVoteBlackboardRef:
    def test_blackboard_ref_default_empty(self):
        v = AgentVote(agent_name="test", direction="buy", confidence=0.5, reasoning="test")
        assert v.blackboard_ref == ""

    def test_blackboard_ref_in_to_dict(self):
        v = AgentVote(agent_name="test", direction="buy", confidence=0.5, reasoning="test", blackboard_ref="abc-123")
        d = v.to_dict()
        assert d["blackboard_ref"] == "abc-123"

    def test_blackboard_ref_omitted_when_empty(self):
        v = AgentVote(agent_name="test", direction="buy", confidence=0.5, reasoning="test")
        d = v.to_dict()
        assert "blackboard_ref" not in d


class TestDecisionPacketDecisionId:
    def test_council_decision_id_in_to_dict(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="buy", final_confidence=0.7,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=True, council_reasoning="test",
            council_decision_id="uuid-abc",
        )
        d = dp.to_dict()
        assert d["council_decision_id"] == "uuid-abc"
        assert d["ttl_seconds"] == 30
        assert d["created_at"] == ""

    def test_council_decision_id_omitted_when_empty(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="buy", final_confidence=0.7,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=True, council_reasoning="test",
        )
        d = dp.to_dict()
        assert "council_decision_id" not in d

    def test_decision_packet_ttl_and_created_at_in_to_dict(self):
        dp = DecisionPacket(
            symbol="SPY", timeframe="1d", timestamp="2025-01-01T12:00:00Z",
            votes=[], final_direction="hold", final_confidence=0.0,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=False, council_reasoning="test",
            council_decision_id="dec-123", ttl_seconds=30,
            created_at="2025-01-01T11:59:00Z",
        )
        d = dp.to_dict()
        assert d["ttl_seconds"] == 30
        assert d["created_at"] == "2025-01-01T11:59:00Z"
        assert d["council_decision_id"] == "dec-123"


class TestArbiterAcceptsBlackboard:
    """Arbiter can receive optional blackboard; behavior unchanged (backward compat)."""

    def test_arbitrate_without_blackboard(self):
        from app.council.arbiter import arbitrate
        votes = [
            AgentVote(agent_name="regime", direction="buy", confidence=0.8, reasoning="ok", weight=1.0),
            AgentVote(agent_name="risk", direction="buy", confidence=0.7, reasoning="ok", weight=1.0),
            AgentVote(agent_name="strategy", direction="buy", confidence=0.75, reasoning="ok", weight=1.0),
        ]
        decision = arbitrate("AAPL", "1d", "2025-01-01T00:00:00Z", votes)
        assert decision.final_direction == "buy"
        assert decision.symbol == "AAPL"

    def test_arbitrate_with_blackboard_same_result(self):
        from app.council.arbiter import arbitrate
        votes = [
            AgentVote(agent_name="regime", direction="buy", confidence=0.8, reasoning="ok", weight=1.0),
            AgentVote(agent_name="risk", direction="buy", confidence=0.7, reasoning="ok", weight=1.0),
            AgentVote(agent_name="strategy", direction="buy", confidence=0.75, reasoning="ok", weight=1.0),
        ]
        bb = BlackboardState(symbol="AAPL", raw_features={"features": {}})
        bb.perceptions["regime"] = {"direction": "buy"}
        decision_without = arbitrate("AAPL", "1d", "2025-01-01T00:00:00Z", votes)
        decision_with = arbitrate("AAPL", "1d", "2025-01-01T00:00:00Z", votes, blackboard=bb)
        assert decision_with.final_direction == decision_without.final_direction
        assert decision_with.final_confidence == decision_without.final_confidence
