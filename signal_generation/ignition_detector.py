"""
Ignition Detector - Stage 3
Detects "fresh" breakouts (not stale) (100 → 40)
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
import yaml
from pathlib import Path

from core.logger import get_logger
from data_collection.yfinance_fetcher import fetcher

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

async def detect_ignitions(compressed_symbols: List[Dict]) -> List[Dict]:
    """
    Detect fresh ignitions (breakouts that just happened)
    
    Fresh Ignition criteria (from your Bible):
    1. Volume surge: 150-250% of average (not climax)
    2. Move percentage: 1-3% (not too stretched)
    3. Time since breakout: <30 minutes (fresh!)
    4. No big gap: <3% gap from prior close
    5. MACD/Williams turning positive in last 3 bars
    
    Args:
        compressed_symbols: List from compression detector
    
    Returns:
        List of fresh ignition signals
    """
    logger.info(f"🔍 Stage 3: Checking ignitions for {len(compressed_symbols)} symbols...")
    
    # Get intraday data (1-hour bars for the last month)
    symbols = [s['symbol'] for s in compressed_symbols]
    intraday_data = await fetcher.fetch_data_for_symbols(symbols, period='1mo', interval='1h')
    
    ignitions = []
    
    for item in compressed_symbols:
        symbol = item['symbol']
        
        if symbol not in intraday_data:
            continue
        
        try:
            df = intraday_data[symbol]
            if len(df) < 30:
                continue
            
            # Calculate ignition indicators
            df = calculate_ignition_indicators(df)
            
            # Check if fresh ignition
            latest = df.iloc[-1]
            is_ignition = check_ignition_criteria(df, latest)
            
            if is_ignition:
                ignition_data = {
                    'symbol': symbol,
                    'compression_days': item['compression_days'],
                    'price': float(latest['close']),
                    'volume_ratio': float(latest['volume_ratio']),
                    'move_pct': float(latest['move_pct']),
                    'gap_pct': float(latest['gap_pct']),
                    'minutes_since_breakout': calculate_minutes_since_breakout(df),
                    'macd_signal': 'BULLISH' if latest['macd'] > latest['macd_signal'] else 'BEARISH',
                    'williams_r': float(latest['williams_r']),
                    'daily_data': item['data'],  # Keep daily data
                    'intraday_data': df  # Keep intraday data
                }
                
                ignitions.append(ignition_data)
        
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            continue
    
    logger.info(f"✅ Stage 3: {len(ignitions)} fresh ignitions found")
    
    return ignitions

def calculate_ignition_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate ignition-specific indicators"""
    
    # Volume ratio (vs 20-period average)
    df['volume_sma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma20']
    
    # Move percentage (from open to close)
    df['move_pct'] = ((df['close'] - df['open']) / df['open']) * 100
    
    # Gap percentage (from prior close)
    df['gap_pct'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1)) * 100
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Williams %R
    high_14 = df['high'].rolling(14).max()
    low_14 = df['low'].rolling(14).min()
    df['williams_r'] = ((high_14 - df['close']) / (high_14 - low_14)) * -100
    
    return df

def check_ignition_criteria(df: pd.DataFrame, latest: pd.Series) -> bool:
    """Check if symbol meets fresh ignition criteria"""
    
    cfg = config['ignition']
    style = config['user_preferences']['trading_style']
    fresh_cfg = config['user_preferences']['fresh_ignition']
    
    # Get style-specific thresholds
    max_move = fresh_cfg['max_move_pct'][style]
    max_time = fresh_cfg['max_time_since_breakout_min'][style]
    max_vol_ratio = fresh_cfg['max_volume_ratio'][style]
    
    # Criterion 1: Volume surge (150-250% for balanced)
    if latest['volume_ratio'] < cfg['min_volume_ratio']:
        return False
    if latest['volume_ratio'] > max_vol_ratio:
        return False  # Too climactic
    
    # Criterion 2: Move percentage (1-3% for balanced)
    move_abs = abs(latest['move_pct'])
    if move_abs < cfg['min_move_pct']:
        return False
    if move_abs > max_move:
        return False  # Too stretched
    
    # Criterion 3: Gap check (<3%)
    if abs(latest['gap_pct']) > cfg['max_gap_pct']:
        return False
    
    # Criterion 4: MACD turning positive (last 3 bars)
    macd_recent = df['macd_hist'].iloc[-3:].values
    if not any(macd_recent > 0):
        return False
    
    # Criterion 5: Williams %R turning up
    williams_recent = df['williams_r'].iloc[-3:].values
    if not any(williams_recent > -80):  # Coming out of oversold
        return False
    
    return True

def calculate_minutes_since_breakout(df: pd.DataFrame) -> int:
    """
    Calculate approximate minutes since breakout
    
    For hourly data, this is an approximation.
    In production, you'd want 5-min or 1-min data.
    """
    # Find the bar where volume first spiked
    df['volume_spike'] = df['volume_ratio'] > 1.5
    
    # Get most recent spike
    spike_bars = df[df['volume_spike']].tail(3)
    
    if spike_bars.empty:
        return 999  # No recent spike
    
    # Count bars since most recent spike
    last_spike_idx = spike_bars.index[-1]
    bars_since = len(df) - df.index.get_loc(last_spike_idx) - 1
    
    # Convert to minutes (assuming 1-hour bars)
    minutes_since = bars_since * 60
    
    return minutes_since

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # First need compressed symbols
        from signal_generation.compression_detector import detect_compression
        
        symbols = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'META', 'AMD', 'MSFT', 'AMZN']
        
        print("\n🔍 Step 1: Finding compressed symbols...")
        compressed = await detect_compression(symbols)
        print(f"   Found {len(compressed)} compressed")
        
        if compressed:
            print("\n🔍 Step 2: Checking for fresh ignitions...")
            ignitions = await detect_ignitions(compressed)
            
            print(f"\n✅ Found {len(ignitions)} fresh ignitions:")
            for item in ignitions:
                print(f"\n{item['symbol']}:")
                print(f"  Volume ratio: {item['volume_ratio']:.2f}x")
                print(f"  Move: {item['move_pct']:.2f}%")
                print(f"  Gap: {item['gap_pct']:.2f}%")
                print(f"  Minutes since breakout: {item['minutes_since_breakout']}")
                print(f"  MACD: {item['macd_signal']}")
    
    asyncio.run(test())
