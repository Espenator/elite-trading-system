"""
Sentiment Intelligence API — aggregated sentiment persisted in SQLite.
GET /api/v1/sentiment returns per-ticker composite scores from DB.
POST /api/v1/sentiment allows agents to submit sentiment data from real sources.
Scores come from Stockgeist, News API, Discord, X when services are connected.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_SENTIMENT_ITEMS = 100


class SentimentSourceData(BaseModel):
    score: float
    volume: Optional[int] = None
    articles: Optional[int] = None
    mentions: Optional[int] = None
    posts: Optional[int] = None
    change: Optional[float] = None


class SentimentSubmit(BaseModel):
    """Schema for submitting sentiment data for a ticker."""
    ticker: str
    overallScore: float
    trend: str  # bullish / bearish / neutral
    sources: Optional[Dict[str, dict]] = None  # stockgeist, news, discord, x
    momentum: Optional[str] = None  # accelerating, decelerating, stable
    profitSignal: Optional[str] = None  # STRONG BUY, BUY, HOLD, SELL, STRONG SELL
    source_name: str = "agent"  # which agent/service submitted


def _get_sentiment_data() -> list:
    stored = db_service.get_config("sentiment_data")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_sentiment_data(data: list) -> None:
    db_service.set_config("sentiment_data", data)


@router.get("")
async def get_sentiment(time_range: str = Query("24h", alias="timeRange")):
    """
    Return sentiment scores per ticker from DB.
    Frontend expects items with ticker, overallScore, trend, sources, etc.
    Returns empty list if no sentiment data has been collected yet.
    """
    items = _get_sentiment_data()
    return {"items": items, "timeRange": time_range, "count": len(items)}


@router.post("")
async def submit_sentiment(data: SentimentSubmit):
    """
    Submit or update sentiment data for a ticker.
    If ticker already exists, updates it. Otherwise appends.
    Called by sentiment agents connected to real data sources.
    """
    items = _get_sentiment_data()
    ticker = data.ticker.upper()

    new_item = {
        "ticker": ticker,
        "overallScore": round(data.overallScore, 1),
        "trend": data.trend.lower(),
        "sources": data.sources or {},
        "momentum": data.momentum or "stable",
        "profitSignal": data.profitSignal or "HOLD",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source_name": data.source_name,
    }

    # Update existing ticker or append
    updated = False
    for i, item in enumerate(items):
        if item.get("ticker") == ticker:
            items[i] = new_item
            updated = True
            break
    if not updated:
        items.append(new_item)

    # Keep list bounded
    if len(items) > MAX_SENTIMENT_ITEMS:
        items = items[-MAX_SENTIMENT_ITEMS:]

    _save_sentiment_data(items)

    await broadcast_ws("sentiment", {"type": "sentiment_updated", "item": new_item})
    logger.info("Sentiment updated: %s score=%s trend=%s", ticker, data.overallScore, data.trend)
    return {"ok": True, "item": new_item}


@router.delete("/{ticker}")
async def remove_sentiment(ticker: str):
    """Remove sentiment data for a ticker."""
    items = _get_sentiment_data()
    ticker_upper = ticker.upper()
    original_len = len(items)
    items = [i for i in items if i.get("ticker") != ticker_upper]
    if len(items) == original_len:
        return {"ok": False, "detail": "Ticker not found"}
    _save_sentiment_data(items)
    await broadcast_ws("sentiment", {"type": "sentiment_removed", "ticker": ticker_upper})
    return {"ok": True}
