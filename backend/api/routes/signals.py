"""
Signals API Routes
Endpoints for fetching and managing trading signals
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from database.database_manager import DatabaseManager

router = APIRouter()
db = DatabaseManager()

@router.get("/signals/")
async def get_signals(
    limit: int = Query(100, ge=1, le=1000),
    tier: Optional[str] = None,
    min_confidence: Optional[float] = None
):
    """Get all signals with optional filtering"""
    try:
        signals = db.get_recent_signals(limit=limit)
        
        # Apply filters
        if tier:
            signals = [s for s in signals if s.get('tier') == tier]
        if min_confidence is not None:
            signals = [s for s in signals if s.get('globalConfidence', 0) >= min_confidence]
        
        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/tier/{tier}")
async def get_signals_by_tier(tier: str):
    """Get signals filtered by tier"""
    try:
        signals = db.get_signals_by_tier(tier)
        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/{ticker}")
async def get_signal_by_ticker(ticker: str):
    """Get the latest signal for a specific ticker"""
    try:
        signal = db.get_signal_by_ticker(ticker)
        if not signal:
            raise HTTPException(status_code=404, detail=f"No signal found for {ticker}")
        return signal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart/{ticker}")
async def get_chart_data(
    ticker: str,
    interval: str = Query("1d", regex="^(1m|5m|15m|1h|1d)$")
):
    """Get chart data for a ticker"""
    try:
        # Import here to avoid circular dependency
        from data_collection.yfinance_fetcher import fetch_ohlcv_data
        
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "1d": "1d"
        }
        
        period_map = {
            "1m": "1d",
            "5m": "5d",
            "15m": "5d",
            "1h": "1mo",
            "1d": "6mo"
        }
        
        data = fetch_ohlcv_data(
            ticker,
            period=period_map[interval],
            interval=interval_map[interval]
        )
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No chart data for {ticker}")
        
        # Convert to format expected by TradingView Lightweight Charts
        chart_data = []
        for idx, row in data.iterrows():
            chart_data.append({
                "time": int(idx.timestamp()),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/{ticker}")
async def get_predictions(ticker: str):
    """Get ML predictions for a ticker"""
    try:
        # Import prediction engine
        from prediction_engine.prediction_service import get_predictions_for_ticker
        
        predictions = get_predictions_for_ticker(ticker)
        
        if not predictions:
            raise HTTPException(status_code=404, detail=f"No predictions for {ticker}")
        
        return predictions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
