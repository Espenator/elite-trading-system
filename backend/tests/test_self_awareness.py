"""Tests for agent self-awareness system."""
import pytest
from unittest.mock import patch, MagicMock
from app.council.self_awareness import (
    BayesianAgentWeights,
    StreakDetector,
    AgentHealthMonitor,
    SelfAwareness,
)


class TestBayesianWeights:
    @patch("app.council.self_awareness.db_service")
    def test_default_weight(self, mock_db):
        mock_db.get_config.return_value = None
        w = BayesianAgentWeights()
        assert w.get_weight("unknown_agent") == 0.5  # Beta(2,2) = 0.5

    @patch("app.council.self_awareness.db_service")
    def test_update_profitable(self, mock_db):
        mock_db.get_config.return_value = None
        w = BayesianAgentWeights()
        w.update("test_agent", True)  # alpha: 2->3, beta: 2
        assert w.get_weight("test_agent") == 3.0 / 5.0  # 0.6

    @patch("app.council.self_awareness.db_service")
    def test_update_loss(self, mock_db):
        mock_db.get_config.return_value = None
        w = BayesianAgentWeights()
        w.update("test_agent", False)  # alpha: 2, beta: 2->3
        assert w.get_weight("test_agent") == 2.0 / 5.0  # 0.4

    @patch("app.council.self_awareness.db_service")
    def test_multiple_updates(self, mock_db):
        mock_db.get_config.return_value = None
        w = BayesianAgentWeights()
        for _ in range(8):
            w.update("good_agent", True)
        for _ in range(2):
            w.update("good_agent", False)
        # alpha=10, beta=4 -> 10/14 = 0.714
        assert abs(w.get_weight("good_agent") - 10.0 / 14.0) < 0.01

    @patch("app.council.self_awareness.db_service")
    def test_get_distribution(self, mock_db):
        mock_db.get_config.return_value = None
        w = BayesianAgentWeights()
        d = w.get_distribution("new_agent")
        assert d["alpha"] == 2.0
        assert d["beta"] == 2.0
        assert d["mean"] == 0.5


class TestStreakDetector:
    @patch("app.council.self_awareness.db_service")
    def test_default_active(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        assert s.get_status("any_agent") == "ACTIVE"

    @patch("app.council.self_awareness.db_service")
    def test_probation_after_5_losses(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(5):
            s.record_outcome("bad_agent", False)
        assert s.get_status("bad_agent") == "PROBATION"
        assert s.get_weight_multiplier("bad_agent") == 0.25

    @patch("app.council.self_awareness.db_service")
    def test_hibernation_after_10_losses(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(10):
            s.record_outcome("terrible_agent", False)
        assert s.get_status("terrible_agent") == "HIBERNATION"
        assert s.get_weight_multiplier("terrible_agent") == 0.0

    @patch("app.council.self_awareness.db_service")
    def test_win_resets_streak(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(4):
            s.record_outcome("agent", False)
        s.record_outcome("agent", True)
        assert s.get_status("agent") == "ACTIVE"

    @patch("app.council.self_awareness.db_service")
    def test_reset_manual(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(10):
            s.record_outcome("agent", False)
        assert s.get_status("agent") == "HIBERNATION"
        s.reset("agent")
        assert s.get_status("agent") == "ACTIVE"


class TestAgentHealthMonitor:
    def test_record_run(self):
        h = AgentHealthMonitor()
        h.record_run("agent_a", 45.0, True)
        health = h.get_health("agent_a")
        assert health["total_runs"] == 1
        assert health["errors"] == 0
        assert health["avg_latency_ms"] == 45.0
        assert health["healthy"] is True

    def test_error_rate(self):
        h = AgentHealthMonitor()
        h.record_run("agent_b", 10.0, True)
        h.record_run("agent_b", 10.0, False, error="timeout")
        health = h.get_health("agent_b")
        assert health["error_rate"] == 0.5
        assert health["last_error"] == "timeout"

    def test_unhealthy_high_errors(self):
        h = AgentHealthMonitor()
        h.record_run("bad", 10.0, False)
        h.record_run("bad", 10.0, False)
        assert h.is_healthy("bad") is False


class TestSelfAwareness:
    @patch("app.council.self_awareness.db_service")
    def test_effective_weight(self, mock_db):
        mock_db.get_config.return_value = None
        sa = SelfAwareness()
        # Default: Bayesian 0.5 * streak 1.0 = 0.5
        assert sa.get_effective_weight("agent") == 0.5

    @patch("app.council.self_awareness.db_service")
    def test_record_trade_outcome(self, mock_db):
        mock_db.get_config.return_value = None
        sa = SelfAwareness()
        sa.record_trade_outcome("agent", True)
        assert sa.weights.get_weight("agent") > 0.5
        assert sa.streaks.get_status("agent") == "ACTIVE"

    @patch("app.council.self_awareness.db_service")
    def test_should_skip_hibernated(self, mock_db):
        mock_db.get_config.return_value = None
        sa = SelfAwareness()
        for _ in range(10):
            sa.streaks.record_outcome("dead_agent", False)
        assert sa.should_skip_agent("dead_agent") is True
