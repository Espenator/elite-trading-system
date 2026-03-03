"""Critic Agent — post-trade learning signals (skips during pre-trade eval)."""
import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "critic"
WEIGHT = 0.5  # Low weight — critic is for learning, not trading decisions


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Produce learning signals from past trades.

    During pre-trade evaluation: returns neutral vote.
    Post-trade: analyzes outcomes and produces critic feedback.
    """
    # Check if this is a post-trade evaluation
    is_post_trade = context.get("post_trade", False)

    if not is_post_trade:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="Pre-trade eval — critic skips (learning signals only post-trade)",
            weight=WEIGHT,
            metadata={"post_trade": False},
        )

    # Post-trade critic analysis
    trade_outcome = context.get("trade_outcome", {})
    r_multiple = trade_outcome.get("r_multiple", 0)
    pnl = trade_outcome.get("pnl", 0)

    lessons = []
    performance_score = 0.5

    if r_multiple > 2.0:
        lessons.append("Excellent R-multiple — strategy working well")
        performance_score = 0.9
    elif r_multiple > 1.0:
        lessons.append("Positive R-multiple — acceptable trade")
        performance_score = 0.7
    elif r_multiple > 0:
        lessons.append("Small gain — consider tighter entry criteria")
        performance_score = 0.5
    elif r_multiple > -1.0:
        lessons.append("Small loss within risk bounds — acceptable")
        performance_score = 0.3
    else:
        lessons.append("Large loss — review entry conditions and stop placement")
        performance_score = 0.1

    # Try brain service for deeper analysis
    try:
        from app.services.brain_client import get_brain_client
        import json

        client = get_brain_client()
        if client.enabled:
            result = await client.critic(
                trade_id=trade_outcome.get("trade_id", "unknown"),
                symbol=symbol,
                entry_context=json.dumps(context.get("entry_context", {}), default=str),
                outcome_json=json.dumps(trade_outcome, default=str),
            )
            if result.get("lessons"):
                lessons.extend(result["lessons"][:3])
            if result.get("performance_score", 0) > 0:
                performance_score = result["performance_score"]
    except Exception as e:
        logger.debug("Critic brain analysis not available: %s", e)

    return AgentVote(
        agent_name=NAME,
        direction="hold",
        confidence=round(performance_score, 2),
        reasoning=f"Post-trade critic: R={r_multiple:.2f}, PnL=${pnl:,.2f}. " + "; ".join(lessons[:3]),
        weight=WEIGHT,
        metadata={
            "post_trade": True,
            "r_multiple": r_multiple,
            "lessons": lessons,
            "performance_score": performance_score,
        },
    )
