"""Canonical event model for the ingestion layer.

Every raw external data point — whether from a live WebSocket, a REST poll,
or a scheduled scrape — is normalised into a ``SourceEvent`` before being
published to the MessageBus.  This gives downstream consumers a single
contract regardless of where the data originated.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class SourceKind(str, Enum):
    """Classification of how a source delivers data."""

    STREAM = "stream"           # True real-time (WebSocket, SSE)
    INCREMENTAL = "incremental" # Cursor/timestamp-based poll
    SNAPSHOT = "snapshot"       # Full-state capture each cycle
    LOW_FREQ = "low_freq"       # Infrequent scheduled fetch (daily / hourly)


@dataclass(frozen=False)
class SourceEvent:
    """Normalised event emitted by every source adapter.

    Fields
    ------
    event_id     : Globally unique event identifier (UUID4).
    source       : Adapter name (e.g. ``"finviz"``, ``"fred"``).
    source_kind  : How the data was acquired (stream / incremental / snapshot / low_freq).
    topic        : MessageBus topic the event will be published to.
    symbol       : Ticker symbol, if applicable. Empty string for non-symbol data.
    entity_id    : Opaque identifier scoped to the source (e.g. series_id, filing accession).
    occurred_at  : Epoch seconds when the upstream event actually occurred.
    ingested_at  : Epoch seconds when we ingested it.
    sequence     : Monotonically increasing per-source counter (0 = unknown).
    dedupe_key   : Key for idempotent persistence (defaults to ``event_id``).
    schema_version : Version tag so consumers can handle migrations.
    payload      : Normalised data dict for downstream consumption.
    raw_payload  : Original upstream data (optional; useful for replay / debug).
    trace_id     : Correlation / trace identifier for distributed tracing.
    """

    source: str
    topic: str
    payload: Dict[str, Any]
    source_kind: SourceKind = SourceKind.SNAPSHOT
    symbol: str = ""
    entity_id: str = ""
    occurred_at: float = 0.0
    ingested_at: float = field(default_factory=time.time)
    sequence: int = 0
    dedupe_key: str = ""
    schema_version: int = 1
    raw_payload: Optional[Dict[str, Any]] = None
    trace_id: str = ""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self):
        if not self.dedupe_key:
            self.dedupe_key = self.event_id
        if self.occurred_at == 0.0:
            self.occurred_at = self.ingested_at
        if not self.trace_id:
            self.trace_id = self.event_id

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "source_kind": self.source_kind.value,
            "topic": self.topic,
            "symbol": self.symbol,
            "entity_id": self.entity_id,
            "occurred_at": self.occurred_at,
            "ingested_at": self.ingested_at,
            "sequence": self.sequence,
            "dedupe_key": self.dedupe_key,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "trace_id": self.trace_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SourceEvent":
        kind = d.get("source_kind", "snapshot")
        return cls(
            event_id=d.get("event_id", uuid.uuid4().hex),
            source=d["source"],
            source_kind=SourceKind(kind) if isinstance(kind, str) else kind,
            topic=d["topic"],
            symbol=d.get("symbol", ""),
            entity_id=d.get("entity_id", ""),
            occurred_at=d.get("occurred_at", 0.0),
            ingested_at=d.get("ingested_at", time.time()),
            sequence=d.get("sequence", 0),
            dedupe_key=d.get("dedupe_key", ""),
            schema_version=d.get("schema_version", 1),
            payload=d.get("payload", {}),
            raw_payload=d.get("raw_payload"),
            trace_id=d.get("trace_id", ""),
        )
