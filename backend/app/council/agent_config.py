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
import os
from typing import Any, Dict, Optional

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

    # Social Perception Agent
    "social_bullish_threshold": 62,
    "social_bearish_threshold": 38,
    "social_strong_bullish_threshold": 75,
    "social_strong_bearish_threshold": 25,

    # News Catalyst Agent (no additional thresholds — uses keyword matching)

    # YouTube Knowledge Agent (no additional thresholds — uses concept matching)

    # Critic Agent (R-multiple tiers)
    "critic_excellent_r": 2.0,
    "critic_good_r": 1.0,
    "critic_small_loss_r": -1.0,

    # Circuit Breaker thresholds
    "cb_vix_spike_threshold": 35.0,
    "cb_daily_drawdown_limit": float(os.getenv("CB_DAILY_DRAWDOWN_LIMIT", "0.03")),
    "cb_flash_crash_threshold": 0.05,
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,
    "cb_data_connectivity_min_sources_healthy": 1,

    # Agent weights — Core Council
    "weight_market_perception": 1.0,
    "weight_flow_perception": 0.8,
    "weight_regime": 1.2,
    "weight_social_perception": 0.7,
    "weight_news_catalyst": 0.6,
    "weight_youtube_knowledge": 0.4,
    "weight_hypothesis": 0.9,
    "weight_strategy": 1.1,
    "weight_risk": 1.5,
    "weight_execution": 1.3,
    "weight_critic": 0.5,

    # Agent weights — Supplemental (6 agents, Phase C I5)
    # Default Beta(2,2) = 0.5 neutral starting weight
    "weight_rsi": 1.0,
    "weight_bbv": 0.9,
    "weight_ema_trend": 1.1,
    "weight_relative_strength": 0.9,
    "weight_cycle_timing": 0.8,
    "weight_intermarket": 0.9,

    # Agent weights — Academic Edge Swarms (P0-P4)
    # P0: GEX / Options Flow Swarm
    "weight_gex_agent": 0.9,
    "gex_long_gamma_confidence_boost": 0.05,
    "gex_short_gamma_confidence_reduction": 0.1,

    # P0: Insider Filing Swarm
    "weight_insider_agent": 0.85,
    "insider_cluster_confidence_boost": 0.2,
    "insider_min_transaction_value": 10000,

    # P1: Earnings Tone NLP
    "weight_earnings_tone_agent": 0.8,
    "earnings_cfo_delta_threshold": 0.2,
    "earnings_hedging_ratio_threshold": 0.05,

    # P1: FinBERT Social Sentiment
    "weight_finbert_sentiment_agent": 0.75,
    "sentiment_volume_anomaly_sigma": 3.0,
    "sentiment_extreme_bullish_pct": 0.90,
    "sentiment_extreme_bearish_pct": 0.10,

    # P1: Supply Chain Knowledge Graph
    "weight_supply_chain_agent": 0.7,
    "supply_chain_contagion_decay_1st": 0.8,
    "supply_chain_contagion_decay_2nd": 0.5,

    # P2: 13F Institutional Flow
    "weight_institutional_flow_agent": 0.7,
    "institutional_consensus_min_funds": 5,
    "institutional_crowded_threshold_pct": 0.30,

    # P2: Congressional / Political Trading
    "weight_congressional_agent": 0.6,

    # P2: Dark Pool Accumulation
    "weight_dark_pool_agent": 0.7,
    "dark_pool_dix_bullish_threshold": 0.45,
    "dark_pool_dix_bearish_threshold": 0.40,

    # P3: Multi-Agent RL Portfolio Optimizer
    "weight_portfolio_optimizer_agent": 0.8,
    "portfolio_max_single_position_pct": 0.20,
    "portfolio_drawdown_reduce_25_pct": 0.03,
    "portfolio_drawdown_reduce_50_pct": 0.05,
    "portfolio_drawdown_halt_pct": 0.10,

    # P3: Layered Memory (FinMem)
    "weight_layered_memory_agent": 0.6,
    "memory_short_term_trades": 20,
    "memory_short_term_decay_days": 5,
    "memory_mid_term_days": 90,

    # P4: Alternative Data
    "weight_alt_data_agent": 0.5,

    # P4: Cross-Asset Macro Regime
    "weight_macro_regime_agent": 1.0,
    "macro_vix_complacency": 15,
    "macro_vix_elevated": 35,
    "macro_credit_stress_oas": 600,
}


def get_agent_thresholds(regime: Optional[str] = None) -> Dict[str, Any]:
    """Load agent thresholds from directives (global + regime overlay) and settings.

    Order of precedence: _DEFAULTS < directives (global, then regime overlay) <
    settings service (council category). So thresholds are no longer scattered
    magic numbers; they are discoverable via directives and testable.

    Args:
        regime: Optional market regime (e.g. BULLISH, BEARISH) for regime-specific
            directive overlay. If None, only global directives are applied.
    """
    merged = dict(_DEFAULTS)
    try:
        from app.council.directives.loader import directive_loader
        directives = directive_loader.get_directives_merged(regime)
        for k, v in directives.items():
            if k in _DEFAULTS:
                merged[k] = v
    except Exception as e:
        logger.debug("Directives load failed (using defaults): %s", e)
    try:
        from app.services.settings_service import get_settings_by_category
        stored = get_settings_by_category("council")
        for k, v in stored.items():
            if k in _DEFAULTS and v is not None:
                merged[k] = v
    except Exception:
        pass
    return merged


def get_agent_weight(agent_name: str) -> float:
    """Get the configured weight for a specific agent."""
    cfg = get_agent_thresholds()
    key = f"weight_{agent_name}"
    return float(cfg.get(key, 1.0))
