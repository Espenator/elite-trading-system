"""DuckDB Feature Store — persist and retrieve feature vectors and model evaluations.

Provides stable feature hashing for reproducibility and model evaluation tracking
for champion/challenger gating. Now with comprehensive versioning support for
feature pipeline evolution and model-feature compatibility tracking.

Usage:
    from app.data.feature_store import feature_store
    feature_store.store_features("AAPL", timestamp, "1d", feature_dict, pipeline_version="2.0.0")
    latest = feature_store.get_latest_features("AAPL", "1d", pipeline_version="2.0.0")
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeatureStore:
    """DuckDB-backed feature store for ML pipeline."""

    def _get_conn(self):
        """Get a DuckDB cursor safe for use in any thread context.

        Returns a cursor (not raw connection) to avoid segfaults when
        called from concurrent.futures or asyncio.to_thread workers.
        """
        from app.data.duckdb_storage import duckdb_store
        return duckdb_store.get_thread_cursor()

    @staticmethod
    def _compute_hash(feature_dict: Dict[str, Any]) -> str:
        """Compute stable SHA256 hash of feature dict.

        Sorts keys to ensure same inputs always produce same hash.
        """
        canonical = json.dumps(feature_dict, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def store_features(
        self,
        symbol: str,
        ts: datetime,
        timeframe: str,
        feature_dict: Dict[str, Any],
        pipeline_version: str = "1.0.0",
        schema_version: str = "1.0",
    ) -> str:
        """Persist a feature vector to DuckDB with versioning metadata.

        Args:
            symbol: Stock symbol
            ts: Timestamp for the feature vector
            timeframe: Timeframe (e.g., '1d', '1h')
            feature_dict: Dictionary of feature name -> value
            pipeline_version: Version of the feature pipeline that generated these features
            schema_version: Version of the feature schema

        Returns:
            The feature hash for reproducibility tracking.
        """
        conn = self._get_conn()
        feature_json = json.dumps(feature_dict, default=str)
        feature_hash = self._compute_hash(feature_dict)
        feature_count = len(feature_dict)
        now = datetime.now(timezone.utc)

        conn.execute("""
            INSERT OR REPLACE INTO features
            (symbol, ts, timeframe, feature_json, feature_hash, pipeline_version, schema_version, feature_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [symbol.upper(), ts, timeframe, feature_json, feature_hash, pipeline_version, schema_version, feature_count, now])

        logger.debug(
            "Stored features for %s@%s: hash=%s, pipeline_v=%s, schema_v=%s, count=%d",
            symbol, ts, feature_hash, pipeline_version, schema_version, feature_count
        )
        return feature_hash

    def get_latest_features(
        self,
        symbol: str,
        timeframe: str = "1d",
        pipeline_version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent feature vector for a symbol.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., '1d', '1h')
            pipeline_version: Optional pipeline version filter. If None, gets latest regardless of version.

        Returns:
            Dictionary with features, metadata, and versioning information, or None if not found.
        """
        conn = self._get_conn()

        if pipeline_version:
            query = """
                SELECT feature_json, feature_hash, pipeline_version, schema_version, feature_count, ts, created_at
                FROM features
                WHERE symbol = ? AND timeframe = ? AND pipeline_version = ?
                ORDER BY ts DESC
                LIMIT 1
            """
            result = conn.execute(query, [symbol.upper(), timeframe, pipeline_version]).fetchone()
        else:
            query = """
                SELECT feature_json, feature_hash, pipeline_version, schema_version, feature_count, ts, created_at
                FROM features
                WHERE symbol = ? AND timeframe = ?
                ORDER BY ts DESC
                LIMIT 1
            """
            result = conn.execute(query, [symbol.upper(), timeframe]).fetchone()

        if not result:
            return None

        return {
            "features": json.loads(result[0]) if result[0] else {},
            "feature_hash": result[1],
            "pipeline_version": result[2],
            "schema_version": result[3],
            "feature_count": result[4],
            "ts": str(result[5]),
            "created_at": str(result[6]),
        }

    def get_features_window(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        pipeline_version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve feature vectors for a symbol within a time window.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., '1d', '1h')
            start: Start timestamp (ISO format)
            end: End timestamp (ISO format)
            pipeline_version: Optional pipeline version filter

        Returns:
            List of feature dictionaries with metadata and versioning information.
        """
        conn = self._get_conn()

        if pipeline_version:
            query = """
                SELECT feature_json, feature_hash, pipeline_version, schema_version, feature_count, ts, created_at
                FROM features
                WHERE symbol = ? AND timeframe = ? AND ts BETWEEN ? AND ? AND pipeline_version = ?
                ORDER BY ts
            """
            rows = conn.execute(query, [symbol.upper(), timeframe, start, end, pipeline_version]).fetchall()
        else:
            query = """
                SELECT feature_json, feature_hash, pipeline_version, schema_version, feature_count, ts, created_at
                FROM features
                WHERE symbol = ? AND timeframe = ? AND ts BETWEEN ? AND ?
                ORDER BY ts
            """
            rows = conn.execute(query, [symbol.upper(), timeframe, start, end]).fetchall()

        return [
            {
                "features": json.loads(r[0]) if r[0] else {},
                "feature_hash": r[1],
                "pipeline_version": r[2],
                "schema_version": r[3],
                "feature_count": r[4],
                "ts": str(r[5]),
                "created_at": str(r[6]),
            }
            for r in rows
        ]

    def get_available_versions(
        self,
        symbol: Optional[str] = None,
        timeframe: str = "1d",
    ) -> List[Dict[str, Any]]:
        """Get all available pipeline versions in the feature store.

        Args:
            symbol: Optional symbol to filter by
            timeframe: Timeframe to filter by

        Returns:
            List of dictionaries with version information and statistics.
        """
        conn = self._get_conn()

        if symbol:
            query = """
                SELECT
                    pipeline_version,
                    schema_version,
                    COUNT(*) as record_count,
                    MIN(ts) as earliest_ts,
                    MAX(ts) as latest_ts,
                    AVG(feature_count) as avg_feature_count
                FROM features
                WHERE symbol = ? AND timeframe = ?
                GROUP BY pipeline_version, schema_version
                ORDER BY pipeline_version DESC
            """
            rows = conn.execute(query, [symbol.upper(), timeframe]).fetchall()
        else:
            query = """
                SELECT
                    pipeline_version,
                    schema_version,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT symbol) as symbol_count,
                    MIN(ts) as earliest_ts,
                    MAX(ts) as latest_ts,
                    AVG(feature_count) as avg_feature_count
                FROM features
                WHERE timeframe = ?
                GROUP BY pipeline_version, schema_version
                ORDER BY pipeline_version DESC
            """
            rows = conn.execute(query, [timeframe]).fetchall()

        if symbol:
            return [
                {
                    "pipeline_version": r[0],
                    "schema_version": r[1],
                    "record_count": r[2],
                    "earliest_ts": str(r[3]),
                    "latest_ts": str(r[4]),
                    "avg_feature_count": float(r[5]) if r[5] else 0,
                }
                for r in rows
            ]
        else:
            return [
                {
                    "pipeline_version": r[0],
                    "schema_version": r[1],
                    "record_count": r[2],
                    "symbol_count": r[3],
                    "earliest_ts": str(r[4]),
                    "latest_ts": str(r[5]),
                    "avg_feature_count": float(r[6]) if r[6] else 0,
                }
                for r in rows
            ]

    def check_version_compatibility(
        self,
        required_version: str,
        symbol: str,
        timeframe: str = "1d",
    ) -> Dict[str, Any]:
        """Check if features exist for a specific pipeline version.

        Args:
            required_version: Required pipeline version
            symbol: Stock symbol
            timeframe: Timeframe

        Returns:
            Dictionary with compatibility information.
        """
        conn = self._get_conn()

        result = conn.execute("""
            SELECT
                COUNT(*) as count,
                MIN(ts) as earliest,
                MAX(ts) as latest
            FROM features
            WHERE symbol = ? AND timeframe = ? AND pipeline_version = ?
        """, [symbol.upper(), timeframe, required_version]).fetchone()

        compatible = result[0] > 0 if result else False

        return {
            "compatible": compatible,
            "version": required_version,
            "symbol": symbol,
            "timeframe": timeframe,
            "record_count": result[0] if result else 0,
            "earliest_ts": str(result[1]) if result and result[1] else None,
            "latest_ts": str(result[2]) if result and result[2] else None,
        }

    def store_model_eval(
        self,
        eval_id: str,
        model_id: str,
        window: str,
        metrics: Dict[str, Any],
    ) -> None:
        """Store a model evaluation result."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc)
        conn.execute("""
            INSERT OR REPLACE INTO model_evals
            (eval_id, model_id, "window", sharpe, profit_factor, win_rate, max_dd, passed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            eval_id, model_id, window,
            metrics.get("sharpe", 0.0),
            metrics.get("profit_factor", 0.0),
            metrics.get("win_rate", 0.0),
            metrics.get("max_dd", 0.0),
            metrics.get("passed", False),
            now,
        ])
        logger.info("Stored model eval: %s window=%s passed=%s", model_id, window, metrics.get("passed"))

    def get_model_evals(self, model_id: str) -> List[Dict[str, Any]]:
        """Retrieve all evaluations for a model."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT eval_id, model_id, "window", sharpe, profit_factor,
                   win_rate, max_dd, passed, created_at
            FROM model_evals
            WHERE model_id = ?
            ORDER BY created_at
        """, [model_id]).fetchall()

        return [
            {
                "eval_id": r[0], "model_id": r[1], "window": r[2],
                "sharpe": r[3], "profit_factor": r[4], "win_rate": r[5],
                "max_dd": r[6], "passed": r[7], "created_at": str(r[8]),
            }
            for r in rows
        ]


# Singleton
feature_store = FeatureStore()
