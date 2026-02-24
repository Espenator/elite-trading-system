"""
Data Sources Monitor API — real health checks + DB-persisted status.
GET /api/v1/data-sources returns real connection status for all data feeds.
Alpaca: live ping via alpaca_service. Others: status from DB (updated by agents).
PUT /api/v1/data-sources/{source_id}/status updates a source's status.
No mock data. No fabricated numbers.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.alpaca_service import alpaca_service
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

# Registry of known data sources (static metadata only, no fake metrics)
SOURCE_REGISTRY = [
    {"id": 1, "name": "Finviz", "type": "Screener"},
    {"id": 2, "name": "Unusual Whales (UW)", "type": "Options Flow"},
    {"id": 3, "name": "Alpaca", "type": "Market Data"},
    {"id": 4, "name": "FRED", "type": "Macro"},
    {"id": 5, "name": "SEC EDGAR", "type": "Filings"},
    {"id": 6, "name": "Stockgeist", "type": "Sentiment"},
    {"id": 7, "name": "News API", "type": "News"},
    {"id": 8, "name": "Discord", "type": "Social"},
    {"id": 9, "name": "X (Twitter)", "type": "Social"},
    {"id": 10, "name": "YouTube", "type": "Knowledge"},
]


class SourceStatusUpdate(BaseModel):
    status: str  # healthy, degraded, error, offline
    latencyMs: Optional[int] = None
    recordCount: Optional[int] = None
    lastSync: Optional[str] = None


def _get_source_statuses() -> dict:
    """Return dict of source_id -> status data from DB."""
    stored = db_service.get_config("data_source_statuses")
    if not stored or not isinstance(stored, dict):
        return {}
    return stored


def _save_source_statuses(statuses: dict) -> None:
    db_service.set_config("data_source_statuses", statuses)


async def _check_alpaca_health() -> dict:
    """Live ping Alpaca API and return real status."""
    start = time.time()
    try:
        account = await alpaca_service.get_account()
        latency = int((time.time() - start) * 1000)
        if account is not None:
            return {
                "status": "healthy",
                "latencyMs": latency,
                "lastSync": datetime.now(timezone.utc).isoformat(),
                "recordCount": None,
            }
        return {
            "status": "error",
            "latencyMs": latency,
            "lastSync": None,
            "recordCount": 0,
        }
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        logger.warning("Alpaca health check failed: %s", e)
        return {
            "status": "error",
            "latencyMs": latency,
            "lastSync": None,
            "recordCount": 0,
        }


@router.get("")
async def get_data_sources():
    """
    Return health and metrics for all data sources.
    Alpaca: live health check. Others: status from DB.
    Unregistered sources show as 'unknown' until agents report status.
    """
    db_statuses = _get_source_statuses()
    sources = []

    for reg in SOURCE_REGISTRY:
        src_id = reg["id"]
        source_data = {**reg}

        if reg["name"] == "Alpaca":
            # Live health check for Alpaca
            health = await _check_alpaca_health()
            source_data.update(health)
        else:
            # Pull from DB (set by agents/background tasks)
            db_status = db_statuses.get(str(src_id), {})
            source_data["status"] = db_status.get("status", "unknown")
            source_data["latencyMs"] = db_status.get("latencyMs", None)
            source_data["lastSync"] = db_status.get("lastSync", None)
            source_data["recordCount"] = db_status.get("recordCount", 0)

        sources.append(source_data)

    return {"sources": sources}


@router.put("/{source_id}/status")
async def update_source_status(source_id: int, update: SourceStatusUpdate):
    """
    Update a data source's status (called by agents/background health checks).
    Persists to DB and broadcasts via WebSocket.
    """
    statuses = _get_source_statuses()
    statuses[str(source_id)] = {
        "status": update.status,
        "latencyMs": update.latencyMs,
        "recordCount": update.recordCount,
        "lastSync": update.lastSync or datetime.now(timezone.utc).isoformat(),
    }
    _save_source_statuses(statuses)

    await broadcast_ws("datasources", {
        "type": "status_changed",
        "source_id": source_id,
        "status": update.status,
    })

    logger.info("Data source %d status updated: %s", source_id, update.status)
    return {"ok": True, "source_id": source_id, "status": update.status}
