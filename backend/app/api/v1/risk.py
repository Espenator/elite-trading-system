"""
Risk Intelligence API — risk config and metrics (stub until risk engine is wired).
GET /api/v1/risk returns limits and real-time risk snapshot for Risk Intelligence page.
PUT /api/v1/risk updates risk parameters.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.websocket_manager import broadcast_ws

router = APIRouter()

# In-memory storage (replace with database in production)
_risk_config = {
    "maxDailyDrawdown": 10,
    "positionSizeLimit": 5,
    "maxDailyLossPct": 2,
    "varLimit": 1.5,
}


class RiskUpdate(BaseModel):
    maxDailyDrawdown: float | None = None
    positionSizeLimit: float | None = None
    maxDailyLossPct: float | None = None
    varLimit: float | None = None


@router.get("")
async def get_risk():
    """Return risk parameters and current exposure. Used by Risk Intelligence page."""
    return {
        **{k: v for k, v in _risk_config.items()},
        "estimatedMaxDrawdown": 10.0,
        "potentialDailyLoss": 1.5,
        "currentExposure": 12500,
        "var95": 350,
        "expectedShortfall": 520,
        "allWithinLimits": True,
    }


@router.put("")
async def update_risk(update: RiskUpdate):
    """Update risk parameters. Broadcasts change via WebSocket."""
    if update.maxDailyDrawdown is not None:
        _risk_config["maxDailyDrawdown"] = update.maxDailyDrawdown
    if update.positionSizeLimit is not None:
        _risk_config["positionSizeLimit"] = update.positionSizeLimit
    if update.maxDailyLossPct is not None:
        _risk_config["maxDailyLossPct"] = update.maxDailyLossPct
    if update.varLimit is not None:
        _risk_config["varLimit"] = update.varLimit

    await broadcast_ws("risk", {"type": "config_updated", "config": _risk_config})
    return {"ok": True, "config": _risk_config}
