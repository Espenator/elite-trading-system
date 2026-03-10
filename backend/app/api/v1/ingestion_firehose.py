"""Ingestion Firehose API: status and metrics for channel agents."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.message_bus import get_message_bus
from app.services.channels.orchestrator import get_channels_orchestrator

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.get("/status")
async def ingestion_status():
    """Per-agent status: lag, error rate, last event timestamp, queue depth."""
    try:
        orch = get_channels_orchestrator(get_message_bus())
        return orch.get_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ingestion status unavailable: {exc}")


@router.get("/metrics")
async def ingestion_metrics():
    """Counters and MessageBus metrics for operator monitoring."""
    try:
        orch = get_channels_orchestrator(get_message_bus())
        return orch.get_metrics()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ingestion metrics unavailable: {exc}")
