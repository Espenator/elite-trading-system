"""ML Engine config: feature columns, target, artifact paths, retrain day.

v2.0 — Dynamically loads expanded features from FeaturePipeline manifest.
Falls back to legacy 5-feature list if manifest is unavailable.

Fixes Issue #25 Task 3.
"""

from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Legacy 5-feature list (backward compat)
# ---------------------------------------------------------------------------
LEGACY_FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
LEGACY_TARGET_COL = "y_direction"

# ---------------------------------------------------------------------------
# Dynamic feature loading from FeaturePipeline manifest
# ---------------------------------------------------------------------------
def get_feature_cols() -> List[str]:
    """Return expanded feature columns from pipeline manifest, or legacy fallback."""
    try:
        from app.modules.ml_engine.feature_pipeline import FeaturePipeline
        cols = FeaturePipeline.get_feature_cols()
        if cols and len(cols) > len(LEGACY_FEATURE_COLS):
            return cols
    except Exception:
        pass
    return list(LEGACY_FEATURE_COLS)


def get_target_col() -> str:
    """Return primary target column."""
    return LEGACY_TARGET_COL


def get_label_cols() -> List[str]:
    """Return all label columns from pipeline manifest."""
    try:
        from app.modules.ml_engine.feature_pipeline import FeaturePipeline
        cols = FeaturePipeline.get_label_cols()
        if cols:
            return cols
    except Exception:
        pass
    return [LEGACY_TARGET_COL]


# ---------------------------------------------------------------------------
# Static accessors (for code that imports FEATURE_COLS directly)
# These are evaluated at import time — use get_feature_cols() for dynamic.
# ---------------------------------------------------------------------------
FEATURE_COLS = LEGACY_FEATURE_COLS  # Static fallback; prefer get_feature_cols()
TARGET_COL = LEGACY_TARGET_COL
RETRAIN_WEEKDAY = 6  # Sunday = 6 in Python weekday()

# ---------------------------------------------------------------------------
# Artifact paths
# ---------------------------------------------------------------------------
_ML_ENGINE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = _ML_ENGINE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_FILE = ARTIFACTS_DIR / "xgb_latest.json"
METADATA_FILE = ARTIFACTS_DIR / "ml_metadata.json"
