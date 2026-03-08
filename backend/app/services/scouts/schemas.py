"""Scout agent schemas — standardised discovery payload and health structures.

Every scout produces :class:`DiscoveryPayload` objects that are published to
``swarm.idea`` on the :class:`~app.core.message_bus.MessageBus`.

Design contract
---------------
* Source attribution is mandatory — every payload carries ``scout_id`` and
  ``source_type`` so downstream consumers can weight signals by origin.
* ``priority`` maps to swarm queue priority (1 = highest urgency, 5 = background).
* ``ttl_seconds`` lets consumers discard stale ideas without explicit purging.
* ``attributes`` is an open dict for source-specific metadata (vol ratio, RSI,
  flow premium, macro delta, …) enabling future feature engineering.
* ``feedback_key`` is a stable identifier used by the :mod:`feedback-driven
  learning` subsystem (E7) to correlate outcome data back to the originating
  scout without coupling the scout to the outcome tracker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Source-type enumeration (string constant — avoids Enum serialisation issues)
# ---------------------------------------------------------------------------

SOURCE_ALPACA = "alpaca"
SOURCE_UNUSUAL_WHALES = "unusual_whales"
SOURCE_FINVIZ = "finviz"
SOURCE_FRED = "fred"
SOURCE_SEC_EDGAR = "sec_edgar"
SOURCE_NEWS = "news"
SOURCE_SOCIAL = "social"
SOURCE_MARKET_INTERNAL = "market_internal"

# Direction constants
DIRECTION_BULLISH = "bullish"
DIRECTION_BEARISH = "bearish"
DIRECTION_NEUTRAL = "neutral"

# Signal-type constants (non-exhaustive — scouts may extend with source-specific types)
SIGNAL_VOLUME_SPIKE = "volume_spike"
SIGNAL_UNUSUAL_FLOW = "unusual_flow"
SIGNAL_DARK_POOL = "dark_pool"
SIGNAL_NEWS_CATALYST = "news_catalyst"
SIGNAL_SOCIAL_MOMENTUM = "social_momentum"
SIGNAL_BREAKOUT = "technical_breakout"
SIGNAL_MOMENTUM = "momentum"
SIGNAL_MACRO_SHIFT = "macro_shift"
SIGNAL_FILING_CATALYST = "filing_catalyst"
SIGNAL_SECTOR_ROTATION = "sector_rotation"
SIGNAL_PREMARKET_GAP = "premarket_gap"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DiscoveryPayload:
    """Standardised payload published by every scout to ``swarm.idea``.

    All fields are validated on construction so that the MessageBus never
    receives a structurally invalid idea.
    """

    # --- Identity / attribution -----------------------------------------------
    scout_id: str
    """Unique scout identifier, e.g. ``finviz_momentum``."""

    source: str
    """Human-readable source label, e.g. ``"FinViz Screener"``."""

    source_type: str
    """One of the ``SOURCE_*`` constants — used for downstream weighting."""

    # --- Core signal -----------------------------------------------------------
    symbol: str
    """Primary ticker symbol (uppercase)."""

    direction: str
    """``bullish`` | ``bearish`` | ``neutral``."""

    signal_type: str
    """One of the ``SIGNAL_*`` constants or a custom string."""

    confidence: float
    """Confidence in this discovery, 0.0 – 1.0."""

    score: int
    """Composite urgency / quality score, 0 – 100.  Maps to swarm priority."""

    reasoning: str
    """Human-readable description of *why* this symbol was flagged."""

    # --- Downstream routing ---------------------------------------------------
    priority: int = 3
    """Swarm queue priority, 1 (highest) – 5 (background)."""

    ttl_seconds: int = 300
    """Seconds before this idea is considered stale by consumers."""

    # --- Optional enrichment --------------------------------------------------
    attributes: Dict[str, Any] = field(default_factory=dict)
    """Source-specific metadata (vol_ratio, rsi, flow_premium, etc.)."""

    related_symbols: List[str] = field(default_factory=list)
    """Secondary symbols relevant to this idea (e.g. sector peers, ETFs)."""

    # --- Provenance / lifecycle -----------------------------------------------
    discovered_at: str = field(default_factory=_utcnow)
    """ISO-8601 UTC timestamp when the scout created this payload."""

    feedback_key: str = ""
    """Stable key for outcome feedback (E7).  Auto-set if not provided."""

    def __post_init__(self) -> None:
        self.symbol = self.symbol.upper().strip()
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        self.score = max(0, min(100, int(self.score)))
        self.priority = max(1, min(5, int(self.priority)))
        if not self.feedback_key:
            self.feedback_key = f"{self.scout_id}:{self.symbol}:{self.discovered_at}"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "scout_id": self.scout_id,
            "source": self.source,
            "source_type": self.source_type,
            "symbol": self.symbol,
            "direction": self.direction,
            "signal_type": self.signal_type,
            "confidence": round(self.confidence, 4),
            "score": self.score,
            "reasoning": self.reasoning,
            "priority": self.priority,
            "ttl_seconds": self.ttl_seconds,
            "attributes": self.attributes,
            "related_symbols": self.related_symbols,
            "discovered_at": self.discovered_at,
            "feedback_key": self.feedback_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiscoveryPayload":
        """Reconstruct a payload from a dict (e.g. deserialised from the bus)."""
        return cls(
            scout_id=data["scout_id"],
            source=data["source"],
            source_type=data["source_type"],
            symbol=data["symbol"],
            direction=data["direction"],
            signal_type=data["signal_type"],
            confidence=data["confidence"],
            score=data["score"],
            reasoning=data["reasoning"],
            priority=data.get("priority", 3),
            ttl_seconds=data.get("ttl_seconds", 300),
            attributes=data.get("attributes", {}),
            related_symbols=data.get("related_symbols", []),
            discovered_at=data.get("discovered_at", _utcnow()),
            feedback_key=data.get("feedback_key", ""),
        )


@dataclass
class ScoutHealth:
    """Snapshot of a single scout's operational health.

    Published to ``scout.heartbeat`` every ``heartbeat_interval`` seconds.
    """

    scout_id: str
    status: str
    """``running`` | ``idle`` | ``error`` | ``stopped``."""

    last_scan_at: Optional[str] = None
    last_discovery_at: Optional[str] = None
    consecutive_errors: int = 0
    total_discoveries: int = 0
    total_scans: int = 0
    scan_latency_ms: float = 0.0
    error_message: str = ""
    uptime_seconds: float = 0.0
    ts: str = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scout_id": self.scout_id,
            "status": self.status,
            "last_scan_at": self.last_scan_at,
            "last_discovery_at": self.last_discovery_at,
            "consecutive_errors": self.consecutive_errors,
            "total_discoveries": self.total_discoveries,
            "total_scans": self.total_scans,
            "scan_latency_ms": round(self.scan_latency_ms, 1),
            "error_message": self.error_message,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "ts": self.ts,
        }
