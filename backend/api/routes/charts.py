"""
Chart Data API Routes
Provides TradingView-compatible candlestick data
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import yfinance as yf
from datetime import datetime
from backend.core.logger import get_logger
from backend.database import get_db

logger = get_logger(__name__)
router = APIRouter()


def fetch_yfinance_data(symbol: str, period: str, interval: str):
    """Synchronous function to fetch yfinance data"""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)
    except Exception as e:
        logger.warning(f"yfinance failed for {symbol}: {e}")
        # Return empty dataframe to trigger fallback
        import pandas as pd

        return pd.DataFrame()


@router.get("/chart/data/{symbol}")
def get_chart_data(
    symbol: str,
    timeframe: str = Query("1H", regex="^(1m|5m|15m|1H|4H|1D)$"),
):
    """
    Get chart data for TradingView (synchronous endpoint)

    Args:
        symbol: Stock ticker symbol
        timeframe: Chart timeframe (1m, 5m, 15m, 1H, 4H, 1D)

    Returns:
        Chart data in TradingView format with OHLCV candles
    """
    try:
        # Map timeframe to yfinance interval
        interval_map = {
            "1m": ("1d", "1m"),
            "5m": ("5d", "5m"),
            "15m": ("5d", "15m"),
            "1H": ("1mo", "1h"),
            "4H": ("3mo", "1d"),  # yfinance doesn't have 4h
            "1D": ("1y", "1d"),
        }

        period, interval = interval_map.get(timeframe, ("1mo", "1h"))

        logger.info(f"Fetching chart data for {symbol} with {timeframe} timeframe")

        # TODO: yfinance is currently timing out - using mock data for development
        # Uncomment below to enable real data fetching when network issues are resolved:
        # hist = fetch_yfinance_data(symbol, period, interval)
        
        # Generate mock OHLCV data (using mock data to avoid yfinance timeout)
        logger.info(f"Using mock data for {symbol} (yfinance disabled due to network issues)")
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta

        # Generate realistic mock data
        now = datetime.now()
        dates = pd.date_range(end=now, periods=100, freq="1H")

        # Simulate realistic price movement with trends
        base_price = 450.0 if symbol == "SPY" else 100.0
        trend = np.linspace(0, 5, 100)  # Slight upward trend
        noise = np.cumsum(np.random.randn(100) * 0.5)  # Random walk
        prices = base_price + trend + noise

        hist = pd.DataFrame(
            {
                "Open": prices + np.random.randn(100) * 0.3,
                "High": prices + np.abs(np.random.randn(100) * 0.8),
                "Low": prices - np.abs(np.random.randn(100) * 0.8),
                "Close": prices,
                "Volume": np.random.randint(5000000, 15000000, 100),
            },
            index=dates,
        )

        # Convert to TradingView format
        chart_data = []
        for index, row in hist.iterrows():
            chart_data.append(
                {
                    "time": int(index.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )

        logger.info(f"Returning {len(chart_data)} candles for {symbol}")

        return {"symbol": symbol, "timeframe": timeframe, "data": chart_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
