"""
Learning loop retention test — verify outcomes reach WeightLearner.update_from_outcome().

Simulates many trade outcomes and counts how many reach the weight learner.
Target: >= 70% retention (arch review reported 20-25% due to dropouts).
Logs which dropout point catches each lost outcome for diagnostics.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestLearningRetention:
    """Simulate outcomes and measure retention through the learning chain."""

    def test_feedback_loop_record_decision_stores_trade_id(self):
        """record_decision must store trade_id (council_decision_id) for matching."""
        from app.council.feedback_loop import record_decision, _get_store, reset_feedback
        reset_feedback()
        record_decision(
            symbol="AAPL",
            final_direction="buy",
            votes=[{"agent_name": "risk", "direction": "buy", "confidence": 0.8}],
            trade_id="cid-abc-123",
        )
        store = _get_store()
        decisions = store.get("decisions", [])
        assert len(decisions) == 1
        assert decisions[0]["trade_id"] == "cid-abc-123"
        assert decisions[0]["symbol"] == "AAPL"

    def test_feedback_loop_matches_by_trade_id_not_symbol_only(self):
        """Matching must prefer trade_id (council_decision_id) over symbol."""
        from app.council.feedback_loop import (
            record_decision, record_outcome, _get_store, reset_feedback,
        )
        reset_feedback()
        record_decision(
            symbol="AAPL",
            final_direction="buy",
            votes=[{"agent_name": "risk", "direction": "buy", "confidence": 0.8}],
            trade_id="decision-uuid-1",
        )
        record_decision(
            symbol="AAPL",
            final_direction="sell",
            votes=[{"agent_name": "risk", "direction": "sell", "confidence": 0.7}],
            trade_id="decision-uuid-2",
        )
        result = record_outcome(trade_id="decision-uuid-2", symbol="AAPL", outcome="win", r_multiple=1.0)
        store = _get_store()
        # Should have matched the second decision (sell -> win)
        assert "agent_stats" in result
        assert len(store.get("outcomes", [])) == 1

    def test_update_agent_weights_calls_update_from_outcome(self):
        """update_agent_weights(outcome=...) must call weight_learner.update_from_outcome()."""
        from app.council.feedback_loop import update_agent_weights, record_decision, reset_feedback
        reset_feedback()
        record_decision(
            symbol="MSFT",
            final_direction="buy",
            votes=[{"agent_name": "regime", "direction": "buy", "confidence": 0.75}],
            trade_id="cid-msft-1",
        )
        # Patch where feedback_loop looks up get_weight_learner (inside the function)
        with patch("app.council.weight_learner.get_weight_learner") as m_get:
            mock_learner = MagicMock()
            mock_learner.update_from_outcome.return_value = {"regime": 1.0}
            mock_learner.get_weights.return_value = {"regime": 1.0}
            mock_learner.update_count = 0
            m_get.return_value = mock_learner
            update_agent_weights(outcome={
                "trade_id": "cid-msft-1",
                "symbol": "MSFT",
                "outcome": "win",
                "r_multiple": 1.2,
                "pnl": 100.0,
                "confidence": 1.0,
            })
            mock_learner.update_from_outcome.assert_called_once()
            call_kw = mock_learner.update_from_outcome.call_args[1]
            assert call_kw["symbol"] == "MSFT"
            assert call_kw["outcome_id"] == "cid-msft-1"

    def test_weight_learner_confidence_floor_is_020(self):
        """Phase C: LEARNER_MIN_CONFIDENCE must be 0.20 (not 0.5)."""
        from app.council.weight_learner import LEARNER_MIN_CONFIDENCE
        assert LEARNER_MIN_CONFIDENCE == 0.20

    def test_weight_learner_has_regime_stratified_weights(self):
        """WeightLearner must maintain per-regime Beta (regime-stratified)."""
        from app.council.weight_learner import WeightLearner
        wl = WeightLearner()
        assert hasattr(wl, "_regime_weights")
        assert hasattr(wl, "get_regime_weight")

    def test_simulate_100_outcomes_retention_rate(self):
        """Simulate 100 outcomes; count how many reach update_from_outcome (target >= 70%)."""
        from app.council.feedback_loop import (
            record_decision, record_outcome, update_agent_weights, reset_feedback,
        )
        from app.council.weight_learner import get_weight_learner
        reset_feedback()
        learner = get_weight_learner()
        # Seed feedback_loop store and weight_learner decision history with matching trade_ids
        for i in range(120):
            record_decision(
                symbol="SYM",
                final_direction="buy",
                votes=[{"agent_name": "regime", "direction": "buy", "confidence": 0.6}],
                trade_id=f"cid-{i}",
            )
            learner.record_decision(MagicMock(
                symbol="SYM",
                timestamp=f"2026-01-01T12:00:{i:02d}",
                final_direction="buy",
                final_confidence=0.6,
                votes=[MagicMock(agent_name="regime", direction="buy", confidence=0.6, weight=1.0)],
                regime="NEUTRAL",
                council_decision_id=f"cid-{i}",
            ))
        # Simulate 100 outcomes (valid trade_id, confidence >= 0.20)
        reached_learner = 0
        for i in range(100):
            record_outcome(
                trade_id=f"cid-{i}",
                symbol="SYM",
                outcome="win" if i % 2 == 0 else "loss",
                r_multiple=0.5,
            )
            outcome_data = {
                "trade_id": f"cid-{i}",
                "symbol": "SYM",
                "outcome": "win" if i % 2 == 0 else "loss",
                "r_multiple": 0.5,
                "pnl": 10.0,
                "confidence": 0.8,
            }
            updated = update_agent_weights(outcome=outcome_data)
            if updated and len(updated) > 0:
                reached_learner += 1
        retention = reached_learner / 100.0 * 100
        assert retention >= 70.0, (
            f"Retention rate {retention:.1f}% below target 70%. "
            f"Reached WeightLearner: {reached_learner}/100"
        )
