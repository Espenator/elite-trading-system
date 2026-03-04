"""Council API — evaluate symbols through the 8-agent debate council.

POST /api/v1/council/evaluate     → full DecisionPacket
GET  /api/v1/council/status       → council configuration
GET  /api/v1/council/performance  → agent accuracy stats (feedback loop)
POST /api/v1/council/update-weights → recompute agent weights from outcomes
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/evaluate", dependencies=[Depends(require_auth)])
async def evaluate_symbol(req: CouncilEvalRequest):
    """Run the 8-agent council on a symbol and return DecisionPacket."""
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
    """Return council configuration and agent list."""
    import os

    return {
        "council_enabled": os.getenv("COUNCIL_ENABLED", "true").lower() == "true",
        "brain_enabled": os.getenv("BRAIN_ENABLED", "false").lower() == "true",
        "agents": [
            "market_perception",
            "flow_perception",
            "regime",
            "hypothesis",
            "strategy",
            "risk",
            "execution",
            "critic",
        ],
        "dag_stages": [
            ["market_perception", "flow_perception", "regime"],
            ["hypothesis"],
            ["strategy"],
            ["risk", "execution"],
            ["critic"],
            ["arbiter"],
        ],
    }


@router.get("/performance")
async def council_agent_performance():
    """Return per-agent accuracy stats from the feedback loop."""
    try:
        from app.council.feedback_loop import get_agent_performance
        return get_agent_performance()
    except Exception as e:
        logger.error("Failed to get agent performance: %s", e)
        return {"agent_stats": {}, "total_decisions": 0, "total_outcomes": 0, "feedback_active": False}


@router.post("/update-weights", dependencies=[Depends(require_auth)])
async def council_update_weights():
    """Recompute agent weights from outcome history and persist to settings."""
    try:
        from app.council.feedback_loop import update_agent_weights
        new_weights = update_agent_weights()
        return {"status": "updated", "weights": new_weights}
    except Exception as e:
        logger.error("Failed to update agent weights: %s", e)
        raise HTTPException(status_code=500, detail="Weight update failed")
