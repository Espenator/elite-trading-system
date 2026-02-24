"""
Flywheel API — ML accuracy and outcome feedback persisted in SQLite.
GET /api/v1/flywheel returns metrics from DB (populated by ML pipeline).
POST /api/v1/flywheel/record allows ML modules to submit accuracy snapshots.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_HISTORY = 365  # one year of daily snapshots


class FlywheelRecord(BaseModel):
    """Schema for submitting a flywheel accuracy snapshot."""
    accuracy: float  # 0.0 to 1.0
    resolvedSignals: Optional[int] = None
    pendingResolution: Optional[int] = None
    date: Optional[str] = None  # ISO date, defaults to today


def _get_flywheel_data() -> dict:
    """Return flywheel metrics from DB."""
    stored = db_service.get_config("flywheel_data")
    if not stored or not isinstance(stored, dict):
        return {
            "accuracy30d": 0.0,
            "accuracy90d": 0.0,
            "resolvedSignals": 0,
            "pendingResolution": 0,
            "history": [],
        }
    return stored


def _save_flywheel_data(data: dict) -> None:
    db_service.set_config("flywheel_data", data)


def _compute_accuracy(history: list, days: int) -> float:
    """Compute average accuracy over last N days from history."""
    if not history:
        return 0.0
    recent = history[-days:] if len(history) >= days else history
    if not recent:
        return 0.0
    total = sum(h.get("accuracy", 0) for h in recent)
    return round(total / len(recent), 4)


@router.get("")
async def get_flywheel():
    """
    Return flywheel metrics from DB.
    Metrics are populated by ML pipeline, not hardcoded.
    Returns zeros/empty if no data has been recorded yet.
    """
    data = _get_flywheel_data()
    history = data.get("history", [])

    # Recompute rolling averages from history
    data["accuracy30d"] = _compute_accuracy(history, 30)
    data["accuracy90d"] = _compute_accuracy(history, 90)

    return data


@router.post("/record")
async def record_flywheel(record: FlywheelRecord):
    """
    Record a flywheel accuracy snapshot (called by ML pipeline).
    Appends to history and updates rolling metrics.
    """
    data = _get_flywheel_data()
    history = data.get("history", [])

    snapshot_date = record.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Avoid duplicate entries for same date
    history = [h for h in history if h.get("date") != snapshot_date]
    history.append({
        "date": snapshot_date,
        "accuracy": round(record.accuracy, 4),
    })

    # Sort and trim
    history.sort(key=lambda h: h.get("date", ""))
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    data["history"] = history
    if record.resolvedSignals is not None:
        data["resolvedSignals"] = record.resolvedSignals
    if record.pendingResolution is not None:
        data["pendingResolution"] = record.pendingResolution

    # Recompute rolling averages
    data["accuracy30d"] = _compute_accuracy(history, 30)
    data["accuracy90d"] = _compute_accuracy(history, 90)

    _save_flywheel_data(data)

    await broadcast_ws("flywheel", {"type": "flywheel_updated", "data": data})
    logger.info("Flywheel snapshot recorded: date=%s accuracy=%.4f", snapshot_date, record.accuracy)
    return {"ok": True, "data": data}
