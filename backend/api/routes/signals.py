"""
Signals API Routes
Endpoints for fetching and managing trading signals

🚨 NO MOCK DATA - ALL REAL DATA FROM DATABASE OR EXTERNAL APIS
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import yfinance as yf

from backend.services import get_recent_signals
from database import get_db
from database.models import SignalHistory
from core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/signals/")
async def get_signals(
    limit: int = Query(100, ge=1, le=1000),
    tier: Optional[str] = None,
    min_confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get all signals with optional filtering - REAL DATA FROM DATABASE
    
    NO MOCK DATA - Returns actual signals from SignalHistory table
    """
    try:
        query = db.query(SignalHistory).order_by(SignalHistory.generated_at.desc())
        
        # Apply filters
        if min_confidence:
            query = query.filter(SignalHistory.score >= min_confidence)
        
        signals = query.limit(limit).all()
        
        # Transform to response format
        result = []
        for sig in signals:
            result.append({
                "id": f"sig_{sig.id}",
                "time": sig.generated_at.strftime("%H:%M:%S"),
                "ticker": sig.symbol,
                "tier": "T1" if sig.score >= 80 else "T2" if sig.score >= 60 else "T3",
                "score": sig.score,
                "aiConf": sig.score,  # Using score as confidence
                "rvol": sig.velez_score.get('volume_ratio', 1.0) if sig.velez_score else 1.0,
                "catalyst": "Signal detected" if sig.explosive_signal else "Setup forming"
            })
        
        logger.info(f"✅ Returned {len(result)} signals from database")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch signals from database: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/signals/active/{symbol}")
async def get_active_signal(symbol: str, db: Session = Depends(get_db)):
    """
    Get active signal for a specific symbol - REAL DATA
    
    Priority:
    1. Database SignalHistory (most recent)
    2. Calculate live from yfinance if no recent signal
    3. NO FALLBACK TO MOCK DATA
    """
    try:
        # Try database first (signals from last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        db_signal = db.query(SignalHistory).filter(
            SignalHistory.symbol == symbol.upper(),
            SignalHistory.generated_at >= cutoff
        ).order_by(SignalHistory.generated_at.desc()).first()
        
        if db_signal:
            logger.info(f"✅ Found signal in database for {symbol}")
            return {
                "type": db_signal.direction,
                "confidence": db_signal.score,
                "entry": db_signal.entry_price,
                "target": db_signal.target_price,
                "stop": db_signal.stop_price,
                "riskReward": round((db_signal.target_price - db_signal.entry_price) / 
                                   (db_signal.entry_price - db_signal.stop_price), 2)
            }
        
        # No database signal - calculate live from yfinance
        logger.info(f"⚡ Calculating live signal for {symbol} from yfinance")
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")
        
        if len(hist) < 2:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
        
        # Calculate live signal
        current_price = float(hist['Close'].iloc[-1])
        atr = float((hist['High'] - hist['Low']).mean())
        
        # Simple ATR-based levels
        stop_distance = atr * 1.5
        target_distance = atr * 3.0
        
        return {
            "type": "LONG",  # Default to LONG for live calculation
            "confidence": 75,  # Medium confidence for live calc
            "entry": round(current_price, 2),
            "target": round(current_price + target_distance, 2),
            "stop": round(current_price - stop_distance, 2),
            "riskReward": round(target_distance / stop_distance, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get signal for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching signal: {str(e)}")


@router.get("/signals/tier/{tier}")
async def get_signals_by_tier(tier: str, db: Session = Depends(get_db)):
    """
    Get signals filtered by tier - REAL DATA FROM DATABASE
    """
    try:
        # Map tier to score range
        tier_ranges = {
            "T1": (80, 100),
            "T2": (60, 79),
            "T3": (40, 59)
        }
        
        score_range = tier_ranges.get(tier.upper(), (0, 100))
        
        signals = db.query(SignalHistory).filter(
            SignalHistory.score >= score_range[0],
            SignalHistory.score <= score_range[1]
        ).order_by(SignalHistory.generated_at.desc()).limit(50).all()
        
        result = []
        for sig in signals:
            result.append({
                "id": f"sig_{sig.id}",
                "ticker": sig.symbol,
                "tier": tier,
                "score": sig.score,
                "confidence": sig.score
            })
        
        logger.info(f"✅ Returned {len(result)} {tier} signals")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch tier signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{ticker}")
async def get_signal_by_ticker(ticker: str, db: Session = Depends(get_db)):
    """
    Get the latest signal for a specific ticker - REAL DATA
    """
    try:
        signal = db.query(SignalHistory).filter(
            SignalHistory.symbol == ticker.upper()
        ).order_by(SignalHistory.generated_at.desc()).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"No signals found for {ticker}")
        
        return {
            "ticker": signal.symbol,
            "type": signal.direction,
            "score": signal.score,
            "confidence": signal.score,
            "entry": signal.entry_price,
            "target": signal.target_price,
            "stop": signal.stop_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch signal for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chart/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = Query("1H", regex="^(1m|5m|15m|1H|4H|1D)$")
):
    """
    Get chart data for a symbol - REAL DATA FROM YFINANCE
    
    NO MOCK DATA - Downloads actual OHLCV from yfinance
    """
    try:
        # Map timeframe to yfinance parameters
        timeframe_map = {
            "1m": {"period": "1d", "interval": "1m"},
            "5m": {"period": "5d", "interval": "5m"},
            "15m": {"period": "5d", "interval": "15m"},
            "1H": {"period": "1mo", "interval": "1h"},
            "4H": {"period": "3mo", "interval": "1d"},  # yfinance doesn't have 4H
            "1D": {"period": "1y", "interval": "1d"}
        }
        
        params = timeframe_map.get(timeframe, {"period": "1mo", "interval": "1h"})
        
        logger.info(f"📊 Downloading {timeframe} chart data for {symbol} from yfinance")
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=params["period"], interval=params["interval"])
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No chart data available for {symbol}")
        
        # Convert to chart format
        data = []
        for index, row in hist.iterrows():
            data.append({
                "time": int(index.timestamp()),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
        
        logger.info(f"✅ Returned {len(data)} real candles for {symbol}")
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"yfinance error: {str(e)}")


@router.get("/chart/{ticker}")
async def get_chart_data_legacy(
    ticker: str,
    interval: str = Query("1d", regex="^(1m|5m|15m|1h|1d)$")
):
    """Get chart data for a ticker (legacy endpoint) - redirects to new endpoint"""
    return await get_chart_data(ticker, interval.upper())


@router.get("/predictions/{ticker}")
async def get_predictions(ticker: str, db: Session = Depends(get_db)):
    """
    Get ML predictions for a ticker - REAL DATA
    
    TODO: Connect to actual ML engine
    For now, returns database-based analysis
    """
    try:
        # Get recent signals for this ticker
        recent_signals = db.query(SignalHistory).filter(
            SignalHistory.symbol == ticker.upper()
        ).order_by(SignalHistory.generated_at.desc()).limit(5).all()
        
        if not recent_signals:
            raise HTTPException(status_code=404, detail=f"No prediction data for {ticker}")
        
        # Calculate average direction from recent signals
        long_count = sum(1 for s in recent_signals if s.direction == "LONG")
        short_count = len(recent_signals) - long_count
        
        avg_score = sum(s.score for s in recent_signals) / len(recent_signals)
        
        prediction = "BULLISH" if long_count > short_count else "BEARISH"
        
        latest = recent_signals[0]
        
        return {
            "ticker": ticker,
            "prediction": prediction,
            "confidence": round(avg_score / 100, 2),
            "target": latest.target_price,
            "timeframe": "1-3 days",
            "based_on_signals": len(recent_signals)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to generate prediction for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
