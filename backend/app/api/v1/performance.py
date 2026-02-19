"""
Performance Analytics API — market overview, returns, metrics (stub until analytics are wired).
GET /api/v1/performance returns data for Performance Analytics page.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_performance():
    """Return market stats, performance summary, and optional equity curve. Used by Performance Analytics page."""
    return {
        "marketStats": [
            {
                "label": "SPY (S&P 500 ETF)",
                "value": "$498.75",
                "change": "+0.85%",
                "up": True,
            },
            {
                "label": "VIX (Volatility Index)",
                "value": "17.20",
                "change": "-1.52%",
                "up": False,
            },
            {
                "label": "Market Breadth (Adv/Dec)",
                "value": "+1,250",
                "change": "+8.3%",
                "up": True,
            },
            {
                "label": "Sector Performance (Tech)",
                "value": "+1.1%",
                "sub": "Leading",
                "up": True,
            },
        ],
        "summary": [
            {
                "label": "Total Return",
                "value": "+15.3%",
                "sub": "+1.2% (last month)",
                "up": True,
            },
            {
                "label": "Annualized Return",
                "value": "18.7%",
                "sub": "-0.5% (vs. avg)",
                "up": False,
            },
            {
                "label": "Sharpe Ratio",
                "value": "1.25",
                "sub": "+0.03 (vs. benchmark)",
                "up": True,
            },
        ],
        "monthlyReturns": {
            "2023": [3.5, 1.2, -0.8, 2.1, 4.0, 0.5, 1.8, -2.5, -1.0, 0.7, None, None],
            "2024": [4.1, 2.5, 0.1, 1.5, 3.2, 1.0, None, None, None, None, None, None],
        },
        "factors": [
            {"name": "Equity Exposure", "value": "+7.2%", "up": True},
            {"name": "Fixed Income", "value": "+1.8%", "up": True},
            {"name": "Alternatives", "value": "-0.5%", "up": False},
            {"name": "Currency Hedging", "value": "+0.3%", "up": True},
            {"name": "Sector Rotation", "value": "+1.5%", "up": True},
        ],
    }
