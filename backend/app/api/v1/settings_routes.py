"""
Settings API — load/save user settings (persisted in SQLite).
GET /api/v1/settings returns current settings. PUT /api/v1/settings updates and returns them.
"""

from fastapi import APIRouter
from typing import Any

from app.services.database import db_service

router = APIRouter()

DEFAULT_SETTINGS: dict[str, Any] = {
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


def _get_settings():
    """Return current settings from DB, merged with defaults."""
    stored = db_service.get_config("settings")
    if not stored or not isinstance(stored, dict):
        return DEFAULT_SETTINGS.copy()
    return {**DEFAULT_SETTINGS, **stored}


def _update_settings(settings: dict[str, Any]):
    """Merge and persist settings. Returns full settings."""
    current = db_service.get_config("settings")
    if not current or not isinstance(current, dict):
        current = DEFAULT_SETTINGS.copy()
    for k, v in settings.items():
        current[k] = v
    db_service.set_config("settings", current)
    return current


@router.get("", summary="Get settings")
@router.get("/", summary="Get settings (trailing slash)")
async def get_settings():
    return _get_settings()


@router.put("", summary="Update settings")
@router.put("/", summary="Update settings (trailing slash)")
async def update_settings(settings: dict[str, Any]):
    """Update settings (merge with existing). Persist to DB. Returns full settings."""
    return _update_settings(settings)
