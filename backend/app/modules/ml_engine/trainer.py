"""Train XGBoost/LightGBM on daily_features (historical outcomes).
Uses GPU (CUDA) when available (RTX 4080 etc.).
"""

from datetime import date, timedelta
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from app.data.storage import get_conn
from app.modules.ml_engine.config import (
    get_feature_cols,
    TARGET_COL,
    MODEL_FILE,
    METADATA_FILE,
)

logger = logging.getLogger(__name__)


def load_feature_frame(
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """Load feature DataFrame from DuckDB daily_features."""
    conn = get_conn()
    query = (
        "SELECT symbol, date, close, "
        + ", ".join(get_feature_cols() + [TARGET_COL])
        + " FROM daily_features"
    )
    params = []
    if start and end:
        query += " WHERE date BETWEEN ? AND ?"
        params = [start, end]
    df = conn.execute(query, params).df()
    if df is None or df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["symbol", "date"]).dropna(
        subset=get_feature_cols() + [TARGET_COL], how="any"
    )


def split_by_time(
    df: pd.DataFrame, train_end: str, val_end: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train_mask = df["date"] <= pd.to_datetime(train_end)
    val_mask = (df["date"] > pd.to_datetime(train_end)) & (
        df["date"] <= pd.to_datetime(val_end)
    )
    return df[train_mask], df[val_mask]


def _get_gpu_params_xgb() -> dict:
    """XGBoost GPU params; fallback to CPU if CUDA unavailable or not built with GPU."""
    try:
        import xgboost as xgb
        import os
        gpu_id = int(os.getenv("XGBOOST_GPU_ID", "0"))
        # gpu_hist requires XGBoost built with CUDA
        return {
            "tree_method": "gpu_hist",
            "device": f"cuda:{gpu_id}",
        }
    except Exception:
        return {"tree_method": "hist"}


def train_xgb(
    df: pd.DataFrame,
    train_end: str,
    val_end: str,
    max_depth: int = 6,
    n_estimators: int = 200,
) -> Optional[dict]:
    """
    Train XGBoost classifier on daily_features. Uses GPU when available.
    Returns metadata dict (val_accuracy, last_trained, rows_used) or None on failure.
    """
    try:
        import xgboost as xgb
    except ImportError:
        logger.warning("xgboost not installed; pip install xgboost")
        return None

    if df.empty or len(df) < 100:
        return None

    df_train, df_val = split_by_time(df, train_end, val_end)
    X_train = df_train[get_feature_cols()]
    y_train = df_train[TARGET_COL]
    X_val = df_val[get_feature_cols()]
    y_val = df_val[TARGET_COL]
    if len(X_train) < 50 or len(X_val) < 10:
        return None

    params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "max_depth": max_depth,
        "n_estimators": n_estimators,
        "use_label_encoder": False,
    }
    params.update(_get_gpu_params_xgb())
    model = xgb.XGBClassifier(**params)
    try:
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
    except Exception as e:
        logger.warning("XGBoost GPU fit failed, falling back to CPU: %s", e)
        params["tree_method"] = "hist"
        params.pop("device", None)
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    gpu_used = params.get("tree_method") == "gpu_hist"
    acc = (model.predict(X_val) == y_val).mean()
    model.save_model(str(MODEL_FILE))

    meta = {
        "last_trained": date.today().isoformat(),
        "val_accuracy": round(float(acc), 4),
        "train_rows": len(df_train),
        "val_rows": len(df_val),
        "model_type": "xgboost",
        "gpu_used": gpu_used,
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2))
    return meta


def train_lightgbm(
    df: pd.DataFrame,
    train_end: str,
    val_end: str,
    n_estimators: int = 200,
) -> Optional[dict]:
    """Train LightGBM with GPU if available. Saves to ml_engine/artifacts/lgb_latest.txt."""
    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("lightgbm not installed; pip install lightgbm")
        return None

    if df.empty or len(df) < 100:
        return None

    df_train, df_val = split_by_time(df, train_end, val_end)
    X_train = df_train[get_feature_cols()]
    y_train = df_train[TARGET_COL]
    X_val = df_val[get_feature_cols()]
    y_val = df_val[TARGET_COL]
    if len(X_train) < 50 or len(X_val) < 10:
        return None

    params = {
        "objective": "binary",
        "metric": "auc",
        "num_leaves": 31,
        "n_estimators": n_estimators,
        "verbose": -1,
        "device": "cuda",
    }
    try:
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    except Exception:
        params["device"] = "cpu"
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    acc = (model.predict(X_val) == y_val).mean()
    out_path = Path(MODEL_FILE).parent / "lgb_latest.txt"
    model.booster_.save_model(str(out_path))

    meta = {
        "last_trained": date.today().isoformat(),
        "val_accuracy": round(float(acc), 4),
        "train_rows": len(df_train),
        "val_rows": len(df_val),
        "model_type": "lightgbm",
        "gpu_used": params.get("device") == "cuda",
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2))
    return meta


def run_full_retrain(use_lightgbm: bool = False) -> Optional[dict]:
    """
    Load all daily_features, time split (e.g. last 20% val), train and save.
    Called on Sunday or manually. Returns metadata or None.
    """
    end = date.today()
    start = end - timedelta(days=365 * 3)
    df = load_feature_frame(start=start, end=end)
    if df.empty:
        return None
    # Bug #20 fix: use unique dates for proper time-based split
    # (previously used len(df) row count as day count, which could subtract thousands of years)
    unique_dates = sorted(df["date"].unique())
    split_idx = int(len(unique_dates) * 0.8)
    train_end = (
        pd.Timestamp(unique_dates[split_idx]).isoformat()[:10]
        if split_idx < len(unique_dates)
        else end.isoformat()
    )
    val_end_s = end.isoformat()
    if use_lightgbm:
        return train_lightgbm(df, train_end, val_end_s)
    return train_xgb(df, train_end, val_end_s)
