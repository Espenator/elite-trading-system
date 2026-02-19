"""Patterns API - detected chart patterns. GET /api/v1/patterns."""

from fastapi import APIRouter

router = APIRouter()

_STUB_PATTERNS = [
    {
        "id": 1,
        "ticker": "AAPL",
        "pattern": "Bull Flag",
        "confidence": 92,
        "direction": "bullish",
        "timeframe": "1D",
        "detected": "5m ago",
        "priceTarget": 198.5,
        "currentPrice": 192.3,
    },
    {
        "id": 2,
        "ticker": "MSFT",
        "pattern": "Cup & Handle",
        "confidence": 87,
        "direction": "bullish",
        "timeframe": "4H",
        "detected": "12m ago",
        "priceTarget": 430.0,
        "currentPrice": 415.2,
    },
    {
        "id": 3,
        "ticker": "TSLA",
        "pattern": "Double Bottom",
        "confidence": 78,
        "direction": "bullish",
        "timeframe": "1D",
        "detected": "25m ago",
        "priceTarget": 265.0,
        "currentPrice": 248.1,
    },
    {
        "id": 4,
        "ticker": "NVDA",
        "pattern": "Head & Shoulders",
        "confidence": 74,
        "direction": "bearish",
        "timeframe": "1D",
        "detected": "35m ago",
        "priceTarget": 840.0,
        "currentPrice": 868.2,
    },
    {
        "id": 5,
        "ticker": "AMD",
        "pattern": "Ascending Triangle",
        "confidence": 85,
        "direction": "bullish",
        "timeframe": "1H",
        "detected": "45m ago",
        "priceTarget": 180.0,
        "currentPrice": 168.5,
    },
    {
        "id": 6,
        "ticker": "META",
        "pattern": "Breakout",
        "confidence": 81,
        "direction": "bullish",
        "timeframe": "4H",
        "detected": "1h ago",
        "priceTarget": 610.0,
        "currentPrice": 582.4,
    },
    {
        "id": 7,
        "ticker": "SPY",
        "pattern": "Bearish Engulfing",
        "confidence": 69,
        "direction": "bearish",
        "timeframe": "1D",
        "detected": "1h ago",
        "priceTarget": 492.0,
        "currentPrice": 502.1,
    },
    {
        "id": 8,
        "ticker": "GOOGL",
        "pattern": "Falling Wedge",
        "confidence": 76,
        "direction": "bullish",
        "timeframe": "1D",
        "detected": "2h ago",
        "priceTarget": 190.0,
        "currentPrice": 175.8,
    },
    {
        "id": 9,
        "ticker": "QQQ",
        "pattern": "Rising Channel",
        "confidence": 83,
        "direction": "bullish",
        "timeframe": "4H",
        "detected": "2h ago",
        "priceTarget": 445.0,
        "currentPrice": 432.5,
    },
]


@router.get("")
async def get_patterns():
    return {"patterns": _STUB_PATTERNS}
