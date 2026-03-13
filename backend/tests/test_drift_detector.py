"""Tests for DriftMonitor -- data drift + performance drift detection."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import AsyncMock
from app.modules.ml_engine.drift_detector import (
    DriftMonitor,
    DriftResult,
    _compute_psi,
    check_drift_and_retrain,
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


# --- Rapid regime shift (flash crash / recovery) ---

def test_rapid_regime_shift_sets_data_drift_and_needs_retrain(reference_df):
    """Simulate rapid regime shift: live distribution shifted -> data drift and needs_retrain when cooldown clear."""
    monitor = DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)
    # Live data from clearly different distribution (e.g. post–flash crash)
    np.random.seed(123)
    live_shifted = pd.DataFrame({
        "feature_a": np.random.normal(2.5, 1.5, 100),   # mean shifted
        "feature_b": np.random.normal(10, 3, 100),    # mean + scale shifted
        "feature_c": np.random.uniform(5, 15, 100),   # range shifted
    })
    result = monitor.check(live_shifted, current_accuracy=0.60)
    assert result.data_drift_detected is True
    assert len(result.drifted_features) >= 1
    assert result.psi_scores
    # With no prior retrain trigger, cooldown is ok -> needs_retrain should be True
    assert result.needs_retrain is True


def test_drift_cooldown_blocks_second_retrain_within_24h(reference_df, monkeypatch):
    """Verify 24h cooldown: second drift within 24h does not set needs_retrain."""
    from app.modules.ml_engine import drift_detector
    monkeypatch.setattr(drift_detector, "RETRAIN_COOLDOWN_HOURS", 24)
    monitor = DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)
    live_shifted = pd.DataFrame({
        "feature_a": np.random.normal(3, 1, 100),
        "feature_b": np.random.normal(12, 2, 100),
        "feature_c": np.random.uniform(8, 18, 100),
    })
    result1 = monitor.check(live_shifted, current_accuracy=0.50)
    assert result1.needs_retrain is True
    # Second check immediately: cooldown active
    result2 = monitor.check(live_shifted, current_accuracy=0.48)
    assert result2.performance_drift_detected is True
    assert result2.needs_retrain is False
    assert "cooldown" in result2.message.lower()


@pytest.mark.asyncio
async def test_check_drift_and_retrain_invokes_retrain_fn_when_needs_retrain(reference_df):
    """When drift sets needs_retrain=True, check_drift_and_retrain calls retrain_fn if provided."""
    monitor = DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)
    live_bad = pd.DataFrame({
        "feature_a": np.random.normal(4, 1, 100),
        "feature_b": np.random.normal(15, 2, 100),
        "feature_c": np.random.uniform(10, 20, 100),
    })
    retrain_fn = AsyncMock()
    result = await check_drift_and_retrain(
        monitor=monitor,
        live_df=live_bad,
        current_accuracy=0.45,
        retrain_fn=retrain_fn,
    )
    assert result.needs_retrain is True
    retrain_fn.assert_called_once()


@pytest.mark.asyncio
async def test_check_drift_and_retrain_no_retrain_fn_does_not_raise(reference_df):
    """check_drift_and_retrain with retrain_fn=None does not raise when drift detected."""
    monitor = DriftMonitor(reference_df=reference_df, baseline_accuracy=0.65)
    live_bad = pd.DataFrame({
        "feature_a": np.random.normal(4, 1, 100),
        "feature_b": np.random.normal(15, 2, 100),
        "feature_c": np.random.uniform(10, 20, 100),
    })
    result = await check_drift_and_retrain(
        monitor=monitor,
        live_df=live_bad,
        current_accuracy=0.45,
        retrain_fn=None,
    )
    assert result.needs_retrain is True
