"""Council Runner -- orchestrates the 13-agent DAG and arbiter.

DAG execution order (parallel within stages):
  Stage 1: [market_perception, flow_perception, regime, intermarket]
    Stage 2: [rsi, bbv, ema_trend, relative_strength, cycle_timing]
      Stage 3: [hypothesis]
        Stage 4: [strategy]
          Stage 5: [risk, execution]
            Stage 6: [critic]
              Stage 7: arbiter (deterministic)
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
    """Run the full 13-agent council and return a DecisionPacket.

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

    # Import all agents (original 8)
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

    # Import new smarttrading.club-inspired agents (5)
    from app.council.agents import (
        rsi_agent,
        bbv_agent,
        ema_trend_agent,
        intermarket_agent,
        relative_strength_agent,
        cycle_timing_agent,
    )

    all_votes: List[AgentVote] = []

    # Stage 1: Perception + Intermarket (parallel)
    stage1 = await asyncio.gather(
        _run_agent(market_perception_agent, symbol, timeframe, features, context),
        _run_agent(flow_perception_agent, symbol, timeframe, features, context),
        _run_agent(regime_agent, symbol, timeframe, features, context),
        _run_agent(intermarket_agent, symbol, timeframe, features, context),
    )
    all_votes.extend(stage1)

    # Stage 2: Technical analysis agents (parallel)
    stage2 = await asyncio.gather(
        _run_agent(rsi_agent, symbol, timeframe, features, context),
        _run_agent(bbv_agent, symbol, timeframe, features, context),
        _run_agent(ema_trend_agent, symbol, timeframe, features, context),
        _run_agent(relative_strength_agent, symbol, timeframe, features, context),
        _run_agent(cycle_timing_agent, symbol, timeframe, features, context),
    )
    all_votes.extend(stage2)

    # Stage 3: Hypothesis
    stage3 = await _run_agent(hypothesis_agent, symbol, timeframe, features, context)
    all_votes.append(stage3)

    # Stage 4: Strategy
    stage4 = await _run_agent(strategy_agent, symbol, timeframe, features, context)
    all_votes.append(stage4)

    # Stage 5: Risk + Execution (parallel)
    stage5 = await asyncio.gather(
        _run_agent(risk_agent, symbol, timeframe, features, context),
        _run_agent(execution_agent, symbol, timeframe, features, context),
    )
    all_votes.extend(stage5)

    # Stage 6: Critic
    stage6 = await _run_agent(critic_agent, symbol, timeframe, features, context)
    all_votes.append(stage6)

    # Stage 7: Arbiter
    decision = arbitrate(symbol, timeframe, timestamp, all_votes)

    logger.info(
        "Council decision for %s: %s @ %.0f%% confidence (vetoed=%s, agents=%d)",
        symbol,
        decision.final_direction.upper(),
        decision.final_confidence * 100,
        decision.vetoed,
        len(all_votes),
    )

    # Publish to message bus if available
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        if bus._running:
            await bus.publish("council.verdict", decision.to_dict())
    except Exception:
        pass

    return decision
