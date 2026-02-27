"""Flywheel API v2.0 — ML accuracy, outcome feedback, and Flywheel Engine dashboard.

Enhanced with:
- Model Registry status + champion/challenger info
- Drift Monitor status + drift history
- Feature Pipeline manifest info
- Flywheel health aggregate endpoint

GET /api/v1/flywheel returns metrics from DB (populated by ML pipeline).
POST /api/v1/flywheel/record allows ML modules to submit accuracy snapshots.
GET /api/v1/flywheel/engine returns full flywheel engine status.
No mock data. No fabricated numbers.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    accuracies = [h.get("accuracy", 0) for h in recent if isinstance(h, dict)]
    return round(sum(accuracies) / max(len(accuracies), 1), 4)


# ---------------------------------------------------------------------------
# Core Flywheel Endpoints (preserved from v1)
# ---------------------------------------------------------------------------

@router.get("/flywheel")
async def get_flywheel():
    """Return current flywheel accuracy metrics and history."""
    data = _get_flywheel_data()
    return {
        "accuracy30d": data.get("accuracy30d", 0.0),
        "accuracy90d": data.get("accuracy90d", 0.0),
        "resolvedSignals": data.get("resolvedSignals", 0),
        "pendingResolution": data.get("pendingResolution", 0),
        "history": data.get("history", [])[-90:],
    }


@router.post("/flywheel/record")
async def record_flywheel(record: FlywheelRecord):
    """Submit a flywheel accuracy snapshot (called by ML training/evaluation)."""
    data = _get_flywheel_data()
    history = data.get("history", [])

    entry = {
        "date": record.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "accuracy": round(record.accuracy, 4),
    }
    history.append(entry)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    resolved = data.get("resolvedSignals", 0)
    pending = data.get("pendingResolution", 0)
    if record.resolvedSignals is not None:
        resolved = record.resolvedSignals
    if record.pendingResolution is not None:
        pending = record.pendingResolution

    updated = {
        "accuracy30d": _compute_accuracy(history, 30),
        "accuracy90d": _compute_accuracy(history, 90),
        "resolvedSignals": resolved,
        "pendingResolution": pending,
        "history": history,
    }
    _save_flywheel_data(updated)

    try:
        await broadcast_ws({"type": "flywheel_update", "data": updated})
    except Exception:
        pass

    return {"status": "recorded", "entry": entry}


# ---------------------------------------------------------------------------
# Flywheel Engine Endpoints (v2.0 enhancements)
# ---------------------------------------------------------------------------

@router.get("/flywheel/engine")
async def get_flywheel_engine():
    """Aggregate flywheel engine status: registry + drift + features + accuracy."""
    engine_status: Dict[str, Any] = {
        "flywheel_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Accuracy metrics
    flywheel_data = _get_flywheel_data()
    engine_status["accuracy"] = {
        "accuracy_30d": flywheel_data.get("accuracy30d", 0.0),
        "accuracy_90d": flywheel_data.get("accuracy90d", 0.0),
        "resolved_signals": flywheel_data.get("resolvedSignals", 0),
        "pending_resolution": flywheel_data.get("pendingResolution", 0),
        "history_entries": len(flywheel_data.get("history", [])),
    }

    # Model Registry status
    try:
        from app.modules.ml_engine.model_registry import get_registry
        registry = get_registry()
        engine_status["model_registry"] = registry.get_status() if hasattr(registry, 'get_status') else {"status": "loaded"}
    except ImportError:
        engine_status["model_registry"] = {"status": "not_installed"}
    except Exception as e:
        engine_status["model_registry"] = {"status": "error", "message": str(e)}

    # Drift Monitor status
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        engine_status["drift_monitor"] = monitor.get_status() if hasattr(monitor, 'get_status') else {"status": "loaded"}
    except ImportError:
        engine_status["drift_monitor"] = {"status": "not_installed"}
    except Exception as e:
        engine_status["drift_monitor"] = {"status": "error", "message": str(e)}

    # Feature Pipeline manifest
    try:
        from app.modules.ml_engine.feature_pipeline import FeatureManifest
        manifest = FeatureManifest.load()
        engine_status["feature_pipeline"] = {
            "version": manifest.version,
            "n_features": manifest.n_features,
            "n_labels": manifest.n_labels,
            "data_hash": manifest.data_hash,
            "created_at": manifest.created_at,
        } if manifest.feature_cols else {"status": "no_manifest"}
    except ImportError:
        engine_status["feature_pipeline"] = {"status": "not_installed"}
    except Exception as e:
        engine_status["feature_pipeline"] = {"status": "error", "message": str(e)}

    return engine_status


@router.get("/flywheel/registry")
async def get_registry_status():
    """Get model registry status and champion models."""
    try:
        from app.modules.ml_engine.model_registry import get_registry
        registry = get_registry()
        return registry.get_status() if hasattr(registry, 'get_status') else {"status": "loaded"}
    except ImportError:
        return {"status": "not_installed", "message": "model_registry module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/flywheel/drift")
async def get_drift_status():
    """Get drift monitor status and recent drift history."""
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        status = monitor.get_status() if hasattr(monitor, 'get_status') else {}
        history = monitor.get_drift_history(limit=20) if hasattr(monitor, 'get_drift_history') else []
        return {**status, "recent_checks": history}
    except ImportError:
        return {"status": "not_installed", "message": "drift_detector module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/flywheel/features")
async def get_feature_pipeline_status():
    """Get feature pipeline manifest and configuration."""
    try:
        from app.modules.ml_engine.feature_pipeline import FeatureManifest, PIPELINE_VERSION
        manifest = FeatureManifest.load()
        return {
            "pipeline_version": PIPELINE_VERSION,
            "manifest": {
                "version": manifest.version,
                "feature_cols": manifest.feature_cols,
                "label_cols": manifest.label_cols,
                "n_features": manifest.n_features,
                "n_labels": manifest.n_labels,
                "data_hash": manifest.data_hash,
                "created_at": manifest.created_at,
            } if manifest.feature_cols else None,
        }
    except ImportError:
        return {"status": "not_installed", "message": "feature_pipeline module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
