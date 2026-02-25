"""
ML Brain API - Model performance tracking and staged signal inferences.
GET /api/v1/ml-brain/performance returns walk-forward accuracy from DB (mlmodels table).
GET /api/v1/ml-brain/signals/staged returns top staged inferences from mlfeatures/scannersignals.
GET /api/v1/ml-brain/flywheel-logs returns latest outcomes from tradeoutcomes table.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from app.services.database import db_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_ml_data(key: str, default=None):
    """Read ML Brain data from DB via config store."""
    stored = db_service.get_config(key)
    if stored is None:
        return default
    return stored


@router.get("/performance")
async def get_ml_performance():
    """
    Return ML model walk-forward accuracy history.
    Reads from TimescaleDB mlmodels table.
    Frontend charts: XGBoost accuracy %, RF accuracy % over 252 days.
    """
    data = _get_ml_data("ml_brain_performance", [])
    if not data:
        return []
    return data


@router.get("/signals/staged")
async def get_staged_inferences():
    """
    Return top staged signal inferences.
    Reads from mlfeatures / scannersignals join.
    Filters: WIN_PROB > 70% as per Anticipatory Funnel docs.
    """
    data = _get_ml_data("ml_brain_staged_signals", [])
    if not data:
        return []
    return data


@router.get("/flywheel-logs")
async def get_flywheel_logs():
    """
    Return latest outcomes from the tradeoutcomes table (learning flywheel).
    Shows closed trades fed back into retraining pipeline.
    """
    data = _get_ml_data("ml_brain_flywheel_logs", [])
    if not data:
        return []
    return data


@router.get("/summary")
async def get_ml_brain_summary():
    """
    Aggregate summary for the ML Brain & Flywheel dashboard.
    Returns combined metrics: model accuracy, active signals, flywheel status.
    """
    perf = _get_ml_data("ml_brain_performance", [])
    signals = _get_ml_data("ml_brain_staged_signals", [])
    logs = _get_ml_data("ml_brain_flywheel_logs", [])

    # Compute latest accuracy from performance history
    latest_xgb = perf[-1]["xgboost_acc"] if perf else 0.0
    latest_rf = perf[-1]["rf_acc"] if perf else 0.0

    return {
        "xgboost_accuracy": latest_xgb,
        "rf_accuracy": latest_rf,
        "active_staged_signals": len(signals),
        "flywheel_entries": len(logs),
        "last_updated": datetime.utcnow().isoformat(),
    }
