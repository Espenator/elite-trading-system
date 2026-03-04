"""ML Brain & Flywheel API — Production endpoints.

Replaces random.uniform() stubs with real SQLAlchemy queries against
the backend SQLite / TimescaleDB database.  Three routes:
  /api/v1/ml/performance   – 252-day walk-forward accuracy history
  /api/v1/ml/signals/stage4 – Top Stage-4 ML inferences (win_prob > 70%)
  /api/v1/ml/flywheel-logs  – Recent trade outcomes + weight adjustments

Connects to:
  - backend/app/services/database.py  (get_db session factory)
  - backend/app/models/trainer.py     (MLModel registry)
  - backend/app/models/inference.py   (MLSignal predictions)
  - frontend-v2/src/pages/MLBrainFlywheel.jsx  (consumer)
  - frontend-v2/src/pages/Dashboard.jsx        (consumer)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

# ---------- database dependency ----------
# Try the backend service first; fall back to core timescale manager
try:
    from backend.app.services.database import get_db
except ImportError:
    from database.timescalemanager import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ml", tags=["ML Brain"])


# ────────────────────────────────────────────────────────────
# 1.  Walk-forward ML accuracy over the last 252 trading days
# ────────────────────────────────────────────────────────────
@router.get("/performance")
def get_ml_performance(
    days: int = Query(252, ge=30, le=504),
    db: Session = Depends(get_db),
):
    """
    Query the models_registry / ml_performance table for daily
    accuracy snapshots produced by the walk-forward trainer.
    Falls back to computing from trade outcomes if no dedicated table.
    """
    try:
        # Attempt: read from a dedicated ml_performance table
        rows = db.execute(
            text(
                """
                SELECT
                    date,
                    xgboost_accuracy,
                    rf_accuracy,
                    lstm_accuracy
                FROM ml_performance
                WHERE date >= :cutoff
                ORDER BY date ASC
                """
            ),
            {"cutoff": (datetime.utcnow() - timedelta(days=days)).isoformat()},
        ).fetchall()

        if rows:
            return [
                {
                    "day": r.date,
                    "xgboost_acc": round(r.xgboost_accuracy, 1),
                    "rf_acc": round(r.rf_accuracy, 1),
                    "lstm_acc": round(r.lstm_accuracy, 1) if r.lstm_accuracy else None,
                }
                for r in rows
            ]

        # Fallback: derive accuracy from trade outcomes (signals vs. results)
        outcome_rows = db.execute(
            text(
                """
                SELECT
                    date(created_at) AS day,
                    COUNT(*) AS total,
                    SUM(CASE WHEN result_r > 0 THEN 1 ELSE 0 END) AS wins
                FROM trade_outcomes
                WHERE created_at >= :cutoff
                GROUP BY date(created_at)
                ORDER BY day ASC
                """
            ),
            {"cutoff": (datetime.utcnow() - timedelta(days=days)).isoformat()},
        ).fetchall()

        return [
            {
                "day": r.day,
                "xgboost_acc": round((r.wins / r.total) * 100, 1) if r.total else 0,
                "rf_acc": None,
                "lstm_acc": None,
            }
            for r in outcome_rows
        ]

    except Exception as exc:
        logger.exception("ml/performance query failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ────────────────────────────────────────────────────────────
# 2.  Stage-4 ML Inferences (highest-confidence signals)
# ────────────────────────────────────────────────────────────
@router.get("/signals/stage4")
def get_stage4_inferences(
    limit: int = Query(10, ge=1, le=50),
    min_prob: float = Query(70.0, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """
    Fetch top Stage-4 signals where composite win probability exceeds
    the threshold.  Joins scanner_signals + ml_features tables.
    """
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    s.symbol,
                    s.direction,
                    s.win_probability,
                    s.compression_days,
                    s.velez_score,
                    s.volume_ratio,
                    s.regime_multiplier,
                    s.kelly_size_pct,
                    s.created_at
                FROM scanner_signals s
                WHERE s.stage = 4
                  AND s.win_probability >= :min_prob
                ORDER BY s.win_probability DESC
                LIMIT :lim
                """
            ),
            {"min_prob": min_prob, "lim": limit},
        ).fetchall()

        return [
            {
                "symbol": r.symbol,
                "dir": r.direction,
                "prob": round(r.win_probability, 1),
                "compression_days": r.compression_days,
                "velez_score": r.velez_score,
                "vol_ratio": round(r.volume_ratio, 2) if r.volume_ratio else None,
                "regime_multiplier": r.regime_multiplier,
                "kelly_size_pct": r.kelly_size_pct,
                "timestamp": r.created_at,
            }
            for r in rows
        ]

    except Exception as exc:
        logger.exception("ml/signals/stage4 query failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ────────────────────────────────────────────────────────────
# 3.  Flywheel Learning Logs (trade outcomes + weight updates)
# ────────────────────────────────────────────────────────────
@router.get("/flywheel-logs")
def get_flywheel_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Fetch the most recent trade-outcome events that the learning
    flywheel has processed (weight adjustments, validation results).
    """
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    t.created_at,
                    t.event_type,
                    t.symbol,
                    t.result_description,
                    t.status,
                    t.strategy_name,
                    t.weight_delta
                FROM trade_outcomes t
                ORDER BY t.created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).fetchall()

        return [
            {
                "time": r.created_at,
                "event": r.event_type,
                "symbol": r.symbol,
                "result": r.result_description,
                "status": r.status,
                "strategy": r.strategy_name,
                "weight_delta": r.weight_delta,
            }
            for r in rows
        ]

    except Exception as exc:
        logger.exception("ml/flywheel-logs query failed")
        raise HTTPException(status_code=500, detail="Internal server error")
