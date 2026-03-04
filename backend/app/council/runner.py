"""Council Runner — orchestrates the 8-agent DAG and arbiter.

DAG execution order (parallel within stages):
  Stage 1: [market_perception, flow_perception, regime]
  Stage 2: [hypothesis]
  Stage 3: [strategy]
  Stage 4: [risk, execution]
  Stage 5: [critic]
  Stage 6: arbiter (deterministic)
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate

logger = logging.getLogger(__name__)


async def _run_agent(module, symbol, timeframe, features, context) -> AgentVote:
    """Run a single agent with error handling."""
    try:
        return await module.evaluate(symbol, timeframe, features, context)
    except Exception as e:
        name = getattr(module, "NAME", module.__name__)
        logger.exception("Agent %s failed: %s", name, e)
        return AgentVote(
            agent_name=name,
            direction="hold",
            confidence=0.0,
            reasoning=f"Agent error: {e}",
        )


async def run_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DecisionPacket:
    """Run the full 8-agent council and return a DecisionPacket.

    Args:
        symbol: Ticker symbol to evaluate
        timeframe: Timeframe (default "1d")
        features: Pre-computed feature dict. If None, auto-computes.
        context: Additional context for agents

    Returns:
        DecisionPacket with all votes and final decision
    """
    if context is None:
        context = {}

    # Auto-compute features if not provided
    if features is None:
        try:
            from app.features.feature_aggregator import aggregate
            fv = await aggregate(symbol, timeframe=timeframe)
            features = fv.to_dict()
        except Exception as e:
            logger.warning("Feature aggregation failed for %s: %s", symbol, e)
            features = {"features": {}, "symbol": symbol}

    timestamp = datetime.now(timezone.utc).isoformat()

    # Import all agents
    from app.council.agents import (
        market_perception_agent,
        flow_perception_agent,
        regime_agent,
        hypothesis_agent,
        strategy_agent,
        risk_agent,
        execution_agent,
        critic_agent,
    )

    all_votes: List[AgentVote] = []

    # Stage 1: Perception (parallel)
    stage1 = await asyncio.gather(
        _run_agent(market_perception_agent, symbol, timeframe, features, context),
        _run_agent(flow_perception_agent, symbol, timeframe, features, context),
        _run_agent(regime_agent, symbol, timeframe, features, context),
    )
    all_votes.extend(stage1)
    context["stage1"] = {v.agent_name: v.to_dict() for v in stage1}

    # Stage 2: Hypothesis
    stage2 = await _run_agent(hypothesis_agent, symbol, timeframe, features, context)
    all_votes.append(stage2)
    context["stage2"] = {stage2.agent_name: stage2.to_dict()}

    # Stage 3: Strategy
    stage3 = await _run_agent(strategy_agent, symbol, timeframe, features, context)
    all_votes.append(stage3)
    context["stage3"] = {stage3.agent_name: stage3.to_dict()}

    # Stage 4: Risk + Execution (parallel)
    stage4 = await asyncio.gather(
        _run_agent(risk_agent, symbol, timeframe, features, context),
        _run_agent(execution_agent, symbol, timeframe, features, context),
    )
    all_votes.extend(stage4)
    context["stage4"] = {v.agent_name: v.to_dict() for v in stage4}

    # Stage 5: Critic
    stage5 = await _run_agent(critic_agent, symbol, timeframe, features, context)
    all_votes.append(stage5)
    context["stage5"] = {stage5.agent_name: stage5.to_dict()}

    # Stage 6: Arbiter
    decision = arbitrate(symbol, timeframe, timestamp, all_votes)

    logger.info(
        "Council decision for %s: %s @ %.0f%% confidence (vetoed=%s, agents=%d)",
        symbol,
        decision.final_direction.upper(),
        decision.final_confidence * 100,
        decision.vetoed,
        len(all_votes),
    )

    # Record decision in feedback loop for learning
    try:
        from app.council.feedback_loop import record_decision
        record_decision(
            symbol=symbol,
            final_direction=decision.final_direction,
            votes=[v.to_dict() for v in all_votes],
            trade_id=context.get("trade_id"),
        )
    except Exception as e:
        logger.debug("Feedback loop record failed: %s", e)

    # Publish to message bus if available
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        if bus._running:
            await bus.publish("council.verdict", decision.to_dict())
    except Exception:
        pass

    return decision
