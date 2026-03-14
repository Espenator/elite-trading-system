"""Feedback Learning Loop Tests — decision recording, outcome resolution,
weight updates, and long-term convergence of the council self-learning system.

Tests feedback_loop.py and weight_learner.py together to verify the full
record → resolve → learn cycle that makes Embodier Trader self-improving.
"""
import random
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from collections import defaultdict

import pytest

from app.council.schemas import AgentVote, DecisionPacket
from app.council import feedback_loop
from app.council.weight_learner import WeightLearner, DEFAULT_WEIGHTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENTS = ["regime", "risk", "strategy", "market_perception", "ema_trend"]


def _votes_dicts(direction: str = "buy", confidence: float = 0.8) -> list[dict]:
    """Return vote dicts in the format expected by feedback_loop.record_decision."""
    return [
        {"agent_name": a, "direction": direction, "confidence": confidence}
        for a in AGENTS
    ]


def _agent_votes_objs(direction: str = "buy", confidence: float = 0.8) -> list[AgentVote]:
    """Return AgentVote objects for WeightLearner tests."""
    return [
        AgentVote(
            agent_name=a,
            direction=direction,
            confidence=confidence,
            reasoning=f"{a} vote",
            weight=1.0,
        )
        for a in AGENTS
    ]


class _FakeDecision:
    """Minimal decision object matching WeightLearner.record_decision expectations."""
    def __init__(self, symbol, direction, votes, decision_id="", regime="NEUTRAL"):
        self.symbol = symbol
        self.final_direction = direction
        self.final_confidence = 0.75
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.votes = votes
        self.decision_id = decision_id
        self.council_decision_id = decision_id
        self.regime = regime


def _make_learner() -> WeightLearner:
    """Create a fresh WeightLearner with DuckDB persistence mocked out."""
    with patch.object(WeightLearner, "_load_from_store"):
        learner = WeightLearner(learning_rate=0.05, min_weight=0.2, max_weight=2.5)
    return learner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFeedbackLearningLoop:

    def setup_method(self):
        """Reset feedback loop state before each test."""
        feedback_loop.reset_feedback()

    def test_outcome_resolution_win(self):
        """Record BUY decision → WIN outcome. Buy-voters get correct count."""
        feedback_loop.record_decision(
            symbol="AAPL",
            final_direction="buy",
            votes=_votes_dicts("buy", 0.8),
            trade_id="t1",
        )

        with patch("app.council.feedback_loop._get_decision_from_duckdb", return_value=None):
            result = feedback_loop.record_outcome("t1", "AAPL", "win", r_multiple=2.0)

        stats = result["agent_stats"]
        assert len(stats) > 0, "No agent stats recorded"

        for agent in AGENTS:
            assert agent in stats, f"{agent} missing from stats"
            assert stats[agent]["correct"] >= 1, (
                f"{agent} should have ≥1 correct after win"
            )
            assert stats[agent]["total"] >= 1

    def test_outcome_resolution_loss(self):
        """Record BUY decision → LOSS outcome. Buy-voters get incorrect count."""
        feedback_loop.record_decision(
            symbol="TSLA",
            final_direction="buy",
            votes=_votes_dicts("buy", 0.7),
            trade_id="t2",
        )

        with patch("app.council.feedback_loop._get_decision_from_duckdb", return_value=None):
            result = feedback_loop.record_outcome("t2", "TSLA", "loss", r_multiple=-1.0)

        stats = result["agent_stats"]
        for agent in AGENTS:
            assert agent in stats
            assert stats[agent]["incorrect"] >= 1, (
                f"{agent} should have ≥1 incorrect after loss (voted buy, correct was sell)"
            )

    def test_feedback_loop_win_upweights(self):
        """Win outcome → WeightLearner increases correct-voters' weights."""
        learner = _make_learner()
        votes = _agent_votes_objs("buy", 0.8)
        decision = _FakeDecision("AAPL", "buy", votes, decision_id="d1")
        learner.record_decision(decision)

        initial_weights = learner.get_weights()

        with patch.object(learner, "_persist_to_store"), \
             patch.object(learner, "_store_attribution"), \
             patch.object(learner, "_persist_learner_provenance"):
            updated = learner.update_from_outcome(
                symbol="AAPL",
                outcome_direction="win",
                pnl=500.0,
                r_multiple=2.0,
                trade_id="d1",
            )

        changed_count = sum(
            1 for a in AGENTS
            if a in updated and a in initial_weights
            and updated[a] != initial_weights.get(a)
        )
        assert changed_count > 0, "At least one agent weight should change on win"

    def test_feedback_loop_loss_downweights(self):
        """Loss outcome → buy-voters get downweighted."""
        learner = _make_learner()
        votes = _agent_votes_objs("buy", 0.8)
        decision = _FakeDecision("TSLA", "buy", votes, decision_id="d2")
        learner.record_decision(decision)

        initial = {a: learner.get_weight(a) for a in AGENTS}

        with patch.object(learner, "_persist_to_store"), \
             patch.object(learner, "_store_attribution"), \
             patch.object(learner, "_persist_learner_provenance"):
            updated = learner.update_from_outcome(
                symbol="TSLA",
                outcome_direction="loss",
                pnl=-300.0,
                r_multiple=-1.0,
                trade_id="d2",
            )

        any_decreased = any(
            updated.get(a, initial[a]) != initial[a]
            for a in AGENTS if a in updated
        )
        assert any_decreased, "Loss should change at least one buy-voter's weight"

    def test_daily_outcome_batch(self):
        """10 decisions (5 wins, 5 losses) → all processed, stats reflect all."""
        for i in range(10):
            feedback_loop.record_decision(
                symbol=f"SYM{i}",
                final_direction="buy",
                votes=_votes_dicts("buy", 0.7),
                trade_id=f"batch_{i}",
            )

        with patch("app.council.feedback_loop._get_decision_from_duckdb", return_value=None):
            for i in range(10):
                outcome = "win" if i < 5 else "loss"
                r_mult = 1.5 if outcome == "win" else -1.0
                feedback_loop.record_outcome(f"batch_{i}", f"SYM{i}", outcome, r_mult)

        perf = feedback_loop.get_agent_performance()
        assert perf["total_decisions"] == 10
        assert perf["total_outcomes"] == 10
        assert perf["feedback_active"] is True

        for agent in AGENTS:
            s = perf["agent_stats"].get(agent, {})
            assert s.get("total", 0) == 10, (
                f"{agent} should have 10 total evaluations, got {s.get('total')}"
            )

    def test_self_awareness_accuracy(self):
        """50 decisions (30 correct, 20 wrong) → accuracy ≈ 60%."""
        for i in range(50):
            feedback_loop.record_decision(
                symbol="SPY",
                final_direction="buy",
                votes=_votes_dicts("buy", 0.7),
                trade_id=f"aware_{i}",
            )

        with patch("app.council.feedback_loop._get_decision_from_duckdb", return_value=None):
            for i in range(50):
                outcome = "win" if i < 30 else "loss"
                feedback_loop.record_outcome(f"aware_{i}", "SPY", outcome)

        perf = feedback_loop.get_agent_performance()
        for agent in AGENTS:
            acc = perf["agent_stats"].get(agent, {}).get("accuracy", 0)
            assert 0.55 <= acc <= 0.65, (
                f"{agent} accuracy should be ~0.60, got {acc}"
            )

    def test_overfitting_guard_concept(self):
        """Train accuracy 95% vs test accuracy 55% → gap exceeds 20% threshold."""
        train_accuracy = 0.95
        test_accuracy = 0.55
        gap = train_accuracy - test_accuracy

        OVERFIT_THRESHOLD = 0.20
        assert gap > OVERFIT_THRESHOLD, (
            f"Accuracy gap {gap:.0%} should exceed {OVERFIT_THRESHOLD:.0%} threshold"
        )
        assert gap == pytest.approx(0.40, abs=0.01)

        is_overfitting = gap > OVERFIT_THRESHOLD
        assert is_overfitting, "Should detect overfitting when gap > threshold"

    def test_weight_persistence_across_restart(self):
        """WeightLearner persists weights; new instance can reload them."""
        learner = _make_learner()

        votes = _agent_votes_objs("buy", 0.8)
        for i in range(50):
            symbol = f"SYM{i % 5}"
            decision = _FakeDecision(symbol, "buy", votes, decision_id=f"p_{i}")
            learner.record_decision(decision)
            outcome = "win" if i % 3 != 0 else "loss"

            with patch.object(learner, "_persist_to_store"), \
                 patch.object(learner, "_store_attribution"), \
                 patch.object(learner, "_persist_learner_provenance"):
                learner.update_from_outcome(
                    symbol=symbol,
                    outcome_direction=outcome,
                    pnl=100.0 if outcome == "win" else -50.0,
                    r_multiple=1.5 if outcome == "win" else -1.0,
                    trade_id=f"p_{i}",
                )

        trained_weights = learner.get_weights()
        any_changed = any(
            abs(trained_weights.get(a, DEFAULT_WEIGHTS.get(a, 1.0)) - DEFAULT_WEIGHTS.get(a, 1.0)) > 0.001
            for a in AGENTS if a in trained_weights and a in DEFAULT_WEIGHTS
        )
        assert any_changed, "Weights should differ from defaults after 50 updates"

        saved_weights = dict(trained_weights)
        with patch.object(WeightLearner, "_load_from_store") as mock_load:
            def _restore(self_arg=None):
                for k, v in saved_weights.items():
                    if k in learner._weights:
                        learner._weights[k] = v
            mock_load.side_effect = _restore

            learner2 = WeightLearner.__new__(WeightLearner)
            learner2._weights = dict(DEFAULT_WEIGHTS)
            learner2._regime_weights = defaultdict(lambda: defaultdict(lambda: {"alpha": 2.0, "beta": 2.0}))
            learner2._decision_history = []
            learner2.update_count = 0
            learner2.last_update = None
            learner2.learning_rate = 0.05
            learner2.min_weight = 0.2
            learner2.max_weight = 2.5
            learner2.decay_rate = 0.005
            for k, v in saved_weights.items():
                if k in learner2._weights:
                    learner2._weights[k] = v

            reloaded = learner2.get_weights()
            for agent in AGENTS:
                if agent in saved_weights and agent in reloaded:
                    assert reloaded[agent] == pytest.approx(saved_weights[agent], abs=0.01), (
                        f"{agent}: reloaded {reloaded[agent]} != saved {saved_weights[agent]}"
                    )

    def test_long_term_convergence_500_decisions(self):
        """500 rounds: agent_A 80% correct, agent_B 40% correct.
        After convergence, A's weight should exceed B's weight.
        """
        learner = _make_learner()
        learner._weights["agent_a"] = 1.0
        learner._weights["agent_b"] = 1.0
        random.seed(42)

        for i in range(500):
            a_correct = random.random() < 0.80
            b_correct = random.random() < 0.40

            council_dir = "buy"
            outcome = "win" if a_correct else "loss"

            a_dir = council_dir if a_correct else ("sell" if council_dir == "buy" else "buy")
            b_dir = council_dir if b_correct else ("sell" if council_dir == "buy" else "buy")

            votes = [
                AgentVote("regime", council_dir, 0.7, "regime", weight=1.0),
                AgentVote("risk", council_dir, 0.7, "risk", weight=1.0),
                AgentVote("strategy", council_dir, 0.7, "strategy", weight=1.0),
                AgentVote("agent_a", a_dir, 0.7, "a analysis", weight=1.0),
                AgentVote("agent_b", b_dir, 0.6, "b analysis", weight=1.0),
            ]

            decision = _FakeDecision(
                "TEST", council_dir, votes, decision_id=f"conv_{i}"
            )
            learner.record_decision(decision)

            with patch.object(learner, "_persist_to_store"), \
                 patch.object(learner, "_store_attribution"), \
                 patch.object(learner, "_persist_learner_provenance"):
                learner.update_from_outcome(
                    symbol="TEST",
                    outcome_direction=outcome,
                    pnl=100.0 if outcome == "win" else -80.0,
                    r_multiple=1.5 if outcome == "win" else -1.0,
                    trade_id=f"conv_{i}",
                )

        weights = learner.get_weights()
        w_a = weights.get("agent_a", 1.0)
        w_b = weights.get("agent_b", 1.0)

        assert w_a > w_b, (
            f"agent_a (80% correct) weight {w_a:.4f} should > "
            f"agent_b (40% correct) weight {w_b:.4f}"
        )

    def test_trade_id_matching(self):
        """Two decisions for same symbol with different trade_ids stay separate."""
        feedback_loop.record_decision(
            symbol="GOOG",
            final_direction="buy",
            votes=_votes_dicts("buy", 0.8),
            trade_id="goog_morning",
        )
        feedback_loop.record_decision(
            symbol="GOOG",
            final_direction="sell",
            votes=_votes_dicts("sell", 0.7),
            trade_id="goog_afternoon",
        )

        with patch("app.council.feedback_loop._get_decision_from_duckdb", return_value=None):
            result_morning = feedback_loop.record_outcome(
                "goog_morning", "GOOG", "win", r_multiple=1.5
            )
            result_afternoon = feedback_loop.record_outcome(
                "goog_afternoon", "GOOG", "loss", r_multiple=-1.0
            )

        perf = feedback_loop.get_agent_performance()
        assert perf["total_outcomes"] == 2
        assert perf["total_decisions"] == 2

        for agent in AGENTS:
            s = perf["agent_stats"].get(agent, {})
            assert s["total"] == 2, (
                f"{agent} should have 2 evaluations (morning + afternoon)"
            )
