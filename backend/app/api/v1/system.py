"""
System status API — glass-box visibility of trading mode and module status.

Exposes TRADING_MODE (paper/live) and status of each module for the UI.
"""
from fastapi import APIRouter
from app.modules.social_news_engine import get_status as social_news_status
from app.modules.chart_patterns import get_status as chart_patterns_status
from app.modules.ml_engine import get_status as ml_engine_status
from app.modules.execution_engine import get_status as execution_status, get_trading_mode

router = APIRouter()


@router.get("/status")
async def system_status():
    """
    Return system-wide status for glass-box UI:
    - trading_mode: paper | live
    - modules: status of each component (symbol_universe, social_news, chart_patterns, ml_engine, execution)
    """
    return {
        "trading_mode": get_trading_mode(),
        "modules": {
            "symbol_universe": {
                "status": "ready",
                "description": "Stock/symbol database and watchlists",
            },
            "social_news_engine": social_news_status(),
            "chart_patterns": chart_patterns_status(),
            "ml_engine": ml_engine_status(),
            "execution_engine": execution_status(),
        },
    }
