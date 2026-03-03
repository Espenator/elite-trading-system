"""Risk-adjusted training objective for anti-reward-hacking.

Prevents overfitting to raw returns by penalizing drawdown and volatility.
Provides both a standalone scoring function and an XGBoost-compatible
custom objective + eval metric.
"""
import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Default penalty weights
DD_PENALTY_WEIGHT = 2.0
VOL_PENALTY_WEIGHT = 0.5


def risk_adjusted_expectancy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    drawdowns: Optional[np.ndarray] = None,
    dd_penalty: float = DD_PENALTY_WEIGHT,
    vol_penalty: float = VOL_PENALTY_WEIGHT,
) -> float:
    """Score = expectancy_per_dollar_risked - drawdown_penalty - vol_penalty.

    Args:
        y_true: Actual returns or binary labels.
        y_pred: Predicted probabilities or returns.
        drawdowns: Optional array of drawdown values (negative numbers).
        dd_penalty: Weight for drawdown penalty term.
        vol_penalty: Weight for volatility penalty term.

    Returns:
        Scalar score (higher = better).
    """
    if len(y_true) == 0:
        return 0.0

    # Predicted return expectancy (correlation between prediction and outcome)
    pred_signal = y_pred - 0.5  # center around 0
    actual_signal = y_true - np.mean(y_true)

    # Expectancy: average return captured by following the signal
    expectancy = float(np.mean(pred_signal * actual_signal))

    # Sharpe-like ratio on predicted alignment
    pred_std = float(np.std(pred_signal)) or 1e-8
    sharpe_proxy = expectancy / pred_std

    # Drawdown penalty
    dd_term = 0.0
    if drawdowns is not None and len(drawdowns) > 0:
        max_dd = float(np.min(drawdowns))  # most negative
        dd_term = dd_penalty * abs(max_dd)

    # Volatility penalty — penalizes erratic predictions
    pred_vol = float(np.std(y_pred))
    vol_term = vol_penalty * pred_vol

    score = sharpe_proxy - dd_term - vol_term
    return float(score)


def xgboost_risk_eval(y_pred: np.ndarray, dtrain) -> tuple:
    """Custom XGBoost evaluation metric for risk-adjusted expectancy.

    Usage:
        model = xgb.train(params, dtrain, evals=[(dval, 'val')],
                          custom_metric=xgboost_risk_eval)

    Returns:
        ("risk_adj", score) — higher is better.
    """
    y_true = dtrain.get_label()
    score = risk_adjusted_expectancy(y_true, y_pred)
    return "risk_adj", float(score)


def xgboost_risk_objective(y_pred: np.ndarray, dtrain):
    """Custom XGBoost objective (gradient + hessian) with risk adjustment.

    Combines binary cross-entropy with a penalty for overconfident predictions
    that don't align with risk-adjusted outcomes.

    Returns:
        (gradient, hessian) arrays.
    """
    y_true = dtrain.get_label().astype(np.float64)
    y_pred = y_pred.astype(np.float64)

    # Sigmoid clip to avoid log(0)
    eps = 1e-7
    p = 1.0 / (1.0 + np.exp(-y_pred))
    p = np.clip(p, eps, 1.0 - eps)

    # Standard logistic gradient
    grad = p - y_true
    hess = p * (1.0 - p)

    # Risk penalty: penalize overconfident wrong predictions more heavily
    # When prediction is far from 0.5 AND wrong, increase gradient
    confidence = np.abs(p - 0.5) * 2  # 0 = uncertain, 1 = max confidence
    is_wrong = ((p > 0.5) != (y_true > 0.5)).astype(np.float64)

    # Scale up gradient for confident wrong predictions
    penalty = 1.0 + confidence * is_wrong * DD_PENALTY_WEIGHT
    grad = grad * penalty
    hess = hess * penalty

    return grad, hess
