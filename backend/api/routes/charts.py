"""
Chart Data API Routes
Provides TradingView-compatible candlestick data
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import yfinance as yf
from datetime import datetime
from core.logger import get_logger
from database import get_db

logger = get_logger(__name__)
router = APIRouter()

@router.get("/chart/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = "1H",
    db: Session = Depends(get_db)
):
    """
    Get chart data for TradingView
    
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
        
        # Fetch data from yfinance
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
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


@router.get("/signals/active/{symbol}")
async def get_active_signal(symbol: str, db: Session = Depends(get_db)):
    """
    Get the most recent active signal for a specific symbol
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Most recent signal from last 24 hours
    """
    try:
        from database.models import SignalHistory
        from datetime import timedelta
        
        # Get most recent signal from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        signal = db.query(SignalHistory).filter(
            SignalHistory.symbol == symbol.upper(),
            SignalHistory.generated_at >= cutoff_time
        ).order_by(SignalHistory.generated_at.desc()).first()
        
        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"No active signal found for {symbol}"
            )
        
        return {
            "id": signal.id,
            "symbol": signal.symbol,
            "direction": signal.direction,
            "score": signal.score,
            "entry_price": signal.entry_price,
            "stop_price": signal.stop_price,
            "target_price": signal.target_price,
            "velez_score": signal.velez_score,
            "explosive_signal": signal.explosive_signal,
            "generated_at": signal.generated_at.isoformat(),
            "was_traded": signal.was_traded
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active signal for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
