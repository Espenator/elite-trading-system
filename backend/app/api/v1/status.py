"""Data and model status API (research doc: dashboard monitoring)."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.data.storage import get_conn, DB_PATH

logger = logging.getLogger(__name__)
router = APIRouter()


# Readiness: poll GET /api/v1/status/ready or GET /readyz until 200 before starting frontend.
READINESS_DUCKDB_KEY = "duckdb_ready"
READINESS_MESSAGEBUS_KEY = "message_bus_ready"


@router.get("/ready")
async def get_ready(request: Request):
    """
    Readiness check: returns 200 only when DuckDB and MessageBus are ready.

    Launcher should poll this URL (or GET /readyz) until 200 before starting the frontend.
    Returns 503 with checks detail when not ready.
    """
    duckdb_ready = getattr(request.app.state, READINESS_DUCKDB_KEY, False)
    message_bus_ready = getattr(request.app.state, READINESS_MESSAGEBUS_KEY, False)
    ready = duckdb_ready and message_bus_ready
    checks = {
        "duckdb": "ok" if duckdb_ready else "not_ready",
        "message_bus": "ok" if message_bus_ready else "not_ready",
    }
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


@router.get("")
def get_status_root():
    """
    Dashboard health check. GET /api/v1/status returns status + latency.
    Frontend expects { status: "ok", latency?: ms }.
    """
    import time

    start = time.perf_counter()
    data = get_data_status()
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return {
        "status": "ok" if data.get("connected") else "degraded",
        "connected": data.get("connected", False),
        "latency": elapsed_ms,
        "db_path": data.get("db_path"),
        "daily_bars_last_date": data.get("daily_bars_last_date"),
        "daily_features_last_date": data.get("daily_features_last_date"),
    }


@router.get("/data")
def get_data_status():
    """
    Return last update info for bars/features. For dashboard: connection status, last data timestamp.
    """
    result = {
        "db_path": str(DB_PATH),
        "connected": False,
        "daily_bars_last_date": None,
        "daily_features_last_date": None,
        "daily_predictions_count": None,
    }
    try:
        conn = get_conn()
        result["connected"] = True
        try:
            r = conn.execute("SELECT MAX(date) AS d FROM daily_bars").fetchone()
            result["daily_bars_last_date"] = str(r[0]) if r and r[0] else None
        except Exception:
            pass
        try:
            r = conn.execute("SELECT MAX(date) AS d FROM daily_features").fetchone()
            result["daily_features_last_date"] = str(r[0]) if r and r[0] else None
        except Exception:
            pass
        try:
            r = conn.execute("SELECT COUNT(*) AS c FROM daily_predictions").fetchone()
            result["daily_predictions_count"] = r[0] if r else None
        except Exception:
            pass
        conn.close()
    except Exception as e:
        logger.warning("Status check error: %s", e)
        result["error"] = "Service unavailable"
    return result
