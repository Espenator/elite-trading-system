"""
Drift Detector v1.0 — Data drift + performance drift monitoring with auto-retrain triggers.

Uses alibi-detect TabularDrift for feature distribution monitoring,
plus custom performance drift detection via rolling accuracy decay.
Integrates with: outcome_resolver.py (performance signals), trainer.py (retrain trigger),
    model_registry.py (new models), flywheel.py (metrics dashboard).

Usage:
    from app.modules.ml_engine.drift_detector import DriftMonitor
    monitor = DriftMonitor(reference_df=training_data[feature_cols])
    result = monitor.check(live_data[feature_cols])
    if result.needs_retrain:
        trigger_retrain()
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_DRIFT_DIR = Path(__file__).resolve().parent / "artifacts" / "drift"
_DRIFT_DIR.mkdir(parents=True, exist_ok=True)
_DRIFT_LOG_FILE = _DRIFT_DIR / "drift_log.json"
_REFERENCE_FILE = _DRIFT_DIR / "reference_stats.json"

# Thresholds
DATA_DRIFT_P_VALUE = 0.05         # Below this → feature distribution shifted
PERF_ACCURACY_FLOOR = 0.52        # Below 52% → worse than coin flip
PERF_DECAY_THRESHOLD = 0.10       # 10% accuracy drop from baseline → trigger
PSI_THRESHOLD = 0.20              # Population Stability Index threshold
MAX_HISTORY_ENTRIES = 500
RETRAIN_COOLDOWN_HOURS = 24       # Minimum hours between retrain triggers


@dataclass
class DriftResult:
    """Result of a single drift check."""
    timestamp: str = ""
    data_drift_detected: bool = False
    performance_drift_detected: bool = False
    needs_retrain: bool = False
    drifted_features: List[str] = field(default_factory=list)
    drift_scores: Dict[str, float] = field(default_factory=dict)
    psi_scores: Dict[str, float] = field(default_factory=dict)
    current_accuracy: Optional[float] = None
    baseline_accuracy: Optional[float] = None
    accuracy_delta: Optional[float] = None
    message: str = ""
    method: str = ""  # "alibi_detect", "psi", "ks_test"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReferenceStats:
    """Statistics from the reference (training) distribution."""
    means: Dict[str, float] = field(default_factory=dict)
    stds: Dict[str, float] = field(default_factory=dict)
    quantiles: Dict[str, List[float]] = field(default_factory=dict)  # [q10, q25, q50, q75, q90]
    n_samples: int = 0
    feature_cols: List[str] = field(default_factory=list)
    baseline_accuracy: float = 0.0
    created_at: str = ""

    def save(self, path: Path = _REFERENCE_FILE):
        path.write_text(json.dumps(asdict(self), indent=2, default=str))

    @classmethod
    def load(cls, path: Path = _REFERENCE_FILE) -> Optional["ReferenceStats"]:
        if path.exists():
            try:
                return cls(**json.loads(path.read_text()))
            except Exception:
                return None
        return None


# ---------------------------------------------------------------------------
# PSI (Population Stability Index) — works without alibi-detect
# ---------------------------------------------------------------------------

def _compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Compute Population Stability Index between reference and current distributions."""
    eps = 1e-6
    # Create bins from reference
    breakpoints = np.percentile(reference, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)
    if len(breakpoints) < 3:
        return 0.0

    ref_counts = np.histogram(reference, bins=breakpoints)[0]
    cur_counts = np.histogram(current, bins=breakpoints)[0]

    ref_pct = ref_counts / (ref_counts.sum() + eps) + eps
    cur_pct = cur_counts / (cur_counts.sum() + eps) + eps

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)


# ---------------------------------------------------------------------------
# KS Test fallback (scipy-based)
# ---------------------------------------------------------------------------

def _ks_test(reference: np.ndarray, current: np.ndarray) -> Tuple[float, float]:
    """Kolmogorov-Smirnov test; returns (statistic, p_value)."""
    try:
        from scipy import stats
        result = stats.ks_2samp(reference, current)
        return float(result.statistic), float(result.pvalue)
    except ImportError:
        # Manual KS approximation
        n1, n2 = len(reference), len(current)
        combined = np.concatenate([reference, current])
        sorted_vals = np.sort(np.unique(combined))
        ecdf_ref = np.searchsorted(np.sort(reference), sorted_vals, side="right") / n1
        ecdf_cur = np.searchsorted(np.sort(current), sorted_vals, side="right") / n2
        d_stat = float(np.max(np.abs(ecdf_ref - ecdf_cur)))
        # Approximate p-value
        n_eff = np.sqrt(n1 * n2 / (n1 + n2))
        p_value = float(np.exp(-2 * (d_stat * n_eff) ** 2))
        return d_stat, p_value


# ---------------------------------------------------------------------------
# Alibi-detect wrapper
# ---------------------------------------------------------------------------

def _try_alibi_detect(reference: np.ndarray, current: np.ndarray, feature_names: List[str]) -> Optional[Dict]:
    """Try alibi-detect TabularDrift; return None if not available."""
    try:
        from alibi_detect.cd import TabularDrift

        detector = TabularDrift(
            reference,
            p_val=DATA_DRIFT_P_VALUE,
            categories_per_feature={},
        )
        result = detector.predict(current)
        drift_by_feature = {}
        if "data" in result and "p_val" in result["data"]:
            p_vals = result["data"]["p_val"]
            if hasattr(p_vals, "__len__") and len(p_vals) == len(feature_names):
                for i, fname in enumerate(feature_names):
                    drift_by_feature[fname] = float(p_vals[i])

        return {
            "is_drift": bool(result.get("data", {}).get("is_drift", 0)),
            "p_values": drift_by_feature,
            "threshold": DATA_DRIFT_P_VALUE,
        }
    except ImportError:
        return None
    except Exception as e:
        log.warning("alibi-detect failed: %s, falling back to PSI/KS", e)
        return None


# ---------------------------------------------------------------------------
# Drift Monitor
# ---------------------------------------------------------------------------

class DriftMonitor:
    """
    Monitors feature distribution drift and model performance decay.
    Triggers auto-retrain when thresholds are breached.
    """

    def __init__(
        self,
        reference_df: Optional[pd.DataFrame] = None,
        feature_cols: Optional[List[str]] = None,
        baseline_accuracy: float = 0.60,
    ):
        """
        Args:
            reference_df: Training data features (for computing reference distribution).
            feature_cols: Feature column names. If None, uses all columns of reference_df.
            baseline_accuracy: Model accuracy at training time.
        """
        self._reference_stats: Optional[ReferenceStats] = None
        self._reference_array: Optional[np.ndarray] = None
        self._drift_log: List[Dict] = []
        self._last_retrain_trigger: Optional[datetime] = None
        self._accuracy_history: deque = deque(maxlen=100)

        # Load existing reference if available
        existing = ReferenceStats.load()

        if reference_df is not None and not reference_df.empty:
            cols = feature_cols or list(reference_df.columns)
            self._set_reference(reference_df[cols], cols, baseline_accuracy)
        elif existing:
            self._reference_stats = existing
            log.info("Loaded existing reference stats from disk (%d features)", len(existing.feature_cols))

    def _set_reference(self, df: pd.DataFrame, feature_cols: List[str], baseline_accuracy: float):
        """Compute and store reference distribution statistics."""
        clean = df.dropna()
        if clean.empty:
            log.warning("Reference DataFrame is empty after dropping NaN")
            return

        self._reference_array = clean.values.astype(np.float32)
        stats = ReferenceStats(
            means={c: float(clean[c].mean()) for c in feature_cols},
            stds={c: float(clean[c].std()) for c in feature_cols},
            quantiles={c: clean[c].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).tolist() for c in feature_cols},
            n_samples=len(clean),
            feature_cols=feature_cols,
            baseline_accuracy=baseline_accuracy,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        stats.save()
        self._reference_stats = stats
        log.info("Reference stats set: %d samples, %d features", len(clean), len(feature_cols))

    def update_reference(self, df: pd.DataFrame, feature_cols: List[str], baseline_accuracy: float):
        """Update reference distribution (call after retraining)."""
        self._set_reference(df, feature_cols, baseline_accuracy)

    def record_accuracy(self, accuracy: float, batch_size: int = 1):
        """Record a live accuracy measurement for performance drift tracking."""
        self._accuracy_history.append({
            "accuracy": accuracy,
            "batch_size": batch_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def check(
        self,
        live_df: pd.DataFrame,
        current_accuracy: Optional[float] = None,
    ) -> DriftResult:
        """
        Check for data drift and performance drift.

        Args:
            live_df: Recent live data with same feature columns as reference.
            current_accuracy: Current model accuracy (from outcome_resolver).

        Returns:
            DriftResult with drift status and retrain recommendation.
        """
        result = DriftResult(timestamp=datetime.now(timezone.utc).isoformat())

        if self._reference_stats is None:
            result.message = "No reference distribution set — skip drift check"
            return result

        feature_cols = self._reference_stats.feature_cols
        available_cols = [c for c in feature_cols if c in live_df.columns]
        if not available_cols:
            result.message = f"No matching feature columns in live data"
            return result

        live_clean = live_df[available_cols].dropna()
        if len(live_clean) < 30:
            result.message = f"Insufficient live data ({len(live_clean)} < 30 rows)"
            return result

        # --- 1. Data Drift Detection ---
        result = self._check_data_drift(live_clean, available_cols, result)

        # --- 2. Performance Drift Detection ---
        if current_accuracy is not None:
            result = self._check_performance_drift(current_accuracy, result)

        # --- 3. Retrain Decision ---
        cooldown_ok = self._cooldown_ok()
        if (result.data_drift_detected or result.performance_drift_detected) and cooldown_ok:
            result.needs_retrain = True
            self._last_retrain_trigger = datetime.now(timezone.utc)
            result.message += " | RETRAIN TRIGGERED"
        elif not cooldown_ok:
            result.message += " | retrain cooldown active"

        # Log result
        self._drift_log.append(result.to_dict())
        if len(self._drift_log) > MAX_HISTORY_ENTRIES:
            self._drift_log = self._drift_log[-MAX_HISTORY_ENTRIES:]
        self._save_drift_log()

        return result

    def _check_data_drift(
        self, live_df: pd.DataFrame, feature_cols: List[str], result: DriftResult
    ) -> DriftResult:
        """Check feature distribution drift using alibi-detect → PSI → KS fallback chain."""
        live_array = live_df.values.astype(np.float32)

        # Try alibi-detect first
        if self._reference_array is not None:
            ref_cols = self._reference_stats.feature_cols
            ref_indices = [ref_cols.index(c) for c in feature_cols if c in ref_cols]
            ref_array = self._reference_array[:, ref_indices] if ref_indices else self._reference_array

            alibi_result = _try_alibi_detect(ref_array, live_array, feature_cols)
            if alibi_result is not None:
                result.method = "alibi_detect"
                result.data_drift_detected = alibi_result["is_drift"]
                result.drift_scores = alibi_result["p_values"]
                result.drifted_features = [
                    f for f, p in alibi_result["p_values"].items()
                    if p < DATA_DRIFT_P_VALUE
                ]
                if result.data_drift_detected:
                    result.message = f"Data drift detected via alibi-detect in {len(result.drifted_features)} features"
                return result

        # Fallback: PSI + KS per feature
        result.method = "psi_ks"
        psi_scores = {}
        drifted = []
        stats = self._reference_stats

        for col in feature_cols:
            if col not in stats.means:
                continue
            live_vals = live_df[col].values
            # Reconstruct reference from stats (approximate)
            ref_mean = stats.means[col]
            ref_std = max(stats.stds.get(col, 1.0), 1e-8)
            n_ref = min(stats.n_samples, 5000)
            ref_synthetic = np.random.normal(ref_mean, ref_std, n_ref).astype(np.float32)

            psi = _compute_psi(ref_synthetic, live_vals)
            psi_scores[col] = round(psi, 4)

            if psi > PSI_THRESHOLD:
                drifted.append(col)

            # KS test for additional confirmation
            ks_stat, ks_p = _ks_test(ref_synthetic, live_vals)
            result.drift_scores[col] = round(ks_p, 4)

        result.psi_scores = psi_scores
        result.drifted_features = drifted
        result.data_drift_detected = len(drifted) >= max(1, len(feature_cols) // 5)

        if result.data_drift_detected:
            result.message = f"PSI drift in {len(drifted)}/{len(feature_cols)} features: {drifted[:5]}"

        return result

    def _check_performance_drift(self, current_accuracy: float, result: DriftResult) -> DriftResult:
        """Check if model performance has degraded below thresholds."""
        baseline = self._reference_stats.baseline_accuracy if self._reference_stats else 0.60
        result.current_accuracy = current_accuracy
        result.baseline_accuracy = baseline
        result.accuracy_delta = round(current_accuracy - baseline, 4)

        # Check absolute floor
        if current_accuracy < PERF_ACCURACY_FLOOR:
            result.performance_drift_detected = True
            result.message += f" | Accuracy {current_accuracy:.3f} below floor {PERF_ACCURACY_FLOOR}"
            return result

        # Check relative decay
        if (baseline - current_accuracy) > PERF_DECAY_THRESHOLD:
            result.performance_drift_detected = True
            result.message += f" | Accuracy decayed {result.accuracy_delta:.3f} from baseline {baseline:.3f}"

        return result

    def _cooldown_ok(self) -> bool:
        """Check if enough time has passed since last retrain trigger."""
        if self._last_retrain_trigger is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_retrain_trigger).total_seconds() / 3600
        return elapsed >= RETRAIN_COOLDOWN_HOURS

    def _save_drift_log(self):
        try:
            _DRIFT_LOG_FILE.write_text(json.dumps(self._drift_log[-50:], indent=2, default=str))
        except Exception as e:
            log.warning("Failed to save drift log: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Get drift monitor status for API/dashboard."""
        recent = self._drift_log[-1] if self._drift_log else {}
        return {
            "reference_set": self._reference_stats is not None,
            "reference_features": len(self._reference_stats.feature_cols) if self._reference_stats else 0,
            "reference_samples": self._reference_stats.n_samples if self._reference_stats else 0,
            "baseline_accuracy": self._reference_stats.baseline_accuracy if self._reference_stats else None,
            "last_check": recent.get("timestamp"),
            "data_drift_detected": recent.get("data_drift_detected", False),
            "performance_drift_detected": recent.get("performance_drift_detected", False),
            "needs_retrain": recent.get("needs_retrain", False),
            "drifted_features": recent.get("drifted_features", []),
            "checks_logged": len(self._drift_log),
        }

    def get_drift_history(self, limit: int = 20) -> List[Dict]:
        """Get recent drift check results."""
        return self._drift_log[-limit:]


# ---------------------------------------------------------------------------
# Auto-retrain integration
# ---------------------------------------------------------------------------

async def check_drift_and_retrain(
    monitor: DriftMonitor,
    live_df: pd.DataFrame,
    current_accuracy: Optional[float] = None,
    retrain_fn: Optional[callable] = None,
) -> DriftResult:
    """
    High-level function to check drift and trigger retrain if needed.
    Called from the market data tick loop or a scheduled task.

    Args:
        monitor: DriftMonitor instance.
        live_df: Recent market data with features.
        current_accuracy: Latest accuracy from outcome_resolver.
        retrain_fn: Async callable to trigger retraining.

    Returns:
        DriftResult.
    """
    result = monitor.check(live_df, current_accuracy)

    if result.needs_retrain and retrain_fn is not None:
        log.info("Drift detected — triggering auto-retrain: %s", result.message)
        try:
            await retrain_fn()
            log.info("Auto-retrain completed successfully")
        except Exception as e:
            log.error("Auto-retrain failed: %s", e)

    return result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_monitor: Optional[DriftMonitor] = None


def get_drift_monitor() -> DriftMonitor:
    """Get or create global DriftMonitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = DriftMonitor()
    return _monitor
