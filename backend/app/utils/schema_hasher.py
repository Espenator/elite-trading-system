"""Schema Hasher — Compute stable hashes of feature schemas for versioning.

This module provides utilities for computing schema hashes that track the
structure (column names and types) of features, distinct from data hashes
which track feature values.

Schema hashing enables:
- Detection when feature column names/types change
- Version-aware model retraining
- Prevention of training on incompatible feature schemas
- Integration with pipeline_version system

Usage:
    from app.utils.schema_hasher import SchemaHasher, compute_schema_hash

    # Compute hash from column names and types
    schema_hash = compute_schema_hash(df.dtypes)

    # Or use the class for more control
    hasher = SchemaHasher()
    schema_hash = hasher.hash_dataframe_schema(df)
    schema_hash = hasher.hash_column_list(["feature1", "feature2"])
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class SchemaHasher:
    """Computes stable hashes of feature schemas for versioning."""

    def __init__(self, hash_length: int = 16):
        """Initialize schema hasher.

        Args:
            hash_length: Number of characters to use from SHA256 hash (default: 16)
        """
        self.hash_length = hash_length

    def hash_dataframe_schema(self, df: pd.DataFrame) -> str:
        """Compute hash of DataFrame schema (column names and types).

        Args:
            df: DataFrame to hash schema of

        Returns:
            16-character (or hash_length) hex string representing schema

        Example:
            >>> df = pd.DataFrame({"price": [1.0], "volume": [100]})
            >>> hasher = SchemaHasher()
            >>> hasher.hash_dataframe_schema(df)
            'a3f5b8c9d2e1f4a7'
        """
        if df.empty:
            return self._hash_string("")

        # Build schema representation: {column_name: dtype_name}
        schema_dict = {col: str(df[col].dtype) for col in sorted(df.columns)}
        return self._hash_dict(schema_dict)

    def hash_column_list(self, columns: List[str]) -> str:
        """Compute hash of column name list (order-independent).

        Args:
            columns: List of column names

        Returns:
            16-character (or hash_length) hex string

        Example:
            >>> hasher = SchemaHasher()
            >>> hasher.hash_column_list(["price", "volume", "return_1d"])
            'b4e6a9c7f2d8e1a3'
        """
        # Sort for order-independence
        sorted_cols = sorted(columns)
        return self._hash_string(json.dumps(sorted_cols))

    def hash_column_dict(self, column_types: Dict[str, str]) -> str:
        """Compute hash of column name -> type mapping.

        Args:
            column_types: Dictionary mapping column names to type strings

        Returns:
            16-character (or hash_length) hex string

        Example:
            >>> hasher = SchemaHasher()
            >>> hasher.hash_column_dict({"price": "float64", "volume": "int64"})
            'c7f3a8b2e1d4f6a9'
        """
        return self._hash_dict(column_types)

    def hash_feature_manifest(self, feature_cols: List[str], label_cols: List[str]) -> str:
        """Compute hash of feature + label column structure.

        Args:
            feature_cols: List of feature column names
            label_cols: List of label column names

        Returns:
            16-character (or hash_length) hex string

        Example:
            >>> hasher = SchemaHasher()
            >>> hasher.hash_feature_manifest(
            ...     ["price", "volume"],
            ...     ["target_1d", "target_5d"]
            ... )
            'd8f4b7a9c2e6f3a1'
        """
        manifest_dict = {
            "features": sorted(feature_cols),
            "labels": sorted(label_cols),
        }
        return self._hash_dict(manifest_dict)

    def hash_feature_vector_schema(
        self,
        price_features: List[str],
        volume_features: List[str],
        volatility_features: List[str],
        regime_features: List[str],
        flow_features: List[str],
        indicator_features: List[str],
        intermarket_features: List[str],
        cycle_features: List[str],
    ) -> str:
        """Compute hash of FeatureVector schema structure.

        Args:
            price_features: List of price feature names
            volume_features: List of volume feature names
            volatility_features: List of volatility feature names
            regime_features: List of regime feature names
            flow_features: List of flow feature names
            indicator_features: List of indicator feature names
            intermarket_features: List of intermarket feature names
            cycle_features: List of cycle feature names

        Returns:
            16-character (or hash_length) hex string
        """
        schema_dict = {
            "price": sorted(price_features),
            "volume": sorted(volume_features),
            "volatility": sorted(volatility_features),
            "regime": sorted(regime_features),
            "flow": sorted(flow_features),
            "indicator": sorted(indicator_features),
            "intermarket": sorted(intermarket_features),
            "cycle": sorted(cycle_features),
        }
        return self._hash_dict(schema_dict)

    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """Hash a dictionary with sorted keys for stability."""
        canonical = json.dumps(data, sort_keys=True, default=str)
        return self._hash_string(canonical)

    def _hash_string(self, text: str) -> str:
        """Hash a string and return truncated hex digest."""
        return hashlib.sha256(text.encode()).hexdigest()[:self.hash_length]


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def compute_schema_hash(
    dtypes_or_columns: Union[pd.Series, List[str], Dict[str, str]],
    hash_length: int = 16,
) -> str:
    """Compute schema hash from DataFrame dtypes, column list, or column dict.

    Args:
        dtypes_or_columns: Either:
            - pd.Series: DataFrame.dtypes
            - List[str]: Column names
            - Dict[str, str]: Column name -> type mapping
        hash_length: Number of characters from hash (default: 16)

    Returns:
        Schema hash string

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"price": [1.0], "volume": [100]})
        >>> compute_schema_hash(df.dtypes)
        'a3f5b8c9d2e1f4a7'
        >>> compute_schema_hash(["price", "volume"])
        'b4e6a9c7f2d8e1a3'
        >>> compute_schema_hash({"price": "float64", "volume": "int64"})
        'c7f3a8b2e1d4f6a9'
    """
    hasher = SchemaHasher(hash_length=hash_length)

    if isinstance(dtypes_or_columns, pd.Series):
        # DataFrame dtypes Series
        schema_dict = {col: str(dtype) for col, dtype in dtypes_or_columns.items()}
        schema_dict = {k: schema_dict[k] for k in sorted(schema_dict.keys())}
        return hasher._hash_dict(schema_dict)
    elif isinstance(dtypes_or_columns, list):
        # List of column names
        return hasher.hash_column_list(dtypes_or_columns)
    elif isinstance(dtypes_or_columns, dict):
        # Column name -> type mapping
        return hasher.hash_column_dict(dtypes_or_columns)
    else:
        raise TypeError(
            f"Expected pd.Series, List[str], or Dict[str, str], got {type(dtypes_or_columns)}"
        )


def compute_feature_manifest_hash(feature_cols: List[str], label_cols: List[str]) -> str:
    """Convenience function to compute feature manifest schema hash.

    Args:
        feature_cols: Feature column names
        label_cols: Label column names

    Returns:
        Schema hash string
    """
    hasher = SchemaHasher()
    return hasher.hash_feature_manifest(feature_cols, label_cols)
