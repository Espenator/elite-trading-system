"""Tests for TaskSpawner dynamic agent creation."""
import pytest
from app.council.blackboard import BlackboardState
from app.council.task_spawner import TaskSpawner
from app.council.schemas import AgentVote


@pytest.fixture
def bb():
    return BlackboardState(symbol="SPY", raw_features={"features": {}})


@pytest.fixture
def spawner(bb):
    s = TaskSpawner(bb)
    s.register_all_agents()
    return s


class TestTaskSpawner:
    def test_register_all_agents(self, spawner):
        names = spawner.registered_agents
        assert "market_perception" in names
        assert "flow_perception" in names
        assert "regime" in names
        assert "social_perception" in names
        assert "news_catalyst" in names
        assert "youtube_knowledge" in names
        assert "hypothesis" in names
        assert "strategy" in names
        assert "risk" in names
        assert "execution" in names
        assert "critic" in names
        assert len(names) == 11

    @pytest.mark.anyio
    async def test_spawn_single_agent(self, spawner):
        vote = await spawner.spawn("market_perception", "SPY")
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "market_perception"
        assert vote.blackboard_ref == spawner.blackboard.council_decision_id

    @pytest.mark.anyio
    async def test_spawn_unknown_agent(self, spawner):
        vote = await spawner.spawn("nonexistent", "SPY")
        assert vote.direction == "hold"
        assert vote.confidence == 0.0
        assert "Unknown" in vote.reasoning

    @pytest.mark.anyio
    async def test_spawn_parallel(self, spawner):
        votes = await spawner.spawn_parallel([
            {"agent_type": "market_perception", "symbol": "SPY"},
            {"agent_type": "flow_perception", "symbol": "SPY"},
            {"agent_type": "regime", "symbol": "SPY"},
        ])
        assert len(votes) == 3
        names = {v.agent_name for v in votes}
        assert "market_perception" in names
        assert "flow_perception" in names
        assert "regime" in names

    @pytest.mark.anyio
    async def test_spawn_with_context(self, spawner):
        ctx = {"stage1": {"test": "data"}}
        vote = await spawner.spawn("strategy", "AAPL", context=ctx)
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "strategy"

    @pytest.mark.anyio
    async def test_spawn_background(self, spawner):
        result = await spawner.spawn("critic", "SPY", background=True)
        assert result is None  # Returns immediately
        assert len(spawner._background) == 1
        votes = await spawner.await_background()
        assert len(votes) == 1
        assert votes[0].agent_name == "critic"

    @pytest.mark.anyio
    async def test_model_tier_passed_in_context(self, spawner):
        vote = await spawner.spawn("hypothesis", "AAPL", model_tier="deep")
        assert isinstance(vote, AgentVote)
