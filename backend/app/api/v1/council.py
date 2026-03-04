"""Council API — evaluate symbols through the 8-agent debate council.

POST /api/v1/council/evaluate  → full DecisionPacket
GET  /api/v1/council/status    → council configuration
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/evaluate")
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
