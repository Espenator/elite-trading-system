# app/api/v1/chart.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import yfinance as yf
from datetime import datetime, timedelta
import logging
import time
import random

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_sample_data(symbol: str, timeframe: str, num_candles: int = 200, before_timestamp: int = None):
    """Generate sample OHLCV data when live data is unavailable."""
    # If before_timestamp provided, generate data ending before that time
    if before_timestamp:
        end_time = datetime.fromtimestamp(before_timestamp)
    else:
        end_time = datetime.now()
    
    # Time intervals in minutes
    intervals = {
        "5M": 5,
        "15M": 15,
        "1H": 60,
        "4H": 240,
        "1D": 1440
    }
    
    interval_mins = intervals.get(timeframe, 60)
    
    # Base price depends on symbol
    base_prices = {
        "SPY": 590.0,
        "QQQ": 520.0,
        "AAPL": 195.0,
        "MSFT": 430.0,
        "GOOGL": 175.0,
        "AMZN": 225.0,
        "NVDA": 140.0,
        "TSLA": 400.0,
    }
    
    base_price = base_prices.get(symbol.upper(), 100.0)
    
    # Add some randomness based on before_timestamp to get different price ranges
    if before_timestamp:
        random.seed(before_timestamp)
        base_price = base_price * random.uniform(0.8, 1.2)
    
    data = []
    price = base_price
    
    for i in range(num_candles):
        # Calculate timestamp going backwards from end_time
        candle_time = end_time - timedelta(minutes=interval_mins * (num_candles - i))
        timestamp = int(candle_time.timestamp())
        
        # Generate realistic price movement
        change_pct = random.uniform(-0.02, 0.02)  # -2% to +2% per candle
        open_price = price
        close_price = price * (1 + change_pct)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
        volume = int(random.uniform(1000000, 5000000))
        
        data.append({
            "time": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        
        price = close_price
    
    # Reset random seed
    if before_timestamp:
        random.seed()
    
    return data

# Timeframe mapping to yfinance intervals and periods
TIMEFRAME_CONFIG = {
    "5M": {"interval": "5m", "period": "5d"},
    "15M": {"interval": "15m", "period": "5d"},
    "1H": {"interval": "1h", "period": "30d"},
    "4H": {"interval": "1h", "period": "60d"},  # yfinance doesn't have 4h, we'll aggregate
    "1D": {"interval": "1d", "period": "1y"},
}


@router.get("/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = Query(default="1H", description="Timeframe: 5m, 15m, 1H, 4H, 1D"),
    before: Optional[int] = Query(default=None, description="Load data before this Unix timestamp")
):
    """
    Get OHLCV chart data for a symbol.
    
    Returns candlestick data compatible with lightweight-charts library.
    Supports pagination with 'before' parameter to load historical data.
    """
    try:
        # Normalize timeframe
        tf = timeframe.upper()
        if tf not in TIMEFRAME_CONFIG:
            tf = "1H"
        
        config = TIMEFRAME_CONFIG.get(tf, TIMEFRAME_CONFIG["1H"])
        
        logger.info(f"Fetching chart data for {symbol}, timeframe: {tf}, before: {before}")
        
        # If 'before' is specified, return sample historical data
        # (yfinance doesn't easily support pagination)
        if before:
            sample_data = generate_sample_data(symbol, tf, num_candles=100, before_timestamp=before)
            return {
                "symbol": symbol,
                "timeframe": tf,
                "data": sample_data,
                "count": len(sample_data),
                "is_sample": True
            }
        
        # Use yf.download which is more reliable than Ticker.history for rate limits
        # Add retries for resilience
        max_retries = 3
        df = None
        
        for attempt in range(max_retries):
            try:
                df = yf.download(
                    symbol,
                    period=config["period"],
                    interval=config["interval"],
                    progress=False,
                    timeout=30
                )
                if not df.empty:
                    break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief delay before retry
        
        if df is None or df.empty:
            # Use sample data as fallback when live data unavailable (rate limits, etc.)
            logger.warning(f"Using sample data for {symbol} due to unavailable live data")
            sample_data = generate_sample_data(symbol, tf)
            return {
                "symbol": symbol,
                "timeframe": tf,
                "data": sample_data,
                "count": len(sample_data),
                "is_sample": True  # Flag to indicate this is sample data
            }
        
        # Handle 4H aggregation from 1H data
        if tf == "4H":
            df = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        
        # Convert to lightweight-charts format
        # Time must be Unix timestamp in seconds
        data = []
        for idx, row in df.iterrows():
            # Convert timestamp to Unix seconds
            timestamp = int(idx.timestamp())
            
            # Handle both single-level and multi-level column indices
            open_val = row["Open"] if "Open" in row else row[("Open", symbol)]
            high_val = row["High"] if "High" in row else row[("High", symbol)]
            low_val = row["Low"] if "Low" in row else row[("Low", symbol)]
            close_val = row["Close"] if "Close" in row else row[("Close", symbol)]
            volume_val = row["Volume"] if "Volume" in row else row[("Volume", symbol)]
            
            data.append({
                "time": timestamp,
                "open": round(float(open_val), 2),
                "high": round(float(high_val), 2),
                "low": round(float(low_val), 2),
                "close": round(float(close_val), 2),
                "volume": int(volume_val)
            })
        
        logger.info(f"Returning {len(data)} candles for {symbol}")
        
        return {
            "symbol": symbol,
            "timeframe": tf,
            "data": data,
            "count": len(data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch chart data: {str(e)}"
        )


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current quote for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "symbol": symbol,
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "change": info.get("regularMarketChange"),
            "changePercent": info.get("regularMarketChangePercent"),
            "volume": info.get("regularMarketVolume"),
            "high": info.get("regularMarketDayHigh"),
            "low": info.get("regularMarketDayLow"),
            "open": info.get("regularMarketOpen"),
            "previousClose": info.get("regularMarketPreviousClose"),
        }
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch quote: {str(e)}"
        )
