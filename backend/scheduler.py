import asyncio
from typing import Dict, Any, List
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
from core.logger import get_logger
from data_collection.finviz_scraper import get_universe


class ScannerManager:
    """
    REAL DATA SCANNER - Shows actual stocks with real-time data
    Finviz Elite + yfinance OHLCV - SCANS ALL STOCKS
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)
        self.logger.info("✅ Real Data Scanner initialized (Finviz + yfinance)")
    
    async def run_scan(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        regime = params.get("regime", "YELLOW")
        top_n = params.get("top_n", 20)
        
        self.logger.info("="*70)
        self.logger.info(f"🚀 SCANNING {regime} REGIME - REAL DATA - ALL STOCKS")
        self.logger.info("="*70)
        
        # STAGE 1: Get ALL stocks from Finviz Elite
        try:
            universe = await get_universe(regime, max_results=1000)
            self.logger.info(f"✅ Finviz Elite: {len(universe)} stocks")
        except Exception as e:
            self.logger.error(f"Finviz failed: {e}")
            universe = ["AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META","NFLX","AMD","CRM",
                       "INTC","QCOM","AVGO","TXN","AMAT","LRCX","ADBE","ORCL","CSCO","NOW"]
            self.logger.warning(f"Using fallback: {len(universe)} stocks")
        
        # STAGE 2: Download real OHLCV data for ALL stocks
        self.logger.info(f"📊 Downloading price data for ALL {len(universe)} stocks...")
        
        signals = []
        
        for i, symbol in enumerate(universe):
            try:
                # Progress indicator every 50 stocks
                if (i + 1) % 50 == 0:
                    self.logger.info(f"   Progress: {i+1}/{len(universe)} stocks processed")
                
                # Get 3 months of daily data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="3mo", interval="1d")
                
                if len(hist) < 20:
                    continue
                
                # Current price and metrics
                price = float(hist['Close'].iloc[-1])
                
                # ATR (volatility)
                hist['TR'] = hist['High'] - hist['Low']
                atr = hist['TR'].rolling(14).mean().iloc[-1]
                
                # Volume metrics
                vol_current = hist['Volume'].iloc[-1]
                vol_avg = hist['Volume'].rolling(20).mean().iloc[-1]
                volume_ratio = vol_current / vol_avg if vol_avg > 0 else 1.0
                
                # Price movement
                price_prev = hist['Close'].iloc[-2]
                price_move_pct = ((price - price_prev) / price_prev) * 100
                
                # Moving averages
                sma20 = hist['Close'].rolling(20).mean().iloc[-1]
                sma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else sma20
                
                # Williams %R
                high14 = hist['High'].rolling(14).max().iloc[-1]
                low14 = hist['Low'].rolling(14).min().iloc[-1]
                williams_r = -100 * ((high14 - price) / (high14 - low14)) if (high14 - low14) != 0 else -50
                
                # RSI calculation
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1])) if not pd.isna(rs.iloc[-1]) else 50
                
                # Simple scoring based on momentum and volume
                score = 50.0  # Base
                
                # Volume bonus
                if volume_ratio > 2.0:
                    score += 25
                elif volume_ratio > 1.5:
                    score += 20
                elif volume_ratio > 1.2:
                    score += 10
                
                # Price action bonus
                if abs(price_move_pct) > 3:
                    score += 20
                elif abs(price_move_pct) > 2:
                    score += 15
                elif abs(price_move_pct) > 1:
                    score += 10
                
                # Trend bonus (price above SMAs)
                if price > sma20 and price > sma50:
                    score += 15
                elif price > sma20:
                    score += 10
                
                # RSI bonus (oversold for longs, overbought for shorts)
                if regime == "SHORT" and rsi > 70:
                    score += 10
                elif regime != "SHORT" and rsi < 30:
                    score += 10
                
                # Create signal with all required fields
                signal = {
                    "symbol": symbol,
                    "composite_score": round(score, 1),
                    "freshness_score": round(90 if abs(price_move_pct) < 2 else 70, 1),
                    "ignition_quality": round(min(100, volume_ratio * 50), 1),
                    "ignition_stage": "ACTIVE" if abs(price_move_pct) > 1 else "BUILDING",
                    "bible_score": round(min(95, volume_ratio * 40 + (20 if price > sma20 else 0)), 1),
                    "structure_score": round(80 if price > sma20 and price > sma50 else 60 if price > sma20 else 40, 1),
                    "price_move_pct": round(price_move_pct, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "williams_r": round(williams_r, 1),
                    "price": round(price, 2),
                    "bias": "SHORT" if regime == "SHORT" else "LONG",
                    "momentum_score": round((score + volume_ratio * 20) / 2, 1),
                    "volume_score": round(volume_ratio * 30, 1),
                    "rsi": round(rsi, 1),
                    "atr": round(atr, 2),
                    "sma20": round(sma20, 2),
                    "sma50": round(sma50, 2),
                    "timestamp": datetime.now().isoformat()
                }
                
                signals.append(signal)
                
            except Exception as e:
                self.logger.debug(f"   {symbol}: Failed ({str(e)[:50]})")
                continue
        
        # Sort by score and return top N
        signals.sort(key=lambda x: x["composite_score"], reverse=True)
        final_signals = signals[:top_n]
        
        # Summary
        self.logger.info("="*70)
        self.logger.info(f"✅ SCAN COMPLETE: Scanned {len(signals)} stocks, returning top {len(final_signals)}")
        if final_signals:
            self.logger.info(f"   Top signal: {final_signals[0]['symbol']} (Score: {final_signals[0]['composite_score']})")
        else:
            self.logger.info("   No signals found")
        self.logger.info("="*70)
        
        return final_signals
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "is_scanning": False,
            "last_scan": datetime.now().isoformat(),
            "scanner_type": "REAL_DATA_FINVIZ_YFINANCE_ALL_STOCKS"
        }


