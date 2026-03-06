"""Strategy Agent — enforces playbook constraints with symmetric long/short analysis."""
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "strategy"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Enforce playbook constraints with dual-track bull/bear scoring.

    Uses separate bull_checks and bear_checks counters so that bearish
    indicators (overbought RSI, MACD bearish crossover, downtrend) can
    generate short votes with equal confidence as long votes.
    """
    cfg = get_agent_thresholds()
    f = features.get("features", features)

    bull_checks = 0
    bear_checks = 0
    checks_total = 0
    reasons = []

    # RSI check — symmetric
    rsi = f.get("ind_rsi_14", 0)
    if rsi > 0:
        checks_total += 1
        if cfg["rsi_oversold"] < rsi < cfg["rsi_overbought"]:
            bull_checks += 1
            bear_checks += 1
            reasons.append(f"RSI={rsi:.0f} (neutral zone)")
        elif rsi <= cfg["rsi_oversold"]:
            bull_checks += 1
            reasons.append(f"RSI={rsi:.0f} (oversold → buy bias)")
        else:  # rsi >= overbought
            bear_checks += 1
            reasons.append(f"RSI={rsi:.0f} (overbought → sell bias)")

    # MACD check — symmetric
    macd = f.get("ind_macd", 0)
    macd_signal = f.get("ind_macd_signal", 0)
    if macd != 0 or macd_signal != 0:
        checks_total += 1
        if macd > macd_signal:
            bull_checks += 1
            reasons.append("MACD bullish crossover")
        else:
            bear_checks += 1
            reasons.append("MACD bearish crossover")

    # Moving average trend — symmetric
    sma_20 = f.get("ind_sma_20", 0)
    sma_50 = f.get("ind_sma_50", 0)
    last_close = f.get("last_close", 0)
    if sma_20 > 0 and sma_50 > 0 and last_close > 0:
        checks_total += 1
        if last_close > sma_20 > sma_50:
            bull_checks += 1
            reasons.append("Price > SMA20 > SMA50 (uptrend)")
        elif last_close < sma_20 < sma_50:
            bear_checks += 1
            reasons.append("Price < SMA20 < SMA50 (downtrend)")
        else:
            reasons.append("Mixed MA alignment")

    # ADX trend strength — direction-neutral (boosts both)
    adx = f.get("ind_adx_14", 0)
    if adx > 0:
        checks_total += 1
        if adx > cfg["adx_trending_threshold"]:
            bull_checks += 1
            bear_checks += 1
            reasons.append(f"ADX={adx:.0f} (trending)")
        else:
            reasons.append(f"ADX={adx:.0f} (no trend)")

    # Determine direction based on dual-track checks
    if checks_total == 0:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.3,
            reasoning="Insufficient indicator data for strategy assessment",
            weight=cfg["weight_strategy"],
        )

    bull_rate = bull_checks / checks_total
    bear_rate = bear_checks / checks_total

    if bull_rate >= cfg["strategy_buy_pass_rate"] and bull_rate > bear_rate:
        direction = "buy"
        confidence = 0.4 + bull_rate * 0.4
    elif bear_rate >= cfg["strategy_sell_pass_rate"] and bear_rate > bull_rate:
        direction = "sell"
        confidence = 0.4 + bear_rate * 0.4
    else:
        direction = "hold"
        confidence = 0.4

    # Load regime directives for bias adjustment — symmetric
    regime_bias = "NEUTRAL"
    try:
        from app.council.directives.loader import directive_loader
        regime = str(f.get("regime", "unknown")).lower()
        regime_bias = directive_loader.get_regime_bias(regime)
        if regime_bias == "DEFENSIVE" and direction == "buy":
            confidence *= 0.8
            reasons.append(f"Regime bias={regime_bias} (reduced buy confidence)")
        elif regime_bias == "DEFENSIVE" and direction == "sell":
            confidence *= 1.15  # Boost shorts in defensive regime
            reasons.append(f"Regime bias={regime_bias} (boosted sell confidence)")
        elif regime_bias == "LONG" and direction == "sell":
            confidence *= 0.85
            reasons.append(f"Regime bias={regime_bias} (reduced sell confidence)")
        elif regime_bias == "LONG" and direction == "buy":
            confidence *= 1.10  # Boost longs in bullish regime
            reasons.append(f"Regime bias={regime_bias} (boosted buy confidence)")
    except Exception:
        pass

    # Factor in Stage 1 social/news perception consensus
    blackboard = context.get("blackboard")
    if blackboard:
        social = blackboard.metadata.get("social_sentiment")
        news_cat = blackboard.metadata.get("news_catalysts")

        social_agrees = social and social.get("direction") == direction
        news_agrees = news_cat and news_cat.get("direction") == direction

        if social_agrees and news_agrees:
            confidence = min(0.9, confidence + 0.08)
            reasons.append("Social + News confirm direction")
        elif social_agrees or news_agrees:
            confidence = min(0.9, confidence + 0.04)
            which = "Social" if social_agrees else "News"
            reasons.append(f"{which} confirms direction")

        if social and social.get("spike") and social.get("direction") != direction and direction != "hold":
            confidence *= 0.85
            reasons.append(f"Social spike opposes ({social.get('direction')})")

    reasoning = (
        f"Strategy checks: bull={bull_checks}/{checks_total}, "
        f"bear={bear_checks}/{checks_total}. " + "; ".join(reasons[:5])
    )

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning=reasoning,
        weight=cfg["weight_strategy"],
        metadata={
            "bull_checks": bull_checks,
            "bear_checks": bear_checks,
            "checks_total": checks_total,
            "regime_bias": regime_bias,
        },
    )
