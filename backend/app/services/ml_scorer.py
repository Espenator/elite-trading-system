"""MLScorer — live XGBoost inference for signal scoring.

Loads the trained XGBoost model and provides real-time P(up) predictions
that blend into the EventDrivenSignalEngine scoring pipeline.

Replaces the hardcoded composite score with ML-calibrated probabilities
when a trained model is available. Falls back to TA-only scoring if not.

Architecture:
    EventDrivenSignalEngine._on_bar()
        → _compute_composite_score() [TA baseline]
        → MLScorer.score() [ML boost/override when model loaded]
        → blended final_score published to signal.generated
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Paths match ml_engine/config.py
_ML_ENGINE_DIR = Path(__file__).resolve().parent.parent / "modules" / "ml_engine"
_ARTIFACTS_DIR = _ML_ENGINE_DIR / "artifacts"
_MODEL_FILE = _ARTIFACTS_DIR / "xgb_latest.json"
_METADATA_FILE = _ARTIFACTS_DIR / "ml_metadata.json"


class MLScorer:
    """Live XGBoost scorer for signal pipeline integration."""

    def __init__(self):
        self._model = None
        self._feature_cols: List[str] = []
        self._metadata: Dict[str, Any] = {}
        self._loaded = False
        self._load_time = 0.0
        self._predictions_made = 0
        self._load_model()

    def _load_model(self) -> None:
        """Load the trained XGBoost model if available."""
        if not _MODEL_FILE.exists():
            logger.info("MLScorer: no model at %s — TA-only mode", _MODEL_FILE)
            return

        try:
            import xgboost as xgb
            self._model = xgb.Booster()
            self._model.load_model(str(_MODEL_FILE))

            # Load feature columns
            try:
                from app.modules.ml_engine.config import get_feature_cols
                self._feature_cols = get_feature_cols()
            except Exception:
                self._feature_cols = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]

            # Load metadata
            import json
            if _METADATA_FILE.exists():
                with open(_METADATA_FILE) as f:
                    self._metadata = json.load(f)

            self._loaded = True
            self._load_time = time.time()
            logger.info(
                "MLScorer: model loaded (%d features, val_acc=%.3f)",
                len(self._feature_cols),
                self._metadata.get("val_accuracy", 0),
            )
        except ImportError:
            logger.warning("MLScorer: xgboost not installed — TA-only mode")
        except Exception as e:
            logger.warning("MLScorer: failed to load model: %s", e)

    def reload(self) -> bool:
        """Reload model (e.g., after retraining)."""
        self._loaded = False
        self._model = None
        self._load_model()
        return self._loaded

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def score(self, symbol: str, bars: List[Dict]) -> Optional[Dict[str, Any]]:
        """Score a symbol using the XGBoost model.

        Args:
            symbol: Ticker symbol
            bars: List of OHLCV bar dicts (most recent last), minimum 20 bars

        Returns:
            Dict with ml_score (0-100), probability, confidence, or None if model unavailable
        """
        if not self._loaded or not self._model:
            return None

        if len(bars) < 20:
            return None

        try:
            features = self._extract_features(bars)
            if features is None:
                return None

            import xgboost as xgb
            dmatrix = xgb.DMatrix(features.reshape(1, -1), feature_names=self._feature_cols[:len(features)])
            prob = float(self._model.predict(dmatrix)[0])

            # Convert probability to 0-100 score
            # prob > 0.5 = bullish, prob < 0.5 = bearish
            ml_score = prob * 100.0

            # Confidence: distance from 0.5 (uncertain zone)
            confidence = abs(prob - 0.5) * 2.0  # 0-1 scale

            self._predictions_made += 1

            return {
                "ml_score": round(ml_score, 1),
                "probability": round(prob, 4),
                "confidence": round(confidence, 3),
                "direction": "bullish" if prob > 0.5 else "bearish",
                "model_accuracy": self._metadata.get("val_accuracy", 0),
            }
        except Exception as e:
            logger.debug("MLScorer prediction failed for %s: %s", symbol, e)
            return None

    def _extract_features(self, bars: List[Dict]) -> Optional[np.ndarray]:
        """Extract feature vector from bar data matching training features."""
        try:
            closes = [float(b.get("close", 0)) for b in bars if float(b.get("close", 0)) > 0]
            volumes = [float(b.get("volume", 0)) for b in bars]

            if len(closes) < 20:
                return None

            features = {}

            # Return features
            if closes[-2] > 0:
                features["return_1d"] = (closes[-1] - closes[-2]) / closes[-2]
            else:
                features["return_1d"] = 0.0

            for period, key in [(2, "return_2d"), (3, "return_3d"), (5, "return_5d"), (10, "return_10d"), (20, "return_20d")]:
                if len(closes) > period and closes[-1 - period] > 0:
                    features[key] = (closes[-1] - closes[-1 - period]) / closes[-1 - period]
                else:
                    features[key] = 0.0

            # Moving average distances
            for period, key in [(10, "ma_10_dist"), (20, "ma_20_dist"), (50, "ma_50_dist"), (200, "ma_200_dist")]:
                if len(closes) >= period:
                    ma = sum(closes[-period:]) / period
                    features[key] = (closes[-1] - ma) / ma if ma > 0 else 0.0
                else:
                    features[key] = 0.0

            # Volatility features
            for period, key in [(5, "vol_5"), (10, "vol_10"), (20, "vol_20"), (60, "vol_60")]:
                if len(closes) >= period:
                    returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
                               for i in range(-period, 0) if closes[i - 1] > 0]
                    features[key] = float(np.std(returns)) if returns else 0.0
                else:
                    features[key] = 0.0

            # Volatility ratio
            v5 = features.get("vol_5", 0)
            v60 = features.get("vol_60", 0)
            features["vol_ratio_5_60"] = v5 / v60 if v60 > 0 else 1.0

            # Relative volume
            if len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                features["vol_rel"] = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
            else:
                features["vol_rel"] = 1.0

            # RSI
            features["rsi_14"] = self._compute_rsi(closes, 14) / 50.0 - 1.0  # Normalized to [-1, 1]
            if len(closes) >= 28:
                features["rsi_28"] = self._compute_rsi(closes, 28) / 50.0 - 1.0
            else:
                features["rsi_28"] = features["rsi_14"]

            # Bollinger %B
            if len(closes) >= 20:
                ma20 = sum(closes[-20:]) / 20
                std20 = float(np.std(closes[-20:]))
                upper = ma20 + 2 * std20
                lower = ma20 - 2 * std20
                band_width = upper - lower
                features["bb_pct_20"] = (closes[-1] - lower) / band_width if band_width > 0 else 0.5
                features["bb_width_20"] = band_width / ma20 if ma20 > 0 else 0.0
            else:
                features["bb_pct_20"] = 0.5
                features["bb_width_20"] = 0.0

            # ATR
            highs = [float(b.get("high", 0)) for b in bars[-14:]]
            lows = [float(b.get("low", 0)) for b in bars[-14:]]
            bar_closes = [float(b.get("close", 0)) for b in bars[-15:]]
            if len(highs) >= 14 and len(bar_closes) >= 15:
                trs = []
                for i in range(1, len(highs)):
                    tr = max(highs[i] - lows[i],
                             abs(highs[i] - bar_closes[i]),
                             abs(lows[i] - bar_closes[i]))
                    trs.append(tr)
                atr = sum(trs[-14:]) / min(14, len(trs)) if trs else 0
                features["atr_14_pct"] = atr / closes[-1] if closes[-1] > 0 else 0
            else:
                features["atr_14_pct"] = 0.02

            # Build feature vector in correct order
            feature_vector = []
            for col in self._feature_cols:
                feature_vector.append(features.get(col, 0.0))

            return np.array(feature_vector, dtype=np.float32)

        except Exception as e:
            logger.debug("Feature extraction error: %s", e)
            return None

    @staticmethod
    def _compute_rsi(closes: List[float], period: int = 14) -> float:
        """Compute RSI from close prices."""
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(-period, 0):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def get_status(self) -> Dict[str, Any]:
        return {
            "model_loaded": self._loaded,
            "feature_count": len(self._feature_cols),
            "predictions_made": self._predictions_made,
            "val_accuracy": self._metadata.get("val_accuracy", 0),
            "last_trained": self._metadata.get("last_trained", "never"),
            "model_file": str(_MODEL_FILE),
        }


# Module-level singleton
_scorer: Optional[MLScorer] = None


def get_ml_scorer() -> MLScorer:
    global _scorer
    if _scorer is None:
        _scorer = MLScorer()
    return _scorer
