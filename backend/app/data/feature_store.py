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
        return duckdb_store.get_connection()

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
    ) -> str:
        """Persist a feature vector to DuckDB.

        Returns the feature hash.
        """
        conn = self._get_conn()
        feature_json = json.dumps(feature_dict, default=str)
        feature_hash = self._compute_hash(feature_dict)
        now = datetime.now(timezone.utc)

        conn.execute("""
            INSERT INTO features (symbol, ts, timeframe, feature_json, feature_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, ts, timeframe) DO UPDATE SET
                feature_json = EXCLUDED.feature_json,
                feature_hash = EXCLUDED.feature_hash,
                created_at = EXCLUDED.created_at
        """, [symbol.upper(), ts, timeframe, feature_json, feature_hash, now])

        logger.debug("Stored features for %s@%s: hash=%s", symbol, ts, feature_hash)
        return feature_hash

    def get_latest_features(
        self, symbol: str, timeframe: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent feature vector for a symbol."""
        conn = self._get_conn()
        result = conn.execute("""
            SELECT feature_json, feature_hash, ts, created_at
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
            "ts": str(result[2]),
            "created_at": str(result[3]),
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
            SELECT feature_json, feature_hash, ts, created_at
            FROM features
            WHERE symbol = ? AND timeframe = ? AND ts BETWEEN ? AND ?
            ORDER BY ts
        """, [symbol.upper(), timeframe, start, end]).fetchall()

        return [
            {
                "features": json.loads(r[0]) if r[0] else {},
                "feature_hash": r[1],
                "ts": str(r[2]),
                "created_at": str(r[3]),
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
            INSERT INTO model_evals
            (eval_id, model_id, "window", sharpe, profit_factor, win_rate, max_dd, passed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (eval_id) DO UPDATE SET
                sharpe = EXCLUDED.sharpe,
                profit_factor = EXCLUDED.profit_factor,
                win_rate = EXCLUDED.win_rate,
                max_dd = EXCLUDED.max_dd,
                passed = EXCLUDED.passed,
                created_at = EXCLUDED.created_at
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
