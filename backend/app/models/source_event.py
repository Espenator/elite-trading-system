"""
Source Event Model for Ingestion Tracking

Represents a single ingestion event from an external data source.
Used to track what data was ingested, when, and from which source.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class SourceEvent(BaseModel):
    """Model for tracking individual ingestion events"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = Field(..., description="Source adapter name (finviz, fred, unusual_whales, etc.)")
    source_kind: str = Field(..., description="Type of source (screener, economic, options_flow, filings, stream)")
    topic: Optional[str] = Field(None, description="Message bus topic if published")
    symbol: Optional[str] = Field(None, description="Stock symbol if applicable")
    entity_id: Optional[str] = Field(None, description="Unique identifier from source system")
    occurred_at: datetime = Field(..., description="When the event occurred at the source")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="When we ingested it")
    sequence: Optional[int] = Field(None, description="Sequence number for ordered events")
    dedupe_key: Optional[str] = Field(None, description="Hash key for deduplication")
    schema_version: str = Field(default="1.0", description="Event schema version")
    payload_json: Dict[str, Any] = Field(default_factory=dict, description="Raw event payload")
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "unusual_whales",
                "source_kind": "options_flow",
                "topic": "unusual_whales.flow",
                "symbol": "AAPL",
                "entity_id": "uw_flow_987654",
                "occurred_at": "2026-03-08T10:30:00Z",
                "ingested_at": "2026-03-08T10:30:05Z",
                "sequence": 12345,
                "dedupe_key": "sha256_abc123",
                "schema_version": "1.0",
                "payload_json": {"type": "call_sweep", "premium": 1500000},
                "trace_id": "trace_xyz"
            }
        }
