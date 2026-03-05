"""
Model Registry v1.0 — MLflow-based experiment tracking + champion/challenger arena.

Integrates with: ml_engine/__init__.py, trainer.py, xgboost_trainer.py, flywheel.py API.
Replaces ad-hoc model saving with versioned registry, paper-trade comparison, and auto-promotion.

Usage:
    from app.modules.ml_engine.model_registry import ModelRegistry
    registry = ModelRegistry()
    registry.log_training_run("xgboost_daily", model, params, metrics, feature_cols)
    champion = registry.get_champion("xgboost_daily")
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry storage paths (file-based — no external MLflow server needed)
# ---------------------------------------------------------------------------
_REGISTRY_DIR = Path(__file__).resolve().parent / "artifacts" / "registry"
_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
_MODELS_DIR = _REGISTRY_DIR / "models"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)
_RUNS_FILE = _REGISTRY_DIR / "runs.json"
_CHAMPIONS_FILE = _REGISTRY_DIR / "champions.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TrainingRun:
    """Record of one model training experiment."""
    run_id: str = ""
    model_name: str = ""
    model_type: str = ""  # "xgboost", "lstm", "lightgbm"
    version: int = 0
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    feature_cols: List[str] = field(default_factory=list)
    feature_hash: str = ""
    model_path: str = ""
    stage: str = "candidate"  # "candidate", "champion", "archived"
    created_at: str = ""
    promoted_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TrainingRun":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ArenaResult:
    """Result of champion vs challenger paper-trade comparison."""
    challenger_run_id: str = ""
    champion_run_id: str = ""
    model_name: str = ""
    challenger_metrics: Dict[str, float] = field(default_factory=dict)
    champion_metrics: Dict[str, float] = field(default_factory=dict)
    winner: str = ""  # "challenger" or "champion"
    promotion_decision: str = ""  # "promoted", "rejected", "tie"
    evaluated_at: str = ""
    evaluation_method: str = ""  # "backtest", "paper_trade", "walk_forward"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Registry implementation
# ---------------------------------------------------------------------------

class ModelRegistry:
    """
    File-based model registry with champion/challenger arena.
    No external MLflow server required — stores everything in artifacts/registry/.
    Optional MLflow integration if mlflow is installed.
    """

    def __init__(self, use_mlflow: bool = False):
        self.use_mlflow = use_mlflow and self._check_mlflow()
        self._runs: List[Dict] = self._load_runs()
        self._champions: Dict[str, str] = self._load_champions()  # model_name -> run_id

    # --- Persistence -------------------------------------------------------

    @staticmethod
    def _load_runs() -> List[Dict]:
        if _RUNS_FILE.exists():
            try:
                return json.loads(_RUNS_FILE.read_text())
            except Exception:
                return []
        return []

    def _save_runs(self):
        tmp = _RUNS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._runs, indent=2, default=str))
        tmp.replace(_RUNS_FILE)

    @staticmethod
    def _load_champions() -> Dict[str, str]:
        if _CHAMPIONS_FILE.exists():
            try:
                return json.loads(_CHAMPIONS_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save_champions(self):
        tmp = _CHAMPIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._champions, indent=2))
        tmp.replace(_CHAMPIONS_FILE)

    @staticmethod
    def _check_mlflow() -> bool:
        try:
            import mlflow
            return True
        except ImportError:
            log.info("mlflow not installed; using file-based registry only.")
            return False

    # --- Core API ----------------------------------------------------------

    def log_training_run(
        self,
        model_name: str,
        model: Any,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        feature_cols: List[str],
        model_type: str = "xgboost",
        notes: str = "",
    ) -> TrainingRun:
        """
        Log a completed training run. Saves model artifact and metadata.
        Does NOT promote — call evaluate_and_promote() separately.

        Args:
            model_name: Logical model name (e.g. "xgboost_daily", "lstm_daily").
            model: Trained model object (XGBClassifier, LGBMClassifier, or torch state_dict path).
            params: Hyperparameters used.
            metrics: Evaluation metrics (val_accuracy, sharpe, hit_rate, etc.).
            feature_cols: Feature columns used for training.
            model_type: One of "xgboost", "lightgbm", "lstm".
            notes: Optional human-readable notes.

        Returns:
            TrainingRun record.
        """
        # Generate run ID
        run_id = f"{model_name}_{int(time.time())}_{hashlib.md5(str(params).encode()).hexdigest()[:6]}"

        # Determine version
        existing = [r for r in self._runs if r.get("model_name") == model_name]
        version = len(existing) + 1

        # Save model artifact
        model_dir = _MODELS_DIR / run_id
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self._save_model(model, model_type, model_dir)

        # Feature hash for drift tracking
        feature_hash = hashlib.md5(",".join(sorted(feature_cols)).encode()).hexdigest()[:8]

        run = TrainingRun(
            run_id=run_id,
            model_name=model_name,
            model_type=model_type,
            version=version,
            params={k: str(v) for k, v in params.items()},
            metrics=metrics,
            feature_cols=feature_cols,
            feature_hash=feature_hash,
            model_path=str(model_path),
            stage="candidate",
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )

        self._runs.append(run.to_dict())
        self._save_runs()

        # Optional MLflow logging
        if self.use_mlflow:
            self._log_to_mlflow(run)

        log.info("Logged run %s (v%d): %s metrics=%s", run_id, version, model_name, metrics)
        return run

    def evaluate_and_promote(
        self,
        model_name: str,
        challenger_run_id: str,
        evaluation_fn: Optional[callable] = None,
        min_sharpe_improvement: float = 0.05,
        min_accuracy_improvement: float = 0.01,
    ) -> ArenaResult:
        """
        Compare challenger to current champion. Promote if significantly better.

        Args:
            model_name: Logical model name.
            challenger_run_id: Run ID of the challenger model.
            evaluation_fn: Optional callable(model_path, model_type) -> Dict[str, float].
                           If None, uses logged metrics.
            min_sharpe_improvement: Minimum Sharpe ratio improvement to promote.
            min_accuracy_improvement: Minimum accuracy improvement to promote.

        Returns:
            ArenaResult with winner and promotion decision.
        """
        challenger = self._get_run(challenger_run_id)
        champion_id = self._champions.get(model_name)

        if not challenger:
            log.error("Challenger run %s not found", challenger_run_id)
            return ArenaResult(promotion_decision="error")

        challenger_metrics = challenger.get("metrics", {})

        # If no champion exists, auto-promote
        if not champion_id:
            log.info("No existing champion for %s — auto-promoting %s", model_name, challenger_run_id)
            self._promote(challenger_run_id, model_name)
            return ArenaResult(
                challenger_run_id=challenger_run_id,
                champion_run_id="",
                model_name=model_name,
                challenger_metrics=challenger_metrics,
                champion_metrics={},
                winner="challenger",
                promotion_decision="promoted",
                evaluated_at=datetime.now(timezone.utc).isoformat(),
                evaluation_method="auto_first",
            )

        champion = self._get_run(champion_id)
        champion_metrics = champion.get("metrics", {}) if champion else {}

        # Run evaluation if custom function provided
        if evaluation_fn is not None:
            try:
                challenger_metrics = evaluation_fn(
                    challenger.get("model_path"), challenger.get("model_type")
                )
                champion_metrics = evaluation_fn(
                    champion.get("model_path"), champion.get("model_type")
                )
            except Exception as e:
                log.warning("Evaluation function failed: %s", e)

        # Compare metrics
        winner, decision = self._compare_metrics(
            challenger_metrics, champion_metrics,
            min_sharpe_improvement, min_accuracy_improvement
        )

        if decision == "promoted":
            self._promote(challenger_run_id, model_name)

        result = ArenaResult(
            challenger_run_id=challenger_run_id,
            champion_run_id=champion_id or "",
            model_name=model_name,
            challenger_metrics=challenger_metrics,
            champion_metrics=champion_metrics,
            winner=winner,
            promotion_decision=decision,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            evaluation_method="metric_comparison",
        )

        log.info("Arena result for %s: winner=%s decision=%s", model_name, winner, decision)
        return result

    def get_champion(self, model_name: str) -> Optional[Dict]:
        """Get the current champion run for a model name."""
        run_id = self._champions.get(model_name)
        if run_id:
            return self._get_run(run_id)
        return None

    def get_champion_model_path(self, model_name: str) -> Optional[str]:
        """Get filesystem path to the champion model artifact."""
        champion = self.get_champion(model_name)
        if champion:
            return champion.get("model_path")
        return None

    def get_run_history(self, model_name: str, limit: int = 20) -> List[Dict]:
        """Get recent training runs for a model."""
        runs = [r for r in self._runs if r.get("model_name") == model_name]
        return runs[-limit:]

    def get_all_champions(self) -> Dict[str, Dict]:
        """Get all current champions."""
        result = {}
        for name, run_id in self._champions.items():
            run = self._get_run(run_id)
            if run:
                result[name] = run
        return result

    def evaluate_and_promote_multi_window(
        self,
        model_name: str,
        challenger_run_id: str,
        predictions: "np.ndarray",
        actuals: "np.ndarray",
        prices: "Optional[np.ndarray]" = None,
    ) -> Dict[str, Any]:
        """Multi-window evaluation gate for champion/challenger promotion.

        Uses the anti-reward-hacking multi-window evaluator:
        ALL windows (30, 60, 90, 252d) must pass ALL thresholds.

        Returns:
            Dict with eval_results, promoted (bool), and arena_result.
        """
        from app.modules.ml_engine.multi_window_evaluator import (
            evaluate_model_all_windows,
            should_promote,
        )

        eval_results = evaluate_model_all_windows(predictions, actuals, prices)
        promoted = should_promote(eval_results)

        # Store eval results in DuckDB
        try:
            from app.data.feature_store import feature_store
            for window, metrics in eval_results.get("windows", {}).items():
                eval_id = f"{challenger_run_id}_w{window}"
                feature_store.store_model_eval(
                    eval_id=eval_id,
                    model_id=challenger_run_id,
                    window=str(window),
                    metrics=metrics,
                )
        except Exception as e:
            log.warning("Failed to store eval results: %s", e)

        arena_result = None
        if promoted:
            arena_result = self.evaluate_and_promote(model_name, challenger_run_id)
            log.info("Multi-window PASSED — promoted %s for %s", challenger_run_id, model_name)
        else:
            log.info(
                "Multi-window FAILED for %s — failing windows: %s",
                challenger_run_id, eval_results.get("failing_windows"),
            )

        return {
            "eval_results": eval_results,
            "promoted": promoted,
            "arena_result": arena_result.to_dict() if arena_result else None,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get registry status for API/dashboard."""
        return {
            "total_runs": len(self._runs),
            "champions": {name: self._get_run(rid).get("metrics", {})
                         for name, rid in self._champions.items()
                         if self._get_run(rid)},
            "latest_runs": self._runs[-5:] if self._runs else [],
            "registry_dir": str(_REGISTRY_DIR),
        }

    # --- Internal helpers --------------------------------------------------

    def _get_run(self, run_id: str) -> Optional[Dict]:
        for r in self._runs:
            if r.get("run_id") == run_id:
                return r
        return None

    def _promote(self, run_id: str, model_name: str):
        """Promote run to champion, archive previous champion."""
        old_champion_id = self._champions.get(model_name)
        if old_champion_id:
            for r in self._runs:
                if r.get("run_id") == old_champion_id:
                    r["stage"] = "archived"

        for r in self._runs:
            if r.get("run_id") == run_id:
                r["stage"] = "champion"
                r["promoted_at"] = datetime.now(timezone.utc).isoformat()

        self._champions[model_name] = run_id
        self._save_champions()
        self._save_runs()
        log.info("Promoted %s to champion for %s", run_id, model_name)

    @staticmethod
    def _compare_metrics(
        challenger: Dict[str, float],
        champion: Dict[str, float],
        min_sharpe: float,
        min_accuracy: float,
    ) -> tuple:
        """Compare metrics and decide winner."""
        # Priority: sharpe > val_accuracy > hit_rate
        c_sharpe = challenger.get("sharpe", challenger.get("cv_accuracy", 0))
        h_sharpe = champion.get("sharpe", champion.get("cv_accuracy", 0))
        c_acc = challenger.get("val_accuracy", 0)
        h_acc = champion.get("val_accuracy", 0)

        sharpe_better = (c_sharpe - h_sharpe) >= min_sharpe
        acc_better = (c_acc - h_acc) >= min_accuracy

        if sharpe_better or acc_better:
            return "challenger", "promoted"
        elif c_sharpe >= h_sharpe and c_acc >= h_acc:
            return "challenger", "tie"
        else:
            return "champion", "rejected"

    @staticmethod
    def _save_model(model: Any, model_type: str, model_dir: Path) -> Path:
        """Save model artifact to disk."""
        if model_type == "xgboost":
            path = model_dir / "model.json"
            try:
                model.save_model(str(path))
            except AttributeError:
                # XGBClassifier vs Booster
                try:
                    model.get_booster().save_model(str(path))
                except Exception:
                    path = model_dir / "model.ubj"
                    import joblib
                    joblib.dump(model, str(path))
            return path
        elif model_type == "lightgbm":
            path = model_dir / "model.txt"
            try:
                model.booster_.save_model(str(path))
            except AttributeError:
                import joblib
                path = model_dir / "model.pkl"
                joblib.dump(model, str(path))
            return path
        elif model_type == "lstm":
            path = model_dir / "model.pt"
            try:
                import torch
                if hasattr(model, '_module'):
                    torch.save(model._module.state_dict(), str(path))
                else:
                    torch.save(model.state_dict(), str(path))
            except ImportError:
                log.warning("torch not available for LSTM save")
            return path
        else:
            import joblib
            path = model_dir / "model.pkl"
            joblib.dump(model, str(path))
            return path

    def _log_to_mlflow(self, run: TrainingRun):
        """Optional MLflow logging (if mlflow is installed)."""
        try:
            import mlflow
            mlflow.set_experiment(f"elite-trading-{run.model_name}")
            with mlflow.start_run(run_name=run.run_id):
                mlflow.log_params(run.params)
                mlflow.log_metrics(run.metrics)
                mlflow.log_param("feature_count", len(run.feature_cols))
                mlflow.log_param("feature_hash", run.feature_hash)
                if Path(run.model_path).exists():
                    mlflow.log_artifact(run.model_path)
        except Exception as e:
            log.warning("MLflow logging failed: %s", e)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get or create the global ModelRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry(use_mlflow=False)
    return _registry
