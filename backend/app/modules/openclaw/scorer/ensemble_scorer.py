#!/usr/bin/env python3
"""
ensemble_scorer.py - XGBoost Ensemble Scoring Layer v5.1

Tier 2 Blackboard Scoring Agent: Machine learning ensemble that blends
rule-based composite scoring with gradient-boosted probability predictions.
Uses XGBoost with 25+ features per regime for win probability estimation.

Blackboard Swarm Integration:
    - Subscribes to Topic.SCORED_CANDIDATES from composite_scorer.py
    - Publishes Topic.ML_PREDICTIONS with win probability + confidence
    - Reads Topic.REGIME_STATE for regime-conditioned model selection
    - Reads Topic.WHALE_FLOW for real-time whale feature enrichment
    - Integrates with memory_v3.py for trade history retrieval
    - Publishes Topic.MODEL_METRICS for dashboard monitoring

Architecture:
    Blackboard --> EnsembleScorerAgent --> ML_PREDICTIONS --> auto_executor.py
                                      --> MODEL_METRICS  --> live_dashboard.py

Fixes from Issue #1:
    - Robust imports with try/except for all ML dependencies
    - Graceful fallback when models not trained yet
    - ET timezone for scheduled retraining
    - SHAP feature importance with fallback

Fixes from Issue #6:
    - Time-based train/test split to prevent data leakage
    - Model versioning with timestamp + AUC comparison before overwrite
    - is_friday uses trade's day_of_week, not datetime.now()
    - Feature importance saved correctly (importance only, not full results)
    - Feature drift detection via check_feature_drift()
    - numpy/pandas wrapped in try/except for safe import
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Issue #6 fix: wrap numpy in try/except
try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

try:
    import pandas as pd
    PD_AVAILABLE = True
except ImportError:
    PD_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

# XGBoost
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# Scikit-learn
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        roc_auc_score, log_loss, classification_report,
        precision_recall_fscore_support
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# SHAP for feature importance
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

# Blackboard imports
try:
    from config import (
        BLACKBOARD_ENABLED, ML_ENSEMBLE_ENABLED, MIN_TRAINING_SAMPLES,
        ML_RETRAIN_SCHEDULE, DATA_DIR as CONFIG_DATA_DIR
    )
except ImportError:
    BLACKBOARD_ENABLED = False
    ML_ENSEMBLE_ENABLED = True
    MIN_TRAINING_SAMPLES = 100
    ML_RETRAIN_SCHEDULE = 'saturday_02:00'
    CONFIG_DATA_DIR = 'data'

try:
    from memory_v3 import MemoryV3
except ImportError:
    MemoryV3 = None

# ================================================================
# Logging
# ================================================================
logger = logging.getLogger('ensemble_scorer')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ET = ZoneInfo('America/New_York')

# ================================================================
# Blackboard Topic Registry
# ================================================================
class Topic:
    """Pub/Sub topics for Blackboard swarm communication."""
    SCORED_CANDIDATES = 'scored_candidates'
    ML_PREDICTIONS = 'ml_predictions'
    REGIME_STATE = 'regime_state'
    WHALE_FLOW = 'whale_flow'
    MODEL_METRICS = 'model_metrics'
    TRADE_OUTCOMES = 'trade_outcomes'
    RETRAIN_REQUEST = 'retrain_request'


class Blackboard:
    """Minimal Blackboard for standalone operation."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._subscribers: Dict[str, list] = {}

    def publish(self, topic: str, data: Any):
        self._store[topic] = data
        for cb in self._subscribers.get(topic, []):
            try:
                cb(data)
            except Exception as e:
                logger.debug('Subscriber error on %s: %s', topic, e)

    def read(self, topic: str, default: Any = None) -> Any:
        return self._store.get(topic, default)

    def subscribe(self, topic: str, callback):
        self._subscribers.setdefault(topic, []).append(callback)


# Singleton blackboard
_blackboard: Optional[Blackboard] = None


def get_blackboard() -> Blackboard:
    global _blackboard
    if _blackboard is None:
        _blackboard = Blackboard()
    return _blackboard


def set_blackboard(bb: Blackboard):
    global _blackboard
    _blackboard = bb


# ================================================================
# Configuration
# ================================================================
MODELS_DIR = Path('models')
DATA_DIR = Path(str(CONFIG_DATA_DIR)) if CONFIG_DATA_DIR else Path('data')

# Feature names (25 core + 3 extended = 28 total)
FEATURE_NAMES = [
    # Pillar scores (5)
    'regime_score', 'trend_score', 'pullback_score',
    'momentum_score', 'pattern_score',
    # Sub-indicators (7)
    'rsi', 'williams_r', 'adx', 'macd_hist',
    'volume_ratio', 'atr_pct', 'price_change_5d',
    # Regime context (4)
    'regime_numeric', 'vix', 'hurst_exponent', 'hmm_confidence',
    # Whale data (2)
    'whale_premium_log', 'sentiment_numeric',
    # Sector (3)
    'sector_rank', 'sector_hot', 'sector_cold',
    # Calendar (2)
    'days_to_earnings', 'is_friday',
    # FOM expected moves (2)
    'expected_move_pct', 'entry_distance_pct_of_em',
    # Extended: Memory features (3)
    'ticker_win_rate', 'sector_avg_return', 'regime_hit_rate'
]

# XGBoost hyperparameters
XGB_PARAMS = {
    'objective': 'binary:logistic',
    'eval_metric': ['auc', 'logloss'],
    'max_depth': 6,
    'learning_rate': 0.05,
    'n_estimators': 200,
    'early_stopping_rounds': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'random_state': 42
}

# Training config
TEST_SIZE = 0.2
WIN_THRESHOLD_PCT = 2.0
WIN_LOOKFORWARD_DAYS = 5
ML_PILLAR_MAX = 15
CONFIDENCE_UNCERTAIN_LOW = 0.45
CONFIDENCE_UNCERTAIN_HIGH = 0.55
REGIME_MAP = {'GREEN': 2, 'YELLOW': 1, 'RED': 0}
SENTIMENT_MAP = {'bullish': 1, 'neutral': 0, 'bearish': -1}
POLL_INTERVAL = 5  # seconds between Blackboard polls

# Feature drift threshold (KL divergence)
FEATURE_DRIFT_THRESHOLD = 0.5

# ================================================================
# Feature Engineering
# ================================================================
def _get_memory_features(ticker: str, regime: str) -> Dict[str, float]:
    """Pull historical features from memory_v3 for enrichment."""
    defaults = {'ticker_win_rate': 0.5, 'sector_avg_return': 0.0,
                'regime_hit_rate': 0.5}
    if MemoryV3 is None:
        return defaults
    try:
        mem = MemoryV3()
        stats = mem.get_ticker_stats(ticker) if hasattr(mem, 'get_ticker_stats') else {}
        return {
            'ticker_win_rate': stats.get('win_rate', 0.5),
            'sector_avg_return': stats.get('sector_avg_return', 0.0),
            'regime_hit_rate': stats.get(f'{regime.lower()}_hit_rate', 0.5)
        }
    except Exception:
        return defaults


def extract_features(candidate: Dict, regime: str = 'GREEN') -> np.ndarray:
    """Extract 28 features from a scored candidate.

    Reads pillar scores, technicals, whale data, sector data, calendar,
    FOM expected moves, and memory-enriched features.

    Issue #6 fix: is_friday now uses trade's stored day_of_week
    instead of datetime.now().weekday().
    """
    if not NP_AVAILABLE:
        raise ImportError('numpy is required for feature extraction')

    tech = candidate.get('technicals', {})
    pillars = candidate.get('pillar_scores', {})
    whale = candidate.get('whale_data', {})
    sector = candidate.get('sector_data', {})
    calendar = candidate.get('calendar', {})
    fom = candidate.get('fom_data', {})
    ticker = candidate.get('ticker', 'UNKNOWN')

    # ---- Pillar scores (5) ----
    regime_score = pillars.get('regime', 0)
    trend_score = pillars.get('trend', 0)
    pullback_score = pillars.get('pullback', 0)
    momentum_score = pillars.get('momentum', 0)
    pattern_score = pillars.get('pattern', 0)

    # ---- Sub-indicators (7) ----
    rsi = tech.get('rsi', 50)
    williams_r = tech.get('williams_r', -50)
    adx = tech.get('adx', 20)
    macd_hist = tech.get('macd_hist', 0)
    volume_ratio = tech.get('volume_ratio', 1.0)
    price = tech.get('price', 1)
    atr = tech.get('atr', 0)
    atr_pct = (atr / price * 100) if price > 0 else 0
    price_change_5d = tech.get('price_change_5d', 0)

    # ---- Regime context (4) ----
    regime_numeric = REGIME_MAP.get(regime.upper(), 1)
    vix = candidate.get('vix', 20)
    hurst = candidate.get('hurst_exponent', 0.5)
    hmm_conf = candidate.get('hmm_confidence', 0.5)

    # ---- Whale data (2) ----
    whale_premium = whale.get('net_premium', 0)
    whale_premium_log = np.log10(max(abs(whale_premium), 1))
    if whale_premium < 0:
        whale_premium_log *= -1
    sentiment = SENTIMENT_MAP.get(
        whale.get('sentiment', 'neutral'), 0
    )

    # ---- Sector (3) ----
    sector_rank = sector.get('rank', 6)
    sector_hot = 1 if sector.get('hot', False) else 0
    sector_cold = 1 if sector.get('cold', False) else 0

    # ---- Calendar (2) ----
    days_to_earnings = calendar.get('days_to_earnings', 30)
    # Issue #6 fix: use trade's stored day_of_week, fallback to now()
    trade_day = candidate.get('day_of_week', None)
    if trade_day is None:
        trade_date_str = candidate.get('date', '')
        if trade_date_str:
            try:
                trade_dt = datetime.fromisoformat(trade_date_str)
                trade_day = trade_dt.weekday()
            except (ValueError, TypeError):
                trade_day = datetime.now(ET).weekday()
        else:
            trade_day = datetime.now(ET).weekday()
    is_friday = 1 if trade_day == 4 else 0

    # ---- FOM expected moves (2) ----
    em_pct = fom.get('expected_move_pct', 0)
    entry_dist = fom.get('entry_distance_pct_of_em', 0)

    # ---- Memory enrichment (3) ----
    mem_feats = _get_memory_features(ticker, regime)
    ticker_wr = mem_feats['ticker_win_rate']
    sector_avg = mem_feats['sector_avg_return']
    regime_hr = mem_feats['regime_hit_rate']

    features = np.array([
        regime_score, trend_score, pullback_score,
        momentum_score, pattern_score,
        rsi, williams_r, adx, macd_hist,
        volume_ratio, atr_pct, price_change_5d,
        regime_numeric, vix, hurst, hmm_conf,
        whale_premium_log, sentiment,
        sector_rank, sector_hot, sector_cold,
        days_to_earnings, is_friday,
        em_pct, entry_dist,
        ticker_wr, sector_avg, regime_hr
    ], dtype=np.float32)

    return features

# ================================================================
# Feature Drift Detection (Issue #6 fix)
# ================================================================
def check_feature_drift(
    current_features: np.ndarray,
    reference_stats_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Compare current feature distributions against training set distributions.

    Uses simple mean/std comparison and flags features that have drifted
    beyond FEATURE_DRIFT_THRESHOLD standard deviations.

    Args:
        current_features: Array of shape (n_samples, n_features)
        reference_stats_path: Path to saved training set statistics

    Returns:
        Dict with drift status, drifted features, and details
    """
    if not NP_AVAILABLE:
        return {'error': 'numpy not available', 'drifted': False}

    if reference_stats_path is None:
        reference_stats_path = DATA_DIR / 'training_feature_stats.json'

    if not reference_stats_path.exists():
        return {'error': 'No reference stats found', 'drifted': False}

    try:
        with open(reference_stats_path, 'r') as f:
            ref_stats = json.load(f)
    except Exception as e:
        return {'error': f'Failed to load reference stats: {e}', 'drifted': False}

    if current_features.ndim == 1:
        current_features = current_features.reshape(1, -1)

    current_means = current_features.mean(axis=0)
    drifted_features = []
    drift_details = {}

    for i, name in enumerate(FEATURE_NAMES[:current_features.shape[1]]):
        ref_mean = ref_stats.get(name, {}).get('mean', 0)
        ref_std = ref_stats.get(name, {}).get('std', 1)
        if ref_std < 1e-8:
            ref_std = 1.0

        drift_score = abs(current_means[i] - ref_mean) / ref_std
        drift_details[name] = {
            'current_mean': round(float(current_means[i]), 4),
            'ref_mean': round(ref_mean, 4),
            'ref_std': round(ref_std, 4),
            'drift_score': round(float(drift_score), 4)
        }
        if drift_score > FEATURE_DRIFT_THRESHOLD:
            drifted_features.append(name)

    has_drift = len(drifted_features) > 0
    if has_drift:
        logger.warning(
            'Feature drift detected in %d features: %s',
            len(drifted_features), drifted_features
        )

    return {
        'drifted': has_drift,
        'drifted_features': drifted_features,
        'drift_count': len(drifted_features),
        'total_features': len(FEATURE_NAMES),
        'details': drift_details,
        'timestamp': datetime.now(ET).isoformat()
    }


def _save_training_feature_stats(X: np.ndarray):
    """Save mean/std of training features for drift detection."""
    stats = {}
    for i, name in enumerate(FEATURE_NAMES[:X.shape[1]]):
        stats[name] = {
            'mean': round(float(X[:, i].mean()), 6),
            'std': round(float(X[:, i].std()), 6),
            'min': round(float(X[:, i].min()), 6),
            'max': round(float(X[:, i].max()), 6)
        }
    stats_path = DATA_DIR / 'training_feature_stats.json'
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info('Saved training feature stats to %s', stats_path)

# ================================================================
# Dataset Building
# ================================================================
def build_training_dataset(
    trade_history: List[Dict],
    regime_filter: Optional[str] = None
) -> Tuple:
    """Build X, y, metadata from trade history.

    Returns:
        X: Feature matrix (n_samples, 28)
        y: Labels (1 if 5-day return >= 2%, 0 otherwise)
        metadata: List of dicts with ticker/date info
    """
    X_list, y_list, metadata = [], [], []

    for trade in trade_history:
        try:
            trade_regime = trade.get('regime', 'GREEN').upper()
            if regime_filter and trade_regime != regime_filter.upper():
                continue
            features = extract_features(trade, trade_regime)
            ret_pct = trade.get('return_pct', 0)
            label = 1 if ret_pct >= WIN_THRESHOLD_PCT else 0
            X_list.append(features)
            y_list.append(label)
            metadata.append({
                'ticker': trade.get('ticker', '?'),
                'date': trade.get('date', ''),
                'regime': trade_regime,
                'return_pct': ret_pct
            })
        except Exception as e:
            logger.debug('Skipping trade: %s', e)

    if not X_list:
        return np.array([]), np.array([]), []

    X = np.vstack(X_list)
    y = np.array(y_list)
    logger.info(
        'Built dataset: %d samples, %d features, %.1f%% positive',
        len(y), X.shape[1], np.mean(y) * 100
    )
    return X, y, metadata


# ================================================================
# Model Training
# ================================================================
def _get_previous_model_auc(regime: str) -> Optional[float]:
    """Load AUC from the currently deployed model (Issue #6 fix)."""
    metrics_path = DATA_DIR / 'model_metrics.json'
    if not metrics_path.exists():
        return None
    try:
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        return metrics.get(regime.upper(), {}).get('auc')
    except Exception:
        return None


def _save_model_metrics(results: Dict):
    """Save model metrics for version comparison (Issue #6 fix)."""
    metrics_path = DATA_DIR / 'model_metrics.json'
    try:
        with open(metrics_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    except Exception as e:
        logger.error('Failed to save model metrics: %s', e)


def train_ensemble_models(trade_history: List[Dict]) -> Dict:
    """Train XGBoost models per regime.

    Returns dict with model paths and performance metrics.
    Publishes MODEL_METRICS to Blackboard after training.

    Issue #6 fixes:
        - Time-based split (first 80% train, last 20% test)
        - Model versioning with timestamp filenames
        - AUC comparison before overwriting existing model
        - Correct feature importance storage
        - Training feature stats saved for drift detection
    """
    if not XGB_AVAILABLE or not SKLEARN_AVAILABLE:
        logger.error('XGBoost or sklearn not installed.')
        return {'error': 'Missing dependencies'}
    if not JOBLIB_AVAILABLE:
        logger.error('joblib not installed.')
        return {'error': 'Missing joblib'}

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    bb = get_blackboard()
    timestamp_str = datetime.now(ET).strftime('%Y%m%d_%H%M%S')

    for regime in ['GREEN', 'YELLOW', 'RED']:
        logger.info('Training model for %s regime...', regime)
        X, y, meta = build_training_dataset(trade_history, regime_filter=regime)

        if len(y) < MIN_TRAINING_SAMPLES:
            logger.warning(
                '%s: Only %d samples (need %d). Skipping.',
                regime, len(y), MIN_TRAINING_SAMPLES
            )
            results[regime] = {
                'status': 'insufficient_data',
                'samples': len(y)
            }
            continue

        # Issue #6 fix: Time-based split instead of random split
        # Trades are time-ordered, so use first 80% for training
        split_idx = int(len(y) * (1 - TEST_SIZE))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Save training feature stats for drift detection
        _save_training_feature_stats(X_train)

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train XGBoost
        model = xgb.XGBClassifier(
            objective=XGB_PARAMS['objective'],
            max_depth=XGB_PARAMS['max_depth'],
            learning_rate=XGB_PARAMS['learning_rate'],
            n_estimators=XGB_PARAMS['n_estimators'],
            subsample=XGB_PARAMS['subsample'],
            colsample_bytree=XGB_PARAMS['colsample_bytree'],
            min_child_weight=XGB_PARAMS['min_child_weight'],
            reg_alpha=XGB_PARAMS['reg_alpha'],
            reg_lambda=XGB_PARAMS['reg_lambda'],
            random_state=XGB_PARAMS['random_state'],
            eval_metric='logloss',
            early_stopping_rounds=XGB_PARAMS['early_stopping_rounds']
        )
        model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False
        )

        # Evaluate
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)
        auc = roc_auc_score(y_test, y_pred_proba)
        ll = log_loss(y_test, y_pred_proba)
        prec, rec, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary', zero_division=0
        )

        # Issue #6 fix: Model versioning - compare with previous AUC
        previous_auc = _get_previous_model_auc(regime)
        deploy_model = True
        if previous_auc is not None and auc < previous_auc - 0.02:
            logger.warning(
                '%s: New AUC %.4f < previous %.4f (threshold -0.02). '
                'Keeping old model, saving new as versioned backup.',
                regime, auc, previous_auc
            )
            deploy_model = False

        # Save versioned model (always)
        versioned_model_path = MODELS_DIR / f'xgb_ensemble_{regime.lower()}_{timestamp_str}.pkl'
        versioned_scaler_path = MODELS_DIR / f'scaler_{regime.lower()}_{timestamp_str}.pkl'
        joblib.dump(model, versioned_model_path)
        joblib.dump(scaler, versioned_scaler_path)

        # Deploy to main path only if AUC is acceptable
        model_path = MODELS_DIR / f'xgb_ensemble_{regime.lower()}.pkl'
        scaler_path = MODELS_DIR / f'scaler_{regime.lower()}.pkl'
        if deploy_model:
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            logger.info('%s: Deployed new model (AUC=%.4f)', regime, auc)
        else:
            logger.info('%s: Kept previous model (prev AUC=%.4f, new=%.4f)',
                        regime, previous_auc, auc)

        # Feature importance (native + SHAP fallback)
        importance = dict(zip(FEATURE_NAMES[:len(model.feature_importances_)],
                              model.feature_importances_))
        top_features = sorted(
            importance.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # SHAP analysis
        shap_values_dict = {}
        if SHAP_AVAILABLE:
            try:
                explainer = shap.TreeExplainer(model)
                sv = explainer.shap_values(X_test_scaled[:50])
                mean_abs_shap = np.abs(sv).mean(axis=0)
                for i, name in enumerate(FEATURE_NAMES[:len(mean_abs_shap)]):
                    shap_values_dict[name] = round(float(mean_abs_shap[i]), 6)
            except Exception as e:
                logger.debug('SHAP analysis failed for %s: %s', regime, e)

        results[regime] = {
            'status': 'trained',
            'deployed': deploy_model,
            'auc': round(auc, 4),
            'previous_auc': round(previous_auc, 4) if previous_auc else None,
            'logloss': round(ll, 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1': round(float(f1), 4),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'positive_rate': round(float(np.mean(y)), 4),
            'top_features': [f[0] for f in top_features],
            'shap_importance': shap_values_dict,
            'model_path': str(model_path),
            'versioned_model_path': str(versioned_model_path),
            'scaler_path': str(scaler_path),
            'trained_at': datetime.now(ET).isoformat()
        }

        logger.info(
            '%s: AUC=%.4f LogLoss=%.4f F1=%.4f Top=%s',
            regime, auc, ll, f1, [f[0] for f in top_features]
        )

    # Issue #6 fix: Save feature importance correctly (importance only)
    importance_path = DATA_DIR / 'feature_importance.json'
    importance_data = {}
    for regime, info in results.items():
        if info.get('status') == 'trained':
            importance_data[regime] = {
                'top_features': info.get('top_features', []),
                'shap_importance': info.get('shap_importance', {}),
                'auc': info.get('auc'),
                'trained_at': info.get('trained_at')
            }
    with open(importance_path, 'w') as f:
        json.dump(importance_data, f, indent=2, default=str)

    # Save model metrics for version comparison
    _save_model_metrics(results)

    # Publish to Blackboard
    bb.publish(Topic.MODEL_METRICS, {
        'event': 'models_trained',
        'results': results,
        'timestamp': datetime.now(ET).isoformat()
    })

    return results

# ================================================================
# Prediction Pipeline
# ================================================================
def _load_model(regime: str) -> Tuple:
    """Load model and scaler for a regime."""
    if not JOBLIB_AVAILABLE:
        return None, None
    regime_lower = regime.lower()
    model_path = MODELS_DIR / f'xgb_ensemble_{regime_lower}.pkl'
    scaler_path = MODELS_DIR / f'scaler_{regime_lower}.pkl'
    if not model_path.exists() or not scaler_path.exists():
        return None, None
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        return model, scaler
    except Exception as e:
        logger.error('Failed to load model for %s: %s', regime, e)
        return None, None


def predict_ensemble_score(
    candidate: Dict,
    regime: str = 'GREEN'
) -> float:
    """Predict win probability for a candidate.

    Returns probability (0-1) that stock gains 2%+ in 5 days.
    Falls back to 0.5 if no model available.
    """
    model, scaler = _load_model(regime)
    if model is None or scaler is None:
        logger.debug('No model for %s regime. Returning 0.5.', regime)
        return 0.5
    try:
        features = extract_features(candidate, regime)
        features_scaled = scaler.transform(features.reshape(1, -1))
        proba = model.predict_proba(features_scaled)[0, 1]
        return round(float(proba), 4)
    except Exception as e:
        logger.error('Prediction error: %s', e)
        return 0.5


def calculate_ensemble_confidence(prediction: float) -> float:
    """Calculate confidence level for an ensemble prediction.

    Uncertain predictions (0.45-0.55) get reduced confidence.
    """
    if CONFIDENCE_UNCERTAIN_LOW <= prediction <= CONFIDENCE_UNCERTAIN_HIGH:
        return 0.5
    distance = abs(prediction - 0.5)
    confidence = min(1.0, 0.5 + distance * 2)
    return round(confidence, 4)


def get_ml_pillar_score(
    candidate: Dict,
    regime: str = 'GREEN'
) -> Dict:
    """Get ML ensemble score as a composite pillar component.

    Returns dict with score (0-15), prediction, confidence, and top features.
    Publishes result to Blackboard ML_PREDICTIONS topic.
    """
    bb = get_blackboard()
    prediction = predict_ensemble_score(candidate, regime)
    confidence = calculate_ensemble_confidence(prediction)

    # Scale prediction to ML pillar points
    raw_score = prediction * ML_PILLAR_MAX
    if confidence < 0.7:
        adjusted_score = raw_score * 0.5
    else:
        adjusted_score = raw_score

    # Get top features from stored importance
    top_features = []
    try:
        imp_path = DATA_DIR / 'feature_importance.json'
        if imp_path.exists():
            with open(imp_path, 'r') as f:
                imp_data = json.load(f)
            regime_imp = imp_data.get(regime.upper(), {})
            top_features = regime_imp.get('top_features', [])[:3]
    except Exception:
        pass

    result = {
        'ticker': candidate.get('ticker', 'UNKNOWN'),
        'ml_score': round(adjusted_score, 2),
        'prediction': prediction,
        'confidence': confidence,
        'regime': regime,
        'top_features': top_features,
        'timestamp': datetime.now(ET).isoformat()
    }

    # Publish to Blackboard
    bb.publish(Topic.ML_PREDICTIONS, result)
    return result

# ================================================================
# Scheduled Retraining
# ================================================================
def scheduled_retraining(trade_history: List[Dict] = None) -> Dict:
    """Weekly retraining (Saturday 2:00 AM ET).

    Loads trade history from memory_v3 or file, retrains all regime
    models, publishes metrics to Blackboard.
    """
    logger.info('=== Starting ML ensemble retraining ===')
    if trade_history is None:
        # Try memory_v3 first
        if MemoryV3 is not None:
            try:
                mem = MemoryV3()
                trade_history = (
                    mem.get_all_trades()
                    if hasattr(mem, 'get_all_trades')
                    else []
                )
            except Exception:
                trade_history = []
        # Fallback to file
        if not trade_history:
            history_path = DATA_DIR / 'trade_journal.json'
            try:
                if history_path.exists():
                    with open(history_path, 'r') as f:
                        trade_history = json.load(f)
                else:
                    trade_history = []
            except Exception:
                trade_history = []

    if len(trade_history) < MIN_TRAINING_SAMPLES:
        logger.warning(
            'Only %d trades (need %d). Skipping retraining.',
            len(trade_history), MIN_TRAINING_SAMPLES
        )
        return {'status': 'insufficient_data', 'trades': len(trade_history)}

    results = train_ensemble_models(trade_history)

    # Log summary
    for regime, info in results.items():
        if info.get('status') == 'trained':
            logger.info(
                'ML Model Retrained: %s AUC=%.4f F1=%.4f deployed=%s | Top=%s',
                regime, info['auc'], info.get('f1', 0),
                info.get('deployed', True),
                info.get('top_features', [])
            )

    logger.info('=== ML ensemble retraining complete ===')
    return results


def evaluate_model(
    regime: str = 'GREEN',
    trade_history: List[Dict] = None
) -> Dict:
    """Evaluate current model performance on test data."""
    if trade_history is None:
        history_path = DATA_DIR / 'trade_journal.json'
        try:
            if history_path.exists():
                with open(history_path, 'r') as f:
                    trade_history = json.load(f)
            else:
                return {'error': 'No trade history'}
        except Exception:
            return {'error': 'Failed to load history'}

    model, scaler = _load_model(regime)
    if model is None:
        return {'error': f'No model for {regime}'}

    X, y, meta = build_training_dataset(
        trade_history, regime_filter=regime
    )
    if len(y) == 0:
        return {'error': 'No valid samples'}

    X_scaled = scaler.transform(X)
    y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    prec, rec, f1, _ = precision_recall_fscore_support(
        y, y_pred, average='binary', zero_division=0
    ) if SKLEARN_AVAILABLE else (0, 0, 0, 0)

    # Check feature drift on current data
    drift_result = check_feature_drift(X)

    return {
        'regime': regime,
        'auc': round(roc_auc_score(y, y_pred_proba), 4) if SKLEARN_AVAILABLE else 0,
        'logloss': round(log_loss(y, y_pred_proba), 4) if SKLEARN_AVAILABLE else 0,
        'precision': round(float(prec), 4),
        'recall': round(float(rec), 4),
        'f1': round(float(f1), 4),
        'accuracy': round(float(np.mean(y_pred == y)), 4),
        'samples': len(y),
        'positive_rate': round(float(np.mean(y)), 4),
        'feature_drift': drift_result
    }

# ================================================================
# Blackboard Swarm Agent
# ================================================================
class EnsembleScorerAgent:
    """Async agent that polls Blackboard for scored candidates
    and publishes ML predictions."""

    POLL_INTERVAL = POLL_INTERVAL

    def __init__(self, blackboard: Optional[Blackboard] = None):
        self.bb = blackboard or get_blackboard()
        self.running = False
        self._predictions_count = 0
        self._last_retrain: Optional[str] = None
        set_blackboard(self.bb)
        logger.info('[EnsembleScorer] Agent initialized')

    @property
    def stats(self) -> Dict:
        return {
            'agent': 'ensemble_scorer',
            'running': self.running,
            'predictions': self._predictions_count,
            'last_retrain': self._last_retrain,
            'models_available': {
                r: (MODELS_DIR / f'xgb_ensemble_{r.lower()}.pkl').exists()
                for r in ['GREEN', 'YELLOW', 'RED']
            }
        }

    async def run_forever(self):
        """Main loop: poll Blackboard for candidates, score them."""
        self.running = True
        logger.info('[EnsembleScorer] Starting Blackboard poll loop')
        while self.running:
            try:
                await self._process_candidates()
                await self._check_retrain_schedule()
            except Exception as e:
                logger.error('[EnsembleScorer] Loop error: %s', e)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def _process_candidates(self):
        """Read scored candidates from Blackboard and add ML scores."""
        candidates = self.bb.read(Topic.SCORED_CANDIDATES, [])
        if not candidates:
            return

        regime_data = self.bb.read(Topic.REGIME_STATE, {})
        regime = regime_data.get('regime', 'GREEN') if regime_data else 'GREEN'

        # Enrich with whale data from Blackboard
        whale_data = self.bb.read(Topic.WHALE_FLOW, {})

        batch_results = []
        items = candidates if isinstance(candidates, list) else [candidates]

        for candidate in items:
            if whale_data and 'whale_data' not in candidate:
                ticker = candidate.get('ticker', '')
                candidate['whale_data'] = whale_data.get(ticker, {})

            result = get_ml_pillar_score(candidate, regime)
            batch_results.append(result)
            self._predictions_count += 1

        if batch_results:
            self.bb.publish(Topic.ML_PREDICTIONS, batch_results)
            logger.info(
                '[EnsembleScorer] Scored %d candidates (regime=%s)',
                len(batch_results), regime
            )

    async def _check_retrain_schedule(self):
        """Check if it's time for scheduled retraining."""
        now = datetime.now(ET)
        today_str = now.strftime('%Y-%m-%d')
        if self._last_retrain == today_str:
            return

        # Parse schedule from config
        try:
            day_str, time_str = ML_RETRAIN_SCHEDULE.split('_')
            hour, minute = map(int, time_str.split(':'))
        except (ValueError, AttributeError):
            day_str, hour, minute = 'saturday', 2, 0

        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        target_day = day_map.get(day_str.lower(), 5)

        if now.weekday() == target_day and now.hour == hour and now.minute >= minute:
            logger.info('[EnsembleScorer] Scheduled retraining triggered')
            results = scheduled_retraining()
            self._last_retrain = today_str
            self.bb.publish(Topic.MODEL_METRICS, {
                'event': 'scheduled_retrain',
                'results': results,
                'timestamp': now.isoformat()
            })

    def stop(self):
        self.running = False
        logger.info('[EnsembleScorer] Agent stopped')


# ================================================================
# CLI Interface
# ================================================================
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python ensemble_scorer.py'
              ' [--train|--predict TICKER|--evaluate|--info|--agent|--drift]')
        sys.exit(1)

    command = sys.argv[1]

    if command == '--train':
        print('Running model training...')
        result = scheduled_retraining()
        print(json.dumps(result, indent=2, default=str))

    elif command == '--predict' and len(sys.argv) >= 3:
        ticker = sys.argv[2]
        candidate = {
            'ticker': ticker,
            'regime': 'GREEN',
            'technicals': {'rsi': 45, 'williams_r': -70, 'adx': 28},
            'pillar_scores': {
                'regime': 15, 'trend': 20, 'pullback': 18,
                'momentum': 16, 'pattern': 7
            }
        }
        score = get_ml_pillar_score(candidate, 'GREEN')
        print(f'{ticker} ML Score: {json.dumps(score, indent=2)}')

    elif command == '--evaluate':
        for regime in ['GREEN', 'YELLOW', 'RED']:
            result = evaluate_model(regime)
            print(f'{regime}: {json.dumps(result, indent=2)}')

    elif command == '--drift':
        # Check feature drift against training stats
        print('Checking feature drift...')
        history_path = DATA_DIR / 'trade_journal.json'
        if history_path.exists():
            with open(history_path, 'r') as f:
                trades = json.load(f)
            if trades:
                X, y, _ = build_training_dataset(trades)
                if len(y) > 0:
                    drift = check_feature_drift(X)
                    print(json.dumps(drift, indent=2, default=str))
                else:
                    print('No valid samples for drift check.')
            else:
                print('No trades in journal.')
        else:
            print('No trade journal found.')

    elif command == '--info':
        print('Ensemble Scorer v5.1 - Blackboard Swarm Agent')
        print(f'  Features: {len(FEATURE_NAMES)}')
        print(f'  XGBoost: depth={XGB_PARAMS["max_depth"]}, '
              f'lr={XGB_PARAMS["learning_rate"]}, '
              f'n_est={XGB_PARAMS["n_estimators"]}')
        print(f'  ML Pillar Max: {ML_PILLAR_MAX} points')
        print(f'  Win threshold: {WIN_THRESHOLD_PCT}% in '
              f'{WIN_LOOKFORWARD_DAYS} days')
        print(f'  SHAP available: {SHAP_AVAILABLE}')
        print(f'  XGBoost available: {XGB_AVAILABLE}')
        print(f'  numpy available: {NP_AVAILABLE}')
        print(f'  Memory v3 available: {MemoryV3 is not None}')
        for regime in ['GREEN', 'YELLOW', 'RED']:
            model_path = MODELS_DIR / f'xgb_ensemble_{regime.lower()}.pkl'
            exists = 'YES' if model_path.exists() else 'NO'
            print(f'  {regime} model: {exists}')

    elif command == '--agent':
        print('Starting EnsembleScorer agent...')
        agent = EnsembleScorerAgent()
        try:
            asyncio.run(agent.run_forever())
        except KeyboardInterrupt:
            agent.stop()
            print('Agent stopped.')

    else:
        print('Unknown command. Use --train, --predict, --evaluate, --info, --agent, --drift')
