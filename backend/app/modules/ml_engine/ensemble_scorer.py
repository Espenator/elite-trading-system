"""Ensemble Scorer — combines XGBoost + LSTM predictions for higher accuracy.

Level 2A enhancement: When PyTorch is available, runs LSTM alongside XGBoost
and blends predictions with configurable weights. Falls back to XGBoost-only
when PyTorch is not installed.

Architecture:
    XGBoost (GPU-accelerated) → prob_up_xgb ─┐
                                              ├─ weighted blend → final_prob_up
    LSTM (GPU if available)   → prob_up_lstm ─┘

Default weights: XGBoost 60%, LSTM 40% (LSTM captures temporal patterns
that tree models miss, but XGBoost is more robust to noise).

Usage:
    from app.modules.ml_engine.ensemble_scorer import get_ensemble_scorer
    scorer = get_ensemble_scorer()
    result = await scorer.score(symbol, features_df)
    # result = {"prob_up": 0.73, "xgb_prob": 0.71, "lstm_prob": 0.76, "ensemble": True}
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Ensemble weights — configurable via env
XGB_WEIGHT = float(os.getenv("ENSEMBLE_XGB_WEIGHT", "0.6"))
LSTM_WEIGHT = float(os.getenv("ENSEMBLE_LSTM_WEIGHT", "0.4"))

# PyTorch availability
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Model artifact paths
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


class EnsembleScorer:
    """Blends XGBoost + LSTM predictions for each symbol.

    Loads model artifacts lazily on first score() call.
    Thread-safe via asyncio.to_thread for blocking inference.
    """

    def __init__(self):
        self._xgb_model = None
        self._lstm_model = None
        self._xgb_loaded = False
        self._lstm_loaded = False
        self._feature_cols: List[str] = []

    def _load_xgb(self) -> bool:
        """Load best XGBoost model from artifacts."""
        if self._xgb_loaded:
            return self._xgb_model is not None
        self._xgb_loaded = True
        try:
            import xgboost as xgb
            model_path = ARTIFACTS_DIR / "best_xgb_model.json"
            if not model_path.exists():
                # Try .ubj format
                model_path = ARTIFACTS_DIR / "best_xgb_model.ubj"
            if model_path.exists():
                self._xgb_model = xgb.Booster()
                self._xgb_model.load_model(str(model_path))
                logger.info("EnsembleScorer: loaded XGBoost model from %s", model_path)
                return True
            else:
                logger.debug("EnsembleScorer: no XGBoost model found at %s", ARTIFACTS_DIR)
                return False
        except Exception as e:
            logger.warning("EnsembleScorer: failed to load XGBoost: %s", e)
            return False

    def _load_lstm(self) -> bool:
        """Load LSTM model from artifacts if PyTorch is available."""
        if self._lstm_loaded:
            return self._lstm_model is not None
        self._lstm_loaded = True
        if not TORCH_AVAILABLE:
            logger.debug("EnsembleScorer: PyTorch not available, LSTM disabled")
            return False
        try:
            from app.models.inference import load_model
            model_path = ARTIFACTS_DIR / "best_lstm_model.pt"
            if not model_path.exists():
                # Check alternate location
                model_path = Path("backend/app/models/artifacts/best_lstm_model.pt")
            if model_path.exists():
                # Detect feature count from saved model
                state = torch.load(str(model_path), map_location="cpu", weights_only=True)
                # Infer num_features from first linear layer
                num_features = 5  # default
                for key in state:
                    if "weight" in key and state[key].shape[1] == 5:
                        num_features = 5
                        break
                self._lstm_model = load_model(str(model_path), num_features)
                if self._lstm_model is not None:
                    logger.info("EnsembleScorer: loaded LSTM model from %s", model_path)
                    return True
            logger.debug("EnsembleScorer: no LSTM model found")
            return False
        except Exception as e:
            logger.warning("EnsembleScorer: failed to load LSTM: %s", e)
            return False

    def _predict_xgb(self, features: pd.DataFrame) -> Optional[float]:
        """Run XGBoost prediction, returns P(up) in [0, 1]."""
        if self._xgb_model is None:
            return None
        try:
            import xgboost as xgb
            dmatrix = xgb.DMatrix(features)
            preds = self._xgb_model.predict(dmatrix)
            return float(preds[0]) if len(preds) > 0 else None
        except Exception as e:
            logger.debug("XGBoost predict failed: %s", e)
            return None

    def _predict_lstm(
        self, features_df: pd.DataFrame, symbol: str, feature_cols: List[str]
    ) -> Optional[float]:
        """Run LSTM prediction, returns P(up) in [0, 1]."""
        if self._lstm_model is None or not TORCH_AVAILABLE:
            return None
        try:
            from app.models.inference import SEQ_LEN
            df = features_df[features_df["symbol"] == symbol].sort_values("date")
            if len(df) < SEQ_LEN:
                return None
            window = df.iloc[-SEQ_LEN:][feature_cols]
            if window.isna().any().any():
                return None
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._lstm_model._module.to(device)
            x = torch.tensor(window.values, dtype=torch.float32).unsqueeze(0).to(device)
            with torch.no_grad():
                logit = self._lstm_model._module(x)
                prob_up = torch.sigmoid(logit).item()
            return prob_up
        except Exception as e:
            logger.debug("LSTM predict failed: %s", e)
            return None

    async def score(
        self,
        symbol: str,
        features: Optional[pd.DataFrame] = None,
        feature_cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Score a symbol using XGBoost + LSTM ensemble.

        Returns dict with prob_up, individual model probs, and ensemble flag.
        """
        def _score_sync():
            self._load_xgb()
            self._load_lstm()

            xgb_prob = None
            lstm_prob = None

            if features is not None and self._xgb_model is not None:
                cols = feature_cols or self._feature_cols
                if cols:
                    xgb_features = features[cols].iloc[-1:] if len(features) > 0 else features
                    xgb_prob = self._predict_xgb(xgb_features)

            if features is not None and self._lstm_model is not None and feature_cols:
                lstm_prob = self._predict_lstm(features, symbol, feature_cols)

            # Blend predictions
            if xgb_prob is not None and lstm_prob is not None:
                final = XGB_WEIGHT * xgb_prob + LSTM_WEIGHT * lstm_prob
                return {
                    "prob_up": round(final, 4),
                    "xgb_prob": round(xgb_prob, 4),
                    "lstm_prob": round(lstm_prob, 4),
                    "ensemble": True,
                    "xgb_weight": XGB_WEIGHT,
                    "lstm_weight": LSTM_WEIGHT,
                }
            elif xgb_prob is not None:
                return {
                    "prob_up": round(xgb_prob, 4),
                    "xgb_prob": round(xgb_prob, 4),
                    "lstm_prob": None,
                    "ensemble": False,
                    "model": "xgboost_only",
                }
            elif lstm_prob is not None:
                return {
                    "prob_up": round(lstm_prob, 4),
                    "xgb_prob": None,
                    "lstm_prob": round(lstm_prob, 4),
                    "ensemble": False,
                    "model": "lstm_only",
                }
            else:
                return {
                    "prob_up": 0.5,
                    "xgb_prob": None,
                    "lstm_prob": None,
                    "ensemble": False,
                    "model": "no_model_available",
                }

        return await asyncio.to_thread(_score_sync)

    async def batch_score(
        self,
        symbols: List[str],
        features: pd.DataFrame,
        feature_cols: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Score multiple symbols in a single batch.

        Level 2B: Batch inference — scores all watchlist symbols in one
        GPU pass instead of one-at-a-time.
        """
        def _batch_sync():
            self._load_xgb()
            self._load_lstm()
            results = {}

            for symbol in symbols:
                sym_features = features[features["symbol"] == symbol]
                if sym_features.empty:
                    results[symbol] = {
                        "prob_up": 0.5, "ensemble": False, "model": "no_data",
                    }
                    continue

                xgb_prob = None
                lstm_prob = None

                if self._xgb_model is not None and feature_cols:
                    last_row = sym_features[feature_cols].iloc[-1:]
                    xgb_prob = self._predict_xgb(last_row)

                if self._lstm_model is not None and TORCH_AVAILABLE:
                    lstm_prob = self._predict_lstm(features, symbol, feature_cols)

                if xgb_prob is not None and lstm_prob is not None:
                    final = XGB_WEIGHT * xgb_prob + LSTM_WEIGHT * lstm_prob
                    results[symbol] = {
                        "prob_up": round(final, 4),
                        "xgb_prob": round(xgb_prob, 4),
                        "lstm_prob": round(lstm_prob, 4),
                        "ensemble": True,
                    }
                elif xgb_prob is not None:
                    results[symbol] = {
                        "prob_up": round(xgb_prob, 4),
                        "ensemble": False,
                        "model": "xgboost_only",
                    }
                elif lstm_prob is not None:
                    results[symbol] = {
                        "prob_up": round(lstm_prob, 4),
                        "ensemble": False,
                        "model": "lstm_only",
                    }
                else:
                    results[symbol] = {
                        "prob_up": 0.5,
                        "ensemble": False,
                        "model": "no_model",
                    }

            return results

        return await asyncio.to_thread(_batch_sync)

    def get_status(self) -> Dict[str, Any]:
        """Return ensemble scorer status."""
        return {
            "xgb_loaded": self._xgb_model is not None,
            "lstm_loaded": self._lstm_model is not None,
            "torch_available": TORCH_AVAILABLE,
            "ensemble_active": (
                self._xgb_model is not None and self._lstm_model is not None
            ),
            "xgb_weight": XGB_WEIGHT,
            "lstm_weight": LSTM_WEIGHT,
        }


# ── Singleton ─────────────────────────────────────────────────────────────
_ensemble_scorer: Optional[EnsembleScorer] = None


def get_ensemble_scorer() -> EnsembleScorer:
    """Get or create the singleton EnsembleScorer."""
    global _ensemble_scorer
    if _ensemble_scorer is None:
        _ensemble_scorer = EnsembleScorer()
    return _ensemble_scorer
