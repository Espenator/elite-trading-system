"""XGBoost GPU trainer for Embodier Trader.

APEX Phase 2 – XGBoost companion model:
- GPU-accelerated training via tree_method='gpu_hist' (falls back to 'hist' on CPU)
- Grid search over key hyperparameters with cross-validation
- Feature importance extraction and logging
- v2.0: Reads from FeaturePipeline (30+ features) via feature_service
- Saves best model artefact to MODEL_ARTIFACTS_PATH

Fixes Issue #25 Task 3 — Wire trainer to FeaturePipeline.
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
# Feature / target columns — dynamic from FeaturePipeline, legacy fallback
# ---------------------------------------------------------------------------
def _get_feature_cols() -> List[str]:
    """Load feature columns from pipeline manifest or config fallback."""
    try:
        from app.modules.ml_engine.config import get_feature_cols
        return get_feature_cols()
    except Exception:
        return ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]


def _get_target_col() -> str:
    """Load target column from config."""
    try:
        from app.modules.ml_engine.config import get_target_col
        return get_target_col()
    except Exception:
        return "y_direction"


# Static references for backward compat (use functions for dynamic)
FEATURE_COLS: List[str] = _get_feature_cols()
TARGET_COL: str = _get_target_col()


# ---------------------------------------------------------------------------
# DuckDB data loader (legacy path — prefer feature_service for new code)
# ---------------------------------------------------------------------------
def load_feature_frame(
    conn,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """Load feature DataFrame from DuckDB daily_features.

    Legacy loader. For new code, use:
        from app.services.feature_service import feature_service
        train_df, val_df, manifest = feature_service.build_training_set(symbols)
    """
    feature_cols = _get_feature_cols()
    target_col = _get_target_col()

    # Try new DuckDB analytics path first
    try:
        from app.data.duckdb_storage import duckdb_store
        from app.modules.ml_engine.feature_pipeline import FeaturePipeline

        symbols_result = conn.execute(
            "SELECT DISTINCT symbol FROM daily_ohlcv"
        ).fetchdf()
        if not symbols_result.empty:
            symbols = symbols_result["symbol"].tolist()
            start_str = start.isoformat() if start else "2020-01-01"
            end_str = end.isoformat() if end else date.today().isoformat()

            raw_df = duckdb_store.get_training_window(symbols, start_str, end_str)
            if not raw_df.empty:
                pipeline = FeaturePipeline()
                df, manifest = pipeline.generate(raw_df, include_labels=True)
                feature_cols = manifest.feature_cols
                log.info(
                    "Loaded %d rows with %d expanded features via FeaturePipeline",
                    len(df), len(feature_cols)
                )
                return df
    except Exception as exc:
        log.debug("New data path unavailable, falling back to legacy: %s", exc)

    # Legacy path: direct query from daily_features table
    query = (
        "SELECT symbol, date, close, "
        + ", ".join(feature_cols + [target_col])
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
    feature_names: List[str] = None,
    n_folds: int = 5,
    num_boost_round: int = 300,
    early_stopping_rounds: int = 20,
) -> Dict[str, float]:
    """Run XGBoost CV and return mean metrics."""
    import xgboost as xgb

    dtrain = xgb.DMatrix(X, label=y, feature_names=feature_names)
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
    feature_cols: Optional[List[str]] = None,
    target_col: Optional[str] = None,
    param_grid: Optional[Dict[str, List[Any]]] = None,
    n_folds: int = 5,
    num_boost_round: int = 300,
    early_stopping_rounds: int = 20,
    checkpoint_dir: Optional[str] = None,
    use_risk_adjusted: bool = False,
) -> Optional[Dict[str, Any]]:
    """Train XGBoost with GPU grid-search, CV, feature importance.

    v2.0 changes:
    - feature_cols/target_col params override defaults (for FeaturePipeline integration)
    - Falls back to dynamic config if not provided
    - feature_names passed through to DMatrix and metadata

    Args:
        df: Full feature dataframe (all symbols, dates).
        train_end: Inclusive end date for training split (YYYY-MM-DD).
        val_end: Inclusive end date for validation split (YYYY-MM-DD).
        feature_cols: Override feature columns (from manifest). If None, uses config.
        target_col: Override target column. If None, uses config.
        param_grid: Hyperparameter grid; defaults to DEFAULT_PARAM_GRID.
        n_folds: CV fold count.
        num_boost_round: Max boosting rounds per CV run.
        early_stopping_rounds: Rounds without improvement before stopping.
        checkpoint_dir: Where to save model; defaults to ARTIFACTS_DIR.

    Returns:
        Dict with best model, params, metrics, feature importance – or None.
    """
    try:
        import xgboost as xgb
    except ImportError:
        log.error("xgboost is not installed – pip install xgboost")
        return None

    # Resolve feature/target columns dynamically
    _fcols = feature_cols or _get_feature_cols()
    _tcol = target_col or _get_target_col()

    log.info(
        "Training with %d features (expanded=%s), target=%s",
        len(_fcols), len(_fcols) > 5, _tcol
    )

    # --- data -----------------------------------------------------------
    df_train, df_val = split_by_time(df, train_end, val_end)

    # Only require columns that exist in the DataFrame
    available_fcols = [c for c in _fcols if c in df_train.columns]
    if len(available_fcols) < len(_fcols):
        missing = set(_fcols) - set(available_fcols)
        log.warning("Missing %d feature cols (using %d available): %s",
                    len(missing), len(available_fcols), missing)
    if not available_fcols:
        log.error("No feature columns found in DataFrame. Columns: %s", list(df_train.columns))
        return None

    _fcols = available_fcols

    df_train = df_train.dropna(subset=_fcols + [_tcol])
    df_val = df_val.dropna(subset=_fcols + [_tcol])

    if df_train.empty:
        log.warning("train_xgboost: empty training set, aborting.")
        return None

    X_train = df_train[_fcols].values.astype(np.float32)
    y_train = df_train[_tcol].values.astype(np.float32)
    X_val = df_val[_fcols].values.astype(np.float32) if not df_val.empty else np.empty((0, len(_fcols)))
    y_val = df_val[_tcol].values.astype(np.float32) if not df_val.empty else np.empty(0)

    log.info(
        "XGBoost data – train=%d  val=%d  features=%d",
        len(X_train), len(X_val), len(_fcols),
    )

    # --- Portfolio heat guardrails (anti-reward-hacking) -----------------
    try:
        from app.core.config import settings
        max_heat = getattr(settings, "MAX_PORTFOLIO_HEAT", 0.06)
        max_single = getattr(settings, "MAX_SINGLE_POSITION", 0.02)
        # These guardrails are informational during training; they become
        # hard limits during live execution via risk_agent + order_executor.
        log.info("Risk guardrails: max_heat=%.2f max_single=%.2f", max_heat, max_single)
    except Exception:
        pass

    # --- GPU config -----------------------------------------------------
    use_gpu = _gpu_available()
    gpu_id = _detect_gpu_id()
    base_params: Dict[str, Any] = {
        "objective": "binary:logistic",
        "eval_metric": ["logloss", "error"],
        "verbosity": 1,
        "seed": 42,
    }

    # GPU acceleration: use device='cuda' (XGBoost 2.0+) with gpu_hist,
    # falling back to CPU hist if GPU init fails at runtime.
    if use_gpu:
        try:
            import xgboost as _xgb_check
            # Verify GPU actually works by creating a tiny DMatrix + train
            _test_dm = _xgb_check.DMatrix(np.array([[1.0]]), label=np.array([0]))
            _test_params = {"tree_method": "gpu_hist", "device": f"cuda:{gpu_id}", "max_depth": 1}
            _xgb_check.train(_test_params, _test_dm, num_boost_round=1, verbose_eval=False)
            base_params["tree_method"] = "gpu_hist"
            base_params["device"] = f"cuda:{gpu_id}"
            log.info("XGBoost GPU verified — using gpu_hist on cuda:%d", gpu_id)
        except Exception as gpu_err:
            log.warning("XGBoost GPU probe failed (%s) — falling back to CPU hist", gpu_err)
            use_gpu = False
            base_params["tree_method"] = "hist"
    else:
        base_params["tree_method"] = "hist"

    # Risk-adjusted custom objective (anti-reward-hacking)
    if use_risk_adjusted:
        try:
            from app.modules.ml_engine.risk_adjusted_objective import xgboost_risk_objective
            base_params["objective"] = xgboost_risk_objective
            base_params["disable_default_eval_metric"] = True
            log.info("Using risk-adjusted custom objective")
        except ImportError:
            log.warning("risk_adjusted_objective not available, using default logistic")

    log.info("XGBoost GPU: %s  tree_method: %s  device: %s",
             use_gpu, base_params["tree_method"], base_params.get("device", "cpu"))

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
                X_train, y_train, merged,
                feature_names=_fcols,
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
                i, len(combos), cv_result["cv_logloss"],
                cv_result["cv_accuracy"], hp,
            )

    if not best_params:
        log.error("All grid search combinations failed.")
        return None

    # --- final model on full training set with val watchlist -----------
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=_fcols)

    evals = [(dtrain, "train")]
    if len(X_val) > 0:
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=_fcols)
        evals.append((dval, "val"))
    else:
        dval = None

    final_model = xgb.train(
        best_params,
        dtrain,
        num_boost_round=best_cv.get("best_round", num_boost_round),
        evals=evals,
        early_stopping_rounds=early_stopping_rounds,
        verbose_eval=50,
    )

    # --- validation metrics -------------------------------------------
    val_accuracy = 0.0
    if dval is not None and len(y_val) > 0:
        val_preds = final_model.predict(dval)
        val_labels = (val_preds > 0.5).astype(np.float32)
        val_accuracy = float(np.mean(val_labels == y_val))
    log.info("Final model val_accuracy=%.4f", val_accuracy)

    # --- feature importance -------------------------------------------
    importance = extract_feature_importance(final_model, "gain")
    log.info("Feature importance (gain, top 10): %s",
             dict(list(importance.items())[:10]))

    # --- save artefacts -----------------------------------------------
    from app.modules.ml_engine.config import ARTIFACTS_DIR
    ckpt_dir = Path(checkpoint_dir) if checkpoint_dir else ARTIFACTS_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    model_path = ckpt_dir / "xgboost_best.json"
    final_model.save_model(str(model_path))
    log.info("Model saved: %s", model_path)

    meta = {
        "best_params": {k: v for k, v in best_params.items() if k != "gpu_id" and not callable(v)},
        "best_cv": best_cv,
        "val_accuracy": val_accuracy,
        "feature_importance": importance,
        "feature_cols": _fcols,
        "feature_count": len(_fcols),
        "expanded_features": len(_fcols) > 5,
        "target_col": _tcol,
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "pipeline_version": "2.0.0" if len(_fcols) > 5 else "1.0.0",
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
# Convenience: train via feature_service (recommended new entry-point)
# ---------------------------------------------------------------------------
def train_xgboost_v2(
    symbols: List[str],
    end_date: str = None,
    param_grid: Optional[Dict[str, List[Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Train XGBoost using FeaturePipeline + DuckDB end-to-end.

    This is the recommended entry-point for new training runs.
    Handles data loading, feature generation, walk-forward split,
    and model training in one call.

    Usage:
        result = train_xgboost_v2(["AAPL", "MSFT", "GOOGL", "NVDA"])
    """
    from app.services.feature_service import feature_service

    train_df, val_df, manifest = feature_service.build_training_set(
        symbols=symbols,
        end_date=end_date,
    )

    if train_df.empty:
        log.error("No training data from feature_service. Check DuckDB has OHLCV data.")
        return None

    feature_cols = manifest.get("feature_cols", _get_feature_cols())
    label_cols = manifest.get("label_cols", [_get_target_col()])
    target_col = _get_target_col()  # y_direction for binary classification

    # Combine train + val for split_by_time compatibility
    df = pd.concat([train_df, val_df], ignore_index=True)
    train_end = str(train_df["date"].max())
    val_end = str(val_df["date"].max()) if not val_df.empty else train_end

    log.info(
        "train_xgboost_v2: %d symbols, %d features, %d labels, train_end=%s",
        df["symbol"].nunique(), len(feature_cols), len(label_cols), train_end
    )

    return train_xgboost(
        df=df,
        train_end=train_end,
        val_end=val_end,
        feature_cols=feature_cols,
        target_col=target_col,
        param_grid=param_grid,
    )


# ---------------------------------------------------------------------------
# Quick CLI entry-point for manual runs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    # Prefer v2 path if feature_service is available
    try:
        symbols = sys.argv[1:] or ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
        log.info("Training v2 pipeline with symbols: %s", symbols)
        result = train_xgboost_v2(symbols)
        if result:
            log.info(
                "Training complete. Val accuracy: %.4f, Features: %d",
                result["val_accuracy"], len(result["metadata"]["feature_cols"])
            )
        else:
            log.error("Training returned None.")
    except Exception as exc:
        log.warning("v2 path failed (%s), trying legacy...", exc)
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_connection()
        df = load_feature_frame(conn)
        if df.empty:
            log.error("No data in daily_features table.")
        else:
            result = train_xgboost(
                df, train_end="2024-06-30", val_end="2024-12-31",
            )
            if result:
                log.info("Training complete. Val accuracy: %.4f", result["val_accuracy"])
