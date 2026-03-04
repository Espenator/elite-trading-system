"""Council Agent Configuration — settings-driven thresholds.

Reads agent thresholds from the settings service instead of hardcoding them.
Falls back to sensible defaults if settings are unavailable.

Usage:
    from app.council.agent_config import get_agent_thresholds
    cfg = get_agent_thresholds()
    if rsi <= cfg["rsi_oversold"]:
        ...
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Hardcoded defaults — used when settings service is unavailable
_DEFAULTS: Dict[str, Any] = {
    # Market Perception Agent
    "return_1d_threshold": 0.005,
    "return_5d_threshold": 0.01,
    "return_20d_threshold": 0.03,
    "volume_surge_threshold": 1.5,
    "near_high_threshold": -0.02,
    "near_low_threshold": 0.02,

    # Flow Perception Agent
    "pcr_bullish_threshold": 0.7,
    "pcr_mild_bearish_threshold": 1.0,
    "pcr_bearish_threshold": 1.3,

    # Strategy Agent
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "adx_trending_threshold": 25,
    "strategy_buy_pass_rate": 0.6,
    "strategy_sell_pass_rate": 0.3,

    # Risk Agent
    "max_portfolio_heat": 0.06,
    "max_single_position": 0.02,
    "risk_score_veto_threshold": 30,
    "volatility_elevated_threshold": 0.30,
    "volatility_extreme_threshold": 0.50,

    # Execution Agent
    "min_volume_threshold": 50_000,

    # Hypothesis Agent (LLM confidence mapping)
    "llm_buy_confidence_threshold": 0.6,
    "llm_sell_confidence_threshold": 0.4,

    # Critic Agent (R-multiple tiers)
    "critic_excellent_r": 2.0,
    "critic_good_r": 1.0,
    "critic_small_loss_r": -1.0,

    # Agent weights
    "weight_market_perception": 1.0,
    "weight_flow_perception": 0.8,
    "weight_regime": 1.2,
    "weight_hypothesis": 0.9,
    "weight_strategy": 1.1,
    "weight_risk": 1.5,
    "weight_execution": 1.3,
    "weight_critic": 0.5,
}


def get_agent_thresholds() -> Dict[str, Any]:
    """Load agent thresholds from settings service, falling back to defaults.

    Reads from 'council' settings category. Any key not found in settings
    falls back to the hardcoded default above.
    """
    try:
        from app.services.settings_service import get_settings_by_category
        stored = get_settings_by_category("council")
        # Merge: stored values override defaults
        merged = {**_DEFAULTS, **{k: v for k, v in stored.items() if k in _DEFAULTS}}
        return merged
    except Exception:
        # Settings service not available (startup, tests, etc.)
        return _DEFAULTS.copy()


def get_agent_weight(agent_name: str) -> float:
    """Get the configured weight for a specific agent."""
    cfg = get_agent_thresholds()
    key = f"weight_{agent_name}"
    return float(cfg.get(key, 1.0))
