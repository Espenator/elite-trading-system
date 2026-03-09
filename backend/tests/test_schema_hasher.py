"""Tests for schema_hasher.py — Schema hashing for feature versioning.

Tests verify that schema hashes:
- Are stable across multiple calls with same schema
- Change when schema changes (columns added/removed)
- Are order-independent (sorted keys)
- Work with DataFrames, column lists, and column dicts
"""

import pandas as pd
import pytest

from app.utils.schema_hasher import (
    SchemaHasher,
    compute_schema_hash,
    compute_feature_manifest_hash,
)


class TestSchemaHasher:
    """Test SchemaHasher class methods."""

    def test_hash_dataframe_schema(self):
        """Test hashing DataFrame schema (column names and types)."""
        df = pd.DataFrame({
            "price": [1.0, 2.0, 3.0],
            "volume": [100, 200, 300],
            "return_1d": [0.01, 0.02, 0.03],
        })
        hasher = SchemaHasher()
        schema_hash = hasher.hash_dataframe_schema(df)

        # Should be 16 characters
        assert len(schema_hash) == 16
        assert isinstance(schema_hash, str)

        # Should be deterministic
        schema_hash2 = hasher.hash_dataframe_schema(df)
        assert schema_hash == schema_hash2

    def test_hash_dataframe_schema_changes_on_column_add(self):
        """Test schema hash changes when columns are added."""
        df1 = pd.DataFrame({"price": [1.0], "volume": [100]})
        df2 = pd.DataFrame({"price": [1.0], "volume": [100], "return_1d": [0.01]})

        hasher = SchemaHasher()
        hash1 = hasher.hash_dataframe_schema(df1)
        hash2 = hasher.hash_dataframe_schema(df2)

        # Different columns = different hash
        assert hash1 != hash2

    def test_hash_dataframe_schema_changes_on_column_remove(self):
        """Test schema hash changes when columns are removed."""
        df1 = pd.DataFrame({"price": [1.0], "volume": [100], "return_1d": [0.01]})
        df2 = pd.DataFrame({"price": [1.0], "volume": [100]})

        hasher = SchemaHasher()
        hash1 = hasher.hash_dataframe_schema(df1)
        hash2 = hasher.hash_dataframe_schema(df2)

        # Different columns = different hash
        assert hash1 != hash2

    def test_hash_dataframe_schema_same_for_different_values(self):
        """Test schema hash is same when only values change, not columns."""
        df1 = pd.DataFrame({"price": [1.0], "volume": [100]})
        df2 = pd.DataFrame({"price": [999.0], "volume": [9999]})

        hasher = SchemaHasher()
        hash1 = hasher.hash_dataframe_schema(df1)
        hash2 = hasher.hash_dataframe_schema(df2)

        # Same schema (columns/types) = same hash
        assert hash1 == hash2

    def test_hash_dataframe_schema_changes_on_dtype_change(self):
        """Test schema hash changes when dtype changes."""
        df1 = pd.DataFrame({"price": [1.0]})  # float64
        df2 = pd.DataFrame({"price": [1]})    # int64

        hasher = SchemaHasher()
        hash1 = hasher.hash_dataframe_schema(df1)
        hash2 = hasher.hash_dataframe_schema(df2)

        # Different dtypes = different hash
        assert hash1 != hash2

    def test_hash_column_list(self):
        """Test hashing a list of column names."""
        columns = ["price", "volume", "return_1d", "ma_20"]
        hasher = SchemaHasher()
        hash1 = hasher.hash_column_list(columns)

        assert len(hash1) == 16
        assert isinstance(hash1, str)

        # Deterministic
        hash2 = hasher.hash_column_list(columns)
        assert hash1 == hash2

    def test_hash_column_list_order_independent(self):
        """Test column list hash is order-independent (sorted internally)."""
        cols1 = ["price", "volume", "return_1d"]
        cols2 = ["volume", "return_1d", "price"]  # Different order

        hasher = SchemaHasher()
        hash1 = hasher.hash_column_list(cols1)
        hash2 = hasher.hash_column_list(cols2)

        # Should be same because internally sorted
        assert hash1 == hash2

    def test_hash_column_list_changes_on_add(self):
        """Test column list hash changes when column added."""
        cols1 = ["price", "volume"]
        cols2 = ["price", "volume", "return_1d"]

        hasher = SchemaHasher()
        hash1 = hasher.hash_column_list(cols1)
        hash2 = hasher.hash_column_list(cols2)

        assert hash1 != hash2

    def test_hash_column_dict(self):
        """Test hashing a column name -> type dict."""
        col_types = {
            "price": "float64",
            "volume": "int64",
            "return_1d": "float64",
        }
        hasher = SchemaHasher()
        hash1 = hasher.hash_column_dict(col_types)

        assert len(hash1) == 16
        assert isinstance(hash1, str)

        # Deterministic
        hash2 = hasher.hash_column_dict(col_types)
        assert hash1 == hash2

    def test_hash_column_dict_order_independent(self):
        """Test column dict hash is order-independent."""
        dict1 = {"price": "float64", "volume": "int64"}
        dict2 = {"volume": "int64", "price": "float64"}  # Different order

        hasher = SchemaHasher()
        hash1 = hasher.hash_column_dict(dict1)
        hash2 = hasher.hash_column_dict(dict2)

        # Same keys/values, different order = same hash
        assert hash1 == hash2

    def test_hash_column_dict_changes_on_type_change(self):
        """Test column dict hash changes when type changes."""
        dict1 = {"price": "float64", "volume": "int64"}
        dict2 = {"price": "float32", "volume": "int64"}  # price type changed

        hasher = SchemaHasher()
        hash1 = hasher.hash_column_dict(dict1)
        hash2 = hasher.hash_column_dict(dict2)

        assert hash1 != hash2

    def test_hash_feature_manifest(self):
        """Test hashing feature + label column lists."""
        feature_cols = ["price", "volume", "return_1d", "ma_20"]
        label_cols = ["target_1d", "target_3d", "target_5d"]

        hasher = SchemaHasher()
        hash1 = hasher.hash_feature_manifest(feature_cols, label_cols)

        assert len(hash1) == 16

        # Deterministic
        hash2 = hasher.hash_feature_manifest(feature_cols, label_cols)
        assert hash1 == hash2

    def test_hash_feature_manifest_changes_on_feature_add(self):
        """Test manifest hash changes when feature added."""
        features1 = ["price", "volume"]
        features2 = ["price", "volume", "return_1d"]
        labels = ["target_1d"]

        hasher = SchemaHasher()
        hash1 = hasher.hash_feature_manifest(features1, labels)
        hash2 = hasher.hash_feature_manifest(features2, labels)

        assert hash1 != hash2

    def test_hash_feature_manifest_changes_on_label_add(self):
        """Test manifest hash changes when label added."""
        features = ["price", "volume"]
        labels1 = ["target_1d"]
        labels2 = ["target_1d", "target_5d"]

        hasher = SchemaHasher()
        hash1 = hasher.hash_feature_manifest(features, labels1)
        hash2 = hasher.hash_feature_manifest(features, labels2)

        assert hash1 != hash2

    def test_hash_feature_vector_schema(self):
        """Test hashing FeatureVector schema structure."""
        hasher = SchemaHasher()
        hash1 = hasher.hash_feature_vector_schema(
            price_features=["close", "return_1d"],
            volume_features=["volume", "volume_sma_20"],
            volatility_features=["atr_14", "bb_width"],
            regime_features=["regime_class"],
            flow_features=["pcr", "net_premium"],
            indicator_features=["rsi_14", "macd"],
            intermarket_features=["spy_corr"],
            cycle_features=["day_of_week"],
        )

        assert len(hash1) == 16

        # Deterministic
        hash2 = hasher.hash_feature_vector_schema(
            price_features=["close", "return_1d"],
            volume_features=["volume", "volume_sma_20"],
            volatility_features=["atr_14", "bb_width"],
            regime_features=["regime_class"],
            flow_features=["pcr", "net_premium"],
            indicator_features=["rsi_14", "macd"],
            intermarket_features=["spy_corr"],
            cycle_features=["day_of_week"],
        )
        assert hash1 == hash2

    def test_hash_feature_vector_schema_changes_on_add(self):
        """Test FeatureVector schema hash changes when feature added."""
        hasher = SchemaHasher()
        hash1 = hasher.hash_feature_vector_schema(
            price_features=["close"],
            volume_features=[],
            volatility_features=[],
            regime_features=[],
            flow_features=[],
            indicator_features=[],
            intermarket_features=[],
            cycle_features=[],
        )
        hash2 = hasher.hash_feature_vector_schema(
            price_features=["close", "return_1d"],  # Added feature
            volume_features=[],
            volatility_features=[],
            regime_features=[],
            flow_features=[],
            indicator_features=[],
            intermarket_features=[],
            cycle_features=[],
        )

        assert hash1 != hash2

    def test_custom_hash_length(self):
        """Test custom hash length parameter."""
        hasher = SchemaHasher(hash_length=32)
        cols = ["price", "volume"]
        hash1 = hasher.hash_column_list(cols)

        assert len(hash1) == 32


class TestComputeSchemaHash:
    """Test convenience function compute_schema_hash."""

    def test_compute_schema_hash_from_dataframe_dtypes(self):
        """Test computing schema hash from DataFrame.dtypes."""
        df = pd.DataFrame({"price": [1.0], "volume": [100]})
        hash1 = compute_schema_hash(df.dtypes)

        assert len(hash1) == 16
        assert isinstance(hash1, str)

        # Deterministic
        hash2 = compute_schema_hash(df.dtypes)
        assert hash1 == hash2

    def test_compute_schema_hash_from_column_list(self):
        """Test computing schema hash from column list."""
        columns = ["price", "volume", "return_1d"]
        hash1 = compute_schema_hash(columns)

        assert len(hash1) == 16

        # Order-independent
        hash2 = compute_schema_hash(["volume", "return_1d", "price"])
        assert hash1 == hash2

    def test_compute_schema_hash_from_column_dict(self):
        """Test computing schema hash from column dict."""
        col_dict = {"price": "float64", "volume": "int64"}
        hash1 = compute_schema_hash(col_dict)

        assert len(hash1) == 16

    def test_compute_schema_hash_invalid_type(self):
        """Test compute_schema_hash raises TypeError on invalid input."""
        with pytest.raises(TypeError):
            compute_schema_hash(123)  # Invalid type

        with pytest.raises(TypeError):
            compute_schema_hash("invalid")  # Invalid type


class TestComputeFeatureManifestHash:
    """Test convenience function compute_feature_manifest_hash."""

    def test_compute_feature_manifest_hash(self):
        """Test computing feature manifest hash."""
        features = ["price", "volume", "return_1d"]
        labels = ["target_1d", "target_5d"]
        hash1 = compute_feature_manifest_hash(features, labels)

        assert len(hash1) == 16

        # Deterministic
        hash2 = compute_feature_manifest_hash(features, labels)
        assert hash1 == hash2

    def test_compute_feature_manifest_hash_order_independent(self):
        """Test manifest hash is order-independent."""
        features1 = ["price", "volume"]
        features2 = ["volume", "price"]
        labels = ["target_1d"]

        hash1 = compute_feature_manifest_hash(features1, labels)
        hash2 = compute_feature_manifest_hash(features2, labels)

        # Should be same (internally sorted)
        assert hash1 == hash2


class TestSchemaHashIntegration:
    """Integration tests with real-world scenarios."""

    def test_detect_feature_addition(self):
        """Test detecting when a new feature is added to pipeline."""
        # Original schema
        df1 = pd.DataFrame({
            "symbol": ["AAPL"],
            "date": ["2026-01-01"],
            "price": [150.0],
            "volume": [1000000],
            "return_1d": [0.01],
        })

        # New schema with added feature
        df2 = pd.DataFrame({
            "symbol": ["AAPL"],
            "date": ["2026-01-01"],
            "price": [150.0],
            "volume": [1000000],
            "return_1d": [0.01],
            "ma_20": [148.5],  # NEW FEATURE
        })

        hash1 = compute_schema_hash(df1.dtypes)
        hash2 = compute_schema_hash(df2.dtypes)

        # Hashes should differ
        assert hash1 != hash2, "Schema hash should change when feature added"

    def test_detect_feature_removal(self):
        """Test detecting when a feature is removed from pipeline."""
        df1 = pd.DataFrame({
            "price": [150.0],
            "volume": [1000000],
            "return_1d": [0.01],
            "ma_20": [148.5],
        })

        df2 = pd.DataFrame({
            "price": [150.0],
            "volume": [1000000],
            "return_1d": [0.01],
            # ma_20 removed
        })

        hash1 = compute_schema_hash(df1.dtypes)
        hash2 = compute_schema_hash(df2.dtypes)

        # Hashes should differ
        assert hash1 != hash2, "Schema hash should change when feature removed"

    def test_no_change_on_data_change(self):
        """Test schema hash stays same when only data values change."""
        df1 = pd.DataFrame({
            "price": [100.0],
            "volume": [1000000],
        })

        df2 = pd.DataFrame({
            "price": [200.0],  # Different value
            "volume": [2000000],  # Different value
        })

        hash1 = compute_schema_hash(df1.dtypes)
        hash2 = compute_schema_hash(df2.dtypes)

        # Hashes should be same (schema unchanged)
        assert hash1 == hash2, "Schema hash should not change when only values change"
