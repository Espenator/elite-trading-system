"""Critic Agent — post-trade learning signals (skips during pre-trade eval).

Writes postmortem to DuckDB after every post-trade evaluation.
"""
import logging
import uuid
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "critic"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Produce learning signals from past trades.

    During pre-trade evaluation: returns neutral vote.
    Post-trade: analyzes outcomes and produces critic feedback, writes postmortem to DuckDB.
    """
    cfg = get_agent_thresholds()

    # Check if this is a post-trade evaluation
    is_post_trade = context.get("post_trade", False)

    if not is_post_trade:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="Pre-trade eval — critic skips (learning signals only post-trade)",
            weight=cfg["weight_critic"],
            metadata={"post_trade": False},
        )

    # Post-trade critic analysis
    trade_outcome = context.get("trade_outcome", {})
    r_multiple = trade_outcome.get("r_multiple", 0)
    pnl = trade_outcome.get("pnl", 0)

    lessons = []
    performance_score = 0.5

    if r_multiple > cfg["critic_excellent_r"]:
        lessons.append("Excellent R-multiple — strategy working well")
        performance_score = 0.9
    elif r_multiple > cfg["critic_good_r"]:
        lessons.append("Positive R-multiple — acceptable trade")
        performance_score = 0.7
    elif r_multiple > 0:
        lessons.append("Small gain — consider tighter entry criteria")
        performance_score = 0.5
    elif r_multiple > cfg["critic_small_loss_r"]:
        lessons.append("Small loss within risk bounds — acceptable")
        performance_score = 0.3
    else:
        lessons.append("Large loss — review entry conditions and stop placement")
        performance_score = 0.1

    # Try brain service for deeper analysis (sends blackboard + outcome)
    critic_analysis = ""
    blackboard = context.get("blackboard")
    try:
        from app.services.brain_client import get_brain_client
        import json

        client = get_brain_client()
        if client.enabled:
            # Build rich entry context from blackboard
            entry_ctx = context.get("entry_context", {})
            if blackboard:
                entry_ctx = {
                    **entry_ctx,
                    "blackboard_snapshot": blackboard.to_snapshot(),
                    "council_decision_id": blackboard.council_decision_id,
                }

            result = await client.critic(
                trade_id=trade_outcome.get("trade_id", "unknown"),
                symbol=symbol,
                entry_context=json.dumps(entry_ctx, default=str),
                outcome_json=json.dumps(trade_outcome, default=str),
            )
            if result.get("lessons"):
                lessons.extend(result["lessons"][:3])
            if result.get("performance_score", 0) > 0:
                performance_score = result["performance_score"]
            critic_analysis = result.get("analysis", "")
        else:
            # Fallback: try Claude deep reasoning for postmortem
            try:
                from app.services.claude_reasoning import get_claude_reasoning
                reasoning_svc = get_claude_reasoning()
                agent_votes = context.get("all_votes", [])
                market_ctx = {}
                if blackboard:
                    market_ctx = blackboard.to_snapshot()
                deep_result = await reasoning_svc.deep_postmortem(
                    trade=trade_outcome,
                    market_context=market_ctx,
                    agent_votes=agent_votes,
                )
                if not deep_result.get("error"):
                    data = deep_result.get("data", {})
                    if data.get("lessons"):
                        lessons.extend([l["lesson"] for l in data["lessons"][:3] if isinstance(l, dict)])
                    if data.get("overall_score") is not None:
                        try:
                            performance_score = float(data["overall_score"]) / 100
                        except (ValueError, TypeError):
                            pass
                    critic_analysis = data.get("key_takeaway", "")
            except Exception as deep_err:
                logger.debug("Claude deep postmortem not available: %s", deep_err)
    except Exception as e:
        logger.debug("Critic brain analysis not available: %s", e)

    # Write postmortem to DuckDB
    try:
        from app.data.duckdb_storage import duckdb_store
        postmortem = {
            "id": str(uuid.uuid4()),
            "council_decision_id": blackboard.council_decision_id if blackboard else "",
            "symbol": symbol,
            "direction": trade_outcome.get("direction", ""),
            "confidence": trade_outcome.get("confidence", 0.0),
            "entry_price": trade_outcome.get("entry_price", 0.0),
            "exit_price": trade_outcome.get("exit_price", 0.0),
            "pnl": pnl,
            "agent_votes": context.get("all_votes", []),
            "blackboard_snapshot": blackboard.to_snapshot() if blackboard else {},
            "critic_analysis": critic_analysis or "; ".join(lessons[:3]),
        }
        duckdb_store.insert_postmortem(postmortem)
        logger.info("Postmortem written for %s: R=%.2f, PnL=$%.2f", symbol, r_multiple, pnl)
    except Exception as e:
        logger.debug("Postmortem write failed: %s", e)

    return AgentVote(
        agent_name=NAME,
        direction="hold",
        confidence=round(performance_score, 2),
        reasoning=f"Post-trade critic: R={r_multiple:.2f}, PnL=${pnl:,.2f}. " + "; ".join(lessons[:3]),
        weight=cfg["weight_critic"],
        metadata={
            "post_trade": True,
            "r_multiple": r_multiple,
            "lessons": lessons,
            "performance_score": performance_score,
        },
    )
