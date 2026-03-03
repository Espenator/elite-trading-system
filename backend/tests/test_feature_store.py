"""Tests for Feature Store and Feature Aggregator."""
import hashlib
import json
from datetime import datetime, timezone

import pytest


class TestFeatureStoreHash:
    """Test feature hash stability."""

    def test_same_inputs_same_hash(self):
        from app.data.feature_store import FeatureStore
        d1 = {"a": 1.0, "b": 2.0, "c": 3.0}
        d2 = {"c": 3.0, "a": 1.0, "b": 2.0}  # Different order
        assert FeatureStore._compute_hash(d1) == FeatureStore._compute_hash(d2)

    def test_different_inputs_different_hash(self):
        from app.data.feature_store import FeatureStore
        d1 = {"a": 1.0, "b": 2.0}
        d2 = {"a": 1.0, "b": 3.0}
        assert FeatureStore._compute_hash(d1) != FeatureStore._compute_hash(d2)

    def test_hash_is_deterministic(self):
        from app.data.feature_store import FeatureStore
        d = {"x": 42, "y": "hello"}
        h1 = FeatureStore._compute_hash(d)
        h2 = FeatureStore._compute_hash(d)
        assert h1 == h2
        assert len(h1) == 16  # Truncated SHA256


class TestFeatureVector:
    """Test FeatureVector dataclass."""

    def test_to_dict_merges_all_features(self):
        from app.features.feature_aggregator import FeatureVector
        fv = FeatureVector(
            symbol="AAPL",
            timestamp="2024-01-01T00:00:00",
            timeframe="1d",
            price_features={"close": 150.0},
            volume_features={"volume": 1000000},
        )
        d = fv.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["features"]["close"] == 150.0
        assert d["features"]["volume"] == 1000000
        assert d["feature_count"] == 2

    def test_hash_stable(self):
        from app.features.feature_aggregator import FeatureVector
        fv1 = FeatureVector(
            symbol="AAPL", timestamp="2024-01-01", timeframe="1d",
            price_features={"a": 1}, volume_features={"b": 2},
        )
        fv2 = FeatureVector(
            symbol="AAPL", timestamp="2024-01-01", timeframe="1d",
            price_features={"a": 1}, volume_features={"b": 2},
        )
        assert fv1.hash == fv2.hash


class TestPriceFeatures:
    """Test price feature computation."""

    def test_returns_from_ohlcv(self):
        from app.features.feature_aggregator import _compute_price_features
        rows = [{"close": 100 + i} for i in range(25)]
        features = _compute_price_features(rows)
        assert "last_close" in features
        assert "return_1d" in features
        assert features["last_close"] == 124.0

    def test_empty_rows(self):
        from app.features.feature_aggregator import _compute_price_features
        assert _compute_price_features([]) == {}


class TestVolumeFeatures:
    """Test volume feature computation."""

    def test_volume_surge(self):
        from app.features.feature_aggregator import _compute_volume_features
        rows = [{"volume": 1000}] * 19 + [{"volume": 5000}]
        features = _compute_volume_features(rows)
        assert features["volume_surge_ratio"] > 1.0

    def test_empty_rows(self):
        from app.features.feature_aggregator import _compute_volume_features
        assert _compute_volume_features([]) == {}


class TestVolatilityFeatures:
    """Test volatility feature computation."""

    def test_atr_from_ohlcv(self):
        from app.features.feature_aggregator import _compute_volatility_features
        rows = []
        for i in range(20):
            rows.append({"open": 100, "high": 102 + i * 0.1, "low": 98 - i * 0.1, "close": 100 + i * 0.5})
        features = _compute_volatility_features(rows)
        assert "atr_14" in features
        assert features["atr_14"] > 0

    def test_too_few_rows(self):
        from app.features.feature_aggregator import _compute_volatility_features
        assert _compute_volatility_features([{"close": 100}]) == {}
