"""SourceEvent - Standardized event structure for all ingestion sources."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


@dataclass
class SourceEvent:
    """Standardized event emitted by all source adapters.

    All external data entering the system flows through SourceEvent objects.
    This ensures uniform structure, metadata, and traceability.

    Attributes:
        event_type: Type of event (e.g., 'market_data.bar', 'perception.edgar')
        source: Name of the source adapter (e.g., 'alpaca', 'unusual_whales')
        data: Event payload (symbol, price, volume, etc.)
        timestamp: When the event occurred
        event_id: Unique identifier for deduplication
        metadata: Additional context (latency, confidence, etc.)

    Example:
        event = SourceEvent(
            event_type='market_data.bar',
            source='alpaca_stream',
            data={'symbol': 'AAPL', 'close': 175.50, 'volume': 1000000},
            timestamp=datetime.now(timezone.utc),
        )
    """

    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event structure."""
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.source:
            raise ValueError("source is required")
        if not isinstance(self.data, dict):
            raise ValueError("data must be a dictionary")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceEvent":
        """Reconstruct from dictionary."""
        return cls(
            event_type=data["event_type"],
            source=data["source"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_id=data.get("event_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {}),
        )

    def with_metadata(self, **kwargs) -> "SourceEvent":
        """Return a copy with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return SourceEvent(
            event_type=self.event_type,
            source=self.source,
            data=self.data,
            timestamp=self.timestamp,
            event_id=self.event_id,
            metadata=new_metadata,
        )
