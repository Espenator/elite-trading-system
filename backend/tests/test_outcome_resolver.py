"""Tests for ML outcome resolver -- records signal outcomes and computes accuracy."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def clean_resolver():
    """Patch db_service so outcome_resolver uses in-memory store."""
    store = {}
    mock_db = MagicMock()
    mock_db.get_config.side_effect = lambda key: store.get(key)
    mock_db.set_config.side_effect = lambda key, val: store.__setitem__(key, val)

    with patch("app.modules.ml_engine.outcome_resolver.db_service", mock_db):
        from app.modules.ml_engine import outcome_resolver
        yield outcome_resolver, store


def test_record_outcome_stores_entry(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-15", outcome=1, prediction=1)
    data = store["ml_outcome_resolver"]
    assert len(data["resolved"]) == 1
    assert data["resolved"][0]["symbol"] == "AAPL"
    assert data["resolved"][0]["outcome"] == 1


def test_accuracy_computed_after_record(clean_resolver):
    resolver, store = clean_resolver
    # Record 3 correct, 1 wrong -> 75% accuracy
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1, prediction=1)
    resolver.record_outcome("MSFT", "2026-01-02", outcome=0, prediction=0)
    resolver.record_outcome("GOOGL", "2026-01-03", outcome=1, prediction=1)
    resolver.record_outcome("TSLA", "2026-01-04", outcome=0, prediction=1)  # wrong
    data = store["ml_outcome_resolver"]
    assert data["accuracy_30d"] == 0.75


def test_outcome_capped_at_2000_entries(clean_resolver):
    resolver, store = clean_resolver
    for i in range(2010):
        resolver.record_outcome(f"SYM{i}", f"2026-01-{(i % 28) + 1:02d}", outcome=1)
    data = store["ml_outcome_resolver"]
    assert len(data["resolved"]) <= 2000


def test_flywheel_metrics_returns_counts(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1, prediction=1)
    metrics = resolver.get_flywheel_metrics()
    assert metrics["resolved_count"] == 1
    assert metrics["accuracy_30d"] is not None


def test_no_prediction_excluded_from_accuracy(clean_resolver):
    resolver, store = clean_resolver
    resolver.record_outcome("AAPL", "2026-01-01", outcome=1)  # no prediction
    data = store["ml_outcome_resolver"]
    assert data["accuracy_30d"] is None  # can't compute without prediction
