"""SourceEvent — normalized ingestion event model.

Every piece of data entering the system is wrapped in a SourceEvent before
being persisted to DuckDB's ``ingestion_events`` table.  The model provides:

- A stable **dedupe_key** (SHA-256 of source+topic+symbol+payload) so the
  event sink can skip exact duplicates.
- A **trace_id** slot for distributed-tracing correlation (optional).
- Typed accessors so adapters don't have to repeat JSON serialization.

Usage::

    from app.models.source_event import SourceEvent

    event = SourceEvent(
        source="fred",
        source_kind="poll",
        topic="ingestion.macro",
        payload={"series_id": "VIXCLS", "date": "2026-01-10", "value": 14.32},
        entity_id="VIXCLS",
    )
    row = event.to_row()   # ready for DuckDB insert
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class SourceEvent:
    """Normalized ingestion event emitted by every source adapter.

    Attributes:
        source:         Adapter name, e.g. ``"alpaca"``, ``"fred"``, ``"finviz"``.
        source_kind:    Transport type: ``"stream"`` | ``"poll"`` | ``"push"``.
        topic:          MessageBus topic, e.g. ``"ingestion.ohlcv"``.
        payload:        Raw event data as a Python dict (not yet serialized).
        symbol:         Ticker symbol for equity events; ``None`` for macro.
        entity_id:      Non-equity identifier, e.g. FRED series ID ``"VIXCLS"``.
        occurred_at:    When the event occurred at the source (defaults to ingested_at).
        sequence:       Monotonic counter within a single fetch batch (for ordering).
        schema_version: ``"1.0"`` unless the payload shape changes.
        trace_id:       Optional distributed-tracing correlation ID.
        event_id:       UUID auto-generated; uniquely identifies this event row.
        ingested_at:    UTC timestamp set at construction time.
        dedupe_key:     32-char SHA-256 prefix computed from source+topic+symbol+payload.
        payload_json:   ``json.dumps(payload)`` — cached once at construction.
    """

    # ── Required fields (no defaults) ────────────────────────────────────
    source: str
    source_kind: str
    topic: str
    payload: Dict[str, Any]

    # ── Optional identity fields ──────────────────────────────────────────
    symbol: Optional[str] = None
    entity_id: Optional[str] = None
    occurred_at: Optional[datetime] = None
    sequence: int = 0
    schema_version: str = "1.0"
    trace_id: Optional[str] = None

    # ── Auto-generated (do NOT pass these; set by __post_init__) ─────────
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ingested_at: datetime = field(default_factory=_utcnow)
    dedupe_key: str = field(default="", init=False, repr=False)
    payload_json: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        if self.occurred_at is None:
            self.occurred_at = self.ingested_at
        # Serialize payload once
        if not self.payload_json:
            self.payload_json = json.dumps(self.payload, default=str, sort_keys=True)
        # Stable dedupe key
        if not self.dedupe_key:
            raw = f"{self.source}:{self.topic}:{self.symbol or ''}:{self.payload_json}"
            self.dedupe_key = hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_row(self) -> Dict[str, Any]:
        """Return a dict matching the ``ingestion_events`` DuckDB table columns."""
        return {
            "event_id": self.event_id,
            "source": self.source,
            "source_kind": self.source_kind,
            "topic": self.topic,
            "symbol": self.symbol,
            "entity_id": self.entity_id,
            "occurred_at": self.occurred_at,
            "ingested_at": self.ingested_at,
            "sequence": self.sequence,
            "dedupe_key": self.dedupe_key,
            "schema_version": self.schema_version,
            "payload_json": self.payload_json,
            "trace_id": self.trace_id,
        }

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "SourceEvent":
        """Reconstruct a SourceEvent from a DuckDB row dict (e.g. for replay)."""
        payload = json.loads(row.get("payload_json") or "{}")
        evt = cls(
            source=row["source"],
            source_kind=row["source_kind"],
            topic=row["topic"],
            payload=payload,
            symbol=row.get("symbol"),
            entity_id=row.get("entity_id"),
            occurred_at=row.get("occurred_at"),
            sequence=row.get("sequence", 0),
            schema_version=row.get("schema_version", "1.0"),
            trace_id=row.get("trace_id"),
            event_id=row.get("event_id") or str(uuid.uuid4()),
        )
        # Override auto-set fields
        if row.get("ingested_at"):
            object.__setattr__(evt, "ingested_at", row["ingested_at"])
        if row.get("dedupe_key"):
            object.__setattr__(evt, "dedupe_key", row["dedupe_key"])
        if row.get("payload_json"):
            object.__setattr__(evt, "payload_json", row["payload_json"])
        return evt

    def __repr__(self) -> str:  # pragma: no cover
        sym = f" sym={self.symbol}" if self.symbol else ""
        eid = f" eid={self.entity_id}" if self.entity_id else ""
        return (
            f"<SourceEvent {self.source}/{self.topic}{sym}{eid}"
            f" seq={self.sequence} id={self.event_id[:8]}>"
        )
