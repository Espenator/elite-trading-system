"""Hypothesis Agent — LLM-powered hypothesis via Brain Service."""
import json
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "hypothesis"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Call brain_client for LLM inference when enabled; otherwise stub."""
    cfg = get_agent_thresholds()

    try:
        from app.services.brain_client import get_brain_client

        client = get_brain_client()
        if not client.enabled:
            return AgentVote(
                agent_name=NAME,
                direction="hold",
                confidence=0.1,
                reasoning="Brain service disabled — no LLM hypothesis",
                weight=cfg["weight_hypothesis"],
                metadata={"brain_enabled": False},
            )

        feature_json = json.dumps(features.get("features", features), default=str)
        regime = str(features.get("features", {}).get("regime", "unknown"))

        # Load trading directives for current regime
        directives_text = ""
        try:
            from app.council.directives.loader import directive_loader
            directives_text = directive_loader.load(regime)
        except Exception:
            pass

        # Build rich context from blackboard (perceptions + regime + features + directives)
        blackboard = context.get("blackboard")
        if blackboard:
            brain_context = json.dumps({
                "perceptions": blackboard.perceptions,
                "regime": regime,
                "council_decision_id": blackboard.council_decision_id,
                "stage1_votes": context.get("stage1", {}),
                "directives": directives_text[:2000] if directives_text else "",
            }, default=str)
        else:
            brain_context = json.dumps(context, default=str) if context else ""

        result = await client.infer(
            symbol=symbol,
            timeframe=timeframe,
            feature_json=feature_json,
            regime=regime,
            context=brain_context,
        )

        # Map LLM confidence to direction
        llm_conf = result.get("confidence", 0.5)
        risk_flags = result.get("risk_flags", [])

        if "llm_unavailable" in risk_flags or "brain_disabled" in risk_flags:
            return AgentVote(
                agent_name=NAME,
                direction="hold",
                confidence=0.1,
                reasoning=result.get("summary", "LLM unavailable"),
                weight=cfg["weight_hypothesis"],
                metadata={"brain_enabled": True, "error": result.get("error", "")},
            )

        if llm_conf > cfg["llm_buy_confidence_threshold"]:
            direction = "buy"
        elif llm_conf < cfg["llm_sell_confidence_threshold"]:
            direction = "sell"
        else:
            direction = "hold"

        reasoning = result.get("summary", "No summary")
        bullets = result.get("reasoning_bullets", [])
        if bullets:
            reasoning += " | " + "; ".join(bullets[:3])

        return AgentVote(
            agent_name=NAME,
            direction=direction,
            confidence=round(llm_conf, 2),
            reasoning=reasoning,
            weight=cfg["weight_hypothesis"],
            metadata={
                "brain_enabled": True,
                "risk_flags": risk_flags,
            },
        )

    except Exception as e:
        logger.warning("Hypothesis agent error: %s", e)
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning=f"Hypothesis error: {e}",
            weight=cfg["weight_hypothesis"],
        )
