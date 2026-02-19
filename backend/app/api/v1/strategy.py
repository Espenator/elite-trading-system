"""
Strategy Intelligence API - active strategies and config (stub until strategy engine is wired).
GET /api/v1/strategy returns strategies for Strategy Intelligence page.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_strategies():
    """Return active strategies and status. Used by Strategy Intelligence page."""
    return {
        "strategies": [
            {
                "id": 1,
                "name": "Momentum Scalper v2",
                "status": "Active",
                "description": "Aggressive short-term momentum strategy with tight stop-losses.",
                "dailyPL": 1.25,
                "winRate": 68,
                "maxDrawdown": -3.1,
            },
            {
                "id": 2,
                "name": "Trend Follower FX",
                "status": "Paused",
                "description": "Medium-term trend following strategy across major FX pairs.",
                "dailyPL": 0.1,
                "winRate": 55,
                "maxDrawdown": -5.8,
            },
            {
                "id": 3,
                "name": "Arbitrage Crypto",
                "status": "Error",
                "description": "Cross-exchange cryptocurrency arbitrage with automated execution.",
                "dailyPL": -0.5,
                "winRate": 72,
                "maxDrawdown": -1.2,
            },
            {
                "id": 4,
                "name": "Mean Reversion",
                "status": "Active",
                "description": "Statistical arbitrage on mean-reverting equity pairs.",
                "dailyPL": 0.85,
                "winRate": 61,
                "maxDrawdown": -2.4,
            },
        ],
    }
