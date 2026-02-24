"""XGBoost GPU trainer for Elite Trading System.

APEX Phase 2 – XGBoost companion model:
- GPU-accelerated training via tree_method='gpu_hist' (falls back to 'hist' on CPU)
- Grid search over key hyperparameters with cross-validation
- Feature importance extraction and logging
- Reads from DuckDB daily_features (same schema as LSTM trainer)
- Saves best model artefact to MODEL_ARTIFACTS_PATH
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from itertools import product as iter_product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature / target columns (shared with LSTM trainer)
# ---------------------------------------------------------------------------
FEATURE_COLS: List[str] = [
    "return_1d",
    "ma_10_dist",
    "ma_20_dist",
    "vol_20",
    "vol_rel",
]
TARGET_COL: str = "y_direction"


# ---------------------------------------------------------------------------
# DuckDB data loader (mirrors trainer.py exactly)
# ---------------------------------------------------------------------------
def load_feature_frame(
    conn,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """Load feature DataFrame from DuckDB daily_features."""
    query = (
        "SELECT symbol, date, close, "
        + ", ".join(FEATURE_COLS + [TARGET_COL])
        + " FROM daily_features"
    )
    params: list = []
    if start and end:
        query += " WHERE date BETWEEN ? AND ?"
        params = [start, end]
    df = conn.execute(query, params).df()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["symbol", "date"])


def split_by_time(
    df: pd.DataFrame, train_end: str, val_end: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split DataFrame by date for train / val."""
    train_mask = df["date"] <= pd.to_datetime(train_end)
    val_mask = (df["date"] > pd.to_datetime(train_end)) & (
        df["date"] <= pd.to_datetime(val_end)
    )
    return df[train_mask], df[val_mask]


# ---------------------------------------------------------------------------
# GPU detection helper
# ---------------------------------------------------------------------------
def _detect_gpu_id() -> int:
    """Return XGBOOST_GPU_ID from env, defaulting to 0."""
    return int(os.getenv("XGBOOST_GPU_ID", "0"))


def _gpu_available() -> bool:
    """Check whether CUDA is visible to XGBoost (nvidia-smi probe)."""
    try:
        import subprocess

        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Grid search parameter space
# ---------------------------------------------------------------------------
DEFAULT_PARAM_GRID: Dict[str, List[Any]] = {
    "max_depth": [4, 6, 8],
    "learning_rate": [0.01, 0.05, 0.1],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
    "min_child_weight": [1, 5],
}


def _build_combinations(
    grid: Dict[str, List[Any]],
) -> List[Dict[str, Any]]:
    """Cartesian product of hyper-parameter grid."""
    keys = list(grid.keys())
    values = list(grid.values())
    return [dict(zip(keys, combo)) for combo in iter_product(*values)]


# ---------------------------------------------------------------------------
# Cross-validation helper
# ---------------------------------------------------------------------------
def xgb_cross_validate(
    X: np.ndarray,
    y: np.ndarray,
    params: Dict[str, Any],
    n_folds: int = 5,
    num_boost_round: int = 300,
    early_stopping_rounds: int = 20,
) -> Dict[str, float]:
    """Run XGBoost CV and return mean metrics."""
    import xgboost as xgb

    dtrain = xgb.DMatrix(X, label=y, feature_names=FEATURE_COLS)
    cv_results = xgb.cv(
        params,
        dtrain,
        num_boost_round=num_boost_round,
        nfold=n_folds,
        early_stopping_rounds=early_stopping_rounds,
        metrics=["logloss", "error"],
        seed=42,
        verbose_eval=False,
    )
    best_idx = int(cv_results["test-logloss-mean"].idxmin())
    return {
        "best_round": best_idx + 1,
        "cv_logloss": float(cv_results.loc[best_idx, "test-logloss-mean"]),
        "cv_logloss_std": float(cv_results.loc[best_idx, "test-logloss-std"]),
        "cv_error": float(cv_results.loc[best_idx, "test-error-mean"]),
        "cv_accuracy": 1.0 - float(cv_results.loc[best_idx, "test-error-mean"]),
    }


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------
def extract_feature_importance(
    model,
    importance_type: str = "gain",
) -> Dict[str, float]:
    """Return feature importance dict sorted descending."""
    raw = model.get_score(importance_type=importance_type)
    total = sum(raw.values()) or 1.0
    normed = {k: round(v / total, 6) for k, v in raw.items()}
    return dict(sorted(normed.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Main training entry-point
# ---------------------------------------------------------------------------
def train_xgboost(
    df: pd.DataFrame,
    train_end: str,
    val_end: str,
    param_grid: Optional[Dict[str, List[Any]]] = None,
    n_folds: int = 5,
    num_boost_round: int = 300,
    early_stopping_rounds: int = 20,
    checkpoint_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Train XGBoost with GPU grid-search, CV, feature importance.

    Args:
        df: Full feature dataframe (all symbols, dates).
        train_end: Inclusive end date for training split (YYYY-MM-DD).
        val_end: Inclusive end date for validation split (YYYY-MM-DD).
        param_grid: Hyperparameter grid; defaults to DEFAULT_PARAM_GRID.
        n_folds: CV fold count.
        num_boost_round: Max boosting rounds per CV run.
        early_stopping_rounds: Rounds without improvement before stopping.
        checkpoint_dir: Where to save model; defaults to MODEL_ARTIFACTS_PATH
            env var or 'models/artifacts'.

    Returns:
        Dict with best model, params, metrics, feature importance – or None
        if training data is empty.
    """
    try:
        import xgboost as xgb
    except ImportError:
        log.error("xgboost is not installed – pip install xgboost")
        return None

    # --- data -----------------------------------------------------------
    df_train, df_val = split_by_time(df, train_end, val_end)
    df_train = df_train.dropna(subset=FEATURE_COLS + [TARGET_COL])
    df_val = df_val.dropna(subset=FEATURE_COLS + [TARGET_COL])

    if df_train.empty:
        log.warning("train_xgboost: empty training set, aborting.")
        return None

    X_train = df_train[FEATURE_COLS].values.astype(np.float32)
    y_train = df_train[TARGET_COL].values.astype(np.float32)
    X_val = df_val[FEATURE_COLS].values.astype(np.float32)
    y_val = df_val[TARGET_COL].values.astype(np.float32)

    log.info(
        "XGBoost data – train=%d  val=%d  features=%d",
        len(X_train),
        len(X_val),
        len(FEATURE_COLS),
    )

    # --- GPU config -----------------------------------------------------
    use_gpu = _gpu_available()
    gpu_id = _detect_gpu_id()
    base_params: Dict[str, Any] = {
        "objective": "binary:logistic",
        "eval_metric": ["logloss", "error"],
        "tree_method": "gpu_hist" if use_gpu else "hist",
        "verbosity": 1,
        "seed": 42,
    }
    if use_gpu:
        base_params["gpu_id"] = gpu_id
    log.info("XGBoost GPU: %s  tree_method: %s", use_gpu, base_params["tree_method"])

    # --- grid search with CV -------------------------------------------
    grid = param_grid or DEFAULT_PARAM_GRID
    combos = _build_combinations(grid)
    log.info("Grid search: %d combinations x %d-fold CV", len(combos), n_folds)

    best_score: float = float("inf")
    best_params: Dict[str, Any] = {}
    best_cv: Dict[str, float] = {}

    for i, hp in enumerate(combos, 1):
        merged = {**base_params, **hp}
        try:
            cv_result = xgb_cross_validate(
                X_train,
                y_train,
                merged,
                n_folds=n_folds,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )
        except Exception as exc:
            log.warning("CV combo %d/%d failed: %s", i, len(combos), exc)
            continue

        if cv_result["cv_logloss"] < best_score:
            best_score = cv_result["cv_logloss"]
            best_params = merged
            best_cv = cv_result
            log.info(
                "  [%d/%d] NEW BEST logloss=%.5f acc=%.4f params=%s",
                i,
                len(combos),
                cv_result["cv_logloss"],
                cv_result["cv_accuracy"],
                hp,
            )

    if not best_params:
        log.error("All grid search combinations failed.")
        return None

    # --- final model on full training set with val watchlist -----------
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLS)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=FEATURE_COLS)

    final_model = xgb.train(
        best_params,
        dtrain,
        num_boost_round=best_cv.get("best_round", num_boost_round),
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=early_stopping_rounds,
        verbose_eval=50,
    )

    # --- validation metrics -------------------------------------------
    val_preds = final_model.predict(dval)
    val_labels = (val_preds > 0.5).astype(np.float32)
    val_accuracy = float(np.mean(val_labels == y_val))
    log.info("Final model val_accuracy=%.4f", val_accuracy)

    # --- feature importance -------------------------------------------
    importance = extract_feature_importance(final_model, "gain")
    log.info("Feature importance (gain): %s", importance)

    # --- save artefacts -----------------------------------------------
    ckpt_dir = Path(
        checkpoint_dir
        or os.getenv("MODEL_ARTIFACTS_PATH", "models/artifacts")
    )
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    model_path = ckpt_dir / "xgboost_best.json"
    final_model.save_model(str(model_path))
    log.info("Model saved: %s", model_path)

    meta = {
        "best_params": {k: v for k, v in best_params.items() if k != "gpu_id"},
        "best_cv": best_cv,
        "val_accuracy": val_accuracy,
        "feature_importance": importance,
        "feature_cols": FEATURE_COLS,
        "target_col": TARGET_COL,
        "train_samples": len(X_train),
        "val_samples": len(X_val),
    }
    meta_path = ckpt_dir / "xgboost_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    log.info("Metadata saved: %s", meta_path)

    return {
        "model": final_model,
        "model_path": str(model_path),
        "params": best_params,
        "cv_results": best_cv,
        "val_accuracy": val_accuracy,
        "feature_importance": importance,
        "metadata": meta,
    }


# ---------------------------------------------------------------------------
# Quick CLI entry-point for manual runs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import duckdb

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    conn = duckdb.connect("elite_trading.duckdb", read_only=True)
    df = load_feature_frame(conn)
    if df.empty:
        log.error("No data in daily_features table.")
    else:
        result = train_xgboost(
            df,
            train_end="2024-06-30",
            val_end="2024-12-31",
        )
        if result:
            log.info("Training complete. Val accuracy: %.4f", result["val_accuracy"])
        else:
            log.error("Training returned None.")
    conn.close()
