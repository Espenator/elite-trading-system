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


# ── Session-Aware Threshold Adjustments ──────────────────────────────
# Outside regular hours, raise the council gate threshold to require
# stronger signals before entering trades (lower liquidity = higher bar).

_SESSION_THRESHOLD_ADJUSTMENTS = {
    "regular": 0,       # No adjustment — full liquidity
    "pre_market": 5,    # +5 points — thinner book
    "after_hours": 5,   # +5 points — thinner book
    "overnight": 10,    # +10 points — minimal liquidity, require strong conviction
    "weekend": 100,     # Effectively blocks trading (added to 80 = 180, unreachable)
}


def get_session_threshold_adjustment() -> int:
    """Return the threshold adjustment (points) for the current session.

    Added to the base council gate threshold to make it harder to enter
    trades during low-liquidity sessions.

    Returns:
        Integer points to add to gate threshold.
        REGULAR=+0, PRE_MARKET=+5, AFTER_HOURS=+5, OVERNIGHT=+10, WEEKEND=+100
    """
    try:
        from app.services.data_swarm.session_clock import get_session_clock
        session = get_session_clock().get_current_session()
        return _SESSION_THRESHOLD_ADJUSTMENTS.get(session.value, 0)
    except Exception:
        return 0  # Safe default: no adjustment


# Session-specific data staleness thresholds (seconds)
# Wider thresholds in low-liquidity sessions where data updates are less frequent
_SESSION_STALENESS_THRESHOLDS = {
    "regular": 120,       # 2 min — tight, bars arrive every 60s
    "pre_market": 300,    # 5 min — snapshot polling every 30s
    "after_hours": 300,   # 5 min — snapshot polling every 30s
    "overnight": 600,     # 10 min — snapshot polling every 60s
    "weekend": 3600,      # 1 hour — no live data expected
}


def get_session_staleness_threshold() -> int:
    """Return session-appropriate data staleness threshold in seconds.

    Used by the health monitor and signal engine to decide when data
    is too old to act on. Wider thresholds during low-liquidity sessions.

    Returns:
        Staleness threshold in seconds.
    """
    try:
        from app.services.data_swarm.session_clock import get_session_clock
        session = get_session_clock().get_current_session()
        return _SESSION_STALENESS_THRESHOLDS.get(session.value, 300)
    except Exception:
        return 300  # Safe default: 5 min
