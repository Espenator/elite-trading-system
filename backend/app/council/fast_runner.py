"""Fast Council Runner — optimized 5-agent council for high-confidence signals (<200ms).

Fast Council DAG (parallel within stages):
  Stage 1: Quick Perception (parallel — 2 agents)
    [market_perception, regime]
  Stage 2: Quick Risk Check (1 agent)
    [risk]
  Stage 3: Quick Strategy (1 agent)
    [strategy]
  Stage 4: Fast Arbiter (deterministic)

Total: 5 agents, target latency <200ms for high-confidence signals.
Escalates to full 31-agent Deep Council if confidence is insufficient.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate
from app.council.task_spawner import TaskSpawner

logger = logging.getLogger(__name__)


async def run_fast_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    signal_score: float = 0.0,
) -> DecisionPacket:
    """Run the fast 5-agent council for high-confidence signals.

    Args:
        symbol: Ticker symbol to evaluate
        timeframe: Timeframe (default "1d")
        features: Pre-computed feature dict. If None, auto-computes.
        context: Additional context for agents
        signal_score: Original signal score (0-100 scale)

    Returns:
        DecisionPacket with all votes and final decision.
        If confidence < 0.7, should be escalated to deep council.
    """
    start_time = time.monotonic() * 1000

    if context is None:
        context = {}

    context["council_tier"] = "fast"
    context["signal_score"] = signal_score

    # Auto-compute features if not provided (prefer pre-computed for speed)
    if features is None:
        try:
            from app.features.feature_aggregator import aggregate
            fv = await aggregate(symbol, timeframe=timeframe)
            features = fv.to_dict()
        except Exception as e:
            logger.warning("Fast council feature aggregation failed for %s: %s", symbol, e)
            features = {"features": {}, "symbol": symbol}

    # Create BlackboardState
    blackboard = BlackboardState(
        symbol=symbol,
        raw_features=features,
    )
    blackboard.council_start_ms = start_time
    blackboard.metadata["council_tier"] = "fast"
    blackboard.metadata["signal_score"] = signal_score
    context["blackboard"] = blackboard

    timestamp = datetime.now(timezone.utc).isoformat()

    # Quick homeostasis check
    try:
        from app.council.homeostasis import get_homeostasis
        homeostasis = get_homeostasis()
        mode = homeostasis.get_mode()

        if mode == "HALTED":
            logger.warning("Homeostasis HALTED for %s — skipping fast council", symbol)
            return DecisionPacket(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                votes=[],
                final_direction="hold",
                final_confidence=0.0,
                reasoning="System halted by homeostasis",
                metadata={"council_tier": "fast", "homeostasis_mode": "HALTED"},
            )
    except Exception:
        pass  # Homeostasis unavailable, proceed

    # Initialize task spawner
    spawner = TaskSpawner(features, blackboard)
    spawner.register_all_agents()

    all_votes: list[AgentVote] = []

    # Stage 1: Quick Perception (parallel — 2 agents)
    _stage_start = time.monotonic() * 1000
    stage1_configs = [
        {"agent_type": "market_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "regime", "symbol": symbol, "timeframe": timeframe, "context": context},
    ]
    stage1 = await spawner.spawn_parallel(stage1_configs)
    all_votes.extend(stage1)
    context["stage1"] = {v.agent_name: v.to_dict() for v in stage1}
    for v in stage1:
        blackboard.perceptions[v.agent_name] = v.to_dict()
    blackboard.stage_latencies["fast_stage1"] = time.monotonic() * 1000 - _stage_start

    # Stage 2: Quick Risk Check (1 agent)
    _stage_start = time.monotonic() * 1000
    stage2 = await spawner.spawn("risk", symbol, timeframe, context=context)
    all_votes.append(stage2)
    context["stage2"] = {stage2.agent_name: stage2.to_dict()}
    blackboard.risk_assessment = stage2.to_dict()
    blackboard.stage_latencies["fast_stage2"] = time.monotonic() * 1000 - _stage_start

    # Stage 3: Quick Strategy (1 agent)
    _stage_start = time.monotonic() * 1000
    stage3 = await spawner.spawn("strategy", symbol, timeframe, context=context)
    all_votes.append(stage3)
    context["stage3"] = {stage3.agent_name: stage3.to_dict()}
    blackboard.strategy = stage3.to_dict()
    blackboard.stage_latencies["fast_stage3"] = time.monotonic() * 1000 - _stage_start

    # Stage 4: Fast Arbiter
    _stage_start = time.monotonic() * 1000
    decision = arbitrate(all_votes, symbol, blackboard)
    blackboard.stage_latencies["fast_arbiter"] = time.monotonic() * 1000 - _stage_start

    # Compute total latency
    total_latency = time.monotonic() * 1000 - start_time
    decision.metadata["total_latency_ms"] = round(total_latency, 2)
    decision.metadata["council_tier"] = "fast"
    decision.metadata["agent_count"] = len(all_votes)
    decision.metadata["stage_latencies"] = blackboard.stage_latencies

    logger.info(
        "⚡ Fast Council complete for %s: %s @ %.0f%% confidence (%d agents, %.0fms)",
        symbol,
        decision.final_direction.upper(),
        decision.final_confidence * 100,
        len(all_votes),
        total_latency,
    )

    return decision


async def should_escalate_to_deep(decision: DecisionPacket, threshold: float = 0.7) -> bool:
    """Determine if fast council decision should be escalated to deep council.

    Args:
        decision: DecisionPacket from fast council
        threshold: Confidence threshold for escalation (default 0.7)

    Returns:
        True if should escalate to deep council, False otherwise
    """
    # Escalate if confidence is too low
    if decision.final_confidence < threshold:
        return True

    # Escalate if risk agent vetoed
    for vote in decision.votes:
        if vote.agent_name == "risk" and vote.direction == "hold" and vote.confidence > 0.8:
            return True

    return False
