"""Alpaca API proxy endpoints for frontend direct access.

Mounts at /api/v1/alpaca — proxies account, positions, orders, activities
from Alpaca Markets v2 API through the centralized AlpacaService.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional

from app.core.security import require_auth
from app.services.alpaca_service import alpaca_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/account")
async def get_account():
    """GET /v2/account — full account details."""
    try:
        result = await alpaca_service.get_account()
        if result is None:
            return {}
        return result
    except Exception as e:
        logger.error("alpaca/account failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/positions")
async def get_positions():
    """GET /v2/positions — all open positions."""
    try:
        result = await alpaca_service.get_positions()
        if result is None:
            return []
        return result
    except Exception as e:
        logger.error("alpaca/positions failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orders")
async def get_orders(status: str = "open", limit: int = 50):
    """GET /v2/orders — list orders with status filter."""
    try:
        result = await alpaca_service.get_orders(status=status, limit=limit)
        if result is None:
            return []
        return result
    except Exception as e:
        logger.error("alpaca/orders failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activities")
async def get_activities(limit: int = 30, activity_type: str = "FILL"):
    """GET /v2/account/activities — trade activities."""
    try:
        result = await alpaca_service.get_activities()
        if result is None:
            return []
        # Alpaca returns all activities; filter and limit
        activities = result if isinstance(result, list) else []
        if activity_type:
            activities = [a for a in activities if a.get("activity_type") == activity_type or a.get("type") == activity_type][:limit]
        else:
            activities = activities[:limit]
        return activities
    except Exception as e:
        logger.error("alpaca/activities failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/positions/{symbol}", dependencies=[Depends(require_auth)])
async def close_position(symbol: str, qty: Optional[str] = None, percentage: Optional[str] = None):
    """DELETE /v2/positions/{symbol} — close or reduce position."""
    try:
        result = await alpaca_service.close_position(symbol, qty=qty, percentage=percentage)
        return result or {"status": "closed", "symbol": symbol}
    except Exception as e:
        logger.error("alpaca/close_position failed: %s", e)
        raise HTTPException(status_code=400, detail="Internal server error")


@router.delete("/positions", dependencies=[Depends(require_auth)])
async def close_all_positions():
    """DELETE /v2/positions — liquidate all."""
    try:
        result = await alpaca_service.close_all_positions()
        return result or {"status": "all_closed"}
    except Exception as e:
        logger.error("alpaca/close_all_positions failed: %s", e)
        raise HTTPException(status_code=400, detail="Internal server error")
