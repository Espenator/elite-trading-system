"""Critic Agent — post-trade learning signals (skips during pre-trade eval).

GPU Channel 7: Routes LLM inference through brain_client (gRPC to PC2)
for GPU-accelerated postmortem analysis. Falls back to local LLM router
if brain service is unavailable.

Writes postmortem to DuckDB after every post-trade evaluation.
"""
import asyncio
import logging
import os
import uuid
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "critic"
# Critic can tolerate slightly longer timeout than hypothesis (postmortem is background)
_CRITIC_TIMEOUT = float(os.getenv("BRAIN_SERVICE_TIMEOUT", "1.5")) * 2  # 3.0s default


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

    # GPU Channel 7: Route critic LLM inference through brain_client (PC2)
    # Fallback chain: brain_client (PC2 GPU) → local LLM router → Claude deep reasoning → rule-based only
    critic_analysis = ""
    inference_source = "rule_based"
    blackboard = context.get("blackboard")

    # Build rich entry context (shared across all fallback tiers)
    entry_ctx = context.get("entry_context", {})
    if blackboard:
        entry_ctx = {
            **entry_ctx,
            "blackboard_snapshot": blackboard.to_snapshot(),
            "council_decision_id": blackboard.council_decision_id,
        }

    # --- Tier 1: brain_client (PC2 GPU via gRPC) ---
    brain_succeeded = False
    try:
        from app.services.brain_client import get_brain_client
        import json

        client = get_brain_client()
        if client.enabled:
            result = await client.critic(
                trade_id=trade_outcome.get("trade_id", "unknown"),
                symbol=symbol,
                entry_context=json.dumps(entry_ctx, default=str),
                outcome_json=json.dumps(trade_outcome, default=str),
                timeout=_CRITIC_TIMEOUT,
            )
            if not result.get("error"):
                if result.get("lessons"):
                    lessons.extend(result["lessons"][:3])
                if result.get("performance_score", 0) > 0:
                    performance_score = result["performance_score"]
                critic_analysis = result.get("analysis", "")
                inference_source = "brain_pc2"
                brain_succeeded = True
                logger.info(
                    "[critic] LLM: brain_pc2 | score=%.2f | symbol=%s",
                    performance_score, symbol,
                )
            else:
                logger.debug("Brain critic returned error: %s", result.get("error"))
    except Exception as e:
        logger.debug("Critic brain_client unavailable: %s", e)

    # --- Tier 2: Local LLM router (Ollama on localhost) ---
    if not brain_succeeded:
        try:
            import json
            from app.services.llm_router import get_llm_router, Tier

            router = get_llm_router()
            prompt = (
                f"Post-trade analysis for {symbol}:\n"
                f"Direction: {trade_outcome.get('direction', '?')}, "
                f"R-multiple: {r_multiple:.2f}, PnL: ${pnl:,.2f}\n"
                f"Entry context: {json.dumps(entry_ctx, default=str)[:800]}\n\n"
                f"Return JSON: {{\"lessons\": [str], \"performance_score\": 0.0-1.0, "
                f"\"analysis\": str}}"
            )
            result = await router.route_with_fallback(
                tier=Tier.BRAINSTEM,
                messages=[
                    {"role": "system", "content": "You are a trade postmortem analyst. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                task="critic_postmortem",
                temperature=0.2,
                max_tokens=512,
            )
            if not result.error and result.content:
                import re
                parsed = None
                try:
                    parsed = json.loads(result.content.strip())
                except json.JSONDecodeError:
                    match = re.search(r'\{.*\}', result.content, re.DOTALL)
                    if match:
                        try:
                            parsed = json.loads(match.group())
                        except json.JSONDecodeError:
                            pass
                if parsed:
                    if parsed.get("lessons"):
                        lessons.extend(parsed["lessons"][:3])
                    if parsed.get("performance_score", 0) > 0:
                        try:
                            performance_score = float(parsed["performance_score"])
                        except (ValueError, TypeError):
                            pass
                    critic_analysis = parsed.get("analysis", "")
                    inference_source = f"local_llm/{result.tier}"
                    brain_succeeded = True
                    logger.debug("Critic used local LLM router for %s", symbol)
        except Exception as llm_err:
            logger.debug("Critic local LLM router unavailable: %s", llm_err)

    # --- Tier 3: Claude deep reasoning (expensive, last resort) ---
    if not brain_succeeded:
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
                inference_source = "claude_deep"
        except Exception as deep_err:
            logger.debug("Claude deep postmortem not available: %s", deep_err)

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
        await asyncio.to_thread(duckdb_store.insert_postmortem, postmortem)
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
            "inference_source": inference_source,
        },
    )
