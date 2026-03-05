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

    def test_to_snapshot_excludes_raw_features(self):
        bb = BlackboardState(symbol="TSLA", raw_features={"big": "data"})
        snap = bb.to_snapshot()
        assert "raw_features" not in snap
        assert snap["symbol"] == "TSLA"

    def test_unique_decision_ids(self):
        bb1 = BlackboardState(symbol="A")
        bb2 = BlackboardState(symbol="B")
        assert bb1.council_decision_id != bb2.council_decision_id


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

    def test_council_decision_id_omitted_when_empty(self):
        dp = DecisionPacket(
            symbol="AAPL", timeframe="1d", timestamp="2025-01-01T00:00:00Z",
            votes=[], final_direction="buy", final_confidence=0.7,
            vetoed=False, veto_reasons=[], risk_limits={},
            execution_ready=True, council_reasoning="test",
        )
        d = dp.to_dict()
        assert "council_decision_id" not in d
