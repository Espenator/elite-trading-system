"""Checkpoint store for adapter state persistence."""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.data.duckdb_manager import DuckDBManager

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Manages adapter checkpoints for incremental ingestion.

    Stores the last successful ingestion state for each adapter,
    allowing them to resume from where they left off.
    """

    def __init__(self, db_manager: Optional[DuckDBManager] = None):
        self.db = db_manager or DuckDBManager()
        self._ensure_table()

    def _ensure_table(self):
        """Create checkpoints table if it doesn't exist."""
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
                    adapter_id VARCHAR PRIMARY KEY,
                    last_event_id VARCHAR,
                    last_event_time TIMESTAMP,
                    checkpoint_data JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception as e:
            logger.error(f"Failed to create checkpoints table: {e}")

    def get_checkpoint(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """Get the last checkpoint for an adapter.

        Args:
            adapter_id: Unique identifier for the adapter

        Returns:
            Dictionary with checkpoint data or None if no checkpoint exists
        """
        try:
            result = self.db.query(
                "SELECT * FROM ingestion_checkpoints WHERE adapter_id = ?",
                [adapter_id]
            )
            if result and len(result) > 0:
                row = result[0]
                return {
                    "adapter_id": row[0],
                    "last_event_id": row[1],
                    "last_event_time": row[2],
                    "checkpoint_data": row[3],
                    "updated_at": row[4]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get checkpoint for {adapter_id}: {e}")
            return None

    def save_checkpoint(
        self,
        adapter_id: str,
        last_event_id: Optional[str] = None,
        last_event_time: Optional[datetime] = None,
        checkpoint_data: Optional[Dict[str, Any]] = None
    ):
        """Save or update checkpoint for an adapter.

        Args:
            adapter_id: Unique identifier for the adapter
            last_event_id: ID of the last processed event
            last_event_time: Timestamp of the last processed event
            checkpoint_data: Additional state data (JSON-serializable dict)
        """
        try:
            import json
            checkpoint_json = json.dumps(checkpoint_data) if checkpoint_data else None

            self.db.execute("""
                INSERT INTO ingestion_checkpoints
                (adapter_id, last_event_id, last_event_time, checkpoint_data, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (adapter_id) DO UPDATE SET
                    last_event_id = EXCLUDED.last_event_id,
                    last_event_time = EXCLUDED.last_event_time,
                    checkpoint_data = EXCLUDED.checkpoint_data,
                    updated_at = CURRENT_TIMESTAMP
            """, [adapter_id, last_event_id, last_event_time, checkpoint_json])

            logger.debug(f"Saved checkpoint for {adapter_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {adapter_id}: {e}")

    def delete_checkpoint(self, adapter_id: str):
        """Delete checkpoint for an adapter.

        Args:
            adapter_id: Unique identifier for the adapter
        """
        try:
            self.db.execute(
                "DELETE FROM ingestion_checkpoints WHERE adapter_id = ?",
                [adapter_id]
            )
            logger.info(f"Deleted checkpoint for {adapter_id}")
        except Exception as e:
            logger.error(f"Failed to delete checkpoint for {adapter_id}: {e}")
