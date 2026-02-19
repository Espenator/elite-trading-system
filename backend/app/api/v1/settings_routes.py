"""
Settings API — load/save user settings (in-memory stub; use DB in production).
GET /api/v1/settings returns current settings. PUT /api/v1/settings updates and returns them.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

router = APIRouter()

# In-memory store (replace with DB in production)
_SETTINGS: dict[str, Any] = {
    "theme": "dark",
    "timezone": "EST",
    "currency": "USD",
    "defaultTimeframe": "1D",
    "maxPositions": 15,
    "positionSize": 2.0,
    "riskPerTrade": 2.0,
    "maxDailyLoss": 5.0,
    "circuitBreaker": True,
    "stopLossDefault": 2.0,
    "alpacaKey": "****",
    "alpacaSecret": "****",
    "finhubKey": "****",
    "unusualWhalesKey": "****",
    "telegramEnabled": True,
    "emailEnabled": True,
    "signalAlerts": True,
    "tradeAlerts": True,
    "minCompositeScore": 60,
    "minMLConfidence": 40,
    "autoRetrain": True,
    "retrainDay": "Sunday",
    "marketScanner": True,
    "patternAI": True,
    "riskAgent": True,
    "youtubeAgent": True,
}


@router.get("")
async def get_settings():
    """Return current settings. Used by Settings page."""
    return _SETTINGS.copy()


@router.put("")
async def update_settings(settings: dict[str, Any]):
    """Update settings (merge with existing). Returns full settings."""
    for k, v in settings.items():
        if k in _SETTINGS:
            _SETTINGS[k] = v
        else:
            _SETTINGS[k] = v
    return _SETTINGS.copy()
