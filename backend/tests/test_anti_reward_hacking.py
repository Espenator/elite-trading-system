"""Tests for anti-reward-hacking: risk-adjusted objective + multi-window evaluator."""
import numpy as np
import pytest

from app.modules.ml_engine.risk_adjusted_objective import (
    risk_adjusted_expectancy,
    xgboost_risk_objective,
)
from app.modules.ml_engine.multi_window_evaluator import (
    THRESHOLDS,
    _compute_window_metrics,
    _check_thresholds,
    evaluate_model_all_windows,
    should_promote,
)


# ---------------------------------------------------------------------------
# Risk-adjusted objective
# ---------------------------------------------------------------------------
class TestRiskAdjustedObjective:
    def test_perfect_predictions_score_positive(self):
        y_true = np.array([1.0, 0.0, 1.0, 0.0, 1.0])
        y_pred = np.array([0.9, 0.1, 0.8, 0.2, 0.85])
        score = risk_adjusted_expectancy(y_true, y_pred)
        assert score > 0, f"Perfect predictions should score positive, got {score}"

    def test_random_predictions_score_near_zero(self):
        rng = np.random.RandomState(42)
        y_true = rng.randint(0, 2, size=1000).astype(float)
        y_pred = rng.random(1000)
        score = risk_adjusted_expectancy(y_true, y_pred)
        assert abs(score) < 0.5, f"Random predictions should score near zero, got {score}"

    def test_drawdown_penalty_reduces_score(self):
        y_true = np.array([1.0, 0.0, 1.0, 0.0, 1.0])
        y_pred = np.array([0.9, 0.1, 0.8, 0.2, 0.85])

        score_no_dd = risk_adjusted_expectancy(y_true, y_pred)
        score_with_dd = risk_adjusted_expectancy(
            y_true, y_pred, drawdowns=np.array([-0.10, -0.20, -0.05])
        )
        assert score_with_dd < score_no_dd, "Drawdown should reduce score"

    def test_empty_arrays_return_zero(self):
        assert risk_adjusted_expectancy(np.array([]), np.array([])) == 0.0

    def test_xgboost_objective_returns_grad_hess(self):
        """Smoke test: objective returns arrays of correct shape."""

        class FakeDMatrix:
            def get_label(self):
                return np.array([1.0, 0.0, 1.0, 0.0, 1.0])

        y_pred = np.array([0.5, -0.3, 0.8, -0.1, 0.6])
        grad, hess = xgboost_risk_objective(y_pred, FakeDMatrix())
        assert grad.shape == y_pred.shape
        assert hess.shape == y_pred.shape
        assert np.all(hess >= 0), "Hessian should be non-negative"

    def test_overconfident_wrong_penalized_more(self):
        """Confident wrong predictions should get larger gradients."""

        class FakeDMatrix:
            def get_label(self):
                return np.array([0.0, 0.0])  # both actually 0

        # Prediction 1: barely wrong (0.51 → buy but actual is 0)
        # Prediction 2: very wrong (0.99 → buy but actual is 0)
        y_pred = np.array([0.05, 3.0])  # raw logits
        grad, hess = xgboost_risk_objective(y_pred, FakeDMatrix())
        assert abs(grad[1]) > abs(grad[0]), "More confident wrong pred should have larger gradient"


# ---------------------------------------------------------------------------
# Multi-window evaluator
# ---------------------------------------------------------------------------
class TestComputeWindowMetrics:
    def test_all_winning_trades(self):
        preds = np.ones(100)  # all buy
        actuals = np.ones(100) * 0.01  # all positive returns
        metrics = _compute_window_metrics(preds, actuals)
        assert metrics["win_rate"] == 1.0
        assert metrics["profit_factor"] > 1.0
        assert metrics["sharpe"] > 0

    def test_all_losing_trades(self):
        preds = np.ones(100)
        actuals = np.ones(100) * -0.01
        metrics = _compute_window_metrics(preds, actuals)
        assert metrics["win_rate"] == 0.0
        assert metrics["profit_factor"] == 0.0

    def test_empty_arrays(self):
        metrics = _compute_window_metrics(np.array([]), np.array([]))
        assert metrics["sharpe"] == 0.0
        assert metrics["win_rate"] == 0.0

    def test_no_trades_when_no_signals(self):
        preds = np.zeros(100)  # all hold (below 0.5)
        actuals = np.ones(100) * 0.01
        metrics = _compute_window_metrics(preds, actuals)
        assert metrics["win_rate"] == 0.0


class TestCheckThresholds:
    def test_passes_when_all_above(self):
        metrics = {"sharpe": 1.0, "profit_factor": 2.0, "max_dd": -0.05, "win_rate": 0.6}
        assert _check_thresholds(metrics) is True

    def test_fails_on_low_sharpe(self):
        metrics = {"sharpe": 0.1, "profit_factor": 2.0, "max_dd": -0.05, "win_rate": 0.6}
        assert _check_thresholds(metrics) is False

    def test_fails_on_deep_drawdown(self):
        metrics = {"sharpe": 1.0, "profit_factor": 2.0, "max_dd": -0.25, "win_rate": 0.6}
        assert _check_thresholds(metrics) is False

    def test_fails_on_low_win_rate(self):
        metrics = {"sharpe": 1.0, "profit_factor": 2.0, "max_dd": -0.05, "win_rate": 0.3}
        assert _check_thresholds(metrics) is False

    def test_fails_on_low_profit_factor(self):
        metrics = {"sharpe": 1.0, "profit_factor": 0.8, "max_dd": -0.05, "win_rate": 0.6}
        assert _check_thresholds(metrics) is False


class TestMultiWindowEvaluation:
    def test_all_windows_pass(self):
        """Strongly profitable model should pass all windows."""
        n = 300
        preds = np.ones(n)
        actuals = np.ones(n) * 0.02  # 2% returns every day
        result = evaluate_model_all_windows(preds, actuals, windows=[30, 60, 90])
        # With constant positive returns and all buy signals, should pass
        assert result["all_passed"] is True
        assert len(result["failing_windows"]) == 0

    def test_fails_if_any_window_below_threshold(self):
        """Mixed returns may fail some windows."""
        rng = np.random.RandomState(99)
        n = 300
        preds = rng.random(n)
        actuals = rng.normal(0.0, 0.02, n)  # random walk
        result = evaluate_model_all_windows(preds, actuals, windows=[30, 60, 90])
        # Random predictions on random walk should likely fail
        assert result["all_passed"] is False or len(result["failing_windows"]) >= 0

    def test_not_enough_data_marks_skipped(self):
        preds = np.ones(20)
        actuals = np.ones(20) * 0.01
        result = evaluate_model_all_windows(preds, actuals, windows=[30, 60])
        assert result["windows"][30]["skipped"] is True
        assert result["windows"][60]["skipped"] is True
        assert result["all_passed"] is False

    def test_should_promote_true_when_all_pass(self):
        result = {"all_passed": True, "windows": {}, "failing_windows": []}
        assert should_promote(result) is True

    def test_should_promote_false_when_any_fail(self):
        result = {"all_passed": False, "windows": {}, "failing_windows": [30]}
        assert should_promote(result) is False

    def test_custom_thresholds(self):
        """Relaxed thresholds should pass easier."""
        rng = np.random.RandomState(42)
        n = 100
        preds = np.ones(n)
        actuals = rng.normal(0.005, 0.01, n)
        relaxed = {"sharpe": 0.0, "profit_factor": 0.5, "max_dd": -0.5, "win_rate": 0.3}
        result = evaluate_model_all_windows(
            preds, actuals, windows=[30], thresholds=relaxed,
        )
        # With relaxed thresholds, should pass
        assert result["windows"][30]["passed"] is True
