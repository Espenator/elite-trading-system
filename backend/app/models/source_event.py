"""Normalised source event emitted by ingestion adapters.

Every data-source adapter (Unusual Whales, FRED, EDGAR …) normalises its
raw API responses into *SourceEvent* objects before publishing them to the
MessageBus.  This gives downstream consumers a predictable schema
regardless of the originating API.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SourceEvent:
    """A single normalised event from a data-source adapter.

    Attributes:
        source:     Adapter name, e.g. ``"unusual_whales"``.
        event_type: Sub-category, e.g. ``"flow_alert"``, ``"darkpool"``.
        event_id:   Stable unique identifier.  Adapters that lack a native
                    ID should compute a SHA-256 hash of stable content fields.
        timestamp:  Unix epoch (float) when the event *occurred* on the
                    source side.  Falls back to ingestion time when unknown.
        symbol:     Primary equity ticker, if applicable.
        payload:    Full raw API payload for the event (dict).
    """

    source: str
    event_type: str
    event_id: str
    timestamp: float
    symbol: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_bus_payload(self) -> Dict[str, Any]:
        """Return a dict suitable for MessageBus publication."""
        return {
            "source": self.source,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "payload": self.payload,
        }
