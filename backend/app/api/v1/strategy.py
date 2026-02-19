"""
Strategy Intelligence API — controls persisted in SQLite.
GET /api/v1/strategy returns strategies and controls. POST /api/v1/strategy/controls updates controls.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.websocket_manager import broadcast_ws
from app.services.database import db_service

router = APIRouter()

DEFAULT_CONTROLS = {
    "masterSwitch": True,
    "pauseAll": False,
    "closeAllPositions": False,
}


class StrategyControls(BaseModel):
    masterSwitch: bool | None = None
    pauseAll: bool | None = None
    closeAllPositions: bool | None = None


def _get_controls():
    stored = db_service.get_config("strategy_controls")
    if not stored or not isinstance(stored, dict):
        return {**DEFAULT_CONTROLS}
    return {**DEFAULT_CONTROLS, **stored}


@router.get("")
async def get_strategies():
    """Return active strategies and controls from DB."""
    controls = _get_controls()
    return {
        "controls": controls,
        "strategies": [
            {
                "id": 1,
                "name": "Momentum Scalper v2",
                "status": "Active",
                "description": "Aggressive short-term momentum strategy with tight stop-losses.",
                "dailyPL": 1.25,
                "winRate": 68,
                "maxDrawdown": -3.1,
            },
            {
                "id": 2,
                "name": "Trend Follower FX",
                "status": "Paused",
                "description": "Medium-term trend following strategy across major FX pairs.",
                "dailyPL": 0.1,
                "winRate": 55,
                "maxDrawdown": -5.8,
            },
            {
                "id": 3,
                "name": "Arbitrage Crypto",
                "status": "Error",
                "description": "Cross-exchange cryptocurrency arbitrage with automated execution.",
                "dailyPL": -0.5,
                "winRate": 72,
                "maxDrawdown": -1.2,
            },
            {
                "id": 4,
                "name": "Mean Reversion",
                "status": "Active",
                "description": "Statistical arbitrage on mean-reverting equity pairs.",
                "dailyPL": 0.85,
                "winRate": 61,
                "maxDrawdown": -2.4,
            },
        ],
    }


@router.post("/controls")
async def update_controls(controls: StrategyControls):
    """Update emergency controls in DB. Broadcasts change via WebSocket."""
    ctrl = _get_controls()
    if controls.masterSwitch is not None:
        ctrl["masterSwitch"] = controls.masterSwitch
    if controls.pauseAll is not None:
        ctrl["pauseAll"] = controls.pauseAll
    if controls.closeAllPositions is not None:
        ctrl["closeAllPositions"] = controls.closeAllPositions
    db_service.set_config("strategy_controls", ctrl)
    await broadcast_ws("strategy", {"type": "controls_updated", "controls": ctrl})
    return {"ok": True, "controls": ctrl}
