"""
Strategy Intelligence API - active strategies and config (stub until strategy engine is wired).
GET /api/v1/strategy returns strategies for Strategy Intelligence page.
POST /api/v1/strategy/controls updates emergency controls (master switch, pause all, etc.).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.websocket_manager import broadcast_ws

router = APIRouter()

# In-memory storage (replace with database in production)
_controls = {
    "masterSwitch": True,
    "pauseAll": False,
    "closeAllPositions": False,
}


class StrategyControls(BaseModel):
    masterSwitch: bool | None = None
    pauseAll: bool | None = None
    closeAllPositions: bool | None = None


@router.get("")
async def get_strategies():
    """Return active strategies and status. Used by Strategy Intelligence page."""
    return {
        "controls": _controls,
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
    """Update emergency controls (master switch, pause all, close all positions). Broadcasts change via WebSocket."""
    if controls.masterSwitch is not None:
        _controls["masterSwitch"] = controls.masterSwitch
    if controls.pauseAll is not None:
        _controls["pauseAll"] = controls.pauseAll
    if controls.closeAllPositions is not None:
        _controls["closeAllPositions"] = controls.closeAllPositions

    await broadcast_ws("strategy", {"type": "controls_updated", "controls": _controls})
    return {"ok": True, "controls": _controls}
