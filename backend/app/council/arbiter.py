"""Arbiter — deterministic rules for final council decision.

Rules:
1. VETO from risk_agent or execution_agent → hold, vetoed=True
2. Requires: regime OK + risk OK + strategy OK for any trade
3. Weighted confidence aggregation for direction
4. Hypothesis contributes confidence but cannot override risk veto
5. Final confidence = weighted average of non-vetoing agents
"""
import logging
from typing import Dict, List

from app.council.schemas import AgentVote, DecisionPacket

logger = logging.getLogger(__name__)

# Agents whose approval is required for trading
REQUIRED_AGENTS = {"regime", "risk", "strategy"}
# Agents with veto power
VETO_AGENTS = {"risk", "execution"}


def arbitrate(
    symbol: str,
    timeframe: str,
    timestamp: str,
    votes: List[AgentVote],
) -> DecisionPacket:
    """Apply deterministic arbiter rules to produce final decision.

    Args:
        symbol: Ticker symbol
        timeframe: Timeframe
        timestamp: ISO timestamp
        votes: List of AgentVote from all agents

    Returns:
        DecisionPacket with final decision
    """
    # Collect vetoes
    veto_reasons = []
    for v in votes:
        if v.veto and v.agent_name in VETO_AGENTS:
            veto_reasons.append(f"{v.agent_name}: {v.veto_reason}")

    # If vetoed, decision is hold
    if veto_reasons:
        risk_limits = _extract_risk_limits(votes)
        return DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            votes=votes,
            final_direction="hold",
            final_confidence=0.0,
            vetoed=True,
            veto_reasons=veto_reasons,
            risk_limits=risk_limits,
            execution_ready=False,
            council_reasoning=f"VETOED by: {'; '.join(veto_reasons)}",
        )

    # Check required agents voted non-hold
    required_votes = {v.agent_name: v for v in votes if v.agent_name in REQUIRED_AGENTS}
    missing = REQUIRED_AGENTS - set(required_votes.keys())
    if missing:
        return DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            votes=votes,
            final_direction="hold",
            final_confidence=0.0,
            vetoed=False,
            veto_reasons=[],
            risk_limits=_extract_risk_limits(votes),
            execution_ready=False,
            council_reasoning=f"Missing required agents: {missing}",
        )

    # Load Bayesian self-awareness weights (graceful fallback to static weights)
    effective_weights = {}
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        for v in votes:
            effective_weights[v.agent_name] = sa.get_effective_weight(v.agent_name)
    except Exception as e:
        logger.debug("Self-awareness weights unavailable (%s), using static weights", e)

    # Weighted voting for direction
    buy_weight = 0.0
    sell_weight = 0.0
    hold_weight = 0.0
    total_weight = 0.0

    for v in votes:
        if v.veto:
            continue  # Skip vetoing agents from direction calc
        agent_weight = effective_weights.get(v.agent_name, v.weight)
        w = agent_weight * v.confidence
        total_weight += w
        if v.direction == "buy":
            buy_weight += w
        elif v.direction == "sell":
            sell_weight += w
        else:
            hold_weight += w

    # Determine direction
    if total_weight == 0:
        final_direction = "hold"
        final_confidence = 0.0
    else:
        if buy_weight == sell_weight:
            final_direction = "hold"
            final_confidence = hold_weight / total_weight if hold_weight > 0 else 0.0
        else:
            max_weight = max(buy_weight, sell_weight, hold_weight)
            if max_weight == buy_weight:
                final_direction = "buy"
                final_confidence = buy_weight / total_weight
            elif max_weight == sell_weight:
                final_direction = "sell"
                final_confidence = sell_weight / total_weight
            else:
                final_direction = "hold"
                final_confidence = hold_weight / total_weight

    # Execution readiness
    execution_ready = final_direction != "hold" and final_confidence > 0.4
    exec_vote = next((v for v in votes if v.agent_name == "execution"), None)
    if exec_vote and exec_vote.metadata:
        execution_ready = execution_ready and exec_vote.metadata.get("execution_ready", False)

    risk_limits = _extract_risk_limits(votes)

    # Build reasoning summary
    direction_counts = {"buy": 0, "sell": 0, "hold": 0}
    for v in votes:
        if not v.veto:
            direction_counts[v.direction] = direction_counts.get(v.direction, 0) + 1

    reasoning = (
        f"Council vote: buy={direction_counts['buy']} sell={direction_counts['sell']} "
        f"hold={direction_counts['hold']}. "
        f"Weighted: buy={buy_weight:.2f} sell={sell_weight:.2f} hold={hold_weight:.2f}. "
        f"Decision: {final_direction.upper()} @ {final_confidence:.0%} confidence."
    )

    return DecisionPacket(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        votes=votes,
        final_direction=final_direction,
        final_confidence=round(final_confidence, 4),
        vetoed=False,
        veto_reasons=[],
        risk_limits=risk_limits,
        execution_ready=execution_ready,
        council_reasoning=reasoning,
    )


def _extract_risk_limits(votes: List[AgentVote]) -> Dict:
    """Extract risk limits from agent metadata."""
    for v in votes:
        if v.agent_name == "risk" and v.metadata:
            return v.metadata.get("risk_limits", {})
    return {}
