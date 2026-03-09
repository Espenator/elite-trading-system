"""Tests for BlackboardState and its integration with the council pipeline."""
import asyncio
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


class TestBlackboardAtomicOperations:
    """Test atomic lock-protected operations for race condition prevention."""

    @pytest.mark.asyncio
    async def test_set_single_value(self):
        """Test atomic set operation."""
        bb = BlackboardState(symbol="AAPL")
        await bb.set("gex", "regime", "long_gamma")
        assert bb.gex["regime"] == "long_gamma"

    @pytest.mark.asyncio
    async def test_set_metadata_value(self):
        """Test atomic set on metadata namespace."""
        bb = BlackboardState(symbol="AAPL")
        sentiment_data = {"score": 0.75, "source": "finbert"}
        await bb.set("metadata", "social_sentiment", sentiment_data)
        assert bb.metadata["social_sentiment"] == sentiment_data

    @pytest.mark.asyncio
    async def test_update_multiple_values(self):
        """Test atomic update operation with multiple values."""
        bb = BlackboardState(symbol="AAPL")
        updates = {
            "net_gamma": 100.5,
            "regime": "long_gamma",
            "call_wall": 450.0,
            "put_wall": 400.0
        }
        await bb.update("gex", updates)
        assert bb.gex["net_gamma"] == 100.5
        assert bb.gex["regime"] == "long_gamma"
        assert bb.gex["call_wall"] == 450.0
        assert bb.gex["put_wall"] == 400.0

    @pytest.mark.asyncio
    async def test_update_preserves_existing_values(self):
        """Test that update doesn't clear existing values."""
        bb = BlackboardState(symbol="AAPL")
        bb.gex["existing_key"] = "existing_value"
        await bb.update("gex", {"new_key": "new_value"})
        assert bb.gex["existing_key"] == "existing_value"
        assert bb.gex["new_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_set_invalid_namespace_raises_error(self):
        """Test that setting on non-dict namespace raises error."""
        bb = BlackboardState(symbol="AAPL")
        with pytest.raises(ValueError, match="not a dictionary"):
            await bb.set("symbol", "key", "value")  # symbol is a str, not dict

    @pytest.mark.asyncio
    async def test_update_invalid_namespace_raises_error(self):
        """Test that updating non-dict namespace raises error."""
        bb = BlackboardState(symbol="AAPL")
        with pytest.raises(ValueError, match="not a dictionary"):
            await bb.update("ttl_seconds", {"key": "value"})  # ttl_seconds is int

    @pytest.mark.asyncio
    async def test_concurrent_sets_no_race_condition(self):
        """Test that concurrent set operations don't lose data."""
        bb = BlackboardState(symbol="AAPL")

        # Simulate 13 Stage 1 agents writing concurrently
        async def agent_write(agent_id: int):
            await bb.set("perceptions", f"agent_{agent_id}", {"data": agent_id})

        # Run 13 concurrent writes
        await asyncio.gather(*[agent_write(i) for i in range(13)])

        # Verify all 13 writes succeeded
        assert len(bb.perceptions) == 13
        for i in range(13):
            assert bb.perceptions[f"agent_{i}"]["data"] == i

    @pytest.mark.asyncio
    async def test_concurrent_updates_no_race_condition(self):
        """Test that concurrent update operations don't corrupt data."""
        bb = BlackboardState(symbol="AAPL")

        # Simulate multiple agents updating different namespaces
        async def gex_agent():
            await bb.update("gex", {"net_gamma": 100.0, "regime": "long_gamma"})

        async def dark_pool_agent():
            await bb.update("dark_pool", {"dix": 0.45, "dix_signal": "bullish_accumulation"})

        async def macro_agent():
            await bb.update("macro_regime", {"vix_regime": "elevated", "macro_regime": "CAUTIOUS"})

        # Run 3 agents concurrently (simulates Stage 5)
        await asyncio.gather(gex_agent(), dark_pool_agent(), macro_agent())

        # Verify all updates succeeded
        assert bb.gex["net_gamma"] == 100.0
        assert bb.gex["regime"] == "long_gamma"
        assert bb.dark_pool["dix"] == 0.45
        assert bb.dark_pool["dix_signal"] == "bullish_accumulation"
        assert bb.macro_regime["vix_regime"] == "elevated"
        assert bb.macro_regime["macro_regime"] == "CAUTIOUS"

    @pytest.mark.asyncio
    async def test_concurrent_metadata_writes(self):
        """Test concurrent writes to shared metadata namespace."""
        bb = BlackboardState(symbol="AAPL")

        async def social_agent():
            await bb.set("metadata", "social_sentiment", {"score": 0.8})

        async def youtube_agent():
            await bb.set("metadata", "youtube_knowledge", {"mentions": 150})

        async def intelligence_agent():
            await bb.set("metadata", "intelligence", {"signal": "strong"})

        # Run 3 agents writing to same namespace concurrently
        await asyncio.gather(social_agent(), youtube_agent(), intelligence_agent())

        # Verify all writes succeeded without corruption
        assert bb.metadata["social_sentiment"] == {"score": 0.8}
        assert bb.metadata["youtube_knowledge"] == {"mentions": 150}
        assert bb.metadata["intelligence"] == {"signal": "strong"}
        assert len(bb.metadata) == 3

    @pytest.mark.asyncio
    async def test_high_volume_concurrent_writes(self):
        """Test high-volume concurrent writes (31 agents scenario)."""
        bb = BlackboardState(symbol="AAPL")

        async def agent_write(agent_id: int, namespace: str):
            await bb.set(namespace, f"agent_{agent_id}", {"id": agent_id, "vote": "buy"})

        # Simulate 31 agents writing concurrently (max DAG parallelism)
        tasks = []
        for i in range(31):
            namespace = "perceptions" if i < 21 else "metadata"
            tasks.append(agent_write(i, namespace))

        await asyncio.gather(*tasks)

        # Verify all 31 writes succeeded
        perception_count = sum(1 for k in bb.perceptions.keys() if k.startswith("agent_"))
        metadata_count = sum(1 for k in bb.metadata.keys() if k.startswith("agent_"))
        assert perception_count == 21
        assert metadata_count == 10
        assert perception_count + metadata_count == 31

    @pytest.mark.asyncio
    async def test_mixed_set_and_update_concurrent(self):
        """Test concurrent mix of set and update operations."""
        bb = BlackboardState(symbol="AAPL")

        async def set_operations():
            for i in range(5):
                await bb.set("gex", f"key_{i}", i)

        async def update_operations():
            for i in range(5):
                await bb.update("gex", {f"batch_{i}": i * 10})

        await asyncio.gather(set_operations(), update_operations())

        # Verify both sets and updates completed
        assert len(bb.gex) > 12  # default fields + 5 set + 5 update keys
        for i in range(5):
            assert bb.gex[f"key_{i}"] == i
            assert bb.gex[f"batch_{i}"] == i * 10


class TestBlackboardSnapshot:
    """Test get_snapshot() deep copy functionality."""

    def test_snapshot_is_deep_copy(self):
        """Test that snapshot is a true deep copy."""
        bb = BlackboardState(symbol="AAPL")
        bb.gex["regime"] = "long_gamma"
        bb.metadata["test"] = {"nested": {"value": 123}}

        snapshot = bb.get_snapshot()

        # Verify it's a different object
        assert snapshot is not bb
        assert snapshot.gex is not bb.gex
        assert snapshot.metadata is not bb.metadata

        # Verify deep copy of nested structures
        assert snapshot.metadata["test"] is not bb.metadata["test"]
        assert snapshot.metadata["test"]["nested"] is not bb.metadata["test"]["nested"]

    def test_snapshot_mutation_doesnt_affect_original(self):
        """Test that modifying snapshot doesn't affect original."""
        bb = BlackboardState(symbol="AAPL")
        bb.gex["regime"] = "long_gamma"
        bb.metadata["score"] = 0.75

        snapshot = bb.get_snapshot()

        # Mutate snapshot
        snapshot.gex["regime"] = "short_gamma"
        snapshot.metadata["score"] = 0.25
        snapshot.perceptions["new_agent"] = {"vote": "sell"}

        # Verify original unchanged
        assert bb.gex["regime"] == "long_gamma"
        assert bb.metadata["score"] == 0.75
        assert "new_agent" not in bb.perceptions

    def test_snapshot_preserves_all_fields(self):
        """Test that snapshot contains all fields."""
        bb = BlackboardState(symbol="AAPL")
        bb.perceptions["agent1"] = {"vote": "buy"}
        bb.hypothesis = {"direction": "buy"}
        bb.strategy = {"action": "long"}
        bb.gex["regime"] = "long_gamma"
        bb.metadata["custom"] = "data"

        snapshot = bb.get_snapshot()

        assert snapshot.symbol == bb.symbol
        assert snapshot.council_decision_id == bb.council_decision_id
        assert snapshot.perceptions == bb.perceptions
        assert snapshot.hypothesis == bb.hypothesis
        assert snapshot.strategy == bb.strategy
        assert snapshot.gex == bb.gex
        assert snapshot.metadata == bb.metadata

    @pytest.mark.asyncio
    async def test_snapshot_during_concurrent_writes(self):
        """Test snapshot can be safely taken during concurrent writes."""
        bb = BlackboardState(symbol="AAPL")

        snapshots = []

        async def take_snapshots():
            for _ in range(10):
                snapshots.append(bb.get_snapshot())
                await asyncio.sleep(0.001)

        async def concurrent_writes():
            for i in range(50):
                await bb.set("perceptions", f"agent_{i}", {"id": i})
                await asyncio.sleep(0.0001)

        await asyncio.gather(take_snapshots(), concurrent_writes())

        # Verify snapshots were taken successfully
        assert len(snapshots) == 10
        # Each snapshot should be independent
        for snap in snapshots:
            assert isinstance(snap, BlackboardState)
            assert snap.symbol == "AAPL"


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
