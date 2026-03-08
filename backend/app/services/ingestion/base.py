"""Base adapter interface for data source ingestion."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.source_event import SourceEvent
from app.data.checkpoint_store import CheckpointStore
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)


class AdapterHealth(ABC):
    """Health status for an adapter."""

    def __init__(
        self,
        adapter_id: str,
        is_healthy: bool,
        last_run: Optional[datetime] = None,
        last_success: Optional[datetime] = None,
        last_error: Optional[str] = None,
        events_ingested: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.adapter_id = adapter_id
        self.is_healthy = is_healthy
        self.last_run = last_run
        self.last_success = last_success
        self.last_error = last_error
        self.events_ingested = events_ingested
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "adapter_id": self.adapter_id,
            "is_healthy": self.is_healthy,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "events_ingested": self.events_ingested,
            "metadata": self.metadata
        }


class BaseSourceAdapter(ABC):
    """Base class for all data source adapters.

    Adapters are responsible for:
    1. Fetching data from external sources
    2. Converting to SourceEvent format
    3. Publishing to MessageBus
    4. Maintaining checkpoints for incremental ingestion
    """

    def __init__(
        self,
        adapter_id: str,
        checkpoint_store: Optional[CheckpointStore] = None,
        message_bus: Optional[Any] = None
    ):
        """Initialize adapter.

        Args:
            adapter_id: Unique identifier for this adapter
            checkpoint_store: Store for persisting adapter state
            message_bus: MessageBus for publishing events
        """
        self.adapter_id = adapter_id
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.message_bus = message_bus or get_message_bus()
        self.logger = logging.getLogger(f"{__name__}.{adapter_id}")

        # Health tracking
        self._last_run: Optional[datetime] = None
        self._last_success: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._events_ingested_total: int = 0

    @abstractmethod
    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch events from the data source.

        Args:
            since: Fetch events after this timestamp (for incremental ingestion)

        Returns:
            List of SourceEvent objects
        """
        pass

    @abstractmethod
    def get_topic(self) -> str:
        """Get the MessageBus topic to publish events to.

        Returns:
            Topic string (e.g., 'perception.finviz.screener')
        """
        pass

    async def run(self) -> int:
        """Execute one ingestion cycle.

        Returns:
            Number of events ingested
        """
        self._last_run = datetime.utcnow()
        events_count = 0

        try:
            # Get checkpoint
            checkpoint = self.checkpoint_store.get_checkpoint(self.adapter_id)
            since = checkpoint.get("last_event_time") if checkpoint else None

            # Fetch events
            self.logger.info(f"Fetching events since {since}")
            events = await self.fetch_events(since=since)
            events_count = len(events)

            if events_count == 0:
                self.logger.debug(f"No new events from {self.adapter_id}")
                self._last_success = datetime.utcnow()
                return 0

            # Publish to MessageBus
            topic = self.get_topic()
            for event in events:
                try:
                    await self.message_bus.publish(topic, event.model_dump())
                except Exception as e:
                    self.logger.error(f"Failed to publish event {event.event_id}: {e}")

            # Update checkpoint with the latest event
            if events:
                latest_event = max(events, key=lambda e: e.event_time)
                self.checkpoint_store.save_checkpoint(
                    adapter_id=self.adapter_id,
                    last_event_id=latest_event.event_id,
                    last_event_time=latest_event.event_time,
                    checkpoint_data=self.get_checkpoint_data()
                )

            self._last_success = datetime.utcnow()
            self._events_ingested_total += events_count
            self._last_error = None

            self.logger.info(f"Ingested {events_count} events from {self.adapter_id}")

        except Exception as e:
            self._last_error = str(e)
            self.logger.exception(f"Error in {self.adapter_id}: {e}")
            raise

        return events_count

    def get_checkpoint_data(self) -> Dict[str, Any]:
        """Get additional checkpoint data to persist.

        Override this to store adapter-specific state.

        Returns:
            Dictionary of checkpoint data (must be JSON-serializable)
        """
        return {}

    def get_health(self) -> AdapterHealth:
        """Get current health status.

        Returns:
            AdapterHealth object
        """
        is_healthy = (
            self._last_success is not None and
            self._last_error is None
        )

        return AdapterHealth(
            adapter_id=self.adapter_id,
            is_healthy=is_healthy,
            last_run=self._last_run,
            last_success=self._last_success,
            last_error=self._last_error,
            events_ingested=self._events_ingested_total
        )

    def reset_checkpoint(self):
        """Reset checkpoint to force full re-ingestion."""
        self.checkpoint_store.delete_checkpoint(self.adapter_id)
        self.logger.info(f"Reset checkpoint for {self.adapter_id}")
