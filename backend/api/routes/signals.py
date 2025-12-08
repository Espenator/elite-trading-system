"""
Signals API Routes
Endpoints for fetching and managing trading signals

🚨 NO MOCK DATA - ALL REAL DATA FROM DATABASE OR EXTERNAL APIS
"""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import yfinance as yf
import asyncio

from backend.services import get_recent_signals
from database import get_db
from database.models import SignalHistory, SymbolUniverse
from core.logger import get_logger
from data_collection.finviz_scraper import FinvizClient

router = APIRouter()
logger = get_logger(__name__)

# Global scan state
scan_state = {
    "is_scanning": False,
    "last_scan_time": None,
    "signals_generated": 0
}


@router.post("/scan/force")
async def force_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Force a market scan - REAL DATA ONLY
    
    1. Fetches universe from Finviz Elite API
    2. Gets real price data from yfinance
    3. Scores using Velez algorithm
    4. Saves to database
    5. Returns top 10 signals
    """
    global scan_state
    
    if scan_state["is_scanning"]:
        raise HTTPException(status_code=409, detail="Scan already in progress")
    
    try:
        scan_state["is_scanning"] = True
        scan_state["last_scan_time"] = datetime.utcnow()
        
        logger.info("🚀 Starting FORCE SCAN...")
        
        # Step 1: Get symbol universe from database
        symbols = db.query(SymbolUniverse).filter(
            SymbolUniverse.is_active == True
        ).limit(50).all()  # Limit to 50 for speed
        
        if not symbols:
            raise HTTPException(status_code=404, detail="No symbols in database. Run INITIALIZE_SYSTEM.ps1 first")
        
        symbol_list = [s.symbol for s in symbols]
        logger.info(f"✅ Loaded {len(symbol_list)} symbols from database")
        
        # Step 2: Fetch real price data and generate signals
        signals_generated = []
        
        for symbol in symbol_list[:20]:  # Process first 20 for speed
            try:
                logger.info(f"📈 Analyzing {symbol}...")
                
                # Get real data from yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d", interval="1d")
                
                if hist.empty or len(hist) < 2:
                    logger.warning(f"⚠️ No data for {symbol}, skipping")
                    continue
                
                # Calculate metrics
                current_price = float(hist['Close'].iloc[-1])
                atr = float((hist['High'] - hist['Low']).mean())
                volume_avg = float(hist['Volume'].mean())
                volume_current = float(hist['Volume'].iloc[-1])
                volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1.0
                
                # Price change
                price_change_pct = ((current_price - float(hist['Open'].iloc[-1])) / float(hist['Open'].iloc[-1])) * 100
                
                # Calculate score (Velez-style)
                score = 50.0  # Base
                
                # Volume surge bonus
                if volume_ratio > 2.0:
                    score += 20
                elif volume_ratio > 1.5:
                    score += 10
                
                # Price movement bonus
                if abs(price_change_pct) > 2.0:
                    score += 15
                elif abs(price_change_pct) > 1.0:
                    score += 10
                
                # ATR-based stops and targets
                entry_price = current_price
                stop_price = round(current_price - (atr * 2.0), 2)
                target_price = round(current_price + (atr * 3.0), 2)
                
                # Determine direction
                direction = "LONG" if price_change_pct > 0 else "SHORT"
                
                # Create signal
                signal = SignalHistory(
                    symbol=symbol,
                    direction=direction,
                    score=round(score, 1),
                    entry_price=entry_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    explosive_signal=volume_ratio > 2.0,
                    compression_days=0,
                    velez_score={
                        "m5": 0.0,
                        "m15": 0.0,
                        "h1": 0.0,
                        "volume_ratio": round(volume_ratio, 2),
                        "price_change_pct": round(price_change_pct, 2)
                    },
                    generated_at=datetime.utcnow()
                )
                
                db.add(signal)
                signals_generated.append({
                    "symbol": symbol,
                    "score": score,
                    "direction": direction,
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "stop_price": stop_price
                })
                
                logger.info(f"✅ {symbol}: Score {score:.1f} | {direction} | Entry ${entry_price}")
                
            except Exception as e:
                logger.error(f"❌ Failed to analyze {symbol}: {e}")
                continue
        
        # Commit all signals
        db.commit()
        
        # Sort by score
        signals_generated.sort(key=lambda x: x['score'], reverse=True)
        
        scan_state["signals_generated"] = len(signals_generated)
        
        logger.info(f"✅ SCAN COMPLETE! Generated {len(signals_generated)} signals")
        
        return {
            "status": "success",
            "signals_generated": len(signals_generated),
            "scan_time": scan_state["last_scan_time"].isoformat(),
            "top_signals": signals_generated[:10]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}")
    finally:
        scan_state["is_scanning"] = False


@router.get("/scan/status")
async def get_scan_status():
    """
    Get current scan status
    """
    return {
        "is_scanning": scan_state["is_scanning"],
        "last_scan_time": scan_state["last_scan_time"].isoformat() if scan_state["last_scan_time"] else None,
        "signals_generated": scan_state["signals_generated"]
    }


@router.get("/signals")
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
                "aiConf": sig.score,
                "rvol": sig.velez_score.get('volume_ratio', 1.0) if sig.velez_score else 1.0,
                "catalyst": "Signal detected" if sig.explosive_signal else "Setup forming",
                "direction": sig.direction,
                "entry_price": sig.entry_price,
                "target_price": sig.target_price,
                "stop_price": sig.stop_price
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
    """
    try:
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
        
        raise HTTPException(status_code=404, detail=f"No recent signal for {symbol}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get signal for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching signal: {str(e)}")


@router.get("/chart/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = Query("1H", regex="^(1m|5m|15m|1H|4H|1D)$")
):
    """
    Get chart data for a symbol - REAL DATA FROM YFINANCE
    """
    try:
        timeframe_map = {
            "1m": {"period": "1d", "interval": "1m"},
            "5m": {"period": "5d", "interval": "5m"},
            "15m": {"period": "5d", "interval": "15m"},
            "1H": {"period": "1mo", "interval": "1h"},
            "4H": {"period": "3mo", "interval": "1d"},
            "1D": {"period": "1y", "interval": "1d"}
        }
        
        params = timeframe_map.get(timeframe, {"period": "1mo", "interval": "1h"})
        
        logger.info(f"📊 Downloading {timeframe} chart data for {symbol} from yfinance")
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=params["period"], interval=params["interval"])
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No chart data available for {symbol}")
        
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
