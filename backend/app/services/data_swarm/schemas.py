"""Normalized data schemas for the data swarm — Price, Flow, Screener, Futures.

All collectors publish payloads that conform to these dataclasses so downstream
(feature_aggregator, council, Blackboard) get a consistent shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PriceUpdate:
    """Single price/quote update from any source."""

    symbol: str
    price: float
    bid: Optional[float]
    ask: Optional[float]
    volume: int
    timestamp: datetime
    source: str  # "alpaca" | "unusual_whales" | "finviz"
    session: str  # "overnight" | "pre_market" | "regular" | "after_hours"
    is_realtime: bool  # True for WebSocket, False for REST poll

    def to_message_bus_payload(self) -> dict:
        """Serialize for MessageBus publish."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "session": self.session,
            "is_realtime": self.is_realtime,
        }


@dataclass
class FlowUpdate:
    """Options/dark pool/lit flow event."""

    symbol: str
    flow_type: str  # "options" | "darkpool" | "lit"
    direction: str  # "bullish" | "bearish" | "neutral"
    premium: float
    volume: int
    open_interest: Optional[int]
    strike: Optional[float]
    expiry: Optional[str]
    timestamp: datetime
    source: str

    def to_message_bus_payload(self) -> dict:
        return {
            "symbol": self.symbol,
            "flow_type": self.flow_type,
            "direction": self.direction,
            "premium": self.premium,
            "volume": self.volume,
            "open_interest": self.open_interest,
            "strike": self.strike,
            "expiry": self.expiry,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
        }


@dataclass
class ScreenerUpdate:
    """Screener signal (unusual volume, breakout, gap, etc.)."""

    symbol: str
    signal_type: str  # "unusual_volume" | "new_high" | "breakout" | "gap_up"
    price: float
    change_pct: float
    relative_volume: float
    timestamp: datetime
    source: str

    def to_message_bus_payload(self) -> dict:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "price": self.price,
            "change_pct": self.change_pct,
            "relative_volume": self.relative_volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
        }


@dataclass
class FuturesUpdate:
    """Futures contract price (ES, NQ, CL, etc.)."""

    symbol: str  # "ES" | "NQ" | "CL" | "GC" etc.
    price: float
    change_pct: float
    volume: int
    timestamp: datetime
    source: str
    is_delayed: bool  # True for FinViz (e.g. 20min delay)

    def to_message_bus_payload(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "is_delayed": self.is_delayed,
        }
