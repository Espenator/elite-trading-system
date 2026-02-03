"""
Model training API — datasets, training runs, progress, and metrics.

Provides endpoints for the Model Training UI. Data is in-memory until
the ML engine is fully integrated; same API contract will be used.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()

# --- In-memory store (replace with DB/ML engine when ready) ---
DATASETS = [
    {"name": "FinancialTimeSeries_V1", "size": "1.2 GB", "lastUpdated": "2023-11-20", "status": "Ready"},
    {"name": "MarketSentiment_V1", "size": "850 MB", "lastUpdated": "2023-11-18", "status": "Processing"},
    {"name": "AlternativeData_V3", "size": "2.1 GB", "lastUpdated": "2023-11-15", "status": "Error"},
    {"name": "TechnicalIndicators_V2", "size": "650 MB", "lastUpdated": "2023-11-12", "status": "Ready"},
]

# Mutable list for runs so we can append new runs
TRAINING_RUNS: List[dict] = [
    {"runId": "MT-001", "modelName": "XGBoost_V1", "dataset": "FinancialTimeSeries_V1", "algorithm": "XGBoost",
     "startTime": "2023-12-10 10:00", "endTime": "2023-12-10 10:15", "status": "Completed", "accuracy": "92.5%", "loss": "0.22"},
    {"runId": "MT-002", "modelName": "RandomForest_V2", "dataset": "FinancialTimeSeries_V1", "algorithm": "Random Forest",
     "startTime": "2023-12-09 14:30", "endTime": "2023-12-09 14:52", "status": "Completed", "accuracy": "89.3%", "loss": "0.28"},
    {"runId": "MT-003", "modelName": "NeuralNet_V3", "dataset": "FinancialTimeSeries_V1", "algorithm": "Neural Network",
     "startTime": "2023-12-08 09:15", "endTime": "2023-12-08 10:00", "status": "Completed", "accuracy": "91.0%", "loss": "0.25"},
    {"runId": "MT-004", "modelName": "XGBoost_V2", "dataset": "AlternativeData_V3", "algorithm": "XGBoost",
     "startTime": "2023-12-07 11:00", "endTime": "2023-12-07 11:05", "status": "Failed", "accuracy": "N/A", "loss": "0.45"},
]

# Active run progress (one at a time for UI)
ACTIVE_RUN: Optional[dict] = None

MODEL_COMPARISON = [
    {"model": "XGBoost_V1", "accuracy": 92.5, "precision": 88.1, "recall": 90.3, "f1Score": 89.2, "trainingTime": "15m", "datasetSize": "1.2 GB"},
    {"model": "RandomForest_V2", "accuracy": 89.3, "precision": 85.2, "recall": 87.8, "f1Score": 86.5, "trainingTime": "22m", "datasetSize": "1.2 GB"},
    {"model": "NeuralNet_V3", "accuracy": 91.0, "precision": 87.5, "recall": 89.1, "f1Score": 88.3, "trainingTime": "45m", "datasetSize": "1.2 GB"},
]

# Metrics and feature importance per run (keyed by runId)
RUN_METRICS = {
    "MT-001": {
        "performanceMetrics": {
            "accuracy": 92.5, "precision": 88.1, "recall": 90.3, "f1Score": 89.2,
            "confusionMatrix": {"truePositive": 850, "falseNegative": 50, "falsePositive": 70, "trueNegative": 930},
        },
        "featureImportance": [
            {"name": "Volume", "importance": 95}, {"name": "Change", "importance": 82},
            {"name": "RSIDivergence", "importance": 75}, {"name": "MACDCrossover", "importance": 68},
            {"name": "VIXProximity", "importance": 55}, {"name": "Market Regime", "importance": 48},
            {"name": "Historical Volatility", "importance": 42},
        ],
    },
    "MT-002": {
        "performanceMetrics": {
            "accuracy": 89.3, "precision": 85.2, "recall": 87.8, "f1Score": 86.5,
            "confusionMatrix": {"truePositive": 820, "falseNegative": 80, "falsePositive": 90, "trueNegative": 910},
        },
        "featureImportance": [
            {"name": "Volume", "importance": 88}, {"name": "Change", "importance": 79},
            {"name": "RSIDivergence", "importance": 72}, {"name": "MACDCrossover", "importance": 65},
        ],
    },
    "MT-003": {
        "performanceMetrics": {
            "accuracy": 91.0, "precision": 87.5, "recall": 89.1, "f1Score": 88.3,
            "confusionMatrix": {"truePositive": 840, "falseNegative": 60, "falsePositive": 75, "trueNegative": 925},
        },
        "featureImportance": [
            {"name": "Volume", "importance": 92}, {"name": "Change", "importance": 85},
            {"name": "RSIDivergence", "importance": 78}, {"name": "MACDCrossover", "importance": 70},
        ],
    },
}

# Default metrics for runs without stored metrics
DEFAULT_METRICS = {
    "performanceMetrics": {
        "accuracy": 0, "precision": 0, "recall": 0, "f1Score": 0,
        "confusionMatrix": {"truePositive": 0, "falseNegative": 0, "falsePositive": 0, "trueNegative": 0},
    },
    "featureImportance": [],
}


# --- Request/Response models ---
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


# --- Endpoints ---
@router.get("/datasets", response_model=List[dict])
async def get_datasets():
    """List all datasets available for training."""
    return DATASETS


@router.get("/runs", response_model=List[dict])
async def get_training_runs():
    """List training run history (all runs)."""
    return TRAINING_RUNS


@router.get("/runs/active/progress")
async def get_active_progress():
    """Get current training run progress if one is active."""
    if ACTIVE_RUN is None:
        return {"active": False, "progress": None}
    return {"active": True, "progress": ACTIVE_RUN.get("progress"), "runId": ACTIVE_RUN.get("runId")}


@router.get("/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get a single run's details including metrics and feature importance."""
    run = next((r for r in TRAINING_RUNS if r["runId"] == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    metrics = RUN_METRICS.get(run_id, DEFAULT_METRICS)
    return {"run": run, **metrics}


def _simulate_training(run_id: str, total_epochs: int):
    """Background task: simulate progress and complete the run."""
    global ACTIVE_RUN, TRAINING_RUNS
    import time
    for step in range(total_epochs + 1):
        if ACTIVE_RUN is None or ACTIVE_RUN.get("runId") != run_id:
            return
        # Simulate: accuracy goes up, loss goes down
        acc = min(92, (step / total_epochs) * 95)
        loss = max(0.12, 1.0 - (step / total_epochs) * 0.88)
        ACTIVE_RUN["progress"] = {
            "epochsCompleted": step,
            "totalEpochs": total_epochs,
            "accuracy": round(acc, 1),
            "loss": round(loss, 3),
        }
        time.sleep(0.15)  # ~7.5s for 50 epochs, ~15s for 100
    # Complete the run
    run = next((r for r in TRAINING_RUNS if r["runId"] == run_id), None)
    if run and ACTIVE_RUN and ACTIVE_RUN.get("runId") == run_id:
        p = ACTIVE_RUN.get("progress") or {}
        run["status"] = "Completed"
        run["endTime"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        run["accuracy"] = f"{p.get('accuracy', 0)}%"
        run["loss"] = str(p.get("loss", 0.12))
    ACTIVE_RUN = None


@router.post("/runs")
async def start_training(body: StartTrainingRequest, background_tasks: BackgroundTasks):
    """Start a new training run. Returns runId; progress available via /runs/active/progress."""
    global ACTIVE_RUN
    if ACTIVE_RUN is not None:
        raise HTTPException(status_code=409, detail="A training run is already in progress")
    run_id = f"MT-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_run = {
        "runId": run_id,
        "modelName": body.modelName,
        "dataset": body.datasetSource,
        "algorithm": body.algorithm,
        "startTime": now,
        "endTime": "",
        "status": "Running",
        "accuracy": "N/A",
        "loss": "N/A",
    }
    TRAINING_RUNS.insert(0, new_run)
    ACTIVE_RUN = {
        "runId": run_id,
        "progress": {
            "epochsCompleted": 0,
            "totalEpochs": body.epochs,
            "accuracy": 0,
            "loss": 1.0,
        },
        "epochs": body.epochs,
    }
    background_tasks.add_task(_simulate_training, run_id, body.epochs)
    return {"runId": run_id, "message": "Training started"}


@router.post("/runs/{run_id}/stop")
async def stop_training(run_id: str):
    """Stop an active training run (stub: marks as Completed with current progress)."""
    global ACTIVE_RUN
    if ACTIVE_RUN is None or ACTIVE_RUN.get("runId") != run_id:
        raise HTTPException(status_code=404, detail="No active run with this ID")
    run = next((r for r in TRAINING_RUNS if r["runId"] == run_id), None)
    if run:
        progress = ACTIVE_RUN.get("progress") or {}
        run["status"] = "Completed"
        run["endTime"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        run["accuracy"] = f"{progress.get('accuracy', 0)}%"
        run["loss"] = str(progress.get("loss", 0.2))
    ACTIVE_RUN = None
    return {"runId": run_id, "message": "Training stopped"}


@router.get("/models/compare", response_model=List[dict])
async def get_model_comparison():
    """List model comparison metrics (accuracy, precision, recall, etc.)."""
    return MODEL_COMPARISON


@router.post("/config")
async def save_config(body: SaveConfigRequest):
    """Save training configuration (stub: acknowledged)."""
    return {"saved": True, "message": "Configuration saved"}


@router.post("/deploy")
async def deploy_model():
    """Request deployment of current best model (stub)."""
    return {"deployed": True, "message": "Deployment requested", "endpoint": "https://api.example.com/v1/predict"}
