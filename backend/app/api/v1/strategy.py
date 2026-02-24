"""
Strategy Intelligence API — controls + strategies persisted in SQLite.
GET /api/v1/strategy returns strategies and controls from DB.
POST /api/v1/strategy/controls updates emergency controls.
POST /api/v1/strategy adds a new strategy (from agents/config).
PUT /api/v1/strategy/{strategy_id} updates strategy metrics.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
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


class StrategyCreate(BaseModel):
    """Schema for registering a strategy."""
    name: str
    description: str = ""
    status: str = "Inactive"  # Active, Paused, Inactive, Error


class StrategyMetricsUpdate(BaseModel):
    """Schema for updating strategy performance metrics."""
    status: Optional[str] = None
    dailyPL: Optional[float] = None
    winRate: Optional[float] = None
    maxDrawdown: Optional[float] = None


def _get_controls() -> dict:
    stored = db_service.get_config("strategy_controls")
    if not stored or not isinstance(stored, dict):
        return {**DEFAULT_CONTROLS}
    return {**DEFAULT_CONTROLS, **stored}


def _get_strategies() -> list:
    """Return strategies from DB."""
    stored = db_service.get_config("strategies")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_strategies(strategies: list) -> None:
    db_service.set_config("strategies", strategies)


def _next_id(strategies: list) -> int:
    if not strategies:
        return 1
    return max(s.get("id", 0) for s in strategies) + 1


@router.get("")
async def get_strategies():
    """
    Return active strategies and controls from DB.
    Strategies are registered by config/agents, not hardcoded.
    Returns empty list if no strategies registered yet.
    """
    controls = _get_controls()
    strategies = _get_strategies()
    return {"controls": controls, "strategies": strategies}


@router.post("")
async def create_strategy(data: StrategyCreate):
    """Register a new strategy (from config or agents)."""
    strategies = _get_strategies()
    new_strategy = {
        "id": _next_id(strategies),
        "name": data.name,
        "status": data.status,
        "description": data.description,
        "dailyPL": 0.0,
        "winRate": 0,
        "maxDrawdown": 0.0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    strategies.append(new_strategy)
    _save_strategies(strategies)

    await broadcast_ws("strategy", {"type": "strategy_created", "strategy": new_strategy})
    logger.info("Strategy registered: %s", data.name)
    return {"ok": True, "strategy": new_strategy}


@router.put("/{strategy_id}")
async def update_strategy_metrics(strategy_id: int, update: StrategyMetricsUpdate):
    """Update strategy performance metrics (called by execution engine)."""
    strategies = _get_strategies()
    for s in strategies:
        if s.get("id") == strategy_id:
            if update.status is not None:
                s["status"] = update.status
            if update.dailyPL is not None:
                s["dailyPL"] = round(update.dailyPL, 2)
            if update.winRate is not None:
                s["winRate"] = round(update.winRate, 1)
            if update.maxDrawdown is not None:
                s["maxDrawdown"] = round(update.maxDrawdown, 2)
            s["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _save_strategies(strategies)
            await broadcast_ws("strategy", {"type": "strategy_updated", "strategy": s})
            return {"ok": True, "strategy": s}
    raise HTTPException(status_code=404, detail="Strategy not found")


@router.delete("/{strategy_id}")
async def remove_strategy(strategy_id: int):
    """Remove a strategy by ID."""
    strategies = _get_strategies()
    original_len = len(strategies)
    strategies = [s for s in strategies if s.get("id") != strategy_id]
    if len(strategies) == original_len:
        raise HTTPException(status_code=404, detail="Strategy not found")
    _save_strategies(strategies)
    await broadcast_ws("strategy", {"type": "strategy_removed", "id": strategy_id})
    return {"ok": True}


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
