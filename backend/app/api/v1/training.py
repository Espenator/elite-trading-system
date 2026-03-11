"""
Model training API — datasets, training runs, progress, and metrics.

This file is DB-backed and executes real training via ml_training.py.
No in-memory mock structures, no simulated metrics, no fabricated dates.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from app.core.security import require_auth
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.services.ml_training import trainer
from app.services.training_store import TrainingRunCreate, training_store

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request models (keep frontend contract) ---------------------------------
class StartTrainingRequest(BaseModel):
    modelName: str
    datasetSource: str
    algorithm: str
    epochs: int = 100
    validationSplit: str = "20%"


class SaveConfigRequest(BaseModel):
    modelName: str
    datasetSource: str
    algorithm: str
    epochs: int
    validationSplit: str


class DeployRequest(BaseModel):
    modelName: Optional[str] = None
    version: Optional[str] = None


# --- Internal helpers --------------------------------------------------------
def _run_training_job(run_db_id: int, body: StartTrainingRequest) -> None:
    """
    Background training job.
    Persists progress to DB; respects stop requests (best-effort).
    """
    try:

        def stop_check() -> bool:
            status = training_store.get_run_status(run_db_id)
            return (status or "").lower().strip() == "stop_requested"

        def progress_callback(payload: Dict[str, Any]) -> None:
            # payload expected: {epochsCompleted,totalEpochs,accuracy,loss}
            training_store.upsert_progress(
                run_db_id=run_db_id,
                epochs_completed=int(payload.get("epochsCompleted") or 0),
                total_epochs=int(payload.get("totalEpochs") or 0),
                accuracy=payload.get("accuracy"),
                loss=payload.get("loss"),
            )

        result = trainer.train(
            model_name=body.modelName,
            window_days=252,
            epochs=int(body.epochs),
            batch_size=32,
            lr=0.001,
            run_db_id=run_db_id,
            dataset_source=body.datasetSource,
            algorithm=body.algorithm,
            validation_split=body.validationSplit,
            progress_callback=progress_callback,
            stop_check=stop_check,
        )

        if isinstance(result, dict) and result.get("stopped"):
            training_store.set_run_stopped(run_db_id, note="Stopped by user request")
            return

        if isinstance(result, dict) and result.get("error"):
            training_store.set_run_failed(run_db_id, error=str(result.get("error")))
            return

        # Ensure run row has a result_json even if ml_training already updated it.
        training_store.set_run_success(
            run_db_id, result=result if isinstance(result, dict) else {"result": result}
        )

    except Exception as e:
        logger.exception("Training job failed")
        training_store.set_run_failed(run_db_id, error=str(e))


# --- Endpoints ----------------------------------------------------------------
@router.get("", response_model=dict)
@router.get("/", response_model=dict)
async def get_training_summary():
    """Summary for Signal Intelligence / dashboards: datasets, runs, last run (avoids 404 on GET /api/v1/training)."""
    try:
        datasets = training_store.list_datasets_payload()
        runs = training_store.list_runs(limit=5)
        progress = training_store.get_active_progress_payload()
        return {
            "datasets": datasets or [],
            "runs": runs or [],
            "activeProgress": progress,
            "last_retrain": (runs[0] or {}).get("createdAt") if runs else None,
        }
    except Exception as e:
        logger.debug("Training summary failed: %s", e)
        return {
            "datasets": [],
            "runs": [],
            "activeProgress": None,
            "last_retrain": None,
        }


@router.get("/datasets", response_model=List[dict])
async def get_datasets():
    """List all datasets available for training (real DB-derived)."""
    return training_store.list_datasets_payload()


@router.get("/runs", response_model=List[dict])
async def get_training_runs(limit: int = 50):
    """List training run history (real DB rows)."""
    return training_store.list_runs(limit=limit)


@router.get("/runs/active/progress")
async def get_active_progress():
    """Get current training run progress if one is active (real DB-backed)."""
    return training_store.get_active_progress_payload()


@router.get("/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get a single run's details including metrics and feature importance (real DB-backed)."""
    try:
        return training_store.get_run_details_payload(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@router.post("/runs", dependencies=[Depends(require_auth)])
async def start_training(body: StartTrainingRequest, background_tasks: BackgroundTasks):
    """
    Start a new training run.
    Real async background training; progress available via /runs/active/progress.
    """
    if training_store.has_active_run():
        raise HTTPException(
            status_code=409, detail="A training run is already in progress"
        )

    run_db_id = training_store.create_run(
        TrainingRunCreate(
            model_name=body.modelName,
            dataset_source=body.datasetSource,
            algorithm=body.algorithm,
            epochs=int(body.epochs),
            validation_split=body.validationSplit,
            params={
                "modelName": body.modelName,
                "datasetSource": body.datasetSource,
                "algorithm": body.algorithm,
                "epochs": int(body.epochs),
                "validationSplit": body.validationSplit,
            },
        )
    )

    background_tasks.add_task(_run_training_job, run_db_id, body)

    return {"runId": f"MT-{run_db_id:06d}", "message": "Training started"}


@router.post("/runs/{run_id}/stop", dependencies=[Depends(require_auth)])
async def stop_training(run_id: str):
    """
    Stop an active training run (best-effort).
    This sets a stop_requested flag in DB; training loop cooperatively stops.
    """
    run_db_id = None
    try:
        run_db_id = int(str(run_id).replace("MT-", "").strip())
    except Exception:
        raise HTTPException(status_code=404, detail="No active run with this ID")

    ok = training_store.request_stop(run_db_id)
    if not ok:
        raise HTTPException(status_code=404, detail="No active run with this ID")

    return {"runId": f"MT-{run_db_id:06d}", "message": "Stop requested"}


@router.post("/retrain", dependencies=[Depends(require_auth)])
async def retrain_model(body: dict, background_tasks: BackgroundTasks):
    """
    Trigger a retrain for a specific model by ID.
    Frontend sends: { modelId: "xgboost_v2" }
    Maps to the existing training pipeline with defaults.
    """
    model_id = body.get("modelId", "xgboost_default")
    if training_store.has_active_run():
        raise HTTPException(
            status_code=409, detail="A training run is already in progress"
        )

    run_db_id = training_store.create_run(
        TrainingRunCreate(
            model_name=model_id,
            dataset_source="retrain",
            algorithm=body.get("algorithm", "xgboost"),
            epochs=int(body.get("epochs", 100)),
            validation_split=body.get("validationSplit", "20%"),
            params={"modelId": model_id, "trigger": "manual_retrain"},
        )
    )

    req = StartTrainingRequest(
        modelName=model_id,
        datasetSource="retrain",
        algorithm=body.get("algorithm", "xgboost"),
        epochs=int(body.get("epochs", 100)),
        validationSplit=body.get("validationSplit", "20%"),
    )
    background_tasks.add_task(_run_training_job, run_db_id, req)

    return {"ok": True, "runId": f"MT-{run_db_id:06d}", "message": f"Retrain started for {model_id}"}


@router.get("/models/compare", response_model=List[dict])
async def get_model_comparison(limit: int = 20):
    """List model comparison metrics from models_registry (real DB-backed)."""
    return training_store.model_comparison_payload(limit=limit)


@router.post("/config", dependencies=[Depends(require_auth)])
async def save_config(body: SaveConfigRequest):
    """Save training configuration to DB (real persistence)."""
    training_store.save_config(body.model_dump())
    return {"saved": True, "message": "Configuration saved"}


@router.post("/deploy", dependencies=[Depends(require_auth)])
async def deploy_model(body: Optional[DeployRequest] = None):
    """
    Mark a trained model as active in models_registry (real DB-backed).
    Does NOT claim a live prediction endpoint unless you actually have one.
    """
    body = body or DeployRequest()
    return training_store.deploy_model(model_name=body.modelName, version=body.version)
