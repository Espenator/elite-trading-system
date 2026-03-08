"""
Checkpoint Store for Ingestion Adapters

Tracks incremental ingestion progress for each adapter to support:
- Resume from last successful position
- Idempotent ingestion (avoid duplicate processing)
- Audit trail of ingestion batches
"""

import duckdb
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Persistent storage for adapter checkpoint state"""

    def __init__(self, db_path: str = "data/checkpoints.duckdb"):
        """
        Initialize checkpoint store with DuckDB backend

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        """Create checkpoints table if it doesn't exist"""
        with duckdb.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS adapter_checkpoints (
                    adapter_name VARCHAR PRIMARY KEY,
                    source_key VARCHAR,
                    last_cursor VARCHAR,
                    last_timestamp TIMESTAMP,
                    batch_id VARCHAR,
                    status VARCHAR,
                    row_count INTEGER,
                    error_message VARCHAR,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_adapter_updated
                ON adapter_checkpoints(adapter_name, updated_at)
            """)

    def get_checkpoint(self, adapter_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest checkpoint for an adapter

        Args:
            adapter_name: Name of the adapter (e.g., 'finviz', 'fred')

        Returns:
            Dictionary with checkpoint data or None if no checkpoint exists
        """
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT
                    adapter_name,
                    source_key,
                    last_cursor,
                    last_timestamp,
                    batch_id,
                    status,
                    row_count,
                    error_message,
                    metadata,
                    updated_at
                FROM adapter_checkpoints
                WHERE adapter_name = ?
            """, [adapter_name]).fetchone()

            if result:
                return {
                    "adapter_name": result[0],
                    "source_key": result[1],
                    "last_cursor": result[2],
                    "last_timestamp": result[3],
                    "batch_id": result[4],
                    "status": result[5],
                    "row_count": result[6],
                    "error_message": result[7],
                    "metadata": result[8],
                    "updated_at": result[9]
                }
            return None

    def save_checkpoint(
        self,
        adapter_name: str,
        source_key: Optional[str] = None,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None,
        batch_id: Optional[str] = None,
        status: str = "success",
        row_count: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save or update checkpoint for an adapter

        Args:
            adapter_name: Name of the adapter
            source_key: Unique key identifying the data source (e.g., symbol, dataset ID)
            last_cursor: Cursor/offset for incremental fetching
            last_timestamp: Timestamp of last processed record
            batch_id: Unique ID for this ingestion batch
            status: Status of ingestion (success, failed, partial)
            row_count: Number of rows processed in this batch
            error_message: Error message if status is failed
            metadata: Additional metadata as JSON
        """
        with duckdb.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO adapter_checkpoints (
                    adapter_name,
                    source_key,
                    last_cursor,
                    last_timestamp,
                    batch_id,
                    status,
                    row_count,
                    error_message,
                    metadata,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (adapter_name) DO UPDATE SET
                    source_key = EXCLUDED.source_key,
                    last_cursor = EXCLUDED.last_cursor,
                    last_timestamp = EXCLUDED.last_timestamp,
                    batch_id = EXCLUDED.batch_id,
                    status = EXCLUDED.status,
                    row_count = EXCLUDED.row_count,
                    error_message = EXCLUDED.error_message,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, [
                adapter_name,
                source_key,
                last_cursor,
                last_timestamp,
                batch_id,
                status,
                row_count,
                error_message,
                metadata
            ])
            conn.commit()
            logger.info(f"Checkpoint saved for {adapter_name}: {row_count} rows, status={status}")

    def get_all_checkpoints(self) -> list[Dict[str, Any]]:
        """Get all adapter checkpoints for health monitoring"""
        with duckdb.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT
                    adapter_name,
                    source_key,
                    last_timestamp,
                    batch_id,
                    status,
                    row_count,
                    updated_at
                FROM adapter_checkpoints
                ORDER BY updated_at DESC
            """).fetchall()

            return [
                {
                    "adapter_name": r[0],
                    "source_key": r[1],
                    "last_timestamp": r[2],
                    "batch_id": r[3],
                    "status": r[4],
                    "row_count": r[5],
                    "updated_at": r[6]
                }
                for r in results
            ]

    def clear_checkpoint(self, adapter_name: str):
        """Clear checkpoint for an adapter (useful for resets/testing)"""
        with duckdb.connect(self.db_path) as conn:
            conn.execute("DELETE FROM adapter_checkpoints WHERE adapter_name = ?", [adapter_name])
            conn.commit()
            logger.info(f"Checkpoint cleared for {adapter_name}")
