"""Multi-window evaluator for champion/challenger promotion gate.

Anti-reward-hacking: a model must pass ALL thresholds in ALL time windows
before it can be promoted from challenger to champion.

Eval windows: 30, 60, 90, 252 trading days.
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

EVAL_WINDOWS = [30, 60, 90, 252]  # trading days

THRESHOLDS = {
    "sharpe": 0.5,
    "profit_factor": 1.2,
    "max_dd": -0.15,  # must be ABOVE (less negative) this
    "win_rate": 0.45,
}


def _compute_window_metrics(
    predictions: np.ndarray,
    actuals: np.ndarray,
    prices: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute trading metrics for a single evaluation window.

    Args:
        predictions: Model predictions (probabilities or signals).
        actuals: Actual returns or binary outcomes.
        prices: Optional price series for drawdown calculation.

    Returns:
        Dict with sharpe, profit_factor, max_dd, win_rate.
    """
    if len(predictions) == 0 or len(actuals) == 0:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_dd": -1.0, "win_rate": 0.0}

    # Convert predictions to signals: >0.5 → buy (1), else → flat (0)
    signals = (predictions > 0.5).astype(float)

    # Simulated returns: when we have a buy signal, we capture the actual return
    if np.all((actuals == 0) | (actuals == 1)):
        # Binary labels — convert to pseudo-returns
        returns = signals * (actuals * 2 - 1) * 0.01  # small per-trade return
    else:
        returns = signals * actuals

    # Win rate
    trades = returns[signals > 0]
    if len(trades) > 0:
        win_rate = float(np.mean(trades > 0))
    else:
        win_rate = 0.0

    # Sharpe ratio (annualized from daily)
    mean_ret = float(np.mean(returns))
    std_ret = float(np.std(returns)) or 1e-8
    sharpe = (mean_ret / std_ret) * np.sqrt(252)

    # Profit factor
    gross_profit = float(np.sum(returns[returns > 0])) or 0.0
    gross_loss = abs(float(np.sum(returns[returns < 0]))) or 1e-8
    profit_factor = gross_profit / gross_loss

    # Max drawdown
    if prices is not None and len(prices) > 0:
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        dd = (cumulative - peak) / peak
        max_dd = float(np.min(dd))
    else:
        # Estimate from returns
        cumulative = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative)
        dd = cumulative - peak
        max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
        # Normalize
        if abs(max_dd) > 0:
            max_dd = max(max_dd / (abs(float(np.max(cumulative))) or 1.0), -1.0)

    return {
        "sharpe": round(sharpe, 4),
        "profit_factor": round(profit_factor, 4),
        "max_dd": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }


def _check_thresholds(metrics: Dict[str, float], thresholds: Dict[str, float] = None) -> bool:
    """Check if metrics pass all thresholds."""
    t = thresholds or THRESHOLDS

    if metrics.get("sharpe", 0) < t["sharpe"]:
        return False
    if metrics.get("profit_factor", 0) < t["profit_factor"]:
        return False
    if metrics.get("max_dd", -1) < t["max_dd"]:  # more negative = worse
        return False
    if metrics.get("win_rate", 0) < t["win_rate"]:
        return False
    return True


def evaluate_model_all_windows(
    predictions: np.ndarray,
    actuals: np.ndarray,
    prices: Optional[np.ndarray] = None,
    windows: Optional[List[int]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Evaluate model across all time windows.

    Args:
        predictions: Full array of model predictions.
        actuals: Full array of actual outcomes.
        prices: Optional price series.
        windows: Override evaluation windows.
        thresholds: Override pass/fail thresholds.

    Returns:
        {
            "windows": {30: {metrics + passed}, 60: {...}, ...},
            "all_passed": bool,
            "failing_windows": [int, ...],
        }
    """
    w = windows or EVAL_WINDOWS
    t = thresholds or THRESHOLDS
    result: Dict[str, Any] = {"windows": {}, "all_passed": True, "failing_windows": []}

    for window in w:
        if len(predictions) < window:
            # Not enough data for this window — skip gracefully
            log.warning("Not enough data for %d-day window (have %d)", window, len(predictions))
            result["windows"][window] = {
                "sharpe": 0.0, "profit_factor": 0.0, "max_dd": -1.0, "win_rate": 0.0,
                "passed": False, "skipped": True,
            }
            result["all_passed"] = False
            result["failing_windows"].append(window)
            continue

        # Use the last N days for each window
        preds_w = predictions[-window:]
        actuals_w = actuals[-window:]
        prices_w = prices[-window:] if prices is not None else None

        metrics = _compute_window_metrics(preds_w, actuals_w, prices_w)
        passed = _check_thresholds(metrics, t)

        result["windows"][window] = {**metrics, "passed": passed}

        if not passed:
            result["all_passed"] = False
            result["failing_windows"].append(window)
            log.info(
                "Window %d FAILED: sharpe=%.2f pf=%.2f dd=%.2f wr=%.2f",
                window, metrics["sharpe"], metrics["profit_factor"],
                metrics["max_dd"], metrics["win_rate"],
            )

    return result


def should_promote(eval_results: Dict[str, Any]) -> bool:
    """ALL windows must pass ALL thresholds for promotion."""
    return eval_results.get("all_passed", False)
