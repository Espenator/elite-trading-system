"""
Sentiment Intelligence API — aggregated sentiment from Stockgeist, News API, Discord, X.
GET /api/v1/sentiment returns per-ticker composite scores (stub until services are wired).
"""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def get_sentiment(time_range: str = Query("24h", alias="timeRange")):
    """
    Return sentiment scores per ticker from all sources.
    Frontend: Sentiment Intelligence page; expects items with ticker, overallScore, trend, sources, etc.
    """
    return {
        "items": [
            {
                "ticker": "NVDA",
                "overallScore": 82,
                "trend": "bullish",
                "sources": {
                    "stockgeist": {"score": 85, "volume": 1250, "change": 12},
                    "news": {"score": 78, "articles": 45, "change": 8},
                    "discord": {"score": 88, "mentions": 320, "change": 15},
                    "x": {"score": 80, "posts": 890, "change": 5},
                },
                "momentum": "accelerating",
                "profitSignal": "STRONG BUY",
            },
        ],
    }
