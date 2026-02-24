"""
ML Engine — XGBoost/LightGBM on GPU (CUDA), historical outcomes, Sunday retrain, flywheel.

Consumes Symbol Universe and daily_features (from Market Data / daily job).
Produces trained model and signal scores; outcome resolver feeds accuracy back.
"""

import json
import logging
from datetime import date
from typing import List, Tuple

from app.modules.ml_engine.config import RETRAIN_WEEKDAY, METADATA_FILE, MODEL_FILE
from app.modules.ml_engine import outcome_resolver

logger = logging.getLogger(__name__)

AGENT_NAME = "ML Learning Agent"


def get_status() -> dict:
    """Return ML engine status (model_loaded, last_trained, accuracy, gpu_used, error)."""
    out = {
        "status": "stopped",
        "model_loaded": False,
        "last_trained": None,
        "error": None,
        "gpu_used": False,
    }
    try:
        if METADATA_FILE.exists():
            meta = json.loads(METADATA_FILE.read_text())
            out["last_trained"] = meta.get("last_trained")
            out["val_accuracy"] = meta.get("val_accuracy")
            out["gpu_used"] = meta.get("gpu_used", False)
        if MODEL_FILE.exists():
            out["model_loaded"] = True
        out["status"] = "running" if out["model_loaded"] else "no_model"
        fly = outcome_resolver.get_flywheel_metrics()
        out["accuracy_30d"] = fly.get("accuracy_30d")
        out["accuracy_90d"] = fly.get("accuracy_90d")
        out["resolved_count"] = fly.get("resolved_count", 0)
    except Exception as e:
        out["error"] = str(e)[:80]
    return out


def get_latest_signals(limit: int = 20) -> list:
    """Return latest signal scores per symbol (from inference if model loaded). Stub returns []."""
    return []


async def run_tick(
    *,
    force_retrain: bool = False,
    use_lightgbm: bool = False,
) -> List[Tuple[str, str]]:
    """
    Run one ML Learning Agent tick.
    On Sunday (or force_retrain): full retrain (XGBoost/LightGBM on GPU).
    Otherwise: idle message + flywheel stats.
    Returns list of (message, level) for activity log.
    """
    entries: List[Tuple[str, str]] = []
    today = date.today()
    is_retrain_day = today.weekday() == RETRAIN_WEEKDAY

    if force_retrain or is_retrain_day:
        try:
            from app.modules.ml_engine.trainer import run_full_retrain

            meta = run_full_retrain(use_lightgbm=use_lightgbm)
            if meta:
                acc = meta.get("val_accuracy", 0)
                gpu = "GPU" if meta.get("gpu_used") else "CPU"
                entries.append(
                    (
                        f"Full retrain completed ({gpu}): val_accuracy={acc:.2%}, train_rows={meta.get('train_rows', 0)}",
                        "success",
                    )
                )
            else:
                entries.append(
                    (
                        "Full retrain skipped: no daily_features or insufficient data (run daily_update job)",
                        "warning",
                    )
                )
        except Exception as e:
            logger.exception("ML retrain failed")
            entries.append((f"Retrain failed: {str(e)[:80]}", "warning"))
    else:
        days_until = (RETRAIN_WEEKDAY - today.weekday() + 7) % 7
        if days_until == 0:
            days_until = 7
        entries.append(
            (f"Idle until next Sunday retrain (in {days_until} days)", "info")
        )

    try:
        fly = outcome_resolver.get_flywheel_metrics()
        count = fly.get("resolved_count", 0)
        a30 = fly.get("accuracy_30d")
        a90 = fly.get("accuracy_90d")
        if count > 0:
            acc_msg = f"Flywheel: {count} resolved"
            if a30 is not None:
                acc_msg += f", 30d acc={a30:.1%}"
            if a90 is not None:
                acc_msg += f", 90d acc={a90:.1%}"
            entries.append((acc_msg, "info"))
    except Exception:
        pass

    status = get_status()
    if status.get("model_loaded") and status.get("last_trained"):
        entries.append(
            (f"Inference batch ready (model: {status['last_trained']})", "info")
        )
    elif not entries:
        entries.append(
            ("No model yet; run retrain on Sunday or trigger manually", "info")
        )

    return entries
