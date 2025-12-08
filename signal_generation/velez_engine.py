"""
Velez Indicator Engine
Translates your Velez scoring system to Python
Multi-timeframe analysis: Weekly, Daily, 4H, 1H
"""

import pandas as pd
import numpy as np
from typing import Dict

from core.logger import get_logger

logger = get_logger(__name__)

def calculate_velez_score(
    weekly_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    four_hour_df: pd.DataFrame,
    one_hour_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate Velez score across multiple timeframes
    
    Returns weighted composite from your Bible:
    - Weekly: 30%
    - Daily: 40%
    - 4-Hour: 20%
    - 1-Hour: 10%
    
    Args:
        weekly_df: Weekly OHLCV data
        daily_df: Daily OHLCV data
        four_hour_df: 4-hour OHLCV data (use 1h as proxy)
        one_hour_df: 1-hour OHLCV data
    
    Returns:
        Dict with scores per timeframe and composite
    """
    scores = {}
    
    # Calculate score for each timeframe
    scores['weekly'] = calculate_single_timeframe_score(weekly_df) if len(weekly_df) >= 20 else 0
    scores['daily'] = calculate_single_timeframe_score(daily_df) if len(daily_df) >= 20 else 0
    scores['four_hour'] = calculate_single_timeframe_score(four_hour_df) if len(four_hour_df) >= 20 else 0
    scores['one_hour'] = calculate_single_timeframe_score(one_hour_df) if len(one_hour_df) >= 20 else 0
    
    # Weighted composite (from your Bible)
    weights = {
        'weekly': 0.30,
        'daily': 0.40,
        'four_hour': 0.20,
        'one_hour': 0.10
    }
    
    composite = sum(scores[tf] * weights[tf] for tf in weights.keys())
    scores['composite'] = composite
    
    return scores

def calculate_single_timeframe_score(df: pd.DataFrame) -> float:
    """
    Calculate Velez score for a single timeframe
    
    Based on your Velez indicator logic:
    - Trend strength
    - Momentum
    - Volume confirmation
    - Structure quality (HH/HL or LL/LH)
    
    Returns:
        Score from 0-100
    """
    if len(df) < 20:
        return 0.0
    
    score = 0.0
    
    # Calculate indicators
    df = df.copy()
    
    # Moving averages
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean() if len(df) >= 50 else df['sma20']
    df['ema12'] = df['close'].ewm(span=12).mean()
    df['ema26'] = df['close'].ewm(span=26).mean()
    
    latest = df.iloc[-1]
    
    # 1. Trend Direction (30 points)
    if latest['close'] > latest['sma20'] > latest['sma50']:
        score += 30  # Strong uptrend
    elif latest['close'] > latest['sma20']:
        score += 20  # Uptrend
    elif latest['close'] < latest['sma20'] < latest['sma50']:
        score += 30  # Strong downtrend (for SHORT)
    elif latest['close'] < latest['sma20']:
        score += 20  # Downtrend (for SHORT)
    
    # 2. Momentum (25 points)
    macd = latest['ema12'] - latest['ema26']
    macd_signal = df['ema12'].iloc[-9:].ewm(span=9).mean().iloc[-1] - df['ema26'].iloc[-9:].ewm(span=9).mean().iloc[-1]
    
    if macd > macd_signal and macd > 0:
        score += 25  # Strong bullish momentum
    elif macd > macd_signal:
        score += 15  # Bullish momentum
    elif macd < macd_signal and macd < 0:
        score += 25  # Strong bearish momentum (for SHORT)
    elif macd < macd_signal:
        score += 15  # Bearish momentum (for SHORT)
    
    # 3. Volume Confirmation (20 points)
    df['volume_sma20'] = df['volume'].rolling(20).mean()
    volume_ratio = latest['volume'] / latest['volume_sma20']
    
    if volume_ratio > 1.5:
        score += 20  # Strong volume
    elif volume_ratio > 1.2:
        score += 15  # Above average
    elif volume_ratio > 1.0:
        score += 10  # Average
    
    # 4. Structure Quality (25 points)
    # Check for HH/HL (uptrend) or LL/LH (downtrend)
    structure_score = analyze_structure(df)
    score += structure_score * 0.25
    
    return min(100.0, max(0.0, score))

def analyze_structure(df: pd.DataFrame, lookback: int = 10) -> float:
    """
    Analyze market structure (HH/HL or LL/LH)
    
    Returns:
        Score 0-100 based on structure quality
    """
    if len(df) < lookback:
        return 0.0
    
    recent = df.tail(lookback)
    
    # Find swing highs and lows
    highs = []
    lows = []
    
    for i in range(1, len(recent) - 1):
        # Swing high: higher than neighbors
        if recent['high'].iloc[i] > recent['high'].iloc[i-1] and recent['high'].iloc[i] > recent['high'].iloc[i+1]:
            highs.append(recent['high'].iloc[i])
        
        # Swing low: lower than neighbors
        if recent['low'].iloc[i] < recent['low'].iloc[i-1] and recent['low'].iloc[i] < recent['low'].iloc[i+1]:
            lows.append(recent['low'].iloc[i])
    
    if len(highs) < 2 or len(lows) < 2:
        return 50.0  # Insufficient data
    
    # Check for HH/HL (uptrend)
    hh_count = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
    hl_count = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
    
    uptrend_score = ((hh_count + hl_count) / (len(highs) + len(lows) - 2)) * 100
    
    # Check for LL/LH (downtrend)
    ll_count = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
    lh_count = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])
    
    downtrend_score = ((ll_count + lh_count) / (len(highs) + len(lows) - 2)) * 100
    
    # Return higher score (works for both LONG and SHORT)
    return max(uptrend_score, downtrend_score)

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from data_collection.yfinance_fetcher import fetcher
    
    async def test():
        symbol = 'AAPL'
        
        print(f"\n📊 Testing Velez engine for {symbol}...")
        
        # Get multi-timeframe data
        data = await fetcher.get_multiple_timeframes([symbol])
        
        if symbol not in data:
            print("Failed to get data")
            return
        
        scores = calculate_velez_score(
            weekly_df=data[symbol]['weekly'],
            daily_df=data[symbol]['daily'],
            four_hour_df=data[symbol]['four_hour'],
            one_hour_df=data[symbol]['one_hour']
        )
        
        print(f"\n✅ Velez Scores:")
        print(f"   Weekly:   {scores['weekly']:.1f}")
        print(f"   Daily:    {scores['daily']:.1f}")
        print(f"   4-Hour:   {scores['four_hour']:.1f}")
        print(f"   1-Hour:   {scores['one_hour']:.1f}")
        print(f"   ─────────────────────")
        print(f"   COMPOSITE: {scores['composite']:.1f}")
    
    asyncio.run(test())


# === MERGED FROM LEGACY elite_scoring_engine.py ===

def calculate_elite_score(ticker, price, volume, change, composite_score, direction='long'):
    """
    Calculate elite score for a stock.
    
    Args:
        ticker (str): Stock ticker
        price (float): Stock price
        volume (int): Trading volume
        change (float): Percent change
        composite_score (float): Pre-calculated composite score
        direction (str): 'long' or 'short'
    
    Returns:
        dict: Score data with elite_score
    """
    try:
        # Validate inputs
        if price <= 0 or volume <= 0:
            return {'elite_score': 0, 'finviz_boost': 0}
        
        # Base score from composite
        base_score = composite_score
        
        # Add momentum bonus
        momentum_bonus = min(abs(change) * 2, 10)
        
        # Add liquidity bonus
        liquidity = price * volume
        liquidity_bonus = min(liquidity / 10_000_000, 5)
        
        # Calculate elite score
        elite_score = base_score + momentum_bonus + liquidity_bonus
        
        # Finviz boost (placeholder - no actual validation in simplified version)
        finviz_boost = FINVIZ_SCORE_BOOST if AUTO_FINVIZ_VALIDATE else 0
        elite_score += finviz_boost
        
        # Cap at 100
        elite_score = min(elite_score, 100)
        
        return {
            'elite_score': round(elite_score, 2),
            'finviz_boost': finviz_boost,
            'base_score': round(base_score, 2),
            'momentum_bonus': round(momentum_bonus, 2),
            'liquidity_bonus': round(liquidity_bonus, 2)
        }
        
    except Exception as e:
        return {'elite_score': 0, 'finviz_boost': 0, 'error': str(e)}

def calculate_composite_score(stock_data, direction='long'):
    """Legacy compatibility function"""
    return calculate_elite_score(
        ticker=stock_data.get('Ticker', 'UNKNOWN'),
        price=stock_data.get('Price', 0),
        volume=stock_data.get('Volume', 0),
        change=stock_data.get('Change', 0),
        composite_score=stock_data.get('composite_score', 0),
        direction=direction
    )





def calculate_composite_score(stock_data, direction='long'):
    """Legacy compatibility function"""
    return calculate_elite_score(
        ticker=stock_data.get('Ticker', 'UNKNOWN'),
        price=stock_data.get('Price', 0),
        volume=stock_data.get('Volume', 0),
        change=stock_data.get('Change', 0),
        composite_score=stock_data.get('composite_score', 0),
        direction=direction
    )





