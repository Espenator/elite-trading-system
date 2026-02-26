"""Data and model status API (research doc: dashboard monitoring)."""

from fastapi import APIRouter
from app.data.storage import get_conn, DB_PATH

router = APIRouter()


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
        result["error"] = str(e)
    return result
