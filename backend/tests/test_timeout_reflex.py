"""Tests for agent timeout reflex system."""
import asyncio
import pytest
from app.council.reflexes.timeout_reflex import (
    TimeoutManager,
    get_timeout_manager,
    AgentTimeoutStats,
)
from app.council.schemas import AgentVote


class TestAgentTimeoutStats:
    """Test the AgentTimeoutStats dataclass."""

    def test_timeout_rate_no_executions(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        assert stats.timeout_rate == 0.0

    def test_timeout_rate_with_timeouts(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        stats.total_executions = 10
        stats.total_timeouts = 3
        assert stats.timeout_rate == 0.3

    def test_p50_latency_empty(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        assert stats.p50_latency == 0.0

    def test_p50_latency(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        stats.execution_times.extend([100, 200, 300, 400, 500])
        assert stats.p50_latency == 300

    def test_p95_latency_empty(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        assert stats.p95_latency == 0.0

    def test_p95_latency(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        stats.execution_times.extend([100, 200, 300, 400, 500])
        # p95 of 5 items = index 4 (95% of 5 = 4.75, rounded to 4)
        assert stats.p95_latency == 500

    def test_avg_latency_empty(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        assert stats.avg_latency == 0.0

    def test_avg_latency(self):
        stats = AgentTimeoutStats(agent_name="test_agent")
        stats.execution_times.extend([100, 200, 300])
        assert stats.avg_latency == 200.0


class TestTimeoutManager:
    """Test the TimeoutManager class."""

    def test_get_timeout_perception_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("market_perception", use_adaptive=False)
        assert timeout == 5.0  # Perception tier default

    def test_get_timeout_technical_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("rsi", use_adaptive=False)
        assert timeout == 10.0  # Technical tier default

    def test_get_timeout_hypothesis_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("hypothesis", use_adaptive=False)
        assert timeout == 15.0  # Hypothesis tier default

    def test_get_timeout_strategy_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("strategy", use_adaptive=False)
        assert timeout == 12.0  # Strategy tier default

    def test_get_timeout_risk_execution_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("risk", use_adaptive=False)
        assert timeout == 8.0  # Risk/execution tier default

    def test_get_timeout_critic_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("critic", use_adaptive=False)
        assert timeout == 12.0  # Critic tier default

    def test_get_timeout_default_tier(self):
        tm = TimeoutManager()
        timeout = tm.get_timeout("unknown_agent", use_adaptive=False)
        assert timeout == 30.0  # Default tier

    def test_get_timeout_manual_override(self):
        tm = TimeoutManager()
        tm.set_timeout_override("test_agent", 7.5)
        timeout = tm.get_timeout("test_agent")
        assert timeout == 7.5

    def test_get_timeout_adaptive_not_enough_samples(self):
        tm = TimeoutManager()
        tm._min_samples = 10
        # Record only 5 executions
        for i in range(5):
            tm.record_execution("market_perception", elapsed_ms=100, timed_out=False)
        # Should return base timeout (not adaptive)
        timeout = tm.get_timeout("market_perception", use_adaptive=True)
        assert timeout == 5.0  # Base perception timeout

    def test_get_timeout_adaptive_with_enough_samples(self):
        tm = TimeoutManager()
        tm._min_samples = 10
        tm._adaptive_multiplier = 1.2
        # Record 10 executions with p95 = 2000ms
        for i in range(10):
            tm.record_execution("market_perception", elapsed_ms=2000, timed_out=False)
        # Adaptive timeout should be p95 * multiplier = 2.0s * 1.2 = 2.4s
        # But shouldn't go below base timeout of 5.0s
        timeout = tm.get_timeout("market_perception", use_adaptive=True)
        assert timeout == 5.0  # Should use base timeout (higher than adaptive)

    def test_get_timeout_adaptive_exceeds_base(self):
        tm = TimeoutManager()
        tm._min_samples = 10
        tm._adaptive_multiplier = 1.2
        # Record 10 executions with p95 = 6000ms (6s)
        for i in range(10):
            tm.record_execution("market_perception", elapsed_ms=6000, timed_out=False)
        # Adaptive timeout = 6.0s * 1.2 = 7.2s (exceeds base of 5s)
        timeout = tm.get_timeout("market_perception", use_adaptive=True)
        # Should be 7.2s but capped at 2x base = 10s
        assert timeout == 7.2

    def test_get_timeout_adaptive_capped_at_2x(self):
        tm = TimeoutManager()
        tm._min_samples = 10
        tm._adaptive_multiplier = 1.2
        # Record 10 executions with p95 = 20000ms (20s)
        for i in range(10):
            tm.record_execution("market_perception", elapsed_ms=20000, timed_out=False)
        # Adaptive timeout = 20.0s * 1.2 = 24s
        # Should be capped at 2x base = 10s
        timeout = tm.get_timeout("market_perception", use_adaptive=True)
        assert timeout == 10.0  # Capped at 2x base

    def test_record_execution_successful(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=500, timed_out=False, error=False)

        stats = tm._stats["test_agent"]
        assert stats.total_executions == 1
        assert stats.total_timeouts == 0
        assert stats.total_errors == 0
        assert stats.timeout_streak == 0
        assert len(stats.execution_times) == 1
        assert stats.execution_times[0] == 500

    def test_record_execution_timeout(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True, error=False)

        stats = tm._stats["test_agent"]
        assert stats.total_executions == 1
        assert stats.total_timeouts == 1
        assert stats.total_errors == 0
        assert stats.timeout_streak == 1
        # Timeout executions shouldn't be added to execution_times
        assert len(stats.execution_times) == 0

    def test_record_execution_error(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=200, timed_out=False, error=True)

        stats = tm._stats["test_agent"]
        assert stats.total_executions == 1
        assert stats.total_timeouts == 0
        assert stats.total_errors == 1
        assert stats.timeout_streak == 0
        # Error executions shouldn't be added to execution_times
        assert len(stats.execution_times) == 0

    def test_record_execution_timeout_streak(self):
        tm = TimeoutManager()
        # Record 3 consecutive timeouts
        for i in range(3):
            tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True)

        stats = tm._stats["test_agent"]
        assert stats.timeout_streak == 3
        assert stats.total_timeouts == 3

        # Record a successful execution
        tm.record_execution("test_agent", elapsed_ms=500, timed_out=False)
        assert stats.timeout_streak == 0  # Streak reset

    def test_set_clear_timeout_override(self):
        tm = TimeoutManager()
        tm.set_timeout_override("test_agent", 15.0)
        assert tm.get_timeout("test_agent") == 15.0

        tm.clear_timeout_override("test_agent")
        # Should return base timeout for unknown agent (default tier)
        assert tm.get_timeout("test_agent", use_adaptive=False) == 30.0

    def test_get_stats_specific_agent(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=500, timed_out=False)
        tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True)

        stats = tm.get_stats("test_agent")
        assert stats["agent_name"] == "test_agent"
        assert stats["total_executions"] == 2
        assert stats["total_timeouts"] == 1
        assert stats["timeout_rate"] == 0.5
        assert stats["timeout_streak"] == 1
        assert "current_timeout_s" in stats

    def test_get_stats_aggregate(self):
        tm = TimeoutManager()
        tm.record_execution("agent1", elapsed_ms=500, timed_out=False)
        tm.record_execution("agent2", elapsed_ms=5000, timed_out=True)
        tm.record_execution("agent3", elapsed_ms=300, timed_out=False)

        stats = tm.get_stats()
        assert stats["total_executions"] == 3
        assert stats["total_timeouts"] == 1
        assert stats["overall_timeout_rate"] == 1/3
        assert stats["agents_tracked"] == 3
        assert stats["agents_with_timeouts"] == 1

    def test_get_all_agent_stats(self):
        tm = TimeoutManager()
        tm.record_execution("agent1", elapsed_ms=500, timed_out=False)
        tm.record_execution("agent2", elapsed_ms=5000, timed_out=True)

        all_stats = tm.get_all_agent_stats()
        assert "agent1" in all_stats
        assert "agent2" in all_stats
        assert all_stats["agent1"]["total_timeouts"] == 0
        assert all_stats["agent2"]["total_timeouts"] == 1

    def test_reset_stats_specific_agent(self):
        tm = TimeoutManager()
        tm.record_execution("agent1", elapsed_ms=500, timed_out=False)
        tm.record_execution("agent2", elapsed_ms=5000, timed_out=True)

        tm.reset_stats("agent1")
        assert "agent1" not in tm._stats
        assert "agent2" in tm._stats

    def test_reset_stats_all(self):
        tm = TimeoutManager()
        tm.record_execution("agent1", elapsed_ms=500, timed_out=False)
        tm.record_execution("agent2", elapsed_ms=5000, timed_out=True)

        tm.reset_stats()
        assert len(tm._stats) == 0

    def test_should_skip_agent_no_timeouts(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=500, timed_out=False)
        assert tm.should_skip_agent("test_agent") is False

    def test_should_skip_agent_few_timeouts(self):
        tm = TimeoutManager()
        for i in range(4):
            tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True)
        # 4 timeouts is below threshold of 5
        assert tm.should_skip_agent("test_agent") is False

    def test_should_skip_agent_many_timeouts(self):
        tm = TimeoutManager()
        for i in range(5):
            tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True)
        # 5+ consecutive timeouts should trigger skip
        assert tm.should_skip_agent("test_agent") is True

    def test_create_fallback_vote(self):
        tm = TimeoutManager()
        tm.record_execution("test_agent", elapsed_ms=5000, timed_out=True)

        vote = tm.create_fallback_vote("test_agent", "timeout", "blackboard123")
        assert isinstance(vote, AgentVote)
        assert vote.agent_name == "test_agent"
        assert vote.direction == "hold"
        assert vote.confidence == 0.0
        assert "timeout" in vote.reasoning
        assert vote.blackboard_ref == "blackboard123"

    def test_get_timeout_manager_singleton(self):
        """Test that get_timeout_manager returns a singleton."""
        tm1 = get_timeout_manager()
        tm2 = get_timeout_manager()
        assert tm1 is tm2


class TestTimeoutManagerIntegration:
    """Integration tests simulating real usage patterns."""

    @pytest.mark.anyio
    async def test_agent_with_consistent_fast_execution(self):
        """Agent that consistently executes quickly should keep base timeout."""
        tm = TimeoutManager()
        tm._min_samples = 5

        # Simulate 10 fast executions
        for i in range(10):
            tm.record_execution("fast_agent", elapsed_ms=200, timed_out=False)

        # Should use base timeout since adaptive would be lower
        timeout = tm.get_timeout("fast_agent")
        assert timeout == 30.0  # Default tier base timeout

    @pytest.mark.anyio
    async def test_agent_with_slow_execution(self):
        """Agent that executes slowly should get increased adaptive timeout."""
        tm = TimeoutManager()
        tm._min_samples = 5
        tm._adaptive_multiplier = 1.2

        # Simulate 10 slow executions (4s each for a 5s perception agent)
        for i in range(10):
            tm.record_execution("slow_perception", elapsed_ms=4000, timed_out=False)

        # Adaptive timeout = 4.0s * 1.2 = 4.8s, but base is 5.0s
        timeout = tm.get_timeout("slow_perception")
        assert timeout == 5.0  # Should use base (higher)

    @pytest.mark.anyio
    async def test_agent_timeout_recovery(self):
        """Agent that times out then recovers should reset streak."""
        tm = TimeoutManager()

        # 3 timeouts
        for i in range(3):
            tm.record_execution("flaky_agent", elapsed_ms=5000, timed_out=True)

        stats = tm._stats["flaky_agent"]
        assert stats.timeout_streak == 3

        # Recovery
        tm.record_execution("flaky_agent", elapsed_ms=500, timed_out=False)
        assert stats.timeout_streak == 0

    @pytest.mark.anyio
    async def test_multiple_agents_tracked(self):
        """Multiple agents should be tracked independently."""
        tm = TimeoutManager()

        # Agent 1: fast and reliable
        for i in range(5):
            tm.record_execution("reliable_agent", elapsed_ms=300, timed_out=False)

        # Agent 2: slow but doesn't timeout
        for i in range(5):
            tm.record_execution("slow_agent", elapsed_ms=2000, timed_out=False)

        # Agent 3: frequently times out
        for i in range(5):
            tm.record_execution("timeout_agent", elapsed_ms=5000, timed_out=True)

        all_stats = tm.get_all_agent_stats()
        assert len(all_stats) == 3
        assert all_stats["reliable_agent"]["timeout_rate"] == 0.0
        assert all_stats["slow_agent"]["timeout_rate"] == 0.0
        assert all_stats["timeout_agent"]["timeout_rate"] == 1.0
