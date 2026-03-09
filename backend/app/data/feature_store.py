"""DuckDB Feature Store — persist and retrieve feature vectors and model evaluations.

Provides stable feature hashing for reproducibility and model evaluation tracking
for champion/challenger gating.

Usage:
    from app.data.feature_store import feature_store
    feature_store.store_features("AAPL", timestamp, "1d", feature_dict)
    latest = feature_store.get_latest_features("AAPL", "1d")
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
        """Get DuckDB connection from the shared storage instance."""
        from app.data.duckdb_storage import duckdb_store
        return duckdb_store._get_conn()

    @staticmethod
    def _compute_hash(feature_dict: Dict[str, Any]) -> str:
        """Compute stable SHA256 hash of feature dict (data hash).

        Sorts keys to ensure same inputs always produce same hash.
        """
        canonical = json.dumps(feature_dict, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    @staticmethod
    def _compute_schema_hash(feature_dict: Dict[str, Any]) -> str:
        """Compute stable SHA256 hash of feature schema (structure, not values).

        Only keys are hashed, not values. Detects when features are added/removed.
        """
        from app.utils.schema_hasher import SchemaHasher
        hasher = SchemaHasher()
        return hasher.hash_column_list(sorted(feature_dict.keys()))

    def store_features(
        self,
        symbol: str,
        ts: datetime,
        timeframe: str,
        feature_dict: Dict[str, Any],
    ) -> str:
        """Persist a feature vector to DuckDB.

        Returns the feature hash.
        """
        conn = self._get_conn()
        feature_json = json.dumps(feature_dict, default=str)
        feature_hash = self._compute_hash(feature_dict)
        schema_hash = self._compute_schema_hash(feature_dict)
        now = datetime.now(timezone.utc)

        conn.execute("""
            INSERT OR REPLACE INTO features (symbol, ts, timeframe, feature_json, feature_hash, schema_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [symbol.upper(), ts, timeframe, feature_json, feature_hash, schema_hash, now])

        logger.debug("Stored features for %s@%s: hash=%s schema_hash=%s", symbol, ts, feature_hash, schema_hash)
        return feature_hash

    def get_latest_features(
        self, symbol: str, timeframe: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent feature vector for a symbol."""
        conn = self._get_conn()
        result = conn.execute("""
            SELECT feature_json, feature_hash, schema_hash, ts, created_at
            FROM features
            WHERE symbol = ? AND timeframe = ?
            ORDER BY ts DESC
            LIMIT 1
        """, [symbol.upper(), timeframe]).fetchone()

        if not result:
            return None

        return {
            "features": json.loads(result[0]) if result[0] else {},
            "feature_hash": result[1],
            "schema_hash": result[2],
            "ts": str(result[3]),
            "created_at": str(result[4]),
        }

    def get_features_window(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve feature vectors for a symbol within a time window."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT feature_json, feature_hash, schema_hash, ts, created_at
            FROM features
            WHERE symbol = ? AND timeframe = ? AND ts BETWEEN ? AND ?
            ORDER BY ts
        """, [symbol.upper(), timeframe, start, end]).fetchall()

        return [
            {
                "features": json.loads(r[0]) if r[0] else {},
                "feature_hash": r[1],
                "schema_hash": r[2],
                "ts": str(r[3]),
                "created_at": str(r[4]),
            }
            for r in rows
        ]

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
