"""
Bible Scorer - Academic Pattern Quality Analysis
Fractal patterns, volume quality, staircase consistency
"""

import asyncio
from typing import Dict, List
import pandas as pd
import numpy as np

from core.logger import get_logger
from data_collection.yfinance_fetcher import get_data

logger = get_logger(__name__)


class BibleScorer:
    """
    Bible Scoring System - Academic pattern quality
    - Fractal Score (40%): HH/HL or LL/LH pattern quality
    - Volume Score (30%): Volume at swing points
    - Staircase Score (30%): Trend consistency
    """
    
    def __init__(self):
        self.logger = logger
        logger.info("Bible Scorer initialized")
    
    async def score_batch(self, symbols: List[str], lookback_days: int = 60) -> Dict[str, Dict]:
        """
        Score a batch of symbols
        
        Args:
            symbols: List of ticker symbols
            lookback_days: Days of historical data
        
        Returns:
            Dictionary of {symbol: {total_score, fractal_score, volume_quality, staircase_score}}
        """
        
        logger.info(f"📚 Bible Scoring {len(symbols)} symbols...")
        
        # Fetch data
        period = '3mo' if lookback_days <= 90 else '6mo'
        data = await get_data(symbols, period=period, interval='1d')
        
        results = {}
        
        for symbol, df in data.items():
            if df is None or df.empty or len(df) < 20:
                continue
            
            try:
                # Calculate 3 components
                fractal_score = self._calculate_fractal_score(df)
                volume_score = self._calculate_volume_score(df)
                staircase_score = self._calculate_staircase_score(df)
                
                # Weighted total (40% fractal, 30% volume, 30% staircase)
                total_score = (
                    (fractal_score * 0.40) +
                    (volume_score * 0.30) +
                    (staircase_score * 0.30)
                )
                
                results[symbol] = {
                    'total_score': round(total_score, 2),
                    'fractal_score': round(fractal_score, 2),
                    'volume_quality': round(volume_score, 2),
                    'staircase_score': round(staircase_score, 2),
                }
                
            except Exception as e:
                logger.debug(f"Error scoring {symbol}: {e}")
                continue
        
        logger.info(f"✅ Bible scored {len(results)}/{len(symbols)} symbols")
        
        return results
    
    def _calculate_fractal_score(self, df: pd.DataFrame, window: int = 5) -> float:
        """
        Calculate fractal pattern quality (0-100)
        Higher score = cleaner HH/HL or LL/LH patterns
        """
        
        if len(df) < window * 2:
            return 0.0
        
        # Find swing highs and lows
        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            # Swing high: higher than surrounding bars
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                highs.append((i, df['high'].iloc[i]))
            
            # Swing low: lower than surrounding bars
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                lows.append((i, df['low'].iloc[i]))
        
        if len(highs) < 2 or len(lows) < 2:
            return 0.0
        
        # Check for HH/HL pattern (uptrend)
        hh_count = sum(1 for i in range(1, len(highs)) if highs[i][1] > highs[i-1][1])
        hl_count = sum(1 for i in range(1, len(lows)) if lows[i][1] > lows[i-1][1])
        
        # Check for LL/LH pattern (downtrend)
        ll_count = sum(1 for i in range(1, len(lows)) if lows[i][1] < lows[i-1][1])
        lh_count = sum(1 for i in range(1, len(highs)) if highs[i][1] < highs[i-1][1])
        
        # Score based on pattern consistency
        uptrend_score = (hh_count + hl_count) / (len(highs) + len(lows) - 2) * 100
        downtrend_score = (ll_count + lh_count) / (len(highs) + len(lows) - 2) * 100
        
        # Return best pattern
        return max(uptrend_score, downtrend_score)
    
    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """
        Calculate volume quality at key swing points (0-100)
        Higher score = volume surges at structural breaks
        """
        
        if len(df) < 20:
            return 0.0
        
        # Calculate average volume
        avg_volume = df['volume'].mean()
        
        if avg_volume == 0:
            return 0.0
        
        # Find high volume days
        high_vol_days = df[df['volume'] > avg_volume * 1.5]
        
        if len(high_vol_days) == 0:
            return 0.0
        
        # Check if high volume days coincide with price moves
        price_moves = abs(df['close'].pct_change())
        high_vol_price_moves = price_moves[df['volume'] > avg_volume * 1.5].mean()
        avg_price_moves = price_moves.mean()
        
        if avg_price_moves == 0:
            return 0.0
        
        # Score: ratio of price moves on high volume vs average
        volume_quality = (high_vol_price_moves / avg_price_moves) * 50
        
        return min(100, volume_quality)
    
    def _calculate_staircase_score(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate trend consistency (0-100)
        Higher score = smooth, consistent trend (staircase pattern)
        """
        
        if len(df) < period:
            return 0.0
        
        # Calculate moving average
        sma = df['close'].rolling(period).mean()
        
        # Measure distance from SMA
        distance_from_sma = abs((df['close'] - sma) / sma * 100)
        
        # Score: lower average distance = more consistent trend
        avg_distance = distance_from_sma.mean()
        
        if avg_distance == 0:
            return 100.0
        
        # Invert: closer to SMA = higher score
        staircase_score = max(0, 100 - (avg_distance * 10))
        
        return staircase_score


# Global instance
bible_scorer = BibleScorer()


# Convenience function
async def score_symbols(symbols: List[str]) -> Dict[str, Dict]:
    """
    Convenience function to score symbols
    
    Usage:
        results = await score_symbols(['AAPL', 'TSLA', 'NVDA'])
    """
    return await bible_scorer.score_batch(symbols)

