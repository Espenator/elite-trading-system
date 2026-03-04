"""
Feature Pipeline v2.0 — Expand from 5 to 30+ features with multi-horizon utility labels.

Drop-in replacement for the 5-feature config in ml_engine/config.py.
Integrates with: xgboost_trainer.py, trainer.py (LSTM), inference.py, outcome_resolver.py.
Data sources: DuckDB daily_features, Alpaca OHLCV, FRED macro, options flow aggregates.

Usage:
    from app.modules.ml_engine.feature_pipeline import FeaturePipeline
    pipeline = FeaturePipeline()
    df_features, manifest = pipeline.generate(raw_ohlcv_df)
    # manifest['feature_cols'] replaces FEATURE_COLS everywhere
    # manifest['label_cols'] replaces TARGET_COL with multi-task targets
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline config (extends ml_engine/config.py)
# ---------------------------------------------------------------------------
PIPELINE_VERSION = "2.0.0"

# Original 5 features preserved for backward compat
LEGACY_FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]

# Horizons for multi-task labels
LABEL_HORIZONS = [1, 3, 5, 10]

# Artifacts
_PIPELINE_DIR = Path(__file__).resolve().parent / "artifacts"
_PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE = _PIPELINE_DIR / "feature_manifest.json"


@dataclass
class FeatureManifest:
    """Versioned record of what the pipeline produced."""
    version: str = PIPELINE_VERSION
    feature_cols: List[str] = field(default_factory=list)
    label_cols: List[str] = field(default_factory=list)
    legacy_cols: List[str] = field(default_factory=lambda: list(LEGACY_FEATURE_COLS))
    n_features: int = 0
    n_labels: int = 0
    data_hash: str = ""
    created_at: str = ""

    def save(self, path: Path = MANIFEST_FILE):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path = MANIFEST_FILE) -> "FeatureManifest":
        if path.exists():
            return cls(**json.loads(path.read_text()))
        return cls()


# ---------------------------------------------------------------------------
# TA helpers (use 'ta' library already in requirements.txt)
# ---------------------------------------------------------------------------
def _safe_ta_import():
    """Import ta library with fallback."""
    try:
        import ta
        return ta
    except ImportError:
        log.warning("'ta' library not installed. Install with: pip install ta")
        return None


# ---------------------------------------------------------------------------
# Feature generators (each returns columns added to df)
# ---------------------------------------------------------------------------

def _add_return_features(df: pd.DataFrame) -> List[str]:
    """Multi-horizon return features."""
    cols = []
    for period in [1, 2, 3, 5, 10, 20]:
        col = f"return_{period}d"
        df[col] = df.groupby("symbol")["close"].pct_change(period)
        cols.append(col)
    return cols


def _add_ma_features(df: pd.DataFrame) -> List[str]:
    """Moving average distance features across multiple timeframes."""
    cols = []
    for period in [10, 20, 50, 200]:
        col = f"ma_{period}_dist"
        ma = df.groupby("symbol")["close"].transform(lambda x: x.rolling(period).mean())
        df[col] = (df["close"] - ma) / (ma + 1e-10)
        cols.append(col)
    return cols


def _add_volatility_features(df: pd.DataFrame) -> List[str]:
    """Realized volatility at multiple scales."""
    cols = []
    ret = df.groupby("symbol")["close"].pct_change()

    for window in [5, 10, 20, 60]:
        col = f"vol_{window}"
        df[col] = ret.groupby(df["symbol"]).transform(lambda x: x.rolling(window).std())
        cols.append(col)

    # Volatility ratio (short/long) — mean reversion signal
    if "vol_5" in df.columns and "vol_60" in df.columns:
        df["vol_ratio_5_60"] = df["vol_5"] / (df["vol_60"] + 1e-10)
        cols.append("vol_ratio_5_60")

    # Relative volume (today's volume vs 20d average)
    if "volume" in df.columns:
        avg_vol = df.groupby("symbol")["volume"].transform(lambda x: x.rolling(20).mean())
        df["vol_rel"] = df["volume"] / (avg_vol + 1)
        cols.append("vol_rel")

    return cols


def _add_momentum_features(df: pd.DataFrame) -> List[str]:
    """RSI, rate of change, momentum indicators."""
    ta = _safe_ta_import()
    cols = []

    if ta is not None:
        for period in [14, 28]:
            col = f"rsi_{period}"
            df[col] = df.groupby("symbol")["close"].transform(
                lambda x: ta.momentum.RSIIndicator(x, window=period).rsi()
            )
            # Normalize to [-1, 1] centered at 50
            df[col] = (df[col] - 50.0) / 50.0
            cols.append(col)

        # Stochastic K
        df["stoch_k"] = df.groupby("symbol").apply(
            lambda g: ta.momentum.StochasticOscillator(
                g["high"], g["low"], g["close"], window=14
            ).stoch() / 100.0
        ).reset_index(level=0, drop=True)
        cols.append("stoch_k")
    else:
        # Fallback: manual RSI
        delta = df.groupby("symbol")["close"].pct_change()
        gain = delta.clip(lower=0).groupby(df["symbol"]).transform(lambda x: x.rolling(14).mean())
        loss = (-delta.clip(upper=0)).groupby(df["symbol"]).transform(lambda x: x.rolling(14).mean())
        rs = gain / (loss + 1e-10)
        # Bug #18 fix: was (100.0 / (1.0 + rs)) which is the complement of RSI
        # Correct RSI = 100 - 100/(1+RS), then normalize to [-1, 1]
        df["rsi_14"] = ((100.0 - 100.0 / (1.0 + rs)) - 50.0) / 50.0
        cols.append("rsi_14")

    return cols


def _add_bollinger_features(df: pd.DataFrame) -> List[str]:
    """Bollinger Band features — %B and bandwidth."""
    cols = []
    for window in [20]:
        ma = df.groupby("symbol")["close"].transform(lambda x: x.rolling(window).mean())
        std = df.groupby("symbol")["close"].transform(lambda x: x.rolling(window).std())
        upper = ma + 2 * std
        lower = ma - 2 * std
        df[f"bb_pct_{window}"] = (df["close"] - lower) / (upper - lower + 1e-10)
        df[f"bb_width_{window}"] = (upper - lower) / (ma + 1e-10)
        cols.extend([f"bb_pct_{window}", f"bb_width_{window}"])
    return cols


def _add_volume_profile_features(df: pd.DataFrame) -> List[str]:
    """Volume-weighted features."""
    cols = []
    if "volume" in df.columns:
        # OBV approximation (cumulative volume direction)
        ret_sign = np.sign(df.groupby("symbol")["close"].pct_change())
        df["obv_norm"] = (ret_sign * df["volume"]).groupby(df["symbol"]).cumsum()
        # Normalize OBV by 20d rolling max
        obv_max = df.groupby("symbol")["obv_norm"].transform(
            lambda x: x.rolling(20).apply(lambda w: max(abs(w.max()), abs(w.min()), 1))
        )
        df["obv_norm"] = df["obv_norm"] / (obv_max + 1)
        cols.append("obv_norm")

        # VWAP distance (intraday proxy — daily close vs volume-weighted close)
        df["vwap_dist"] = 0.0  # Placeholder; real VWAP needs intraday bars
        cols.append("vwap_dist")
    return cols


def _add_atr_features(df: pd.DataFrame) -> List[str]:
    """Average True Range features."""
    cols = []
    if all(c in df.columns for c in ["high", "low", "close"]):
        for period in [14]:
            prev_close = df.groupby("symbol")["close"].shift(1)
            tr = pd.concat([
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs()
            ], axis=1).max(axis=1)
            df[f"atr_{period}"] = tr.groupby(df["symbol"]).transform(lambda x: x.rolling(period).mean())
            # Normalize ATR by close price
            df[f"atr_{period}_pct"] = df[f"atr_{period}"] / (df["close"] + 1e-10)
            cols.append(f"atr_{period}_pct")
    return cols


def _add_regime_features(df: pd.DataFrame) -> List[str]:
    """Market regime proxy features (from HMM or heuristic)."""
    cols = []
    # Heuristic regime: SMA cross
    ma50 = df.groupby("symbol")["close"].transform(lambda x: x.rolling(50).mean())
    ma200 = df.groupby("symbol")["close"].transform(lambda x: x.rolling(200).mean())
    df["regime_sma"] = (ma50 > ma200).astype(float)  # 1=bull, 0=bear
    cols.append("regime_sma")

    # If HMM regime column exists from intelligence/hmm_regime.py, pass through
    if "hmm_regime" in df.columns:
        cols.append("hmm_regime")

    return cols


def _add_options_flow_features(df: pd.DataFrame) -> List[str]:
    """Options flow aggregate features (from Unusual Whales / whale_flow.py)."""
    cols = []
    flow_cols = {
        "net_premium": "flow_net_prem",
        "call_volume": "flow_call_vol",
        "put_volume": "flow_put_vol",
        "pcr_volume": "flow_pcr_vol",
    }
    for src, dst in flow_cols.items():
        if src in df.columns:
            df[dst] = df[src]
            cols.append(dst)

    # Put/call ratio from raw volumes
    if "call_volume" in df.columns and "put_volume" in df.columns:
        df["flow_pcr_vol"] = df["put_volume"] / (df["call_volume"] + 1)
        if "flow_pcr_vol" not in cols:
            cols.append("flow_pcr_vol")

    return cols


def _add_macro_features(df: pd.DataFrame) -> List[str]:
    """FRED macro features (joined from fred_service.py daily cache)."""
    cols = []
    macro_cols = ["vix_close", "dxy_close", "us10y_yield", "fed_funds_rate"]
    for col in macro_cols:
        if col in df.columns:
            cols.append(col)
    return cols


def _add_calendar_features(df: pd.DataFrame) -> List[str]:
    """Day-of-week, month, quarter dummies."""
    cols = []
    if "date" in df.columns:
        dt = pd.to_datetime(df["date"])
        df["day_of_week"] = dt.dt.dayofweek / 4.0  # Normalize to [0, 1]
        df["month_sin"] = np.sin(2 * np.pi * dt.dt.month / 12)
        df["month_cos"] = np.cos(2 * np.pi * dt.dt.month / 12)
        cols.extend(["day_of_week", "month_sin", "month_cos"])
    return cols


# ---------------------------------------------------------------------------
# Label generators (forward-looking — training only, masked at inference)
# ---------------------------------------------------------------------------

def _add_labels(df: pd.DataFrame, horizons: List[int] = None) -> List[str]:
    """Multi-horizon labels: returns, direction, volatility, MAE, MFE, utility."""
    horizons = horizons or LABEL_HORIZONS
    label_cols = []

    for h in horizons:
        # Forward return
        col_ret = f"label_return_{h}d"
        df[col_ret] = df.groupby("symbol")["close"].transform(
            lambda x: x.shift(-h) / x - 1.0
        )
        label_cols.append(col_ret)

        # Direction (binary)
        col_dir = f"label_dir_{h}d"
        df[col_dir] = (df[col_ret] > 0).astype(float)
        label_cols.append(col_dir)

        # Forward realized vol
        col_vol = f"label_vol_{h}d"
        daily_ret = df.groupby("symbol")["close"].pct_change()
        df[col_vol] = daily_ret.groupby(df["symbol"]).transform(
            lambda x: x.shift(-h).rolling(h).std()
        )
        label_cols.append(col_vol)

        # MAE/MFE (Max Adverse/Favorable Excursion) — needs high/low
        if all(c in df.columns for c in ["high", "low"]):
            # MFE: max upside within horizon
            col_mfe = f"label_mfe_{h}d"
            df[col_mfe] = df.groupby("symbol").apply(
                lambda g: g["high"].rolling(h).max().shift(-h) / g["close"] - 1.0
            ).reset_index(level=0, drop=True)
            label_cols.append(col_mfe)

            # MAE: max drawdown within horizon
            col_mae = f"label_mae_{h}d"
            df[col_mae] = df.groupby("symbol").apply(
                lambda g: g["low"].rolling(h).min().shift(-h) / g["close"] - 1.0
            ).reset_index(level=0, drop=True)
            label_cols.append(col_mae)

        # Utility label (risk-adjusted return)
        col_util = f"label_utility_{h}d"
        vol_col = col_vol if col_vol in df.columns else None
        if vol_col:
            df[col_util] = df[col_ret] - 0.5 * df[vol_col].fillna(0)
        else:
            df[col_util] = df[col_ret]
        label_cols.append(col_util)

    # Legacy binary direction (backward compat with y_direction)
    df["y_direction"] = df.get("label_dir_1d", (df.groupby("symbol")["close"].pct_change().shift(-1) > 0).astype(float))
    label_cols.append("y_direction")

    return label_cols


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class FeaturePipeline:
    """Orchestrates feature generation with version tracking and leak protection."""

    def __init__(self, horizons: List[int] = None, include_legacy: bool = True):
        self.horizons = horizons or LABEL_HORIZONS
        self.include_legacy = include_legacy
        self._manifest: Optional[FeatureManifest] = None

    def generate(
        self,
        df: pd.DataFrame,
        include_labels: bool = True,
        include_options_flow: bool = True,
        include_macro: bool = True,
    ) -> Tuple[pd.DataFrame, FeatureManifest]:
        """
        Generate features from raw OHLCV+ DataFrame.

        Args:
            df: Must contain columns: symbol, date, close. Optional: open, high, low, volume,
                plus any options flow / macro columns pre-joined.
            include_labels: If True, add forward-looking labels (training only).
            include_options_flow: If True, process options flow columns.
            include_macro: If True, process macro columns.

        Returns:
            (feature_df, manifest) — feature_df has all features + labels;
            manifest.feature_cols lists input features;
            manifest.label_cols lists target labels.
        """
        df = df.copy()
        df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
        all_feature_cols: List[str] = []

        log.info("FeaturePipeline v%s: generating features for %d rows, %d symbols",
                 PIPELINE_VERSION, len(df), df["symbol"].nunique())

        # --- Feature generators ---
        all_feature_cols += _add_return_features(df)
        all_feature_cols += _add_ma_features(df)
        all_feature_cols += _add_volatility_features(df)
        all_feature_cols += _add_momentum_features(df)
        all_feature_cols += _add_bollinger_features(df)
        all_feature_cols += _add_volume_profile_features(df)
        all_feature_cols += _add_atr_features(df)
        all_feature_cols += _add_regime_features(df)
        all_feature_cols += _add_calendar_features(df)

        if include_options_flow:
            all_feature_cols += _add_options_flow_features(df)
        if include_macro:
            all_feature_cols += _add_macro_features(df)

        # Deduplicate while preserving order
        seen = set()
        feature_cols = []
        for c in all_feature_cols:
            if c in df.columns and c not in seen:
                feature_cols.append(c)
                seen.add(c)

        # --- Labels ---
        label_cols = []
        if include_labels:
            label_cols = _add_labels(df, self.horizons)
            label_cols = [c for c in label_cols if c in df.columns]

        # --- Build manifest ---
        data_hash = hashlib.md5(
            pd.util.hash_pandas_object(df[feature_cols].head(1000)).values.tobytes()
        ).hexdigest()[:12]

        manifest = FeatureManifest(
            version=PIPELINE_VERSION,
            feature_cols=feature_cols,
            label_cols=label_cols,
            n_features=len(feature_cols),
            n_labels=len(label_cols),
            data_hash=data_hash,
            created_at=datetime.utcnow().isoformat(),
        )
        manifest.save()

        self._manifest = manifest
        log.info("Generated %d features, %d labels. Manifest saved.",
                 len(feature_cols), len(label_cols))

        return df, manifest

    @property
    def manifest(self) -> Optional[FeatureManifest]:
        return self._manifest

    @staticmethod
    def get_feature_cols() -> List[str]:
        """Load feature columns from saved manifest (for inference)."""
        m = FeatureManifest.load()
        return m.feature_cols if m.feature_cols else LEGACY_FEATURE_COLS

    @staticmethod
    def get_label_cols() -> List[str]:
        """Load label columns from saved manifest."""
        m = FeatureManifest.load()
        return m.label_cols if m.label_cols else ["y_direction"]


# ---------------------------------------------------------------------------
# Convenience function matching existing config.py pattern
# ---------------------------------------------------------------------------
def get_expanded_feature_cols() -> List[str]:
    """Drop-in for config.FEATURE_COLS — returns expanded feature list."""
    return FeaturePipeline.get_feature_cols()


def get_expanded_label_cols() -> List[str]:
    """Returns multi-task label columns."""
    return FeaturePipeline.get_label_cols()
