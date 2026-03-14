"""API endpoint for data ingestion / backfill.

Provides manual trigger for full historical data backfill
and status check on DuckDB health.

Usage:
    POST /api/ingestion/backfill {"symbols": ["AAPL","MSFT"], "days": 252}
    GET  /api/ingestion/health
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class BackfillRequest(BaseModel):
    symbols: List[str] = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA",
                          "META", "AMZN", "SPY", "QQQ", "IWM"]
    days: int = 252


class BackfillResponse(BaseModel):
    status: str
    report: dict


@router.post("/backfill", response_model=BackfillResponse, dependencies=[Depends(require_auth)])
async def run_backfill(req: BackfillRequest):
    """Trigger full historical data backfill.

    This fetches OHLCV from Alpaca, computes indicators,
    pulls options flow from UW, macro from FRED, and trade outcomes.
    """
    try:
        from app.services.data_ingestion import data_ingestion
        report = await data_ingestion.ingest_all(
            symbols=req.symbols,
            days=req.days,
        )
        return BackfillResponse(status="ok", report=report)
    except Exception as e:
        logger.exception("Backfill failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def ingestion_health():
    """Check DuckDB health and table row counts. Returns 503 when unhealthy for readiness probes."""
    try:
        import asyncio
        from app.data.duckdb_storage import duckdb_store
        return await asyncio.to_thread(duckdb_store.health_check)
    except Exception as e:
        logger.error("ingestion_health failed: %s", e)
        raise HTTPException(status_code=503, detail="Ingestion/DuckDB unhealthy")
