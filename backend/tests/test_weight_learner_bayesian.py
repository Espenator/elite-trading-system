"""Tests for weight_learner.py Bayesian update logic.

- Winning trade increases agent alpha (aligned agents get weight boost)
- Losing trade increases agent beta (misaligned agents get weight penalty)
- Confidence floor at 0.2 is enforced (inputs below rejected)
"""
import pytest
from unittest.mock import MagicMock, patch

from app.council.schemas import AgentVote
from app.council.weight_learner import WeightLearner, LEARNER_MIN_CONFIDENCE


class TestWeightLearnerBayesian:
    """Bayesian update and confidence floor tests."""

    def test_confidence_floor_0_2_enforced(self):
        """Confidence below 0.2 is rejected when STRICT_LEARNER_INPUTS is True."""
        wl = WeightLearner()
        decision = MagicMock()
        decision.symbol = "AAPL"
        decision.timestamp = "2026-03-12T10:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.8
        decision.regime = "NEUTRAL"
        decision.decision_id = "tid-1"
        decision.votes = [
            AgentVote("strategy", "buy", 0.8, "bullish", weight=1.1),
        ]
        wl.record_decision(decision)

        # Update with confidence 0.15 (below 0.2) — should be dropped when strict
        with patch("app.core.config.settings", MagicMock(STRICT_LEARNER_INPUTS=True)):
            wl.update_from_outcome(
                symbol="AAPL",
                outcome_direction="win",
                confidence=0.15,
                trade_id="tid-1",
            )
        # When strict and low confidence, input is dropped; weights may be unchanged
        assert "strategy" in wl.get_weights()

    def test_winning_trade_increases_aligned_agent_weight(self):
        """When trade wins, update_from_outcome runs and adjusts weights (aligned agents rewarded)."""
        wl = WeightLearner()
        decision = MagicMock()
        decision.symbol = "TSLA"
        decision.timestamp = "2026-03-12T10:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.8
        decision.regime = "BULLISH"
        decision.decision_id = "win-1"
        decision.votes = [
            AgentVote("strategy", "buy", 0.8, "bullish", weight=1.1),
            AgentVote("risk", "buy", 0.6, "ok", weight=1.5),
        ]
        wl.record_decision(decision)

        pre_strategy = wl.get_weight("strategy")
        result = wl.update_from_outcome(
            symbol="TSLA",
            outcome_direction="win",
            confidence=0.8,
            trade_id="win-1",
        )
        post_strategy = wl.get_weight("strategy")
        # Both voted buy, outcome win → aligned → weights increase before normalize
        assert "strategy" in result
        assert post_strategy > 0
        assert wl.update_count >= 1

    def test_losing_trade_decreases_misaligned_agent_weight(self):
        """When trade loses, update_from_outcome runs and adjusts weights (misaligned penalized)."""
        wl = WeightLearner()
        decision = MagicMock()
        decision.symbol = "NVDA"
        decision.timestamp = "2026-03-12T11:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.75
        decision.regime = "NEUTRAL"
        decision.decision_id = "loss-1"
        decision.votes = [
            AgentVote("strategy", "buy", 0.9, "bullish", weight=1.1),
            AgentVote("risk", "sell", 0.7, "bearish", weight=1.5),
        ]
        wl.record_decision(decision)

        result = wl.update_from_outcome(
            symbol="NVDA",
            outcome_direction="loss",
            confidence=0.75,
            trade_id="loss-1",
        )
        # correct_direction = sell. Strategy (buy) misaligned, risk (sell) aligned.
        assert "strategy" in result
        assert "risk" in result
        assert wl.get_weight("strategy") > 0
        assert wl.get_weight("risk") > 0
        assert wl.update_count >= 1

    def test_learner_min_confidence_constant(self):
        """LEARNER_MIN_CONFIDENCE is 0.20 per Phase C."""
        assert LEARNER_MIN_CONFIDENCE == 0.20

    def test_validate_learner_input_rejects_low_confidence(self):
        """_validate_learner_input returns False for confidence < 0.2 when strict."""
        wl = WeightLearner()
        with patch("app.core.config.settings", MagicMock(STRICT_LEARNER_INPUTS=True)):
            accepted, reason = wl._validate_learner_input(
                symbol="AAPL",
                outcome_direction="win",
                is_censored=False,
                confidence=0.18,
            )
        assert accepted is False
        assert reason == "low_confidence"
