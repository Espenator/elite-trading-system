"""Council API — evaluate symbols through the 20-agent council.

POST /api/v1/council/evaluate       -> full DecisionPacket
GET  /api/v1/council/status         -> council configuration (20 agents, 7+1 stages)
GET  /api/v1/council/latest         -> most recent DecisionPacket
GET  /api/v1/council/weights        -> current agent weights (Bayesian-updated)
GET  /api/v1/council/agent-health   -> per-agent health, weight, performance
GET  /api/v1/council/decision/{id}  -> decision replay by ID
POST /api/v1/council/weights/reset  -> reset weights to defaults
"""
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None

# Rate limiting: max evaluations per minute to prevent DoS
_eval_timestamps: list = []
_RATE_LIMIT_MAX = 10  # Max 10 council evaluations per minute
_RATE_LIMIT_WINDOW = 60  # seconds


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


def _check_rate_limit():
    """Enforce rate limiting on council evaluations."""
    now = time.time()
    # Prune old timestamps
    _eval_timestamps[:] = [t for t in _eval_timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_eval_timestamps) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_RATE_LIMIT_MAX} evaluations per minute",
        )
    _eval_timestamps.append(now)


@router.post("/evaluate", dependencies=[Depends(require_auth)])
async def evaluate_symbol(req: CouncilEvalRequest):
    """Run the 13-agent council on a symbol and return DecisionPacket."""
    global _latest_decision
    _check_rate_limit()
    try:
        from app.council.runner import run_council

        decision = await run_council(
            symbol=req.symbol,
            timeframe=req.timeframe,
            features=req.features,
            context=req.context or {},
        )

        result = decision.to_dict()
        _latest_decision = result
        return result
    except Exception as e:
        logger.error("Council evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail="Council evaluation failed")


@router.get("/latest")
async def council_latest():
    """Return the most recent council DecisionPacket (if any)."""
    if _latest_decision is None:
        return {"status": "no_evaluation_yet", "votes": None}
    return _latest_decision


@router.get("/status")
async def council_status():
    """Return council configuration and agent list (20 agents, 7+1 stages)."""
    import os

    # Try to get live weight data from weight_learner
    agent_weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        agent_weights = learner.get_weights()
    except Exception:
        pass

    return {
        "council_enabled": os.getenv("COUNCIL_ENABLED", "true").lower() == "true",
        "brain_enabled": os.getenv("BRAIN_ENABLED", "false").lower() == "true",
        "council_gate_enabled": os.getenv("COUNCIL_GATE_ENABLED", "true").lower() == "true",
        "agent_count": 20,
        "agents": [
            "market_perception", "flow_perception", "regime", "social_perception",
            "news_catalyst", "youtube_knowledge", "intermarket",
            "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
            "hypothesis", "strategy", "risk", "execution",
            "debate_engine", "red_team", "critic",
        ],
        "dag_stages": [
            {"stage": "S1", "name": "Perception", "agents": ["market_perception", "flow_perception", "regime", "social_perception", "news_catalyst", "youtube_knowledge", "intermarket"]},
            {"stage": "S1.5", "name": "Regime Update", "agents": []},
            {"stage": "S2", "name": "Technical", "agents": ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing"]},
            {"stage": "S3", "name": "Hypothesis", "agents": ["hypothesis"]},
            {"stage": "S4", "name": "Strategy", "agents": ["strategy"]},
            {"stage": "S5", "name": "Risk/Execution", "agents": ["risk", "execution"]},
            {"stage": "S5.5", "name": "Debate/RedTeam", "agents": ["debate_engine", "red_team"]},
            {"stage": "S6", "name": "Critic", "agents": ["critic"]},
            {"stage": "S7", "name": "Arbiter", "agents": []},
        ],
        "agent_weights": agent_weights,
    }


@router.get("/agent-health")
async def council_agent_health():
    """Return per-agent health, weight, and recent performance for the consensus matrix."""
    agents_health = {}

    # Get weights from weight_learner
    weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
    except Exception:
        pass

    # Get health from self_awareness
    health_data = {}
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        health_data = sa.get_all_health()
    except Exception:
        pass

    all_agents = [
        "market_perception", "flow_perception", "regime", "social_perception",
        "news_catalyst", "youtube_knowledge", "intermarket",
        "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
        "hypothesis", "strategy", "risk", "execution",
        "debate_engine", "red_team", "critic",
    ]

    for agent in all_agents:
        h = health_data.get(agent, {})
        agents_health[agent] = {
            "name": agent,
            "weight": round(weights.get(agent, 1.0), 3),
            "health_pct": h.get("health_pct", 100),
            "status": h.get("status", "active"),
            "streak": h.get("streak", 0),
            "win_rate_7d": h.get("win_rate_7d", 0),
            "avg_latency_ms": h.get("avg_latency_ms", 0),
            "hibernated": h.get("hibernated", False),
        }

    return {"agents": agents_health, "total": len(all_agents)}


@router.get("/decision/{decision_id}")
async def get_decision(decision_id: str):
    """Retrieve a specific council decision by ID (for decision replay)."""
    # For now, only check if it matches the latest
    if _latest_decision and _latest_decision.get("council_decision_id", "").startswith(decision_id):
        return _latest_decision
    raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")


@router.get("/weights")
async def council_weights():
    """Return current Bayesian-updated agent weights."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        return {
            "weights": learner.get_weights(),
            "update_count": learner.update_count,
            "last_update": learner.last_update,
        }
    except Exception as e:
        return {"status": "weight_learner_unavailable", "error": str(e)}


@router.post("/weights/reset", dependencies=[Depends(require_auth)])
async def reset_weights():
    """Reset agent weights to defaults."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        learner.reset()
        return {"status": "ok", "weights": learner.get_weights()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
