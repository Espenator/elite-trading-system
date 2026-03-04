"""Strategy Agent — enforces playbook constraints."""
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "strategy"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Enforce playbook constraints — do not invent entries.

    Checks:
    - Signal alignment (if existing signals present)
    - RSI/MACD confirmation
    - Trend alignment via moving averages
    """
    cfg = get_agent_thresholds()
    f = features.get("features", features)

    checks_passed = 0
    checks_total = 0
    reasons = []

    # RSI check
    rsi = f.get("ind_rsi_14", 0)
    if rsi > 0:
        checks_total += 1
        if cfg["rsi_oversold"] < rsi < cfg["rsi_overbought"]:
            checks_passed += 1
            reasons.append(f"RSI={rsi:.0f} (neutral zone)")
        elif rsi <= cfg["rsi_oversold"]:
            checks_passed += 1
            reasons.append(f"RSI={rsi:.0f} (oversold → buy bias)")
        else:
            reasons.append(f"RSI={rsi:.0f} (overbought → caution)")

    # MACD check
    macd = f.get("ind_macd", 0)
    macd_signal = f.get("ind_macd_signal", 0)
    if macd != 0 or macd_signal != 0:
        checks_total += 1
        if macd > macd_signal:
            checks_passed += 1
            reasons.append("MACD bullish crossover")
        else:
            reasons.append("MACD bearish")

    # Moving average trend
    sma_20 = f.get("ind_sma_20", 0)
    sma_50 = f.get("ind_sma_50", 0)
    last_close = f.get("last_close", 0)
    if sma_20 > 0 and sma_50 > 0 and last_close > 0:
        checks_total += 1
        if last_close > sma_20 > sma_50:
            checks_passed += 1
            reasons.append("Price > SMA20 > SMA50 (uptrend)")
        elif last_close < sma_20 < sma_50:
            reasons.append("Price < SMA20 < SMA50 (downtrend)")
        else:
            reasons.append("Mixed MA alignment")

    # ADX trend strength
    adx = f.get("ind_adx_14", 0)
    if adx > 0:
        checks_total += 1
        if adx > cfg["adx_trending_threshold"]:
            checks_passed += 1
            reasons.append(f"ADX={adx:.0f} (trending)")
        else:
            reasons.append(f"ADX={adx:.0f} (no trend)")

    # Determine direction based on checks
    if checks_total == 0:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.3,
            reasoning="Insufficient indicator data for strategy assessment",
            weight=cfg["weight_strategy"],
        )

    pass_rate = checks_passed / checks_total
    if pass_rate >= cfg["strategy_buy_pass_rate"]:
        direction = "buy"
        confidence = 0.4 + pass_rate * 0.4
    elif pass_rate <= cfg["strategy_sell_pass_rate"]:
        direction = "sell"
        confidence = 0.4 + (1 - pass_rate) * 0.3
    else:
        direction = "hold"
        confidence = 0.4

    reasoning = f"Strategy checks: {checks_passed}/{checks_total} passed. " + "; ".join(reasons[:4])

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning=reasoning,
        weight=cfg["weight_strategy"],
        metadata={"checks_passed": checks_passed, "checks_total": checks_total},
    )
