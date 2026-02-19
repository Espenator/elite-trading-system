"""
Risk Intelligence API — risk config and metrics (stub until risk engine is wired).
GET /api/v1/risk returns limits and real-time risk snapshot for Risk Intelligence page.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_risk():
    """Return risk parameters and current exposure. Used by Risk Intelligence page."""
    return {
        "maxDailyDrawdown": 10,
        "positionSizeLimit": 5,
        "maxDailyLossPct": 2,
        "varLimit": 1.5,
        "estimatedMaxDrawdown": 10.0,
        "potentialDailyLoss": 1.5,
        "currentExposure": 12500,
        "var95": 350,
        "expectedShortfall": 520,
        "allWithinLimits": True,
    }
