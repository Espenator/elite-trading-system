"""
Sentiment Intelligence API — production-grade endpoints.
GET  /api/v1/sentiment           -> per-ticker composite scores from DB
GET  /api/v1/sentiment/summary   -> aggregated market mood, source health, divergences
GET  /api/v1/sentiment/history   -> rolling 24h trend data for charts
POST /api/v1/sentiment           -> agents submit real sentiment data
POST /api/v1/sentiment/source-health -> agents report source status
DELETE /api/v1/sentiment/{ticker} -> remove ticker sentiment
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.security import require_auth
from app.services.database import db_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_SENTIMENT_ITEMS = 100
MAX_HISTORY_POINTS = 500


# ---- Pydantic Models ----

class SentimentSourceData(BaseModel):
    score: float
    volume: Optional[int] = None
    articles: Optional[int] = None
    mentions: Optional[int] = None
    posts: Optional[int] = None
    change: Optional[float] = None
    latency_ms: Optional[int] = None
    status: Optional[str] = "unknown"


class SentimentSubmit(BaseModel):
    """Schema for submitting sentiment data for a ticker."""
    ticker: str
    overallScore: float
    trend: str  # bullish / bearish / neutral
    sources: Optional[Dict[str, dict]] = None
    momentum: Optional[str] = None
    profitSignal: Optional[str] = None
    socialVolume: Optional[int] = None
    source_name: str = "agent"


class SourceHealthSubmit(BaseModel):
    """Schema for agents to report source health."""
    source: str
    status: str
    latency_ms: int
    score: float
    weight: Optional[int] = None


# ---- DB Helpers ----

def _get_sentiment_data() -> list:
    stored = db_service.get_config("sentiment_data")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_sentiment_data(data: list) -> None:
    db_service.set_config("sentiment_data", data)


def _get_source_health() -> list:
    stored = db_service.get_config("sentiment_source_health")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_source_health(data: list) -> None:
    db_service.set_config("sentiment_source_health", data)


def _get_sentiment_history() -> list:
    stored = db_service.get_config("sentiment_history")
    if not stored or not isinstance(stored, list):
        return []
    return stored


def _save_sentiment_history(data: list) -> None:
    db_service.set_config("sentiment_history", data)


# ---- Computation Helpers ----

def _compute_market_mood(items: list) -> dict:
    """Compute aggregate market mood from all ticker scores."""
    if not items:
        return {"value": 50, "label": "No Data", "trend": "neutral"}
    scores = [i.get("overallScore", 0) for i in items]
    avg = sum(scores) / len(scores)
    value = int(max(0, min(100, (avg + 1) * 50)))
    if value >= 75:
        label = "Extreme Greed"
    elif value >= 60:
        label = "Greed"
    elif value >= 40:
        label = "Neutral"
    elif value >= 25:
        label = "Fear"
    else:
        label = "Extreme Fear"
    trend = "bullish" if avg > 0.1 else ("bearish" if avg < -0.1 else "neutral")
    return {"value": value, "label": label, "trend": trend, "avgScore": round(avg, 3)}


def _detect_divergences(items: list) -> list:
    """Detect tickers where sources disagree significantly."""
    divergences = []
    for item in items:
        sources = item.get("sources", {})
        if len(sources) < 2:
            continue
        scores = {k: v.get("score", 0) if isinstance(v, dict) else 0 for k, v in sources.items()}
        vals = list(scores.values())
        if not vals:
            continue
        max_s = max(vals)
        min_s = min(vals)
        spread = max_s - min_s
        if spread >= 0.8:
            bull_src = [k for k, v in scores.items() if v == max_s][0]
            bear_src = [k for k, v in scores.items() if v == min_s][0]
            divergences.append({
                "ticker": item.get("ticker"),
                "conflict": f"{bear_src} ({min_s:+.1f}) vs {bull_src} ({max_s:+.1f})",
                "spread": round(spread, 2),
                "impact": "High Volatility Expected" if spread >= 1.2 else "Monitor Closely",
                "updatedAt": item.get("updatedAt", ""),
            })
    divergences.sort(key=lambda d: d["spread"], reverse=True)
    return divergences[:10]


# ---- Routes ----

@router.get("")
async def get_sentiment(time_range: str = Query("24h", alias="timeRange")):
    """Return sentiment items from DB and a global score for Dashboard header."""
    items = _get_sentiment_data()
    mood = _compute_market_mood(items)
    return {
        "items": items,
        "timeRange": time_range,
        "count": len(items),
        "sentiment": {"score": mood["value"]},
    }


@router.get("/summary")
async def get_sentiment_summary():
    """
    Aggregated summary: market mood, source health, divergences, stats.
    Main endpoint the Sentiment Intelligence page calls.
    """
    items = _get_sentiment_data()
    source_health = _get_source_health()
    mood = _compute_market_mood(items)
    divergences = _detect_divergences(items)

    sorted_items = sorted(items, key=lambda x: abs(x.get("overallScore", 0)), reverse=True)
    heatmap = [
        {
            "ticker": i["ticker"],
            "score": i.get("overallScore", 0),
            "volume": i.get("socialVolume", 0),
            "trend": i.get("trend", "neutral"),
        }
        for i in sorted_items[:20]
    ]

    signals = [
        {
            "ticker": i["ticker"],
            "composite": i.get("overallScore", 0),
            "sources": i.get("sources", {}),
            "volume": "Extreme" if abs(i.get("overallScore", 0)) >= 0.8
                      else ("High" if abs(i.get("overallScore", 0)) >= 0.5 else "Normal"),
            "profitSignal": i.get("profitSignal", "HOLD"),
            "momentum": i.get("momentum", "stable"),
            "trend": i.get("trend", "neutral"),
        }
        for i in sorted_items[:15]
    ]

    bullish_count = sum(1 for i in items if i.get("overallScore", 0) > 0.2)
    bearish_count = sum(1 for i in items if i.get("overallScore", 0) < -0.2)
    neutral_count = len(items) - bullish_count - bearish_count

    return {
        "mood": mood,
        "sourceHealth": source_health,
        "divergences": divergences,
        "heatmap": heatmap,
        "signals": signals,
        "stats": {
            "totalTickers": len(items),
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count,
        },
    }


@router.get("/history")
async def get_sentiment_history(hours: int = Query(24, ge=1, le=168)):
    """Return rolling sentiment history for the timeline chart."""
    history = _get_sentiment_history()
    if hours < 168:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        history = [h for h in history if h.get("timestamp", "") >= cutoff]
    return {"points": history, "hours": hours, "count": len(history)}


@router.post("", dependencies=[Depends(require_auth)])
async def submit_sentiment(data: SentimentSubmit):
    """Submit or update sentiment for a ticker."""
    items = _get_sentiment_data()
    ticker = data.ticker.upper()
    new_item = {
        "ticker": ticker,
        "overallScore": round(data.overallScore, 3),
        "trend": data.trend.lower(),
        "sources": data.sources or {},
        "momentum": data.momentum or "stable",
        "profitSignal": data.profitSignal or "HOLD",
        "socialVolume": data.socialVolume or 0,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source_name": data.source_name,
    }

    updated = False
    for i, item in enumerate(items):
        if item.get("ticker") == ticker:
            items[i] = new_item
            updated = True
            break
    if not updated:
        items.append(new_item)
    if len(items) > MAX_SENTIMENT_ITEMS:
        items = items[-MAX_SENTIMENT_ITEMS:]

    _save_sentiment_data(items)

    history = _get_sentiment_history()
    history.append({
        "ticker": ticker,
        "score": round(data.overallScore, 3),
        "volume": data.socialVolume or 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(history) > MAX_HISTORY_POINTS:
        history = history[-MAX_HISTORY_POINTS:]
    _save_sentiment_history(history)

    await broadcast_ws("sentiment", {"type": "sentiment_updated", "item": new_item})
    logger.info("Sentiment updated: %s score=%s trend=%s", ticker, data.overallScore, data.trend)
    return {"ok": True, "item": new_item}


@router.post("/source-health", dependencies=[Depends(require_auth)])
async def submit_source_health(data: SourceHealthSubmit):
    """Agents report source health (latency, status, current score)."""
    sources = _get_source_health()
    now = datetime.now(timezone.utc).isoformat()
    new_entry = {
        "source": data.source.lower(),
        "status": data.status.upper(),
        "latency_ms": data.latency_ms,
        "score": round(data.score, 3),
        "weight": data.weight or 25,
        "updatedAt": now,
    }

    updated = False
    for i, s in enumerate(sources):
        if s.get("source") == data.source.lower():
            sources[i] = new_entry
            updated = True
            break
    if not updated:
        sources.append(new_entry)

    _save_source_health(sources)
    await broadcast_ws("sentiment", {"type": "source_health_updated", "source": new_entry})
    return {"ok": True, "source": new_entry}


@router.delete("/{ticker}", dependencies=[Depends(require_auth)])
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
