"""Tests for dual weight system sync (dopamine loop bug fix).

Ensures WeightLearner is the single source of truth for base weights and
SelfAwareness only provides streak multipliers; both are updated from one path.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.council.self_awareness import (
    get_self_awareness,
    SelfAwareness,
    StreakDetector,
)
from app.council.weight_learner import WeightLearner, get_weight_learner
from app.council.feedback_loop import record_outcome, update_agent_weights


class TestDopamineLoopSync:
    """Verify the two weight systems stay synchronized (single source: WeightLearner)."""

    @pytest.mark.anyio
    async def test_weight_learner_and_self_awareness_agree(self):
        """After same outcome, SelfAwareness.get_weight delegates to WeightLearner."""
        with patch("app.council.self_awareness.db_service") as mock_db, \
             patch("app.council.weight_learner.get_weight_learner") as mock_wl:
            mock_db.get_config.return_value = None
            mock_learner = MagicMock()
            mock_learner.get_weight.return_value = 1.2
            mock_learner.get_weights.return_value = {"risk": 1.2, "regime": 0.9}
            mock_wl.return_value = mock_learner

            sa = get_self_awareness()
            w = sa.weights.get_weight("risk")
            assert w == 1.2
            mock_learner.get_weight.assert_called_once_with("risk")

    def test_arbiter_uses_consistent_weights(self):
        """Arbiter uses WeightLearner for base weights and SelfAwareness only for streak multiplier."""
        from app.council.arbiter import _get_learned_weights

        with patch("app.council.weight_learner.get_weight_learner") as mock_wl, \
             patch("app.council.self_awareness.get_self_awareness") as mock_sa:
            mock_learner = MagicMock()
            mock_learner.get_weights.return_value = {"risk": 1.5, "regime": 1.0}
            mock_wl.return_value = mock_learner

            mock_sa_inst = MagicMock()
            mock_sa_inst.streaks.get_weight_multiplier.side_effect = lambda a: 0.25 if a == "risk" else 1.0
            mock_sa.return_value = mock_sa_inst

            weights = _get_learned_weights()
            # Arbiter: base from WeightLearner, then streak multiplier applied
            assert weights["risk"] == 1.5 * 0.25
            assert weights["regime"] == 1.0
            mock_learner.get_weights.assert_called_once()

    @pytest.mark.anyio
    async def test_feedback_loop_updates_weight_learner_only(self):
        """update_agent_weights updates WeightLearner; SelfAwareness streaks updated by OutcomeTracker."""
        with patch("app.council.weight_learner.get_weight_learner") as mock_wl:
            mock_learner = MagicMock()
            mock_learner.get_weights.return_value = {"risk": 1.0}
            mock_learner.update_from_outcome.return_value = {"risk": 1.02}
            mock_wl.return_value = mock_learner

            result = update_agent_weights(outcome={
                "symbol": "AAPL",
                "trade_id": "test-order-1",
                "outcome": "win",
                "r_multiple": 0.5,
                "pnl": 10.0,
                "confidence": 1.0,
            })
            assert result == {"risk": 1.02}
            mock_learner.update_from_outcome.assert_called_once()
            assert mock_learner.update_from_outcome.call_args[1]["symbol"] == "AAPL"
            assert mock_learner.update_from_outcome.call_args[1]["trade_id"] == "test-order-1"

    def test_no_weight_divergence_after_100_trades(self):
        """Single source of truth: SelfAwareness.weights.get_weight returns WeightLearner weight."""
        with patch("app.council.self_awareness.db_service") as mock_db, \
             patch("app.council.weight_learner.get_weight_learner") as mock_wl:
            mock_db.get_config.return_value = None
            mock_learner = MagicMock()
            mock_learner.get_weight.side_effect = lambda a: 1.0 + (hash(a) % 100) / 500.0
            mock_learner.get_weights.return_value = {}
            mock_wl.return_value = mock_learner

            sa = get_self_awareness()
            for i in range(20):
                agent = f"agent_{i}"
                w_sa = sa.weights.get_weight(agent)
                w_wl = mock_learner.get_weight(agent)
                assert w_sa == w_wl, "SelfAwareness weight must equal WeightLearner weight"

    @patch("app.council.self_awareness.db_service")
    def test_hibernated_agent_skipped_in_runner(self, mock_db):
        """If self_awareness says skip (HIBERNATION), runner should skip that agent."""
        mock_db.get_config.return_value = None
        sa = get_self_awareness()
        for _ in range(10):
            sa.streaks.record_outcome("risk", False)
        assert sa.should_skip_agent("risk") is True
        assert sa.streaks.get_weight_multiplier("risk") == 0.0

    @patch("app.council.self_awareness.db_service")
    def test_streak_detector_recovery(self, mock_db):
        """5 wins after HIBERNATION -> PROBATION; then 3 wins -> ACTIVE."""
        mock_db.get_config.return_value = None
        sd = StreakDetector()
        for _ in range(10):
            sd.record_outcome("risk_agent", profitable=False)
        assert sd.get_status("risk_agent") == "HIBERNATION"

        for _ in range(5):
            sd.record_outcome("risk_agent", profitable=True)
        assert sd.get_status("risk_agent") == "PROBATION"
        for _ in range(3):
            sd.record_outcome("risk_agent", profitable=True)
        assert sd.get_status("risk_agent") == "ACTIVE"
        assert sd.get_weight_multiplier("risk_agent") == 1.0

    @patch("app.council.self_awareness.db_service")
    def test_record_trade_outcome_updates_streaks_only(self, mock_db):
        """record_trade_outcome only updates streaks, not a second Bayesian weight store."""
        mock_db.get_config.return_value = None
        sa = get_self_awareness()
        sa.record_trade_outcome("regime", profitable=True)
        assert sa.streaks.get_streak_info("regime")["win_streak"] == 1
        # Weights come from WeightLearner; record_trade_outcome does not call learner.update_from_outcome
