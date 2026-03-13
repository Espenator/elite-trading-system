"""Tests for ModelRegistry cleanup — archive/remove old candidate and archived runs."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import pytest

from app.modules.ml_engine.model_registry import ModelRegistry, TrainingRun, _RUNS_FILE, _MODELS_DIR


@pytest.fixture
def registry_tmp(tmp_path):
    """ModelRegistry with runs and champions stored under tmp_path."""
    runs_file = tmp_path / "runs.json"
    champs_file = tmp_path / "champions.json"
    models_dir = tmp_path / "models"
    models_dir.mkdir(exist_ok=True)

    with patch("app.modules.ml_engine.model_registry._RUNS_FILE", runs_file), \
         patch("app.modules.ml_engine.model_registry._CHAMPIONS_FILE", champs_file), \
         patch("app.modules.ml_engine.model_registry._MODELS_DIR", models_dir):
        reg = ModelRegistry(use_mlflow=False)
        reg._runs = []
        reg._champions = {}
        yield reg


def _make_run(run_id: str, created_at: str, stage: str = "candidate", model_path: str = ""):
    return {
        "run_id": run_id,
        "model_name": "xgboost_daily",
        "model_type": "xgboost",
        "version": 1,
        "params": {},
        "metrics": {"val_accuracy": 0.6},
        "feature_cols": [],
        "stage": stage,
        "created_at": created_at,
        "model_path": model_path or f"/fake/models/{run_id}/model.json",
    }


def test_cleanup_removes_old_candidate_and_archived_runs(registry_tmp):
    """Cleanup removes candidate and archived runs older than 30 days; keeps champions."""
    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=45)).isoformat()
    recent_date = (now - timedelta(days=5)).isoformat()

    reg = registry_tmp
    reg._runs = [
        _make_run("old_candidate", old_date, "candidate"),
        _make_run("old_archived", old_date, "archived"),
        _make_run("recent_candidate", recent_date, "candidate"),
        _make_run("champion_run", old_date, "champion"),
    ]
    reg._champions = {"xgboost_daily": "champion_run"}
    reg._save_runs()
    reg._save_champions()

    result = reg.cleanup_old_runs(older_than_days=30)

    assert result["removed_count"] == 2
    assert "old_candidate" in result["removed_run_ids"]
    assert "old_archived" in result["removed_run_ids"]
    assert "champion_run" not in result["removed_run_ids"]
    assert "recent_candidate" not in result["removed_run_ids"]

    remaining = {r["run_id"] for r in reg._runs}
    assert "old_candidate" not in remaining
    assert "old_archived" not in remaining
    assert "recent_candidate" in remaining
    assert "champion_run" in remaining


def test_cleanup_keeps_recent_candidates(registry_tmp):
    """Runs newer than older_than_days are not removed."""
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()

    reg = registry_tmp
    reg._runs = [_make_run("recent_cand", recent, "candidate")]
    reg._save_runs()

    result = reg.cleanup_old_runs(older_than_days=30)
    assert result["removed_count"] == 0
    assert len(reg._runs) == 1


def test_cleanup_respects_stages_param(registry_tmp):
    """Only specified stages are removed when stages= is provided."""
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=40)).isoformat()

    reg = registry_tmp
    reg._runs = [
        _make_run("old_candidate", old, "candidate"),
        _make_run("old_archived", old, "archived"),
    ]
    reg._save_runs()

    result = reg.cleanup_old_runs(older_than_days=30, stages=["candidate"])
    assert result["removed_count"] == 1
    assert "old_candidate" in result["removed_run_ids"]
    assert "old_archived" not in result["removed_run_ids"]
    assert any(r["run_id"] == "old_archived" for r in reg._runs)


def test_cleanup_no_op_when_all_recent(registry_tmp):
    """When no runs are older than threshold, removed_count is 0."""
    now = datetime.now(timezone.utc)
    reg = registry_tmp
    reg._runs = [
        _make_run("r1", (now - timedelta(days=1)).isoformat(), "candidate"),
        _make_run("r2", (now - timedelta(days=29)).isoformat(), "archived"),
    ]
    reg._save_runs()

    result = reg.cleanup_old_runs(older_than_days=30)
    assert result["removed_count"] == 0
    assert len(reg._runs) == 2
