"""
Market Data API Routes
Endpoints for market indices and real-time data
"""
from fastapi import APIRouter, HTTPException
import yfinance as yf

router = APIRouter()

@router.get("/indices")
async def get_market_indices():
    """Get major market indices data"""
    try:
        indices = {
            'SPY': '^GSPC',  # S&P 500
            'DIA': '^DJI',   # Dow Jones
            'QQQ': '^IXIC'   # NASDAQ
        }
        
        data = {}
        for name, symbol in indices.items():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            data[name] = {
                'price': info.get('regularMarketPrice', 0),
                'change': info.get('regularMarketChange', 0),
                'changePercent': info.get('regularMarketChangePercent', 0)
            }
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quote/{ticker}")
async def get_quote(ticker: str):
    """Get real-time quote for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'ticker': ticker,
            'price': info.get('regularMarketPrice', 0),
            'change': info.get('regularMarketChange', 0),
            'changePercent': info.get('regularMarketChangePercent', 0),
            'volume': info.get('volume', 0),
            'marketCap': info.get('marketCap', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
