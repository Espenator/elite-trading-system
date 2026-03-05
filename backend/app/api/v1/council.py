"""Council API — evaluate symbols through the 14-agent council.

POST /api/v1/council/evaluate  -> full DecisionPacket
GET  /api/v1/council/status    -> council configuration (14 agents, 7 stages)
GET  /api/v1/council/latest    -> most recent DecisionPacket
GET  /api/v1/council/weights   -> current agent weights (Bayesian-updated)
POST /api/v1/council/weights/reset -> reset weights to defaults
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None
_decision_lock = asyncio.Lock()


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/evaluate")
async def evaluate_symbol(req: CouncilEvalRequest):
    """Run the 14-agent council on a symbol and return DecisionPacket."""
    global _latest_decision
    try:
        from app.council.runner import run_council

        decision = await run_council(
            symbol=req.symbol,
            timeframe=req.timeframe,
            features=req.features,
            context=req.context or {},
        )

        result = decision.to_dict()
        async with _decision_lock:
            _latest_decision = result
        return result
    except ImportError as e:
        logger.warning("Council runner not available: %s", e)
        raise HTTPException(status_code=503, detail="Council runner not available")
    except Exception as e:
        logger.exception("Council evaluation failed for %s", req.symbol)
        raise HTTPException(status_code=500, detail=f"Council evaluation failed: {e}")


@router.get("/latest")
async def council_latest():
    """Return the most recent council DecisionPacket (if any)."""
    if _latest_decision is None:
        return {"status": "no_evaluation_yet", "votes": None}
    return _latest_decision


@router.get("/status")
async def council_status():
    """Return council configuration and agent list (14 agents, 7 stages)."""
    import os

    # Try to get live weight data from weight_learner
    agent_weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        agent_weights = learner.get_weights()
    except Exception as e:
        logger.debug("Weight learner unavailable: %s", e)

    return {
        "council_enabled": os.getenv("COUNCIL_ENABLED", "true").lower() == "true",
        "brain_enabled": os.getenv("BRAIN_ENABLED", "false").lower() == "true",
        "council_gate_enabled": os.getenv("COUNCIL_GATE_ENABLED", "true").lower() == "true",
        "agent_count": 14,
        "agents": [
            "market_perception",
            "flow_perception",
            "regime",
            "intermarket",
            "rsi",
            "bbv",
            "ema_trend",
            "relative_strength",
            "cycle_timing",
            "hypothesis",
            "strategy",
            "risk",
            "execution",
            "critic",
        ],
        "dag_stages": [
            ["market_perception", "flow_perception", "regime", "intermarket"],
            ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing"],
            ["hypothesis"],
            ["strategy"],
            ["risk", "execution"],
            ["critic"],
            ["arbiter"],
        ],
        "agent_weights": agent_weights,
    }


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


@router.post("/weights/reset")
async def reset_weights():
    """Reset agent weights to defaults."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        learner.reset()
        return {"status": "ok", "weights": learner.get_weights()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
