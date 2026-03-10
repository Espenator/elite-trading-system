"""Canonical sensory event schema for the firehose layer."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SensorySource(str, Enum):
    """Known ingestion sources."""
    ALPACA_STREAM = "alpaca_stream"
    DISCORD = "discord"
    UNUSUAL_WHALES = "unusual_whales"
    FINVIZ = "finviz"
    NEWS = "news"
    OTHER = "other"


class SensoryEvent(BaseModel):
    """Canonical event from any sensory agent. Router maps to MessageBus topics."""

    source: SensorySource
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    direction: Optional[str] = None  # buy | sell | hold | bullish | bearish
    priority: int = 5  # 1=highest, 5=normal
    topic_hint: Optional[str] = None  # override routing: market_data.bar | swarm.idea | perception.*
    dedupe_key: Optional[str] = None

    def to_swarm_idea(self, reason: str = "") -> Dict[str, Any]:
        """Build swarm.idea payload for router."""
        return {
            "source": f"firehose:{self.source.value}",
            "symbols": self.symbols or ([self.symbol] if self.symbol else []),
            "direction": self.direction or "unknown",
            "reasoning": reason or str(self.payload.get("reasoning", ""))[:500],
            "priority": self.priority,
            "metadata": {"payload": self.payload, "occurred_at": self.occurred_at.isoformat()},
        }

    def to_market_bar(self) -> Dict[str, Any]:
        """Build market_data.bar payload when event is bar-like."""
        p = self.payload
        return {
            "symbol": self.symbol or "",
            "timestamp": p.get("timestamp", self.occurred_at.isoformat()),
            "open": float(p.get("open", 0)),
            "high": float(p.get("high", 0)),
            "low": float(p.get("low", 0)),
            "close": float(p.get("close", 0)),
            "volume": int(p.get("volume", 0)),
            "source": f"firehose_{self.source.value}",
        }
