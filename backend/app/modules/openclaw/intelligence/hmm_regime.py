#!/usr/bin/env python3
"""
hmm_regime.py - Hidden Markov Model Regime Detection for OpenClaw v2.0

v2.0 Changes:
    - Joblib model serialization (train once, predict fast)
    - 4-hour retrain interval (not every call)
    - Regime transition smoothing (min hold period)
    - Multi-seed training with best-score selection
    - Fallback to cached model on data fetch failure
    - Hurst exponent as 4th feature

Uses Gaussian HMM (hmmlearn) to detect market regimes from SPY price data.
Trains on 4 features: returns, price range, volume volatility, Hurst exponent
Outputs 7 regime states from bull_run to crash with confidence scores.
"""
import os
import logging
import time
import numpy as np
import warnings
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- HMM Configuration ---
HMM_N_COMPONENTS = 7
HMM_LOOKBACK_DAYS = 365
HMM_COVARIANCE_TYPE = "full"
HMM_N_ITER = 100
HMM_MIN_HOLD_HOURS = 48
HMM_CONFIDENCE_THRESHOLD = 0.6
HURST_WINDOW = 100
MODEL_RETRAIN_INTERVAL = 4 * 3600  # 4 hours between retrains
MODEL_CACHE_PATH = os.path.join(os.path.dirname(__file__), "hmm_model_cache.pkl")
N_TRAINING_SEEDS = 5  # Train with multiple seeds, pick best

REGIME_LABELS = {
    0: "BULL_RUN",
    1: "BULL_TREND",
    2: "RECOVERY",
    3: "NEUTRAL",
    4: "CAUTIOUS",
    5: "BEARISH",
    6: "CRASH",
}

HMM_TO_OPENCLAW = {
    "BULL_RUN": "GREEN",
    "BULL_TREND": "GREEN",
    "RECOVERY": "YELLOW",
    "NEUTRAL": "YELLOW",
    "CAUTIOUS": "YELLOW",
    "BEARISH": "RED",
    "CRASH": "RED",
}

# Module-level cache
_model_cache = {
    "model": None,
    "state_to_label": None,
    "last_train_time": 0,
    "last_regime": "UNKNOWN",
    "last_regime_time": 0,
    "features": None,
}


def _save_model(model, state_to_label, features):
    """Save trained HMM model to disk via joblib."""
    try:
        import joblib
        data = {
            "model": model,
            "state_to_label": state_to_label,
            "features": features,
            "timestamp": time.time(),
        }
        joblib.dump(data, MODEL_CACHE_PATH)
        logger.info(f"HMM: Model saved to {MODEL_CACHE_PATH}")
    except Exception as e:
        logger.warning(f"HMM: Could not save model: {e}")


def _load_model():
    """Load cached HMM model from disk."""
    try:
        import joblib
        if not os.path.exists(MODEL_CACHE_PATH):
            return None
        data = joblib.load(MODEL_CACHE_PATH)
        age_hours = (time.time() - data.get("timestamp", 0)) / 3600
        logger.info(f"HMM: Loaded cached model (age: {age_hours:.1f}h)")
        return data
    except Exception as e:
        logger.warning(f"HMM: Could not load cached model: {e}")
        return None


def _needs_retrain() -> bool:
    """Check if model needs retraining based on time interval."""
    elapsed = time.time() - _model_cache["last_train_time"]
    return elapsed > MODEL_RETRAIN_INTERVAL or _model_cache["model"] is None


def _fetch_spy_data(days=HMM_LOOKBACK_DAYS):
    """Fetch daily SPY OHLCV data from Alpaca Markets Data API.

    Uses httpx to call Alpaca data endpoint directly.
    No yfinance dependency -- replaced Feb 2026 (Issue #11).
    """
    try:
        import httpx
        from datetime import datetime, timedelta
        import pandas as pd

        from app.core.config import settings

        api_key = settings.ALPACA_API_KEY
        secret_key = settings.ALPACA_SECRET_KEY
        if not api_key or not secret_key:
            logger.warning("HMM: Alpaca API keys not configured")
            return None

        end = datetime.utcnow()
        start = end - timedelta(days=min(days, 730))
        data_url = getattr(settings, "ALPACA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
        url = f"{data_url}/v2/stocks/SPY/bars" if "/v2" not in data_url else f"{data_url}/stocks/SPY/bars"
        params = {
            "start": start.strftime("%Y-%m-%dT00:00:00Z"),
            "end": end.strftime("%Y-%m-%dT00:00:00Z"),
            "timeframe": "1Day",
            "limit": 10000,
            "adjustment": "split",
        }
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "accept": "application/json",
        }

        all_bars = []
        next_token = None
        with httpx.Client(timeout=30.0) as client:
            while True:
                if next_token:
                    params["page_token"] = next_token
                resp = client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.error("HMM: Alpaca bars API %s: %s", resp.status_code, resp.text[:200])
                    break
                body = resp.json()
                bars = body.get("bars") or []
                all_bars.extend(bars)
                next_token = body.get("next_page_token")
                if not next_token:
                    break

        if not all_bars:
            logger.warning("HMM: No SPY bars returned from Alpaca")
            return None

        df = pd.DataFrame(all_bars)
        rename = {"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume", "t": "Timestamp"}
        df.rename(columns=rename, inplace=True)
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)
        df.sort_values("Timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(f"HMM: Fetched {len(df)} SPY daily bars from Alpaca")
        return df

    except Exception as e:
        logger.error(f"HMM: Failed to fetch SPY data from Alpaca: {e}")
        return None


def _calculate_hurst_exponent(prices, min_lag=2, max_lag=20):
    """Calculate Hurst exponent via Rescaled Range analysis."""
    try:
        n = len(prices)
        if n < max_lag * 4:
            return 0.5
        lags = range(min_lag, max_lag)
        rs_values = []
        for lag in lags:
            chunks = [prices[i:i + lag] for i in range(0, n - lag, lag)]
            if not chunks:
                continue
            rs_chunk = []
            for chunk in chunks:
                mean_c = np.mean(chunk)
                deviations = np.cumsum(chunk - mean_c)
                r = np.max(deviations) - np.min(deviations)
                s = np.std(chunk, ddof=1)
                if s > 0:
                    rs_chunk.append(r / s)
            if rs_chunk:
                rs_values.append(np.mean(rs_chunk))
        if len(rs_values) < 3:
            return 0.5
        log_lags = np.log(list(lags)[:len(rs_values)])
        log_rs = np.log(rs_values)
        hurst = np.polyfit(log_lags, log_rs, 1)[0]
        return float(np.clip(hurst, 0.0, 1.0))
    except Exception as e:
        logger.debug(f"HMM: Hurst calc failed: {e}")
        return 0.5


def _rolling_hurst(closes, window=HURST_WINDOW):
    """Compute rolling Hurst exponent aligned with closes[1:]."""
    n = len(closes)
    result = np.full(n - 1, 0.5)
    for i in range(window, n):
        result[i - 1] = _calculate_hurst_exponent(closes[i - window:i])
    return result


def _engineer_features(df):
    """Create 4 features: returns, range, vol change, Hurst."""
    try:
        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        volume = df["Volume"].values.astype(float)

        returns = np.diff(np.log(close))
        price_range = (high[1:] - low[1:]) / close[1:]
        vol_safe = np.where(volume == 0, 1, volume)
        vol_change = np.diff(vol_safe) / vol_safe[:-1]
        hurst_series = _rolling_hurst(close, window=HURST_WINDOW)

        features = np.column_stack([returns, price_range, vol_change, hurst_series])
        mask = np.isfinite(features).all(axis=1)
        features = features[mask]

        logger.info(
            f"HMM: Engineered {features.shape[0]} samples with 4 features"
        )
        return features
    except Exception as e:
        logger.error(f"HMM: Feature engineering failed: {e}")
        return None


def _train_hmm_multi_seed(features):
    """Train HMM with multiple random seeds, return best model."""
    try:
        from hmmlearn.hmm import GaussianHMM

        best_model = None
        best_score = -np.inf
        best_states = None

        for seed in range(N_TRAINING_SEEDS):
            try:
                model = GaussianHMM(
                    n_components=HMM_N_COMPONENTS,
                    covariance_type=HMM_COVARIANCE_TYPE,
                    n_iter=HMM_N_ITER,
                    random_state=seed * 42,
                )
                model.fit(features)
                score = model.score(features)
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_states = model.predict(features)
            except Exception:
                continue

        if best_model is not None:
            logger.info(
                f"HMM: Best model score={best_score:.1f} "
                f"from {N_TRAINING_SEEDS} seeds"
            )
        return best_model, best_states
    except Exception as e:
        logger.error(f"HMM: Training failed: {e}")
        return None, None


def _label_states(model, features, hidden_states):
    """Assign regime labels sorted by mean return."""
    state_returns = {}
    for s in range(HMM_N_COMPONENTS):
        mask = hidden_states == s
        state_returns[s] = features[mask, 0].mean() if mask.any() else 0.0

    sorted_states = sorted(
        state_returns.keys(), key=lambda x: state_returns[x], reverse=True
    )
    state_to_label = {
        state_idx: REGIME_LABELS[rank]
        for rank, state_idx in enumerate(sorted_states)
    }
    return state_to_label, state_returns


def _apply_regime_smoothing(new_label: str) -> str:
    """Enforce minimum hold period before regime change."""
    now = time.time()
    last = _model_cache["last_regime"]
    last_time = _model_cache["last_regime_time"]

    if last == "UNKNOWN" or last_time == 0:
        _model_cache["last_regime"] = new_label
        _model_cache["last_regime_time"] = now
        return new_label

    hours_since = (now - last_time) / 3600
    if new_label != last and hours_since < HMM_MIN_HOLD_HOURS:
        logger.info(
            f"HMM: Smoothing - holding {last} "
            f"({hours_since:.1f}h < {HMM_MIN_HOLD_HOURS}h min)"
        )
        return last

    if new_label != last:
        _model_cache["last_regime"] = new_label
        _model_cache["last_regime_time"] = now
    return new_label


def _vix_fallback_regime(result: Dict) -> Dict:
    """Fallback regime detection using VIX when HMM data unavailable."""
    try:
        from regime import regime_detector
        regime_name, regime_config = regime_detector.get_regime()
        vix = regime_detector.get_vix()
        # Map VIX-based regime to HMM-style labels
        vix_to_hmm = {
            "GREEN": "BULL_TREND",
            "YELLOW": "NEUTRAL",
            "RED": "BEARISH",
            "RED_RECOVERY": "RECOVERY",
        }
        hmm_label = vix_to_hmm.get(regime_name, "NEUTRAL")
        result.update({
            "hmm_regime": hmm_label,
            "hmm_openclaw": regime_name,
            "hmm_confidence": 0.5,  # Moderate confidence for VIX fallback
            "hmm_summary": f"VIX Fallback: {hmm_label} ({regime_name}) | VIX={vix:.1f} | No HMM data",
        })
        logger.info(f"HMM: VIX fallback regime = {regime_name} (VIX={vix:.1f})")
        return result
    except Exception as e:
        logger.error(f"HMM: VIX fallback also failed: {e}")
        return result


def detect_hmm_regime() -> Dict:
    """
    Main entry point: detect current market regime via HMM.
    v2.0: Uses cached model, retrains every 4h, smoothes transitions.
    """
    result = {
        "hmm_regime": "UNKNOWN",
        "hmm_openclaw": "YELLOW",
        "hmm_confidence": 0.0,
        "hmm_state_id": -1,
        "hmm_all_states": {},
        "hurst_exponent": 0.5,
        "hurst_label": "RANDOM",
        "hmm_summary": "HMM regime detection not available",
    }

    try:
        # Check if retrain needed
        if _needs_retrain():
            logger.info("HMM: Retraining model...")
            df = _fetch_spy_data()
            if df is None or len(df) < 100:
                # Try loading from disk
                cached = _load_model()
                if cached:
                    _model_cache["model"] = cached["model"]
                    _model_cache["state_to_label"] = cached["state_to_label"]
                    _model_cache["features"] = cached["features"]
                    _model_cache["last_train_time"] = time.time()
                    logger.info("HMM: Using disk-cached model (data fetch failed)")
                else:
                    logger.warning("HMM: No data and no cached model")
                                        # Fallback: use VIX-based regime from regime.py
                    return _vix_fallback_regime(result)
            else:
                features = _engineer_features(df)
                if features is None or len(features) < 100:
                    logger.warning("HMM: Insufficient features")
                    return result

                model, hidden_states = _train_hmm_multi_seed(features)
                if model is None:
                    return result

                state_to_label, _ = _label_states(model, features, hidden_states)

                # Update cache
                _model_cache["model"] = model
                _model_cache["state_to_label"] = state_to_label
                _model_cache["features"] = features
                _model_cache["last_train_time"] = time.time()

                # Save to disk
                _save_model(model, state_to_label, features)

        # Use cached model for prediction
        model = _model_cache["model"]
        state_to_label = _model_cache["state_to_label"]
        features = _model_cache["features"]

        if model is None or features is None:
            return result

        hidden_states = model.predict(features)
        current_state = hidden_states[-1]
        raw_label = state_to_label[current_state]

        # Apply smoothing
        current_label = _apply_regime_smoothing(raw_label)

        # Confidence
        try:
            proba = model.predict_proba(features[-1:])
            confidence = float(proba[0, current_state])
                        # Fix: if confidence is near-zero, use max state probability
            if confidence < 0.05 and proba is not None:
                max_conf = float(np.max(proba[0]))
                best_state = int(np.argmax(proba[0]))
                if max_conf > confidence:
                    confidence = max_conf
                    current_state = best_state
                    raw_label = state_to_label[current_state]
                    current_label = _apply_regime_smoothing(raw_label)
                    logger.info(f"HMM: Adjusted to highest-prob state {raw_label} (conf: {confidence:.1%})")
        except Exception:
            proba = None
            confidence = 0.5

        # All states
        all_states = {}
        for s in range(HMM_N_COMPONENTS):
            label = state_to_label.get(s, f"STATE_{s}")
            try:
                prob = float(proba[0, s]) if proba is not None else 0.0
            except Exception:
                prob = 0.0
            all_states[label] = round(prob, 4)

        # Hurst from last feature row
        current_hurst = float(features[-1, 3])
        if current_hurst > 0.55:
            hurst_label = "TRENDING"
        elif current_hurst < 0.45:
            hurst_label = "MEAN_REVERTING"
        else:
            hurst_label = "RANDOM"

        openclaw_regime = HMM_TO_OPENCLAW.get(current_label, "YELLOW")

        summary = (
            f"HMM Regime: {current_label} "
            f"(conf: {confidence:.1%}) | "
            f"OpenClaw: {openclaw_regime} | "
            f"Hurst: {current_hurst:.3f} ({hurst_label}) | "
            f"Trained on {len(features)} samples"
        )

        result.update({
            "hmm_regime": current_label,
            "hmm_openclaw": openclaw_regime,
            "hmm_confidence": round(confidence, 4),
            "hmm_state_id": int(current_state),
            "hmm_all_states": all_states,
            "hurst_exponent": round(current_hurst, 4),
            "hurst_label": hurst_label,
            "hmm_summary": summary,
        })

        logger.info(f"HMM: {summary}")
        return result

    except Exception as e:
        logger.error(f"HMM: Regime detection failed: {e}")
        return _vix_fallback_regime(result)


def detect_regime() -> Dict:
    """Alias for main.py compatibility. Maps hmm keys to expected keys."""
    hmm_result = detect_hmm_regime()
    return {
        'regime': hmm_result.get('hmm_openclaw', 'neutral'),
        'confidence': hmm_result.get('hmm_confidence', 0.0),
        'hmm_regime': hmm_result.get('hmm_regime', 'UNKNOWN'),
        'hurst_exponent': hmm_result.get('hurst_exponent', 0.5),
        'hurst_label': hmm_result.get('hurst_label', 'RANDOM'),
        'hmm_summary': hmm_result.get('hmm_summary', ''),
    }
