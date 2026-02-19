"""
Data Sources Monitor API — health of all 10 data feeds.
GET /api/v1/data-sources returns source status (stub until all services are wired).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_data_sources():
    """
    Return health and metrics for all 10 data sources.
    Frontend: Data Sources Monitor uses this; falls back to mock if error.
    """
    return {
        "sources": [
            {
                "id": 1,
                "name": "Finviz",
                "type": "Screener",
                "status": "healthy",
                "latencyMs": 120,
                "lastSync": "2m ago",
                "recordCount": 12450,
            },
            {
                "id": 2,
                "name": "Unusual Whales (UW)",
                "type": "Options Flow",
                "status": "healthy",
                "latencyMs": 85,
                "lastSync": "1m ago",
                "recordCount": 892,
            },
            {
                "id": 3,
                "name": "Alpaca",
                "type": "Market Data",
                "status": "healthy",
                "latencyMs": 45,
                "lastSync": "30s ago",
                "recordCount": 156000,
            },
            {
                "id": 4,
                "name": "FRED",
                "type": "Macro",
                "status": "healthy",
                "latencyMs": 320,
                "lastSync": "1h ago",
                "recordCount": 234,
            },
            {
                "id": 5,
                "name": "SEC EDGAR",
                "type": "Filings",
                "status": "degraded",
                "latencyMs": 2100,
                "lastSync": "15m ago",
                "recordCount": 89,
            },
            {
                "id": 6,
                "name": "Stockgeist",
                "type": "Sentiment",
                "status": "healthy",
                "latencyMs": 180,
                "lastSync": "5m ago",
                "recordCount": 4500,
            },
            {
                "id": 7,
                "name": "News API",
                "type": "News",
                "status": "healthy",
                "latencyMs": 95,
                "lastSync": "1m ago",
                "recordCount": 1203,
            },
            {
                "id": 8,
                "name": "Discord",
                "type": "Social",
                "status": "healthy",
                "latencyMs": 200,
                "lastSync": "3m ago",
                "recordCount": 567,
            },
            {
                "id": 9,
                "name": "X (Twitter)",
                "type": "Social",
                "status": "error",
                "latencyMs": None,
                "lastSync": "—",
                "recordCount": 0,
            },
            {
                "id": 10,
                "name": "YouTube",
                "type": "Knowledge",
                "status": "healthy",
                "latencyMs": 410,
                "lastSync": "10m ago",
                "recordCount": 42,
            },
        ],
    }
