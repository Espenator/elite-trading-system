"""
Signals API Routes
Endpoints for fetching and managing trading signals
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/signals/")
async def get_signals(
    limit: int = Query(100, ge=1, le=1000),
    tier: Optional[str] = None,
    min_confidence: Optional[float] = None
):
    """Get all signals with optional filtering"""
    # TODO: Connect to database
    # For now, return mock data
    return [
        {
            "id": "sig_1",
            "time": "09:35:12",
            "ticker": "TSLA",
            "tier": "T1",
            "score": 85,
            "aiConf": 90,
            "rvol": 2.5,
            "catalyst": "Breakout above resistance"
        },
        {
            "id": "sig_2",
            "time": "09:38:45",
            "ticker": "NVDA",
            "tier": "T1",
            "score": 82,
            "aiConf": 88,
            "rvol": 2.1,
            "catalyst": "Volume surge + compression"
        }
    ]

@router.get("/signals/active/{symbol}")
async def get_active_signal(symbol: str):
    """Get active signal for a specific symbol - FIXES 404 ERROR"""
    # TODO: Connect to signal generation engine
    # For now, return mock signal data
    
    # Mock data for testing
    mock_signals = {
        "SPY": {
            "type": "LONG",
            "confidence": 85,
            "entry": 580.25,
            "target": 590.50,
            "stop": 575.00,
            "riskReward": 2.0
        },
        "TSLA": {
            "type": "LONG",
            "confidence": 92,
            "entry": 245.30,
            "target": 255.00,
            "stop": 240.00,
            "riskReward": 1.8
        },
        "NVDA": {
            "type": "LONG",
            "confidence": 88,
            "entry": 145.75,
            "target": 152.00,
            "stop": 142.00,
            "riskReward": 1.7
        }
    }
    
    signal = mock_signals.get(symbol.upper())
    if not signal:
        # Return default signal for any other symbol
        signal = {
            "type": "LONG",
            "confidence": 75,
            "entry": 100.00,
            "target": 105.00,
            "stop": 97.50,
            "riskReward": 2.0
        }
    
    return signal

@router.get("/signals/tier/{tier}")
async def get_signals_by_tier(tier: str):
    """Get signals filtered by tier"""
    # TODO: Connect to database
    return [
        {
            "id": "sig_1",
            "ticker": "TSLA",
            "tier": tier,
            "score": 85,
            "confidence": 90
        }
    ]

@router.get("/signals/{ticker}")
async def get_signal_by_ticker(ticker: str):
    """Get the latest signal for a specific ticker"""
    # TODO: Connect to database
    return {
        "ticker": ticker,
        "type": "LONG",
        "score": 85,
        "confidence": 90,
        "entry": 150.00,
        "target": 155.00,
        "stop": 148.00
    }

@router.get("/chart/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = Query("1H", regex="^(1m|5m|15m|1H|4H|1D)$")
):
    """Get chart data for a symbol - FIXES 404 ERROR"""
    # TODO: Connect to yfinance fetcher
    # For now, return mock OHLCV data
    
    from datetime import datetime, timedelta
    import time
    
    # Generate mock candlestick data
    base_price = 150.00
    data = []
    current_time = int(datetime.now().timestamp())
    
    for i in range(100):
        timestamp = current_time - (100 - i) * 3600  # Hourly data
        open_price = base_price + (i * 0.1)
        close_price = open_price + 0.5
        high_price = max(open_price, close_price) + 0.3
        low_price = min(open_price, close_price) - 0.2
        
        data.append({
            "time": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": 1000000 + (i * 10000)
        })
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": data
    }

@router.get("/chart/{ticker}")
async def get_chart_data_legacy(
    ticker: str,
    interval: str = Query("1d", regex="^(1m|5m|15m|1h|1d)$")
):
    """Get chart data for a ticker (legacy endpoint)"""
    # Redirect to new endpoint
    return await get_chart_data(ticker, interval.upper())

@router.get("/predictions/{ticker}")
async def get_predictions(ticker: str):
    """Get ML predictions for a ticker"""
    # TODO: Connect to ML engine
    return {
        "ticker": ticker,
        "prediction": "BULLISH",
        "confidence": 0.85,
        "target": 155.00,
        "timeframe": "1-3 days"
    }
