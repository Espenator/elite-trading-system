"""Centralized Regime-Adaptive Thresholds (Phase C, Task C7).

All regime-dependent parameters in one place. Services import from here
instead of hardcoding values.

Usage:
    from app.config.regime_thresholds import get_regime_config
    cfg = get_regime_config("BULLISH")
    rsi_oversold = cfg["rsi_oversold"]
"""
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Regime parameter matrix — rows = regime, cols = parameter
_REGIME_PARAMS: Dict[str, Dict[str, Any]] = {
    "BULLISH": {
        "rsi_oversold": 35, "rsi_overbought": 65,
        "kelly_min_edge": 0.01,
        "max_daily_trades": 20,
        "arbiter_exec_threshold": 0.35,
        "atr_stop_multiplier": 1.5,
        "max_hold_seconds": 10 * 86400,  # 10 days
        "gate_threshold": 55.0,
        "cooldown_seconds": 30,
        "position_scale": 1.2,
    },
    "GREEN": {
        "rsi_oversold": 35, "rsi_overbought": 65,
        "kelly_min_edge": 0.01,
        "max_daily_trades": 18,
        "arbiter_exec_threshold": 0.35,
        "atr_stop_multiplier": 1.5,
        "max_hold_seconds": 10 * 86400,
        "gate_threshold": 55.0,
        "cooldown_seconds": 30,
        "position_scale": 1.1,
    },
    "NEUTRAL": {
        "rsi_oversold": 30, "rsi_overbought": 70,
        "kelly_min_edge": 0.02,
        "max_daily_trades": 15,
        "arbiter_exec_threshold": 0.45,
        "atr_stop_multiplier": 2.0,
        "max_hold_seconds": 5 * 86400,  # 5 days
        "gate_threshold": 65.0,
        "cooldown_seconds": 120,
        "position_scale": 1.0,
    },
    "YELLOW": {
        "rsi_oversold": 28, "rsi_overbought": 72,
        "kelly_min_edge": 0.03,
        "max_daily_trades": 12,
        "arbiter_exec_threshold": 0.50,
        "atr_stop_multiplier": 2.0,
        "max_hold_seconds": 4 * 86400,
        "gate_threshold": 65.0,
        "cooldown_seconds": 120,
        "position_scale": 0.8,
    },
    "BEARISH": {
        "rsi_oversold": 25, "rsi_overbought": 75,
        "kelly_min_edge": 0.03,
        "max_daily_trades": 8,
        "arbiter_exec_threshold": 0.50,
        "atr_stop_multiplier": 2.5,
        "max_hold_seconds": 3 * 86400,  # 3 days
        "gate_threshold": 75.0,
        "cooldown_seconds": 240,
        "position_scale": 0.6,
    },
    "RED": {
        "rsi_oversold": 22, "rsi_overbought": 78,
        "kelly_min_edge": 0.04,
        "max_daily_trades": 5,
        "arbiter_exec_threshold": 0.60,
        "atr_stop_multiplier": 2.5,
        "max_hold_seconds": 2 * 86400,
        "gate_threshold": 75.0,
        "cooldown_seconds": 300,
        "position_scale": 0.4,
    },
    "CRISIS": {
        "rsi_oversold": 20, "rsi_overbought": 80,
        "kelly_min_edge": 0.05,
        "max_daily_trades": 5,
        "arbiter_exec_threshold": 0.55,
        "atr_stop_multiplier": 3.0,
        "max_hold_seconds": 2 * 86400,  # 2 days
        "gate_threshold": 75.0,
        "cooldown_seconds": 300,
        "position_scale": 0.0,
    },
}

# Default fallback (matches NEUTRAL)
_DEFAULT = _REGIME_PARAMS["NEUTRAL"]


def get_regime_config(regime: str) -> Dict[str, Any]:
    """Get all regime-dependent parameters for the given regime.

    Parameters
    ----------
    regime : str
        One of: BULLISH, GREEN, NEUTRAL, YELLOW, BEARISH, RED, CRISIS

    Returns
    -------
    Dict with all regime parameters. Falls back to NEUTRAL for unknown regimes.
    """
    base = dict(_REGIME_PARAMS.get(regime.upper(), _DEFAULT))

    # Allow env var overrides for each parameter
    # e.g. REGIME_BULLISH_MAX_DAILY_TRADES=25
    prefix = f"REGIME_{regime.upper()}_"
    for key in list(base.keys()):
        env_key = prefix + key.upper()
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                # Attempt type-aware conversion
                original = base[key]
                if isinstance(original, int):
                    base[key] = int(env_val)
                elif isinstance(original, float):
                    base[key] = float(env_val)
                else:
                    base[key] = env_val
            except (ValueError, TypeError):
                pass

    return base


def get_param(regime: str, param: str, default: Any = None) -> Any:
    """Get a single regime parameter.

    Usage:
        max_trades = get_param("BULLISH", "max_daily_trades", 15)
    """
    cfg = get_regime_config(regime)
    return cfg.get(param, default)
