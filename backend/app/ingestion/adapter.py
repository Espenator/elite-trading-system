"""BaseSourceAdapter - Abstract base class for all data source adapters."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ingestion.event import SourceEvent
from app.ingestion.checkpoint import CheckpointStore, checkpoint_store
from app.ingestion.health import HealthStatus, HealthMetrics

logger = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    """Abstract base class for all data source adapters.

    All source adapters (Alpaca, Unusual Whales, FRED, etc.) should inherit
    from this class to ensure consistent behavior and integration with the
    ingestion foundation.

    Features:
    - Automatic health monitoring
    - Event deduplication via checkpoint store
    - Standardized error handling and retry logic
    - Metrics collection (latency, error rate, etc.)
    - Integration with MessageBus event sink

    Subclasses must implement:
    - source_name: Unique identifier for this source
    - fetch_data(): Fetch raw data from the external API
    - transform_to_events(): Transform raw data into SourceEvent objects
    """

    def __init__(
        self,
        event_sink=None,
        checkpoint_store: Optional[CheckpointStore] = None,
        max_retries: int = 3,
    ):
        """Initialize the base adapter.

        Args:
            event_sink: MessageBus instance for publishing events
            checkpoint_store: CheckpointStore for deduplication (uses global if None)
            max_retries: Maximum number of retries on failure
        """
        from app.ingestion.checkpoint import checkpoint_store as global_store
        self.event_sink = event_sink
        self.checkpoint_store = checkpoint_store if checkpoint_store is not None else global_store
        self.max_retries = max_retries
        self._metrics = HealthMetrics()
        self._latency_samples: List[float] = []

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the unique name of this source (e.g., 'alpaca_stream')."""
        pass

    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the default event type for this source (e.g., 'market_data.bar')."""
        pass

    @abstractmethod
    async def fetch_data(self) -> Any:
        """Fetch raw data from the external source.

        Returns:
            Raw data from the external API (format varies by source)

        Raises:
            Exception: On fetch failure (will be caught by run_tick)
        """
        pass

    @abstractmethod
    def transform_to_events(self, raw_data: Any) -> List[SourceEvent]:
        """Transform raw API data into standardized SourceEvent objects.

        Args:
            raw_data: Raw data from fetch_data()

        Returns:
            List of SourceEvent objects
        """
        pass

    async def run_tick(self) -> Dict[str, Any]:
        """Execute one ingestion cycle (fetch, transform, emit).

        This is the main entry point called by orchestrators like
        market_data_agent. It handles:
        1. Fetching data from the external source
        2. Transforming to SourceEvent objects
        3. Deduplication via checkpoint store
        4. Publishing to event sink
        5. Health monitoring and metrics

        Returns:
            Status report with counts and metrics
        """
        start_time = time.time()
        report = {
            "source": self.source_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }

        try:
            # Fetch raw data
            raw_data = await self.fetch_data()

            # Transform to events
            events = self.transform_to_events(raw_data)

            # Deduplicate and emit
            new_events = []
            duplicates = 0
            for event in events:
                if not self.checkpoint_store.has_seen(event):
                    self.checkpoint_store.mark_seen(event)
                    new_events.append(event)
                else:
                    duplicates += 1

            # Publish to event sink
            published = 0
            if self.event_sink:
                for event in new_events:
                    await self.event_sink.publish(event.event_type, event.to_dict())
                    published += 1

            # Update metrics
            latency_ms = (time.time() - start_time) * 1000
            self._record_success(latency_ms, len(new_events))

            report.update({
                "events_fetched": len(events),
                "events_new": len(new_events),
                "events_duplicate": duplicates,
                "events_published": published,
                "latency_ms": round(latency_ms, 2),
            })

        except Exception as exc:
            self._record_error(exc)
            report.update({
                "status": "error",
                "error": str(exc),
                "consecutive_errors": self._metrics.consecutive_errors,
            })
            logger.error(f"{self.source_name} tick failed: {exc}")

        return report

    def get_health(self) -> HealthMetrics:
        """Get current health metrics for this adapter.

        Returns:
            HealthMetrics object with current status
        """
        return self._metrics

    def validate_config(self) -> bool:
        """Validate adapter configuration (API keys, etc.).

        Subclasses can override to add custom validation.

        Returns:
            True if configuration is valid
        """
        return True

    def _record_success(self, latency_ms: float, event_count: int) -> None:
        """Record a successful fetch."""
        self._metrics.last_success = datetime.now(timezone.utc)
        self._metrics.consecutive_errors = 0
        self._metrics.total_events += event_count
        self._metrics.status = HealthStatus.HEALTHY

        # Update latency average
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 100:
            self._latency_samples.pop(0)
        self._metrics.average_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

    def _record_error(self, exc: Exception) -> None:
        """Record a fetch error."""
        self._metrics.last_error = datetime.now(timezone.utc)
        self._metrics.consecutive_errors += 1

        # Update status based on error type and count
        if "rate limit" in str(exc).lower():
            self._metrics.status = HealthStatus.RATE_LIMITED
        elif "auth" in str(exc).lower() or "401" in str(exc):
            self._metrics.status = HealthStatus.AUTH_FAILURE
        elif self._metrics.consecutive_errors >= 5:
            self._metrics.status = HealthStatus.OFFLINE
        else:
            self._metrics.status = HealthStatus.DEGRADED
