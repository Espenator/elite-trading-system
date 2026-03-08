"""SourceEvent — normalized event model for the firehose ingestion layer.

All source adapters (Finviz, FRED, SEC EDGAR, OpenClaw, UnusualWhales, …)
emit SourceEvent instances that flow through the MessageBus topic
'source_event' and are persisted idempotently by EventSinkWriter.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.0"


class SourceEvent(BaseModel):
    """Normalized, append-only event produced by a source adapter."""

    # ── Identity ────────────────────────────────────────────────────────────
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Globally unique event ID (UUID4).",
    )
    dedupe_key: str = Field(
        description="Stable key used for idempotent writes (source:scope:hash)."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Payload schema version for forward-compatibility.",
    )

    # ── Source metadata ──────────────────────────────────────────────────────
    source: str = Field(description="Adapter name, e.g. 'finviz', 'fred', 'edgar'.")
    source_version: str = Field(
        default="1",
        description="Version string for this adapter's output format.",
    )
    feed: str = Field(
        default="",
        description="Sub-feed within a source, e.g. 'screener', 'options_flow'.",
    )

    # ── Time ────────────────────────────────────────────────────────────────
    event_ts: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Wall-clock time the event was produced by the adapter.",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Wall-clock time the event entered the pipeline.",
    )

    # ── Entity identifiers ───────────────────────────────────────────────────
    symbols: List[str] = Field(
        default_factory=list,
        description="Ticker symbols referenced by this event (may be empty for macro).",
    )
    entity_id: str = Field(
        default="",
        description="Non-symbol entity key, e.g. CIK for EDGAR, series_id for FRED.",
    )

    # ── Payload ──────────────────────────────────────────────────────────────
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Normalized, typed fields (adapter-specific).",
    )
    raw_payload: Optional[str] = Field(
        default=None,
        description="Original JSON/text from the source, stored for auditability.",
    )

    # ── Ops ──────────────────────────────────────────────────────────────────
    is_deleted: bool = Field(
        default=False,
        description="True when an entity was removed in a snapshot diff.",
    )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def to_bus_dict(self) -> Dict[str, Any]:
        """Serialise to a MessageBus-compatible dict (ISO timestamps)."""
        d = self.model_dump()
        d["event_ts"] = self.event_ts.isoformat()
        d["ingested_at"] = self.ingested_at.isoformat()
        return d

    # ── Constructors ─────────────────────────────────────────────────────────

    @classmethod
    def make_dedupe_key(
        cls,
        source: str,
        scope: str,
        content: Any,
    ) -> str:
        """Build a stable dedupe key from source + scope + content hash."""
        content_str = json.dumps(content, sort_keys=True, default=str)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        return f"{source}:{scope}:{content_hash}"

    @classmethod
    def from_screener_row(
        cls,
        source: str,
        symbol: str,
        row: Dict[str, Any],
        feed: str = "screener",
    ) -> "SourceEvent":
        """Convenience constructor for a single screener/watchlist row."""
        dedupe_key = cls.make_dedupe_key(source, symbol, row)
        return cls(
            dedupe_key=dedupe_key,
            source=source,
            feed=feed,
            symbols=[symbol],
            payload=dict(row),
        )

    @classmethod
    def from_macro_series(
        cls,
        source: str,
        series_id: str,
        value: Any,
        as_of: Optional[datetime] = None,
    ) -> "SourceEvent":
        """Convenience constructor for a macro data point."""
        ts = as_of or datetime.now(timezone.utc)
        content = {"series_id": series_id, "value": value, "as_of": ts.isoformat()}
        dedupe_key = cls.make_dedupe_key(source, series_id, content)
        return cls(
            dedupe_key=dedupe_key,
            source=source,
            feed="macro",
            entity_id=series_id,
            event_ts=ts,
            payload=content,
        )
