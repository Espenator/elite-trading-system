"""Arbiter — deterministic rules for final council decision.

Uses Bayesian-updated weights from WeightLearner (self-learning).
Falls back to static agent weights if learner is unavailable.

Rules:
1. VETO from risk_agent or execution_agent -> hold, vetoed=True
2. Requires: regime, risk, strategy must be present AND must not oppose
   the winning direction for the trade to be executable
3. Weighted confidence aggregation for direction (Bayesian weights)
4. Hypothesis contributes confidence but cannot override risk veto
5. Final confidence = weighted average of non-vetoing agents
6. Tie/deadlock between buy and sell yields a safe hold with explicit reasoning
"""
import logging
from typing import Dict, List

from app.council.schemas import AgentVote, DecisionPacket

logger = logging.getLogger(__name__)

# Agents whose approval is required for trading
REQUIRED_AGENTS = {"regime", "risk", "strategy"}

# Agents with veto power
VETO_AGENTS = {"risk", "execution"}


def _get_learned_weights() -> Dict[str, float]:
    """Fetch Bayesian-updated weights from WeightLearner.

    Returns empty dict if learner is unavailable (arbiter will use
    each agent's static weight from their module-level WEIGHT constant).
    """
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        return learner.get_weights()
    except Exception:
        return {}


def arbitrate(
    symbol: str,
    timeframe: str,
    timestamp: str,
    votes: List[AgentVote],
) -> DecisionPacket:
    """Apply deterministic arbiter rules to produce final decision.

    Uses Bayesian-learned weights when available, otherwise falls back
    to each agent's static WEIGHT constant.

    Rules applied in order:
    1. Veto check: risk or execution agent veto → hold, vetoed=True
    2. Required agent presence: regime, risk, strategy must all vote
    3. Weighted voting: Bayesian-weighted sum for buy/sell/hold
    4. Tie/deadlock: equal buy and sell weight → hold with explicit reasoning
    5. Required agent alignment: regime, risk, strategy must not oppose
       the winning direction for the trade to be marked executable
    6. Execution readiness: direction ≠ hold, confidence > 0.4,
       execution agent approval, and required agents aligned

    Args:
        symbol: Ticker symbol
        timeframe: Timeframe
        timestamp: ISO timestamp
        votes: List of AgentVote from council agents

    Returns:
        DecisionPacket with final decision
    """
    # Get learned weights (may be empty if learner unavailable)
    learned_weights = _get_learned_weights()

    # Apply learned weights to votes (override static weights)
    if learned_weights:
        for v in votes:
            if v.agent_name in learned_weights:
                v.weight = learned_weights[v.agent_name]

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

    # Check required agents are present
    required_votes = {
        v.agent_name: v for v in votes if v.agent_name in REQUIRED_AGENTS
    }
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

    # Weighted voting for direction (using Bayesian weights)
    buy_weight = 0.0
    sell_weight = 0.0
    hold_weight = 0.0
    total_weight = 0.0

    for v in votes:
        if v.veto:
            continue
        w = v.weight * v.confidence
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
    elif buy_weight == sell_weight and buy_weight > 0:
        # Directional deadlock: buy and sell are equally weighted.
        # Conservative policy: refuse to trade when there is no consensus.
        final_direction = "hold"
        final_confidence = max(buy_weight / total_weight, 0.5)
        logger.info(
            "Arbiter deadlock for %s: buy=%.2f sell=%.2f — forcing safe hold",
            symbol, buy_weight, sell_weight,
        )
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

    # Required agent alignment check: for an executable trade (non-hold),
    # regime, risk, and strategy must not oppose the final direction.
    # An agent "opposes" if it voted the opposite direction (buy vs sell).
    required_aligned = True
    opposing_agents = []
    if final_direction in ("buy", "sell"):
        opposite = "sell" if final_direction == "buy" else "buy"
        for agent_name in REQUIRED_AGENTS:
            rv = required_votes.get(agent_name)
            if rv and rv.direction == opposite:
                opposing_agents.append(agent_name)
                required_aligned = False

    # Execution readiness
    execution_ready = (
        final_direction != "hold"
        and final_confidence > 0.4
        and required_aligned
    )
    exec_vote = next((v for v in votes if v.agent_name == "execution"), None)
    if exec_vote:
        execution_ready = execution_ready and exec_vote.metadata.get(
            "execution_ready", False
        )

    risk_limits = _extract_risk_limits(votes)

    # Build reasoning summary
    direction_counts = {"buy": 0, "sell": 0, "hold": 0}
    for v in votes:
        if not v.veto:
            direction_counts[v.direction] = (
                direction_counts.get(v.direction, 0) + 1
            )

    weight_source = "bayesian" if learned_weights else "static"
    reasoning = (
        f"Council vote: buy={direction_counts['buy']} "
        f"sell={direction_counts['sell']} hold={direction_counts['hold']}. "
        f"Weighted ({weight_source}): "
        f"buy={buy_weight:.2f} sell={sell_weight:.2f} hold={hold_weight:.2f}. "
        f"Decision: {final_direction.upper()} @ {final_confidence:.0%} confidence."
    )

    if buy_weight > 0 and buy_weight == sell_weight:
        reasoning += " Directional deadlock (buy == sell) — safe hold."

    if opposing_agents:
        reasoning += (
            f" Required agents opposing {final_direction}: "
            f"{', '.join(opposing_agents)} — execution blocked."
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
