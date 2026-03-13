"""Verify regime entropy affects trading confidence (Agent 6: Regime Entropy)."""
import math
import pytest
from unittest.mock import patch, MagicMock

from app.council.schemas import AgentVote
from app.council.arbiter import arbitrate, _get_execution_threshold


def _vote(name, direction="buy", confidence=0.8, weight=1.0, **meta):
    return AgentVote(
        agent_name=name,
        direction=direction,
        confidence=confidence,
        reasoning=f"{name} test",
        veto=False,
        weight=weight,
        metadata=meta,
    )


def _votes_buy_consensus(confidence=0.8):
    """Votes with full BUY consensus; regime vote has NEUTRAL for exec threshold."""
    return [
        _vote("market_perception", "buy", confidence, 1.0),
        _vote("flow_perception", "buy", confidence, 0.8),
        _vote("regime", "buy", confidence, 1.2, regime_state="NEUTRAL"),
        _vote("hypothesis", "buy", confidence, 0.9),
        _vote("strategy", "buy", confidence, 1.0),
        _vote("risk", "buy", confidence, 1.5),
        _vote("execution", "buy", confidence, 1.3, execution_ready=True),
        _vote("critic", "buy", confidence * 0.5, 0.5),
    ]


class TestRegimeEntropy:
    """Verify regime entropy affects trading confidence."""

    @patch("app.council.arbiter.get_arbiter_meta_model")
    def test_high_entropy_reduces_confidence(self, mock_get_meta):
        """When regime entropy > 1.5, final confidence should be penalized."""
        mock_get_meta.return_value.predict.return_value = None  # force weighted-vote path
        votes = _votes_buy_consensus(confidence=0.8)
        decision = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes, regime_entropy=2.0
        )
        # Weighted vote gives buy consensus; entropy 2.0 -> penalty 0.55x
        assert decision.final_confidence < 0.8
        assert decision.final_direction == "buy"
        assert decision.final_confidence <= 0.6  # penalized (e.g. ~1.0 * 0.55)

    @patch("app.council.arbiter.get_arbiter_meta_model")
    def test_low_entropy_no_penalty(self, mock_get_meta):
        """When regime entropy < 0.5, no confidence penalty."""
        mock_get_meta.return_value.predict.return_value = None
        votes = _votes_buy_consensus(confidence=0.8)
        decision_low_entropy = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes, regime_entropy=0.3
        )
        decision_zero_entropy = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes, regime_entropy=0.0
        )
        # No penalty: final confidence should match weighted average (buy consensus)
        assert decision_low_entropy.final_confidence >= 0.75
        assert decision_zero_entropy.final_confidence >= 0.75
        assert abs(decision_low_entropy.final_confidence - decision_zero_entropy.final_confidence) < 0.05

    @patch("app.council.arbiter._get_learned_weights", return_value={})
    @patch("app.council.arbiter.get_arbiter_meta_model")
    def test_entropy_blocks_execution_in_chaos(self, mock_get_meta, _mock_weights):
        """High entropy should make execution_ready=False more often."""
        mock_get_meta.return_value.predict.return_value = None
        # Buy wins but weighted confidence ~0.65; entropy 2.0 -> 0.55x -> ~0.36 < 0.40
        votes = [
            _vote("market_perception", "hold", 0.6, 1.0),
            _vote("flow_perception", "hold", 0.6, 0.8),
            _vote("regime", "buy", 0.7, 1.2, regime_state="NEUTRAL"),
            _vote("hypothesis", "hold", 0.5, 0.9),
            _vote("strategy", "buy", 0.7, 1.0),
            _vote("risk", "buy", 0.6, 1.5),
            _vote("execution", "buy", 0.6, 1.3, execution_ready=True),
            _vote("critic", "hold", 0.4, 0.5),
        ]
        decision = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes, regime_entropy=2.0
        )
        assert decision.final_direction == "buy"
        assert decision.final_confidence < _get_execution_threshold("NEUTRAL")
        assert decision.execution_ready is False

    def test_entropy_calculated_correctly(self):
        """Verify Shannon entropy formula from regime beliefs (natural log)."""
        from app.council.regime.bayesian_regime import BayesianRegime, STATES

        # Uniform over 6 states -> max entropy = ln(6) ≈ 1.79
        br = BayesianRegime()
        uniform_entropy = br.entropy()
        expected_max = math.log(len(STATES))
        assert abs(uniform_entropy - expected_max) < 0.01

        # High certainty: one state dominant
        from app.council.regime.bayesian_regime import compute_likelihoods
        for _ in range(20):
            # Likelihoods that strongly favor trending_bull
            br.update({
                "trending_bull": 10.0,
                "trending_bear": 0.1,
                "mean_revert": 0.1,
                "high_vol_crisis": 0.1,
                "low_vol_grind": 0.1,
                "transition": 0.1,
            })
        high_certainty_entropy = br.entropy()
        assert high_certainty_entropy < 0.5
        assert high_certainty_entropy > 0

    @patch("app.council.arbiter.get_arbiter_meta_model")
    def test_entropy_passed_through_pipeline(self, mock_get_meta):
        """Verify entropy flows from runner → blackboard → arbiter (arbiter uses it)."""
        mock_get_meta.return_value.predict.return_value = None
        votes = _votes_buy_consensus(confidence=0.8)
        # Simulate blackboard.metadata.get("regime_entropy") passed to arbiter
        regime_entropy_from_blackboard = 1.5
        decision = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes,
            regime_entropy=regime_entropy_from_blackboard,
        )
        # 1.5 -> penalty 0.70; confidence is reduced vs no entropy
        assert decision.final_confidence <= 0.75
        assert decision.final_confidence > 0.4
        decision_no_entropy = arbitrate(
            "AAPL", "1d", "2026-03-13T10:00:00Z", votes, regime_entropy=0.0
        )
        assert decision.final_confidence < decision_no_entropy.final_confidence
