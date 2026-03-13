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
    """BayesianAgentWeights delegates to WeightLearner (single source of truth)."""

    @patch("app.council.self_awareness.db_service")
    @patch("app.council.weight_learner.get_weight_learner")
    def test_get_weight_delegates_to_learner(self, mock_wl, mock_db):
        mock_db.get_config.return_value = None
        mock_learner = MagicMock()
        mock_learner.get_weight.return_value = 1.2
        mock_wl.return_value = mock_learner
        w = BayesianAgentWeights()
        assert w.get_weight("risk") == 1.2
        mock_learner.get_weight.assert_called_once_with("risk")

    @patch("app.council.self_awareness.db_service")
    @patch("app.council.weight_learner.get_weight_learner")
    def test_get_weight_fallback_when_learner_unavailable(self, mock_wl, mock_db):
        mock_db.get_config.return_value = None
        mock_wl.side_effect = RuntimeError("no learner")
        w = BayesianAgentWeights()
        assert w.get_weight("any_agent") == 1.0

    @patch("app.council.self_awareness.db_service")
    @patch("app.council.weight_learner.get_weight_learner")
    def test_get_distribution(self, mock_wl, mock_db):
        mock_db.get_config.return_value = None
        mock_learner = MagicMock()
        mock_learner.get_weight.return_value = 0.8
        mock_wl.return_value = mock_learner
        w = BayesianAgentWeights()
        d = w.get_distribution("new_agent")
        assert d["mean"] == 0.8
        assert d["source"] == "weight_learner"


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
    def test_recovery_3_wins_after_probation_to_active(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(5):
            s.record_outcome("agent", False)
        assert s.get_status("agent") == "PROBATION"
        for _ in range(3):
            s.record_outcome("agent", True)
        assert s.get_status("agent") == "ACTIVE"

    @patch("app.council.self_awareness.db_service")
    def test_recovery_5_wins_from_hibernation_to_probation_then_3_to_active(self, mock_db):
        mock_db.get_config.return_value = None
        s = StreakDetector()
        for _ in range(10):
            s.record_outcome("agent", False)
        assert s.get_status("agent") == "HIBERNATION"
        for _ in range(5):
            s.record_outcome("agent", True)
        assert s.get_status("agent") == "PROBATION"
        for _ in range(3):
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
    @patch("app.council.weight_learner.get_weight_learner")
    def test_effective_weight(self, mock_wl, mock_db):
        mock_db.get_config.return_value = None
        mock_learner = MagicMock()
        mock_learner.get_weight.return_value = 1.0
        mock_wl.return_value = mock_learner
        sa = SelfAwareness()
        # WeightLearner 1.0 * streak 1.0 = 1.0
        assert sa.get_effective_weight("agent") == 1.0

    @patch("app.council.self_awareness.db_service")
    @patch("app.council.weight_learner.get_weight_learner")
    def test_record_trade_outcome(self, mock_wl, mock_db):
        mock_db.get_config.return_value = None
        mock_learner = MagicMock()
        mock_learner.get_weight.return_value = 1.0
        mock_learner.get_weights.return_value = {}
        mock_wl.return_value = mock_learner
        sa = SelfAwareness()
        sa.record_trade_outcome("agent", True)
        assert sa.streaks.get_streak_info("agent")["win_streak"] == 1
        assert sa.streaks.get_status("agent") == "ACTIVE"

    @patch("app.council.self_awareness.db_service")
    def test_should_skip_hibernated(self, mock_db):
        mock_db.get_config.return_value = None
        sa = SelfAwareness()
        for _ in range(10):
            sa.streaks.record_outcome("dead_agent", False)
        assert sa.should_skip_agent("dead_agent") is True
