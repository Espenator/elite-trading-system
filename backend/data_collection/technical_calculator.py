"""
Enhanced Technical Calculator with Freshness Detection
Stage 2 Ignition vs Stage 3 Momentum Detection
"""

from typing import Dict, List
import asyncio
import pandas as pd
from .yfinance_fetcher import get_data
from backend.core.logger import get_logger

logger = get_logger(__name__)


class TechnicalCalculator:
    """Technical calculator with inline freshness scoring"""
    
    def __init__(self):
        self.logger = logger
    
    async def analyze_batch(self, symbols: List[str], days: int = 180) -> Dict[str, Dict]:
        """Analyze batch with freshness scoring"""
        
        # Convert days to period
        if days <= 7:
            period = '5d'
        elif days <= 30:
            period = '1mo'
        elif days <= 90:
            period = '3mo'
        elif days <= 180:
            period = '6mo'
        else:
            period = '1y'
        
        # Fetch data
        data = await get_data(symbols, period=period, interval='1d')
        
        results = {}
        for symbol, df in data.items():
            if df is None or df.empty:
                continue
            
            try:
                current_price = float(df['close'].iloc[-1])
                
                # Calculate freshness metrics
                freshness_data = self._calculate_freshness(symbol, df, current_price)
                
                # Calculate technical indicators
                rsi = self._calculate_rsi(df)
                adx = self._calculate_adx(df)
                atr = self._calculate_atr(df)
                
                # Structure validation
                structure_pass = (
                    freshness_data['freshness_score'] >= 60 and  # Must be fresh
                    freshness_data['ignition_quality'] >= 50      # Must have quality
                )
                
                results[symbol] = {
                    'structure_pass': structure_pass,
                    'structure_score': 75.0,  # Placeholder
                    'price': current_price,
                    
                    # Freshness metrics (NEW!)
                    'freshness_score': freshness_data['freshness_score'],
                    'ignition_quality': freshness_data['ignition_quality'],
                    'ignition_stage': freshness_data['stage'],
                    'price_move_pct': freshness_data['price_move_pct'],
                    'volume_ratio': freshness_data['volume_ratio'],
                    'williams_r': freshness_data['williams_r'],
                    'sma20_distance': freshness_data['sma20_distance_pct'],
                    'minutes_since_breakout': freshness_data['minutes_since_breakout'],
                    
                    # Technical indicators
                    'rsi': rsi,
                    'adx': adx,
                    'atr': atr,
                    'rel_volume': freshness_data['volume_ratio'],
                    'perf_week': freshness_data['price_move_pct'],
                    'higher_low': True,
                    'above_sma20': freshness_data['sma20_distance'] <= 3.0,
                    'above_sma50': True,
                    'is_compressed': freshness_data['stage'] == "STAGE_2_IGNITION",
                    'volatility': 25.0,
                    'bias': 'LONG',
                }
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        return results
    
    def _calculate_freshness(self, symbol: str, df: pd.DataFrame, 
                            current_price: float) -> Dict[str, float]:
        """
        Calculate Freshness Score (0-100) - Stage 2 Ignition Detection
        
        100 = Perfect Stage 2 ignition (just starting)
        50 = Early Stage 3 (marginal)
        0 = Stage 3 climax or Stage 4 exhaustion (too late)
        """
        
        if df is None or len(df) < 20:
            return {
                'freshness_score': 0,
                'ignition_quality': 0,
                'stage': 'UNKNOWN',
                'price_move_pct': 0,
                'volume_ratio': 1.0,
                'williams_r': -50,
                'sma20_distance_pct': 0,
                'minutes_since_breakout': 0,
            }
        
        # Calculate components
        price_move = self._calc_price_move(df, current_price)
        volume_ratio = self._calc_volume_ratio(df)
        williams_r = self._calc_williams_r(df)
        sma20_distance = self._calc_sma20_distance(df, current_price)
        time_factor = self._estimate_breakout_time(df)
        
        # Fresh Ignition Scoring
        fresh_score = 100.0
        
        # 1. Price Move (1-3% = perfect)
        if price_move < 0.5:
            fresh_score -= 20  # Not moving yet
        elif 0.5 <= price_move <= 3.0:
            fresh_score += 0   # Perfect range
        elif 3.0 < price_move <= 5.0:
            fresh_score -= 30  # Getting late
        else:
            fresh_score -= 60  # Too late
        
        # 2. Volume Ratio (150-250% = institutional)
        if 1.5 <= volume_ratio <= 2.5:
            fresh_score += 0   # Perfect
        elif 1.2 <= volume_ratio < 1.5:
            fresh_score -= 10  # Building
        elif volume_ratio > 3.0:
            fresh_score -= 40  # Climax
        else:
            fresh_score -= 25  # Too low
        
        # 3. Williams %R (-80 to -60 = fresh breakout)
        if -80 <= williams_r <= -60:
            fresh_score += 10  # Just breaking out
        elif williams_r < -80:
            fresh_score -= 15  # Still compressed
        elif williams_r > -40:
            fresh_score -= 30  # Overbought
        
        # 4. SMA20 Distance (within 3% = Bible's rule)
        if sma20_distance <= 3.0:
            fresh_score += 10
        elif sma20_distance > 5.0:
            fresh_score -= 30
        
        # 5. Time Factor
        if time_factor > 120:
            fresh_score -= 40  # Stale
        
        fresh_score = max(0, min(100, fresh_score))
        
        # Determine Stage
        if fresh_score >= 80:
            stage = "STAGE_2_IGNITION"
        elif fresh_score >= 60:
            stage = "EARLY_STAGE_3"
        elif fresh_score >= 40:
            stage = "LATE_STAGE_3"
        else:
            stage = "EXHAUSTION"
        
        # Ignition Quality
        ignition_quality = 50.0
        if 1.5 <= volume_ratio <= 2.5:
            ignition_quality += 40
        if -80 <= williams_r <= -60:
            ignition_quality += 30
        if sma20_distance <= 3.0:
            ignition_quality += 30
        ignition_quality = min(100, ignition_quality)
        
        return {
            'freshness_score': round(fresh_score, 1),
            'ignition_quality': round(ignition_quality, 1),
            'stage': stage,
            'price_move_pct': round(price_move, 2),
            'volume_ratio': round(volume_ratio, 2),
            'williams_r': round(williams_r, 1),
            'sma20_distance_pct': round(sma20_distance, 2),
            'minutes_since_breakout': int(time_factor),
        }
    
    def _calc_price_move(self, df: pd.DataFrame, current_price: float) -> float:
        """Today's price move %"""
        if len(df) < 1:
            return 0.0
        open_price = df['open'].iloc[-1]
        if open_price == 0:
            return 0.0
        return ((current_price - open_price) / open_price) * 100
    
    def _calc_volume_ratio(self, df: pd.DataFrame) -> float:
        """Volume vs 20-day average"""
        if len(df) < 20:
            return 1.0
        avg_vol = df['volume'].iloc[-20:-1].mean()
        current_vol = df['volume'].iloc[-1]
        return current_vol / avg_vol if avg_vol > 0 else 1.0
    
    def _calc_williams_r(self, df: pd.DataFrame, period: int = 14) -> float:
        """Williams %R (-100 to 0)"""
        if len(df) < period:
            return -50.0
        high = df['high'].iloc[-period:].max()
        low = df['low'].iloc[-period:].min()
        close = df['close'].iloc[-1]
        if high == low:
            return -50.0
        return ((high - close) / (high - low)) * -100
    
    def _calc_sma20_distance(self, df: pd.DataFrame, current_price: float) -> float:
        """Distance from 20 SMA (%)"""
        if len(df) < 20:
            return 0.0
        sma20 = df['close'].iloc[-20:].mean()
        return abs(((current_price - sma20) / sma20) * 100) if sma20 > 0 else 0.0
    
    def _estimate_breakout_time(self, df: pd.DataFrame) -> int:
        """Estimate minutes since breakout"""
        if len(df) < 2:
            return 0
        current_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].iloc[-20:-1].mean()
        if current_vol > avg_vol * 2:
            return 30
        elif current_vol > avg_vol * 1.5:
            return 60
        return 120
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        if len(df) < period + 1:
            return 50.0
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX (simplified)"""
        return 30.0  # Placeholder
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        if len(df) < period:
            return 2.5
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 2.5


# Global instance
calculator = TechnicalCalculator()

