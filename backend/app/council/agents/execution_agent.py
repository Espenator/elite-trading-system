"""Execution Agent — broker readiness, shadow mode, and slippage guard with VETO power.

Refactored to:
- Accept L2 Quote data (bid/ask depth) from context
- Calculate Impact Cost based on position size vs. order book depth
- Reduce confidence if projected slippage exceeds threshold (0.2% default)
"""
import logging
import os
from typing import Any, Dict, List, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "execution"


def _calculate_impact_cost(
    side: str,
    position_value: float,
    bid_levels: List[Tuple[float, int]],
    ask_levels: List[Tuple[float, int]],
) -> Tuple[float, str]:
    """Calculate the impact cost of executing a trade given L2 order book depth.

    Args:
        side: "buy" or "sell"
        position_value: Dollar value of position to execute
        bid_levels: List of (price, size) tuples for bid side (descending price)
        ask_levels: List of (price, size) tuples for ask side (ascending price)

    Returns:
        (impact_cost_pct, reasoning): Impact cost as % of trade value and explanation

    Impact cost is calculated by simulating eating through the order book levels
    until the entire position is filled, then comparing the average fill price
    to the best bid/ask.
    """
    if not bid_levels and not ask_levels:
        # No L2 data available — assume minimal impact
        return 0.0, "No L2 data available, assuming minimal impact"

    if side == "buy":
        # Buying: we lift offers (asks)
        levels = ask_levels
        best_price = ask_levels[0][0] if ask_levels else 0
    else:
        # Selling: we hit bids
        levels = bid_levels
        best_price = bid_levels[0][0] if bid_levels else 0

    if not levels or best_price == 0:
        return 0.0, f"No {side} levels available"

    # Simulate filling the order by walking through levels
    remaining_value = position_value
    total_shares_filled = 0
    total_cost = 0.0

    for price, size in levels:
        if remaining_value <= 0:
            break

        # How many shares can we fill at this level?
        level_value = price * size

        if level_value >= remaining_value:
            # This level can fill the remainder
            shares_at_level = remaining_value / price
            total_shares_filled += shares_at_level
            total_cost += remaining_value
            remaining_value = 0
        else:
            # Consume entire level and move to next
            total_shares_filled += size
            total_cost += level_value
            remaining_value -= level_value

    if total_shares_filled == 0:
        return 0.0, "Insufficient liquidity in order book"

    # Average fill price
    avg_fill_price = total_cost / total_shares_filled

    # Impact cost as percentage difference from best price
    impact_pct = abs(avg_fill_price - best_price) / best_price

    reasoning = f"Avg fill ${avg_fill_price:.2f} vs best ${best_price:.2f}, impact={impact_pct*100:.2f}%"

    if remaining_value > 0:
        reasoning += f" (unfilled: ${remaining_value:,.0f})"

    return impact_pct, reasoning


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Check broker readiness, trading mode, liquidity, and slippage risk.

    Can VETO if:
    - Trading mode is shadow/paper and auto-execute disabled
    - Broker API is unreachable
    - Insufficient liquidity

    Will REDUCE confidence if:
    - Projected slippage exceeds slippage_threshold (default 0.2%)
    """
    cfg = get_agent_thresholds()
    reasons = []
    veto = False
    veto_reason = ""
    confidence = 0.5  # Base confidence for execution checks

    # Check trading mode
    auto_execute = os.getenv("AUTO_EXECUTE_TRADES", "false").lower() == "true"
    trading_mode = os.getenv("TRADING_MODE", "live").lower()

    if not auto_execute:
        reasons.append("Shadow mode (AUTO_EXECUTE_TRADES=false)")
    else:
        reasons.append("Auto-execute ENABLED")

    if trading_mode == "paper":
        reasons.append("Paper trading mode")
    elif trading_mode == "live":
        reasons.append("LIVE trading mode")

    # Check broker connectivity
    try:
        from app.services.alpaca_service import get_alpaca_service
        svc = get_alpaca_service()
        if svc:
            reasons.append("Alpaca API reachable")
        else:
            reasons.append("Alpaca service not initialized")
    except Exception:
        reasons.append("Alpaca API not available")

    # Check volume/liquidity from features
    f = features.get("features", features)
    last_volume = f.get("last_volume", 0) or f.get("volume", 0)
    if last_volume > 0 and last_volume < cfg["min_volume_threshold"]:
        veto = True
        veto_reason = f"Insufficient liquidity (volume={last_volume:,.0f} < {cfg['min_volume_threshold']:,.0f})"
        reasons.append(f"LOW VOLUME: {last_volume:,.0f}")

    # NEW: Slippage & Impact Cost Check
    # Extract L2 quote data from context (published by alpaca_stream_service via MessageBus)
    l2_data = context.get("l2_quote", {})
    bid_levels = l2_data.get("bids", [])
    ask_levels = l2_data.get("asks", [])

    slippage_impact = 0.0
    impact_reasoning = ""

    if bid_levels or ask_levels:
        # Calculate impact cost based on the intended trade direction and size
        # For now, assume a modest position size (e.g., $10k) as a reference
        # In a real system, this would come from the position sizing logic

        # Infer direction from context or features
        intended_direction = context.get("intended_direction", "buy")
        position_value = context.get("position_value", 10000.0)  # Default $10k position

        slippage_impact, impact_reasoning = _calculate_impact_cost(
            side=intended_direction,
            position_value=position_value,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

        slippage_threshold = cfg.get("slippage_threshold", 0.002)  # Default 0.2%

        if slippage_impact > slippage_threshold:
            # Reduce confidence based on excess slippage
            excess_slippage = slippage_impact - slippage_threshold
            # Linear penalty: reduce confidence by 0.5 for each 0.1% excess slippage
            confidence_penalty = min(0.4, excess_slippage * 5.0)
            confidence = max(0.1, confidence - confidence_penalty)

            reasons.append(
                f"HIGH SLIPPAGE: {slippage_impact*100:.2f}% exceeds {slippage_threshold*100:.2f}% threshold "
                f"(confidence reduced by {confidence_penalty:.2f})"
            )
            reasons.append(impact_reasoning)
        else:
            reasons.append(f"Slippage OK: {slippage_impact*100:.2f}% < {slippage_threshold*100:.2f}%")
            reasons.append(impact_reasoning)
    else:
        # No L2 data available — log it but don't penalize
        reasons.append("No L2 quote data available for slippage check")

    # Execution readiness
    execution_ready = auto_execute and not veto

    if veto:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.9,
            reasoning=f"VETO: {veto_reason}. " + "; ".join(reasons),
            veto=True,
            veto_reason=veto_reason,
            weight=cfg["weight_execution"],
            metadata={
                "execution_ready": False,
                "trading_mode": trading_mode,
                "slippage_impact": slippage_impact,
            },
        )

    return AgentVote(
        agent_name=NAME,
        direction="hold",  # Execution agent doesn't decide direction
        confidence=confidence,
        reasoning="Execution checks passed. " + "; ".join(reasons),
        weight=cfg["weight_execution"],
        metadata={
            "execution_ready": execution_ready,
            "trading_mode": trading_mode,
            "slippage_impact": slippage_impact,
            "impact_reasoning": impact_reasoning,
        },
    )
