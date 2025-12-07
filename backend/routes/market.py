"""
API Routes for Market Data - Glass House UI Backend
Provides market indices, chart data, and OHLCV endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

router = APIRouter(prefix="/api/market", tags=["market"])


# Response Models
class MarketIndex(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    changePercent: float
    sparklineData: List[float]
    lastUpdated: str


class OHLCVCandle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartIndicators(BaseModel):
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    rsi: Optional[float] = None


class ChartData(BaseModel):
    symbol: str
    timeframe: str
    data: List[OHLCVCandle]
    indicators: Optional[ChartIndicators] = None


@router.get("/indices", response_model=dict)
async def get_market_indices():
    """Get current market indices (S&P 500, Dow Jones, NASDAQ)"""
    try:
        indices = {"^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ"}
        result = {"indices": [], "timestamp": datetime.now().isoformat()}
        
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="5m")
                if hist.empty:
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(ticker.info.get('previousClose', current_price))
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close else 0
                sparkline = hist['Close'].tail(30).tolist()
                
                result["indices"].append({
                    "symbol": symbol.replace("^", ""),
                    "name": name,
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "sparklineData": [round(x, 2) for x in sparkline],
                    "lastUpdated": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market indices: {str(e)}")


@router.get("/charts/{symbol}", response_model=ChartData)
async def get_chart_data(symbol: str, timeframe: str = Query("15m", description="Timeframe: 1m, 5m, 15m, 1h, 1d")):
    """Get OHLCV chart data for a symbol with optional indicators"""
    try:
        period_map = {"1m": ("1d", "1m"), "5m": ("5d", "5m"), "15m": ("5d", "15m"), "1h": ("1mo", "1h"), "1d": ("1y", "1d")}
        period, interval = period_map.get(timeframe, ("5d", "15m"))
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
        
        candles = []
        for idx, row in hist.iterrows():
            candles.append({
                "time": int(idx.timestamp()),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
        
        closes = hist['Close']
        indicators = {
            "sma20": round(float(closes.rolling(20).mean().iloc[-1]), 2) if len(closes) >= 20 else None,
            "sma50": round(float(closes.rolling(50).mean().iloc[-1]), 2) if len(closes) >= 50 else None,
            "rsi": calculate_rsi(closes) if len(closes) >= 14 else None
        }
        
        return {"symbol": symbol, "timeframe": timeframe, "data": candles[-500:], "indicators": indicators}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")


def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except:
        return None


@router.get("/ohlcv/{symbol}")
async def get_ohlcv_data(symbol: str, timeframe: str = Query("1d"), limit: int = Query(500, ge=1, le=1000)):
    """Get OHLCV data for charting"""
    try:
        period_map = {"15m": ("5d", "15m"), "1h": ("1mo", "1h"), "1d": ("2y", "1d")}
        period, interval = period_map.get(timeframe, ("1y", "1d"))
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return {"symbol": symbol, "data": [], "error": "No data available"}
        
        data = []
        for idx, row in hist.tail(limit).iterrows():
            data.append({
                "timestamp": int(idx.timestamp()),
                "datetime": idx.isoformat(),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
        
        return {"symbol": symbol, "timeframe": timeframe, "data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
