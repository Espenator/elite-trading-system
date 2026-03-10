"""Tests for Feature Store and Feature Aggregator with versioning support."""
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


class TestFeatureStoreVersioning:
    """Test feature store versioning capabilities."""

    def test_store_features_with_version(self):
        """Test storing features with explicit pipeline version."""
        from app.data.feature_store import feature_store
        from datetime import datetime, timezone

        symbol = "TEST"
        ts = datetime.now(timezone.utc)
        features = {"close": 100.0, "volume": 1000000, "rsi_14": 0.5}

        # Store with version 2.0.0
        hash_val = feature_store.store_features(
            symbol, ts, "1d", features,
            pipeline_version="2.0.0",
            schema_version="1.0"
        )

        assert hash_val is not None
        assert len(hash_val) == 16

        # Retrieve and verify version
        result = feature_store.get_latest_features(symbol, "1d", pipeline_version="2.0.0")
        assert result is not None
        assert result["pipeline_version"] == "2.0.0"
        assert result["schema_version"] == "1.0"
        assert result["feature_count"] == 3

    def test_get_latest_with_version_filter(self):
        """Test retrieving latest features with version filtering."""
        from app.data.feature_store import feature_store
        from datetime import datetime, timezone, timedelta

        symbol = "VTEST"
        base_ts = datetime.now(timezone.utc)
        features_v1 = {"close": 100.0}
        features_v2 = {"close": 100.0, "volume": 1000000}

        # Store v1.0.0 features
        feature_store.store_features(
            symbol, base_ts, "1d", features_v1,
            pipeline_version="1.0.0"
        )

        # Store v2.0.0 features (1 hour later)
        feature_store.store_features(
            symbol, base_ts + timedelta(hours=1), "1d", features_v2,
            pipeline_version="2.0.0"
        )

        # Get latest v1.0.0
        result_v1 = feature_store.get_latest_features(symbol, "1d", pipeline_version="1.0.0")
        assert result_v1 is not None
        assert result_v1["pipeline_version"] == "1.0.0"
        assert result_v1["feature_count"] == 1

        # Get latest v2.0.0
        result_v2 = feature_store.get_latest_features(symbol, "1d", pipeline_version="2.0.0")
        assert result_v2 is not None
        assert result_v2["pipeline_version"] == "2.0.0"
        assert result_v2["feature_count"] == 2

        # Get latest regardless of version (should be v2.0.0)
        result_latest = feature_store.get_latest_features(symbol, "1d")
        assert result_latest is not None
        assert result_latest["pipeline_version"] == "2.0.0"

    def test_get_available_versions(self):
        """Test getting available pipeline versions."""
        from app.data.feature_store import feature_store
        from datetime import datetime, timezone, timedelta

        symbol = "AVTEST"
        ts = datetime.now(timezone.utc)
        features = {"close": 100.0}

        # Store features with different versions (different timestamps to avoid INSERT OR REPLACE collision)
        feature_store.store_features(symbol, ts, "1d", features, pipeline_version="1.0.0")
        feature_store.store_features(symbol, ts + timedelta(seconds=1), "1d", features, pipeline_version="2.0.0")

        # Get versions for specific symbol
        versions = feature_store.get_available_versions(symbol, "1d")
        assert len(versions) >= 2
        version_nums = [v["pipeline_version"] for v in versions]
        assert "1.0.0" in version_nums
        assert "2.0.0" in version_nums

        # Check version has required fields
        for v in versions:
            assert "pipeline_version" in v
            assert "schema_version" in v
            assert "record_count" in v
            assert "avg_feature_count" in v

    def test_check_version_compatibility(self):
        """Test version compatibility checking."""
        from app.data.feature_store import feature_store
        from datetime import datetime, timezone

        symbol = "CTEST"
        ts = datetime.now(timezone.utc)
        features = {"close": 100.0}

        # Store features with version 2.0.0
        feature_store.store_features(symbol, ts, "1d", features, pipeline_version="2.0.0")

        # Check compatibility with existing version
        compat = feature_store.check_version_compatibility("2.0.0", symbol, "1d")
        assert compat["compatible"] is True
        assert compat["version"] == "2.0.0"
        assert compat["record_count"] > 0

        # Check compatibility with non-existing version
        compat_missing = feature_store.check_version_compatibility("3.0.0", symbol, "1d")
        assert compat_missing["compatible"] is False
        assert compat_missing["record_count"] == 0


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
