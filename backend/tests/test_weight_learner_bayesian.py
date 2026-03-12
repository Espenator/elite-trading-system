"""Weight learner Bayesian update logic: win/loss alpha-beta, confidence floor 0.2."""
import pytest
from unittest.mock import MagicMock, patch

from app.council.schemas import AgentVote
from app.council.weight_learner import WeightLearner, LEARNER_MIN_CONFIDENCE


def test_confidence_floor_at_0_2_enforced():
    """Confidence below 0.2 is rejected by _validate_learner_input."""
    wl = WeightLearner()
    accepted, reason = wl._validate_learner_input(
        symbol="AAPL", outcome_direction="win", is_censored=False, confidence=0.15
    )
    assert accepted is False
    assert "low_confidence" in reason or "confidence" in reason.lower()


def test_confidence_at_0_2_accepted():
    """Confidence at 0.2 is accepted (floor is inclusive)."""
    wl = WeightLearner()
    accepted, _ = wl._validate_learner_input(
        symbol="AAPL", outcome_direction="win", is_censored=False, confidence=0.20
    )
    assert accepted is True


def test_winning_trade_increases_agent_weight():
    """Winning trade increases aligned agent weight (alpha effect)."""
    wl = WeightLearner()
    decision = MagicMock()
    decision.symbol = "AAPL"
    decision.timestamp = "2026-03-12T10:00:00"
    decision.final_direction = "buy"
    decision.final_confidence = 0.8
    decision.regime = "GREEN"
    decision.decision_id = "win-test-1"
    vote = AgentVote(agent_name="strategy", direction="buy", confidence=0.85, reasoning="bullish")
    decision.votes = [vote]
    wl.record_decision(decision)

    pre_weight = wl.get_weight("strategy")
    wl.update_from_outcome(symbol="AAPL", outcome_direction="win", trade_id="win-test-1", confidence=0.8)
    post_weight = wl.get_weight("strategy")
    assert post_weight >= pre_weight


def test_losing_trade_penalizes_wrong_agent_relative_to_correct():
    """Losing trade: wrong-direction agent loses ground relative to correct-direction agent (beta effect)."""
    wl = WeightLearner()
    decision = MagicMock()
    decision.symbol = "MSFT"
    decision.timestamp = "2026-03-12T10:00:00"
    decision.final_direction = "buy"
    decision.final_confidence = 0.8
    decision.regime = "NEUTRAL"
    decision.decision_id = "loss-test-1"
    vote_wrong = AgentVote(agent_name="strategy", direction="buy", confidence=0.9, reasoning="bullish")
    vote_correct = AgentVote(agent_name="risk", direction="sell", confidence=0.8, reasoning="bearish")
    decision.votes = [vote_wrong, vote_correct]
    wl.record_decision(decision)

    pre_ratio = wl.get_weight("strategy") / wl.get_weight("risk")
    wl.update_from_outcome(symbol="MSFT", outcome_direction="loss", trade_id="loss-test-1", confidence=0.9)
    post_ratio = wl.get_weight("strategy") / wl.get_weight("risk")
    assert post_ratio < pre_ratio


def test_learner_min_confidence_constant():
    """LEARNER_MIN_CONFIDENCE is 0.2 (Phase C fix)."""
    assert LEARNER_MIN_CONFIDENCE == 0.20


def test_censored_outcome_does_not_update_weights():
    """Censored outcome leaves weights unchanged."""
    wl = WeightLearner()
    decision = MagicMock()
    decision.symbol = "XYZ"
    decision.timestamp = "2026-03-12T10:00:00"
    decision.final_direction = "buy"
    decision.final_confidence = 0.8
    decision.regime = "GREEN"
    decision.decision_id = "censored-1"
    decision.votes = [AgentVote(agent_name="strategy", direction="buy", confidence=0.8, reasoning="x")]
    wl.record_decision(decision)

    weights_before = dict(wl.get_weights())
    wl.update_from_outcome(symbol="XYZ", outcome_direction="win", trade_id="censored-1", is_censored=True)
    weights_after = wl.get_weights()
    assert weights_before == weights_after
