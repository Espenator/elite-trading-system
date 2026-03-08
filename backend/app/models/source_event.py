"""Source event model for unified ingestion layer."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceEvent(BaseModel):
    """Unified event model for all data sources.

    Represents a single event/data point from any external source
    (Finviz, FRED, SEC Edgar, Unusual Whales, OpenClaw, etc.).
    """

    # Identification
    event_id: str = Field(..., description="Unique identifier for this event (source-specific)")
    source: str = Field(..., description="Source adapter name (e.g., 'finviz', 'fred', 'unusual_whales')")
    event_type: str = Field(..., description="Type of event (e.g., 'screener', 'flow_alert', 'filing')")

    # Timing
    event_time: datetime = Field(..., description="When the event occurred (source timestamp)")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="When we ingested it")

    # Symbol/ticker association (if applicable)
    symbol: Optional[str] = Field(None, description="Stock ticker if event is symbol-specific")

    # Data payload
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "flow_12345",
                "source": "unusual_whales",
                "event_type": "options_flow",
                "event_time": "2026-03-08T14:30:00Z",
                "symbol": "AAPL",
                "data": {
                    "strike": 175.0,
                    "expiry": "2026-03-15",
                    "type": "call",
                    "premium": 250000,
                    "sentiment": "bullish"
                }
            }
        }
