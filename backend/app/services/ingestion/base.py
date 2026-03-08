"""
Base Source Adapter

Abstract base class for all ingestion adapters. Provides a common interface
for incremental data ingestion with checkpoint tracking and error handling.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import uuid

from app.models.source_event import SourceEvent
from app.data.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    """
    Abstract base class for all data source adapters

    Each adapter is responsible for:
    - Fetching data from an external source
    - Converting it to SourceEvent objects
    - Tracking ingestion progress via checkpoints
    - Publishing events to the message bus
    """

    def __init__(
        self,
        checkpoint_store: CheckpointStore,
        message_bus: Optional[Any] = None
    ):
        """
        Initialize adapter

        Args:
            checkpoint_store: Checkpoint store for tracking progress
            message_bus: Message bus for publishing events (optional)
        """
        self.checkpoint_store = checkpoint_store
        self.message_bus = message_bus
        self._running = False

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Return the unique name of this adapter

        Returns:
            Adapter name (e.g., 'finviz', 'fred', 'unusual_whales')
        """
        pass

    @abstractmethod
    def get_source_kind(self) -> str:
        """
        Return the type/category of this source

        Returns:
            Source kind (e.g., 'screener', 'economic', 'options_flow', 'filings', 'stream')
        """
        pass

    @abstractmethod
    async def fetch_incremental(
        self,
        last_cursor: Optional[str] = None,
        last_timestamp: Optional[datetime] = None
    ) -> List[SourceEvent]:
        """
        Fetch new data since last checkpoint

        Args:
            last_cursor: Last cursor position from checkpoint
            last_timestamp: Last timestamp from checkpoint

        Returns:
            List of SourceEvent objects representing new data

        Raises:
            Exception: If fetch fails
        """
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that credentials/API keys are configured correctly

        Returns:
            True if credentials are valid, False otherwise
        """
        pass

    async def ingest(self) -> Dict[str, Any]:
        """
        Main ingestion method - fetch data, save checkpoint, publish events

        Returns:
            Dictionary with ingestion stats (row_count, status, batch_id, etc.)
        """
        batch_id = str(uuid.uuid4())
        source_name = self.get_source_name()

        try:
            # Get last checkpoint
            checkpoint = self.checkpoint_store.get_checkpoint(source_name)
            last_cursor = checkpoint.get("last_cursor") if checkpoint else None
            last_timestamp = checkpoint.get("last_timestamp") if checkpoint else None

            logger.info(
                f"[{source_name}] Starting ingestion batch {batch_id} "
                f"(last_cursor={last_cursor}, last_timestamp={last_timestamp})"
            )

            # Fetch new data
            events = await self.fetch_incremental(last_cursor, last_timestamp)

            # Publish to message bus if available
            if self.message_bus and events:
                for event in events:
                    if event.topic:
                        await self.message_bus.publish(event.topic, event.dict())

            # Determine new checkpoint values
            new_cursor = None
            new_timestamp = None
            if events:
                # Use the last event's data for checkpoint
                last_event = events[-1]
                new_cursor = last_event.dedupe_key or last_event.entity_id
                new_timestamp = last_event.occurred_at

            # Save checkpoint
            self.checkpoint_store.save_checkpoint(
                adapter_name=source_name,
                source_key=self.get_source_kind(),
                last_cursor=new_cursor,
                last_timestamp=new_timestamp,
                batch_id=batch_id,
                status="success",
                row_count=len(events),
                metadata={
                    "events_fetched": len(events),
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            logger.info(f"[{source_name}] Batch {batch_id} complete: {len(events)} events")

            return {
                "adapter_name": source_name,
                "batch_id": batch_id,
                "status": "success",
                "row_count": len(events),
                "last_cursor": new_cursor,
                "last_timestamp": new_timestamp
            }

        except Exception as e:
            logger.error(f"[{source_name}] Ingestion failed: {e}", exc_info=True)

            # Save failed checkpoint
            self.checkpoint_store.save_checkpoint(
                adapter_name=source_name,
                source_key=self.get_source_kind(),
                batch_id=batch_id,
                status="failed",
                row_count=0,
                error_message=str(e)
            )

            return {
                "adapter_name": source_name,
                "batch_id": batch_id,
                "status": "failed",
                "row_count": 0,
                "error": str(e)
            }

    async def start(self):
        """Start the adapter (for streaming adapters)"""
        self._running = True
        logger.info(f"[{self.get_source_name()}] Adapter started")

    async def stop(self):
        """Stop the adapter (for streaming adapters)"""
        self._running = False
        logger.info(f"[{self.get_source_name()}] Adapter stopped")

    def is_running(self) -> bool:
        """Check if adapter is currently running"""
        return self._running

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for this adapter

        Returns:
            Dictionary with health status
        """
        source_name = self.get_source_name()
        checkpoint = self.checkpoint_store.get_checkpoint(source_name)

        return {
            "adapter_name": source_name,
            "source_kind": self.get_source_kind(),
            "is_running": self._running,
            "last_checkpoint": checkpoint,
            "credentials_valid": await self.validate_credentials()
        }
