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
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period, interval=interval)

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
            "1D": ("1y", "1d")
        }
        
        period, interval = interval_map.get(timeframe, ("1mo", "1h"))
        
        logger.info(f"Fetching chart data for {symbol} with {timeframe} timeframe")
        
        # Fetch data from yfinance (synchronous - FastAPI handles threading)
        try:
            hist = fetch_yfinance_data(symbol, period, interval)
        except Exception as e:
            logger.error(f"Error fetching yfinance data for {symbol}: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
        
        if hist.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol}"
            )
        
        # Convert to TradingView format
        chart_data = []
        for index, row in hist.iterrows():
            chart_data.append({
                "time": int(index.timestamp()),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        logger.info(f"Returning {len(chart_data)} candles for {symbol}")
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": chart_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


