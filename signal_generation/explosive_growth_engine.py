"""
Explosive Growth Engine
Your 6-criteria system for identifying explosive stocks
"""

import pandas as pd
from typing import Dict, Tuple

from core.logger import get_logger

logger = get_logger(__name__)

def check_explosive_growth(df: pd.DataFrame) -> Tuple[bool, int, Dict]:
    """
    Check all 6 explosive growth criteria
    
    Returns:
        (is_explosive, criteria_met, details)
    """
    if len(df) < 50:
        return False, 0, {}
    
    criteria_met = 0
    details = {}
    
    df = df.copy()
    latest = df.iloc[-1]
    
    # Criterion 1: Strong recent momentum
    df['returns_5d'] = df['close'].pct_change(5)
    if latest['returns_5d'] > 0.05:  # >5% in 5 days
        criteria_met += 1
        details['momentum'] = True
    
    # Criterion 2: Volume expansion
    df['volume_sma20'] = df['volume'].rolling(20).mean()
    volume_ratio = latest['volume'] / latest['volume_sma20']
    if volume_ratio > 1.5:
        criteria_met += 1
        details['volume'] = True
    
    # Criterion 3: Above key moving averages
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    if latest['close'] > latest['sma20'] > latest['sma50']:
        criteria_met += 1
        details['trend'] = True
    
    # Criterion 4: Relative strength
    df['rsi'] = calculate_rsi(df['close'], 14)
    if latest['rsi'] > 60 and latest['rsi'] < 80:
        criteria_met += 1
        details['rsi'] = True
    
    # Criterion 5: Consolidation before breakout
    df['volatility'] = df['close'].rolling(10).std()
    recent_vol = df['volatility'].iloc[-10:].mean()
    prior_vol = df['volatility'].iloc[-30:-10].mean()
    if recent_vol < prior_vol * 0.8:  # Lower vol before breakout
        criteria_met += 1
        details['consolidation'] = True
    
    # Criterion 6: Institutional buying
    # (Proxy: Large volume bars with price up)
    large_vol_bars = df[df['volume'] > df['volume_sma20'] * 2]
    large_vol_up = large_vol_bars[large_vol_bars['close'] > large_vol_bars['open']]
    if len(large_vol_up) >= 3:  # At least 3 in dataset
        criteria_met += 1
        details['institutional'] = True
    
    is_explosive = criteria_met >= 4  # Need 4/6
    
    return is_explosive, criteria_met, details

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
