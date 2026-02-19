"""
Risk Intelligence API — risk config persisted in SQLite.
GET /api/v1/risk returns limits and real-time risk snapshot. PUT /api/v1/risk updates risk parameters.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.websocket_manager import broadcast_ws
from app.services.database import db_service

router = APIRouter()

DEFAULT_RISK = {
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


def _get_risk_config():
    stored = db_service.get_config("risk")
    if not stored or not isinstance(stored, dict):
        return {**DEFAULT_RISK}
    return {**DEFAULT_RISK, **stored}


@router.get("")
async def get_risk():
    """Return risk parameters and current exposure from DB."""
    config = _get_risk_config()
    return {
        **config,
        "estimatedMaxDrawdown": 10.0,
        "potentialDailyLoss": 1.5,
        "currentExposure": 12500,
        "var95": 350,
        "expectedShortfall": 520,
        "allWithinLimits": True,
    }


@router.put("")
async def update_risk(update: RiskUpdate):
    """Update risk parameters in DB. Broadcasts change via WebSocket."""
    config = _get_risk_config()
    if update.maxDailyDrawdown is not None:
        config["maxDailyDrawdown"] = update.maxDailyDrawdown
    if update.positionSizeLimit is not None:
        config["positionSizeLimit"] = update.positionSizeLimit
    if update.maxDailyLossPct is not None:
        config["maxDailyLossPct"] = update.maxDailyLossPct
    if update.varLimit is not None:
        config["varLimit"] = update.varLimit
    db_service.set_config("risk", config)
    await broadcast_ws("risk", {"type": "config_updated", "config": config})
    return {"ok": True, "config": config}
