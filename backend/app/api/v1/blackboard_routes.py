"""Blackboard API: GET /api/v1/blackboard/{symbol} for working memory per symbol."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.blackboard_state import read, get_all_symbols

router = APIRouter()


@router.get("")
async def list_blackboard_symbols():
    """List symbols that have blackboard state."""
    return {"symbols": get_all_symbols()}


@router.get("/{symbol}")
async def get_blackboard(symbol: str):
    """Get working memory (facts) for a symbol. Perception writes; council reads."""
    data = read(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No blackboard state for symbol {symbol}")
    return data
