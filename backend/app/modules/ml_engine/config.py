"""ML Engine config: feature columns, target, artifact paths, retrain day."""

from pathlib import Path

FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
TARGET_COL = "y_direction"
RETRAIN_WEEKDAY = 6  # Sunday = 6 in Python weekday()

_ML_ENGINE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = _ML_ENGINE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_FILE = ARTIFACTS_DIR / "xgb_latest.json"
METADATA_FILE = ARTIFACTS_DIR / "ml_metadata.json"
