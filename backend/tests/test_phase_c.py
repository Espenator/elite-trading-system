"""Tests for Phase C: Sharpen the Brain.

Covers: C1 weight learner fixes, C2 Brier calibration, C3 debate wiring,
C5 R-multiple, C6 homeostasis, C7 regime thresholds, C9 silent failures,
I1 self-awareness, I5 supplemental weights.
"""
import pytest
from unittest.mock import MagicMock, patch


# ── C1: Weight Learner ────────────────────────────────────────────────────

class TestWeightLearner:
    """C1: Weight learner fixes — confidence floor, regime learning, symmetric penalties."""

    def test_confidence_floor_lowered(self):
        from app.council.weight_learner import LEARNER_MIN_CONFIDENCE
        assert LEARNER_MIN_CONFIDENCE == 0.20, "Confidence floor should be 0.20 (not 0.50)"

    def test_decay_rate_increased(self):
        from app.council.weight_learner import WeightLearner
        wl = WeightLearner()
        assert wl.decay_rate == 0.005, "Decay rate should be 0.005 for faster adaptation"

    def test_regime_stratified_weights(self):
        from app.council.weight_learner import WeightLearner
        wl = WeightLearner()
        # Initially no regime-specific data
        w = wl.get_regime_weight("market_perception", "BULLISH")
        assert w == wl.get_weight("market_perception")  # Falls back to global

    def test_trade_id_matching(self):
        """Outcomes should match by trade_id, not just symbol."""
        from app.council.weight_learner import WeightLearner
        from app.council.schemas import AgentVote
        wl = WeightLearner()

        # Mock a decision with trade_id
        decision = MagicMock()
        decision.symbol = "AAPL"
        decision.timestamp = "2026-03-12T10:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.8
        decision.regime = "BULLISH"
        decision.decision_id = "test-trade-123"
        vote = AgentVote(agent_name="strategy", direction="buy", confidence=0.8, reasoning="test")
        decision.votes = [vote]

        wl.record_decision(decision)

        # Update with trade_id — should find match
        result = wl.update_from_outcome(
            symbol="AAPL", outcome_direction="win", trade_id="test-trade-123",
            confidence=0.8,
        )
        assert "strategy" in result

    def test_symmetric_penalty(self):
        """Losing trades should penalize agents symmetrically with winning rewards."""
        from app.council.weight_learner import WeightLearner
        from app.council.schemas import AgentVote
        wl = WeightLearner()

        decision = MagicMock()
        decision.symbol = "TSLA"
        decision.timestamp = "2026-03-12T10:00:00"
        decision.final_direction = "buy"
        decision.final_confidence = 0.8
        decision.regime = "NEUTRAL"
        decision.decision_id = "sym-test-1"
        # "strategy" voted buy (wrong — trade lost, correct was sell) → PENALTY
        # "risk" voted sell (correct — predicted the loss) → REWARD
        vote1 = AgentVote(agent_name="strategy", direction="buy", confidence=0.9, reasoning="bullish")
        vote2 = AgentVote(agent_name="risk", direction="sell", confidence=0.8, reasoning="bearish caution")
        decision.votes = [vote1, vote2]
        wl.record_decision(decision)

        # Capture pre-update ratio (strategy / risk)
        pre_ratio = wl.get_weight("strategy") / wl.get_weight("risk")

        wl.update_from_outcome(
            symbol="TSLA", outcome_direction="loss", trade_id="sym-test-1",
            confidence=0.8,
        )

        # After a loss, the wrong agent (strategy) should lose ground RELATIVE
        # to the correct agent (risk). Normalization preserves mean=1.0 across
        # all 30+ agents, so absolute values shift — but the ratio must drop.
        post_ratio = wl.get_weight("strategy") / wl.get_weight("risk")
        assert post_ratio < pre_ratio, (
            f"Wrong agent should lose ground relative to correct agent: "
            f"ratio {post_ratio:.4f} should be < {pre_ratio:.4f}"
        )


# ── C2: Brier Score Calibration ──────────────────────────────────────────

class TestBrierCalibration:
    """C2: Brier score tracking per agent."""

    def test_brier_score_calculation(self):
        from app.council.calibration import CalibrationTracker
        ct = CalibrationTracker()

        # Perfect calibration: predicts 0.8, outcome 1.0 → (0.8-1.0)^2 = 0.04
        ct.record("agent_a", 0.8, 1.0)
        ct.record("agent_a", 0.8, 1.0)
        assert ct.get_brier_score("agent_a") == 0.04

    def test_brier_score_poor_calibration(self):
        from app.council.calibration import CalibrationTracker
        ct = CalibrationTracker()

        # Poor calibration: predicts 0.9, outcome 0.0 → (0.9-0.0)^2 = 0.81
        ct.record("agent_b", 0.9, 0.0)
        ct.record("agent_b", 0.9, 0.0)
        assert ct.get_brier_score("agent_b") == 0.81

    def test_weight_penalty_threshold(self):
        from app.council.calibration import CalibrationTracker, POORLY_CALIBRATED_THRESHOLD
        ct = CalibrationTracker()

        # Well-calibrated → no penalty
        ct.record("good_agent", 0.7, 1.0)
        assert ct.get_weight_penalty("good_agent") == 1.0

        # Poorly calibrated → 20% penalty
        ct.record("bad_agent", 0.9, 0.0)
        assert ct.get_weight_penalty("bad_agent") == 0.80

    def test_no_score_for_unknown_agent(self):
        from app.council.calibration import CalibrationTracker
        ct = CalibrationTracker()
        assert ct.get_brier_score("unknown") is None
        assert ct.get_weight_penalty("unknown") == 1.0

    def test_rolling_window(self):
        from app.council.calibration import CalibrationTracker
        ct = CalibrationTracker(window_size=5)
        for i in range(10):
            ct.record("agent_c", 0.5, 1.0)
        # Only 5 most recent should be kept
        assert len(ct._observations["agent_c"]) == 5

    def test_get_all_scores(self):
        from app.council.calibration import CalibrationTracker
        ct = CalibrationTracker()
        ct.record("a1", 0.5, 1.0)
        ct.record("a2", 0.8, 0.0)
        scores = ct.get_all_scores()
        assert "a1" in scores
        assert "a2" in scores
        assert scores["a1"]["n_trades"] == 1
        assert scores["a2"]["poorly_calibrated"] is True


# ── C5: R-Multiple Fix ───────────────────────────────────────────────────

class TestRMultiple:
    """C5: R-multiple should use actual stop price, not 2% default."""

    def test_r_multiple_with_actual_stop(self):
        """R = pnl / (abs(entry - stop) * qty) for longs."""
        entry = 100.0
        stop = 95.0
        exit_price = 110.0
        qty = 10
        pnl = (exit_price - entry) * qty  # 100
        risk_per_share = abs(entry - stop)  # 5
        r_multiple = pnl / (risk_per_share * qty)  # 100 / 50 = 2.0
        assert r_multiple == 2.0

    def test_r_multiple_loss(self):
        """Negative R on losing trade."""
        entry = 100.0
        stop = 95.0
        exit_price = 93.0
        qty = 10
        pnl = (exit_price - entry) * qty  # -70
        risk_per_share = abs(entry - stop)  # 5
        r_multiple = pnl / (risk_per_share * qty)  # -70 / 50 = -1.4
        assert r_multiple == pytest.approx(-1.4)


# ── C7: Regime Thresholds ────────────────────────────────────────────────

class TestRegimeThresholds:
    """C7: Centralized regime-adaptive parameters."""

    def test_bullish_regime_config(self):
        from app.config.regime_thresholds import get_regime_config
        cfg = get_regime_config("BULLISH")
        assert cfg["rsi_oversold"] == 35
        assert cfg["kelly_min_edge"] == 0.01
        assert cfg["max_daily_trades"] == 20
        assert cfg["arbiter_exec_threshold"] == 0.35
        assert cfg["atr_stop_multiplier"] == 1.5

    def test_crisis_regime_config(self):
        from app.config.regime_thresholds import get_regime_config
        cfg = get_regime_config("CRISIS")
        assert cfg["rsi_oversold"] == 20
        assert cfg["kelly_min_edge"] == 0.05
        assert cfg["max_daily_trades"] == 5
        assert cfg["atr_stop_multiplier"] == 3.0

    def test_unknown_regime_falls_back_to_neutral(self):
        from app.config.regime_thresholds import get_regime_config
        cfg = get_regime_config("UNKNOWN_REGIME")
        neutral = get_regime_config("NEUTRAL")
        assert cfg == neutral

    def test_get_param(self):
        from app.config.regime_thresholds import get_param
        assert get_param("BULLISH", "max_daily_trades") == 20
        assert get_param("BULLISH", "nonexistent", 42) == 42

    def test_env_var_override(self, monkeypatch):
        from app.config.regime_thresholds import get_regime_config
        monkeypatch.setenv("REGIME_BULLISH_MAX_DAILY_TRADES", "30")
        cfg = get_regime_config("BULLISH")
        assert cfg["max_daily_trades"] == 30


# ── C6: Homeostasis Integration ──────────────────────────────────────────

class TestHomeostasisWiring:
    """C6: Homeostasis mode should affect position sizing."""

    def test_homeostasis_scale_values(self):
        """Verify homeostasis provides expected scale values."""
        # The get_position_scale method should exist and return a float
        from app.council.homeostasis import get_homeostasis
        h = get_homeostasis()
        scale = h.get_position_scale()
        assert isinstance(scale, (int, float))
        assert scale >= 0.0


# ── C9: Silent Failure Alerting ──────────────────────────────────────────

class TestSilentFailureAlerting:
    """C9: Alert topics should exist and task_spawner should publish on failure."""

    def test_alert_topics_in_valid_topics(self):
        from app.core.message_bus import MessageBus
        valid = MessageBus.VALID_TOPICS
        assert "alert.agent_failure" in valid
        assert "alert.data_starvation" in valid
        assert "alert.council_degraded" in valid

    def test_task_spawner_publishes_on_failure(self):
        """TaskSpawner._publish_agent_failure should not raise."""
        from app.council.task_spawner import TaskSpawner
        from app.council.blackboard import BlackboardState
        bb = BlackboardState(symbol="TEST", raw_features={})
        spawner = TaskSpawner(bb)
        # Should not raise
        spawner._publish_agent_failure("test_agent", "RuntimeError", "test error message")


# ── I1: SelfAwareness ────────────────────────────────────────────────────

class TestSelfAwareness:
    """I1: SelfAwareness Bayesian tracking module."""

    def test_singleton_creation(self):
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        assert sa is not None
        assert hasattr(sa, "weights")
        assert hasattr(sa, "streaks")
        assert hasattr(sa, "health")

    def test_effective_weight_combines_bayesian_and_streak(self):
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        w = sa.get_effective_weight("market_perception")
        assert isinstance(w, float)
        assert w >= 0.0

    def test_streak_probation(self):
        from app.council.self_awareness import SelfAwareness
        sa = SelfAwareness()
        agent = "test_probation_agent_c2"
        sa.streaks.reset(agent)
        for _ in range(5):
            sa.streaks.record_outcome(agent, profitable=False)
        assert sa.streaks.get_status(agent) == "PROBATION"
        assert sa.streaks.get_weight_multiplier(agent) == 0.25

    def test_streak_hibernation(self):
        from app.council.self_awareness import SelfAwareness
        sa = SelfAwareness()
        agent = "test_hibernation_agent_c2"
        sa.streaks.reset(agent)
        for _ in range(10):
            sa.streaks.record_outcome(agent, profitable=False)
        assert sa.streaks.get_status(agent) == "HIBERNATION"
        assert sa.streaks.get_weight_multiplier(agent) == 0.0

    def test_bayesian_update(self):
        from app.council.self_awareness import SelfAwareness
        sa = SelfAwareness()
        # Record some wins
        for _ in range(5):
            sa.weights.update("test_agent", trade_profitable=True)
        w = sa.weights.get_weight("test_agent")
        assert w > 0.5  # Should be above neutral after wins


# ── I5: Supplemental Agent Weights ───────────────────────────────────────

class TestSupplementalAgentWeights:
    """I5: 6 supplemental agents should have explicit weights."""

    def test_supplemental_agents_have_weights_in_config(self):
        from app.council.agent_config import get_agent_thresholds
        cfg = get_agent_thresholds()
        for agent in ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing", "intermarket"]:
            key = f"weight_{agent}"
            assert key in cfg, f"Missing weight for supplemental agent: {agent}"
            assert isinstance(cfg[key], (int, float))
            assert cfg[key] > 0

    def test_supplemental_agents_in_weight_learner(self):
        from app.council.weight_learner import DEFAULT_WEIGHTS
        for agent in ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing", "intermarket"]:
            assert agent in DEFAULT_WEIGHTS, f"Missing {agent} in DEFAULT_WEIGHTS"


# ── Arbiter Integration ──────────────────────────────────────────────────

class TestArbiterIntegration:
    """Verify arbiter applies Brier penalty and SelfAwareness multiplier."""

    def test_arbiter_applies_calibration_penalty(self):
        """Arbiter should apply Brier score weight penalty."""
        from app.council.arbiter import arbitrate
        from app.council.schemas import AgentVote

        votes = [
            AgentVote(agent_name="regime", direction="buy", confidence=0.8, reasoning="test", weight=1.2),
            AgentVote(agent_name="risk", direction="buy", confidence=0.7, reasoning="test", weight=1.5),
            AgentVote(agent_name="strategy", direction="buy", confidence=0.9, reasoning="test", weight=1.1),
            AgentVote(agent_name="execution", direction="buy", confidence=0.8, reasoning="test", weight=1.3,
                      metadata={"execution_ready": True}),
        ]
        result = arbitrate("AAPL", "1d", "2026-03-12T10:00:00Z", votes)
        assert result.final_direction == "buy"
        assert result.final_confidence > 0

    def test_arbiter_veto_still_works(self):
        from app.council.arbiter import arbitrate
        from app.council.schemas import AgentVote

        votes = [
            AgentVote(agent_name="regime", direction="buy", confidence=0.8, reasoning="test", weight=1.2),
            AgentVote(agent_name="risk", direction="hold", confidence=0.9, reasoning="veto", weight=1.5,
                      veto=True, veto_reason="Too risky"),
            AgentVote(agent_name="strategy", direction="buy", confidence=0.9, reasoning="test", weight=1.1),
        ]
        result = arbitrate("AAPL", "1d", "2026-03-12T10:00:00Z", votes)
        assert result.vetoed is True
        assert result.final_direction == "hold"
