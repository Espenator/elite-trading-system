"""Cognitive Telemetry API — Embodier Trader Being Intelligence (ETBI) metrics.

Provides the Research Dashboard with cognitive quality metrics from the council.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_auth
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """Get aggregated cognitive telemetry for the Research Dashboard.

    Returns hypothesis diversity, agent agreement, confidence calibration,
    mode distribution, latency profiles, and exploration outcomes.
    """
    try:
        from app.services.cognitive_telemetry import get_cognitive_dashboard
        return get_cognitive_dashboard()
    except Exception as e:
        logger.error("Failed to get cognitive dashboard: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots")
async def get_recent_snapshots(limit: int = 50):
    """Get recent cognitive snapshots for time-series visualization."""
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        snapshots = store.get("snapshots", [])
        return {"snapshots": snapshots[-limit:], "total": len(snapshots)}
    except Exception as e:
        logger.error("Failed to get cognitive snapshots: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration")
async def get_calibration():
    """Get confidence calibration data (Brier score + prediction history)."""
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        calibration = store.get("calibration", {})
        predictions = calibration.get("predictions", [])

        # Compute Brier score
        brier = None
        if predictions:
            brier = sum((p["predicted_conf"] - p["actual"]) ** 2 for p in predictions) / len(predictions)

        return {
            "brier_score": round(brier, 4) if brier is not None else None,
            "total_predictions": len(predictions),
            "recent_predictions": predictions[-20:],
        }
    except Exception as e:
        logger.error("Failed to get calibration data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-outcome", dependencies=[Depends(require_auth)])
async def record_trade_outcome(payload: dict):
    """Record a trade outcome for confidence calibration.

    Body: { "council_decision_id": "...", "outcome": "win"|"loss"|"scratch", "r_multiple": 1.5 }
    """
    try:
        from app.services.cognitive_telemetry import record_outcome
        record_outcome(
            council_decision_id=payload["council_decision_id"],
            outcome=payload["outcome"],
            r_multiple=payload.get("r_multiple", 0),
        )
        return {"status": "recorded"}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")
    except Exception as e:
        logger.error("Failed to record outcome: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
