"""Tests for DriftMonitor -- data drift + performance drift detection."""
import numpy as np
import pandas as pd
import pytest
from app.modules.ml_engine.drift_detector import (
    DriftMonitor,
    DriftResult,
    _compute_psi,
    PERF_ACCURACY_FLOOR,
    PERF_DECAY_THRESHOLD,
    PSI_THRESHOLD,
)


@pytest.fixture
def reference_df():
    """Generate stable reference data (training distribution)."""
    np.random.seed(42)
    return pd.DataFrame({
        "feature_a": np.random.normal(0, 1, 500),
        "feature_b": np.random.normal(5, 2, 500),
        "feature_c": np.random.uniform(0, 10, 500),
    })


@pytest.fixture
def monitor(reference_df):
    return DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)


# --- PSI ---

def test_psi_same_distribution():
    """Same distribution -> PSI near 0."""
    np.random.seed(0)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(0, 1, 1000)
    psi = _compute_psi(ref, cur)
    assert psi < PSI_THRESHOLD


def test_psi_shifted_distribution():
    """Shifted mean -> PSI > threshold."""
    np.random.seed(0)
    ref = np.random.normal(0, 1, 1000)
    cur = np.random.normal(3, 1, 1000)  # shifted by 3 std
    psi = _compute_psi(ref, cur)
    assert psi > PSI_THRESHOLD


# --- No drift ---

def test_no_drift_detected(monitor, reference_df):
    """Live data from same distribution -> no drift."""
    np.random.seed(99)
    live = pd.DataFrame({
        "feature_a": np.random.normal(0, 1, 100),
        "feature_b": np.random.normal(5, 2, 100),
        "feature_c": np.random.uniform(0, 10, 100),
    })
    result = monitor.check(live, current_accuracy=0.63)
    assert result.needs_retrain is False


# --- Performance drift ---

def test_performance_below_floor(monitor, reference_df):
    """Accuracy below coin-flip floor -> performance drift."""
    live = reference_df.sample(50, random_state=1)
    result = monitor.check(live, current_accuracy=0.48)
    assert result.performance_drift_detected is True


def test_performance_decay_from_baseline(monitor, reference_df):
    """Accuracy dropped >10% from baseline -> drift."""
    live = reference_df.sample(50, random_state=1)
    result = monitor.check(live, current_accuracy=0.54)  # 0.65 - 0.54 = 0.11 > 0.10
    assert result.performance_drift_detected is True


# --- Insufficient data ---

def test_insufficient_live_data(monitor):
    """Less than 30 rows -> skip check gracefully."""
    small_df = pd.DataFrame({"feature_a": [1, 2, 3], "feature_b": [4, 5, 6], "feature_c": [7, 8, 9]})
    result = monitor.check(small_df)
    assert "Insufficient" in result.message


# --- No reference ---

def test_no_reference_set(tmp_path, monkeypatch):
    """Monitor without reference -> skip check."""
    # Ensure no existing reference is loaded from disk
    monkeypatch.setattr(
        "app.modules.ml_engine.drift_detector.ReferenceStats.load",
        staticmethod(lambda path=None: None),
    )
    m = DriftMonitor()
    result = m.check(pd.DataFrame({"x": range(50)}))
    assert "No reference" in result.message


# --- Status API ---

def test_get_status(monitor):
    status = monitor.get_status()
    assert status["reference_set"] is True
    assert status["reference_features"] == 3
