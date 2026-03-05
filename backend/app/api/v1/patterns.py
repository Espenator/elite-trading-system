"""
Patterns API — detected chart patterns persisted in SQLite.
GET /api/v1/patterns returns patterns from DB (populated by detection agents).
POST /api/v1/patterns allows agents/modules to submit newly detected patterns.
DELETE /api/v1/patterns/{pattern_id} removes a pattern.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_PATTERNS = 200  # keep DB lean


class PatternSubmit(BaseModel):
    """Schema for submitting a detected pattern."""
    ticker: str
    pattern: str
    confidence: float
    direction: str  # bullish / bearish / neutral
    timeframe: str  # 1m, 5m, 15m, 1H, 4H, 1D, 1W
    priceTarget: Optional[float] = None
    currentPrice: Optional[float] = None
    source: str = "agent"  # who detected it


def _get_patterns() -> list:
    """Return all stored patterns from DB."""
    stored = db_service.get_config("detected_patterns")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_patterns(patterns: list) -> None:
    """Persist patterns to DB."""
    db_service.set_config("detected_patterns", patterns)


def _next_id(patterns: list) -> int:
    """Generate next sequential ID."""
    if not patterns:
        return 1
    return max(p.get("id", 0) for p in patterns) + 1


@router.get("")
async def get_patterns():
    """
    Return all detected patterns from DB.
    Patterns are populated by detection agents, not hardcoded.
    Returns empty list if no patterns have been detected yet.
    """
    patterns = _get_patterns()
    return {"patterns": patterns, "count": len(patterns)}


@router.post("", dependencies=[Depends(require_auth)])
async def submit_pattern(data: PatternSubmit):
    """
    Submit a newly detected pattern (called by agents/modules).
    Broadcasts via WebSocket for live frontend updates.
    """
    patterns = _get_patterns()
    new_pattern = {
        "id": _next_id(patterns),
        "ticker": data.ticker.upper(),
        "pattern": data.pattern,
        "confidence": round(data.confidence, 1),
        "direction": data.direction.lower(),
        "timeframe": data.timeframe,
        "detected": datetime.now(timezone.utc).isoformat(),
        "priceTarget": data.priceTarget,
        "currentPrice": data.currentPrice,
        "source": data.source,
    }
    patterns.append(new_pattern)

    # Keep only most recent patterns
    if len(patterns) > MAX_PATTERNS:
        patterns = patterns[-MAX_PATTERNS:]

    _save_patterns(patterns)

    await broadcast_ws("patterns", {"type": "pattern_detected", "pattern": new_pattern})
    logger.info("Pattern detected: %s %s on %s", data.pattern, data.direction, data.ticker)
    return {"ok": True, "pattern": new_pattern}


@router.delete("/{pattern_id}", dependencies=[Depends(require_auth)])
async def delete_pattern(pattern_id: int):
    """Remove a pattern by ID."""
    patterns = _get_patterns()
    original_len = len(patterns)
    patterns = [p for p in patterns if p.get("id") != pattern_id]
    if len(patterns) == original_len:
        raise HTTPException(status_code=404, detail="Pattern not found")
    _save_patterns(patterns)
    await broadcast_ws("patterns", {"type": "pattern_removed", "id": pattern_id})
    return {"ok": True}


@router.delete("", dependencies=[Depends(require_auth)])
async def clear_patterns():
    """Clear all patterns."""
    _save_patterns([])
    await broadcast_ws("patterns", {"type": "patterns_cleared"})
    return {"ok": True, "cleared": True}
