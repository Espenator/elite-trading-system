from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


SensorySource = Literal[
    "alpaca",
    "unusual_whales",
    "finviz",
    "discord",
    "x",
    "news",
    "fred",
    "sec",
    "youtube",
    "tradingview",
    "internal",
]

SensoryEventType = Literal[
    "trade_print",
    "bar",
    "news",
    "options_flow",
    "dark_pool",
    "screener_hit",
    "macro_release",
    "filing",
    "social_post",
    "transcript",
    "alert",
    "anomaly",
    "idea",
]

DataQuality = Literal["live", "paper", "mock", "unknown"]


class SensoryRouting(BaseModel):
    topics: List[str] = Field(default_factory=list)
    next_agents: List[str] = Field(default_factory=list)
    to_awareness: bool = False


class SensoryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: SensorySource
    event_type: SensoryEventType
    symbols: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
    normalized: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    priority: int = Field(default=50, ge=0, le=100)
    tags: List[str] = Field(default_factory=list)
    embedding_ref: Optional[str] = None
    routing: SensoryRouting = Field(default_factory=SensoryRouting)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    data_quality: DataQuality = "unknown"

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def from_alpaca_bar(
        cls,
        bar: Dict[str, Any],
        *,
        data_quality: DataQuality = "live",
        tags: Optional[List[str]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> "SensoryEvent":
        symbol = (bar.get("symbol") or "").strip().upper()
        ts_raw = bar.get("timestamp") or bar.get("ts") or ""
        ts = cls._coerce_ts(ts_raw) or cls.utc_now()

        normalized = {
            "symbol": symbol,
            "open": float(bar.get("open") or 0),
            "high": float(bar.get("high") or 0),
            "low": float(bar.get("low") or 0),
            "close": float(bar.get("close") or 0),
            "volume": int(bar.get("volume") or 0),
            "vwap": bar.get("vwap"),
            "trade_count": bar.get("trade_count"),
            "source": bar.get("source"),
        }

        return cls(
            ts=ts,
            source="alpaca",
            event_type="bar",
            symbols=[symbol] if symbol else [],
            raw=dict(bar),
            normalized=normalized,
            tags=list(tags or ["market", "bar"]),
            provenance=dict(provenance or {}),
            data_quality=data_quality,
        )

    @classmethod
    def from_discord_signal(
        cls,
        *,
        symbols: List[str],
        direction: str,
        text: str,
        channel: str,
        source_type: str,
        message_id: str = "",
        author: str = "",
        data_quality: DataQuality = "live",
    ) -> "SensoryEvent":
        cleaned = [s.strip().upper() for s in symbols if s and s.strip()]
        normalized = {
            "direction": direction,
            "text": text,
            "channel": channel,
            "source_type": source_type,
            "author": author,
        }
        prov = {"message_id": message_id, "channel": channel, "source_type": source_type}
        tags = ["social", "discord"]
        if direction and direction != "unknown":
            tags.append(direction)
        return cls(
            ts=cls.utc_now(),
            source="discord",
            event_type="social_post",
            symbols=cleaned,
            raw={"text": text},
            normalized=normalized,
            confidence=0.55,
            priority=65,
            tags=tags,
            provenance=prov,
            data_quality=data_quality,
        )

    @classmethod
    def from_uw_source_event(
        cls,
        payload: Dict[str, Any],
        *,
        data_quality: DataQuality = "live",
    ) -> "SensoryEvent":
        """Build SensoryEvent from a SourceEvent-style payload (topic, symbol, payload_json, etc.)."""
        topic = (payload.get("topic") or "").strip()
        symbol = (payload.get("symbol") or "").strip().upper()
        source_kind = payload.get("source_kind") or "options_flow"
        payload_json = dict(payload.get("payload_json") or {})
        occurred_at = cls._coerce_ts(payload.get("occurred_at")) or cls.utc_now()

        if "unusual_whales.flow" in topic:
            event_type = "options_flow"
            tags = ["options_flow", "unusual_whales"]
        elif "unusual_whales.congress" in topic:
            event_type = "filing"
            tags = ["congress", "unusual_whales"]
        elif "unusual_whales.insider" in topic:
            event_type = "filing"
            tags = ["insider", "unusual_whales"]
        elif "unusual_whales.darkpool" in topic:
            event_type = "dark_pool"
            tags = ["dark_pool", "unusual_whales"]
        else:
            event_type = "options_flow"
            tags = ["unusual_whales"]

        normalized = {
            "symbol": symbol,
            "entity_id": payload.get("entity_id"),
            "dedupe_key": payload.get("dedupe_key"),
            "payload_type": payload_json.get("type"),
            "source_kind": source_kind,
        }
        # Flatten inner data for reasoning if present
        inner = payload_json.get("data")
        if isinstance(inner, dict):
            normalized["premium"] = inner.get("premium")
            normalized["ticker"] = inner.get("ticker") or symbol
            normalized["time"] = inner.get("time")

        return cls(
            event_id=payload.get("event_id") or str(uuid4()),
            ts=occurred_at,
            source="unusual_whales",
            event_type=event_type,
            symbols=[symbol] if symbol else [],
            raw=payload_json,
            normalized=normalized,
            tags=tags,
            provenance={"topic": topic, "source": payload.get("source"), "entity_id": payload.get("entity_id")},
            data_quality=data_quality,
            priority=60,
            confidence=0.6,
        )

    @classmethod
    def from_finviz_source_event(
        cls,
        payload: Dict[str, Any],
        *,
        data_quality: DataQuality = "live",
    ) -> "SensoryEvent":
        """Build SensoryEvent from a Finviz SourceEvent-style payload (topic finviz.screener, payload_json = stock row)."""
        topic = (payload.get("topic") or "").strip()
        symbol = (payload.get("symbol") or "").strip().upper()
        if not symbol and isinstance(payload.get("payload_json"), dict):
            symbol = (payload["payload_json"].get("Ticker") or payload["payload_json"].get("ticker") or "").strip().upper()
        payload_json = dict(payload.get("payload_json") or {})
        occurred_at = cls._coerce_ts(payload.get("occurred_at")) or cls.utc_now()

        normalized = {
            "symbol": symbol,
            "entity_id": payload.get("entity_id"),
            "dedupe_key": payload.get("dedupe_key"),
            "source_kind": payload.get("source_kind") or "screener",
            "market_cap": payload_json.get("Market Cap") or payload_json.get("market_cap"),
            "price": payload_json.get("Price") or payload_json.get("price"),
            "change_pct": payload_json.get("Change") or payload_json.get("change_pct"),
        }

        return cls(
            event_id=payload.get("event_id") or str(uuid4()),
            ts=occurred_at,
            source="finviz",
            event_type="screener_hit",
            symbols=[symbol] if symbol else [],
            raw=payload_json,
            normalized=normalized,
            tags=["screener", "finviz"],
            provenance={"topic": topic, "source": payload.get("source")},
            data_quality=data_quality,
            priority=45,
            confidence=0.55,
        )

    @classmethod
    def from_news_item(
        cls,
        headline: str,
        source: str,
        symbols: List[str],
        *,
        url: str = "",
        sentiment: str = "neutral",
        urgency: str = "background",
        sentiment_score: float = 0.0,
        published_at: str = "",
        hash_id: str = "",
        data_quality: DataQuality = "live",
    ) -> "SensoryEvent":
        """Build SensoryEvent from a news aggregator item (headline, source, symbols, sentiment)."""
        direction = "unknown"
        if sentiment == "bullish":
            direction = "bullish"
        elif sentiment == "bearish":
            direction = "bearish"
        cleaned = [s.strip().upper() for s in symbols if s and str(s).strip()]
        normalized = {
            "text": headline,
            "headline": headline[:500],
            "url": url,
            "news_source": source,
            "sentiment": sentiment,
            "urgency": urgency,
            "sentiment_score": sentiment_score,
            "published_at": published_at,
        }
        tags = ["news", "headline"]
        if sentiment != "neutral":
            tags.append(sentiment)
        if urgency != "background":
            tags.append(urgency)
        priority = 70 if urgency == "breaking" else (55 if urgency == "developing" else 40)
        return cls(
            ts=cls.utc_now(),
            source="news",
            event_type="news",
            symbols=cleaned,
            raw={"headline": headline, "url": url, "source": source},
            normalized=normalized,
            tags=tags,
            provenance={"hash_id": hash_id, "news_source": source},
            data_quality=data_quality,
            priority=priority,
            confidence=0.5 + abs(sentiment_score) * 0.3,
        )

    @staticmethod
    def _coerce_ts(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)) and value > 0:
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except Exception:
                return None
        if isinstance(value, str) and value:
            try:
                v = value.replace("Z", "+00:00")
                dt = datetime.fromisoformat(v)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                return None
        return None
