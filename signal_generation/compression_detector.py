"""
Compression Detector - Stage 2
Finds stocks that are "coiling" before a breakout (500 → 100)
"""

import pandas as pd
import numpy as np
from typing import List, Dict
import yaml
from pathlib import Path

from core.logger import get_logger
from data_collection.yfinance_fetcher import get_data

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

async def detect_compression(symbols: List[str]) -> List[Dict]:
    """
    Detect compression in symbols
    
    Compression criteria (from your Bible):
    1. ATR squeeze: Bollinger Bands narrowing (<1.5% width)
    2. Volume decline: Below 80% of average for 3+ days
    3. Near 20 SMA: Within 3% of moving average
    4. Dark pool activity: 5+ blocks in last 7 days
    
    Args:
        symbols: List of stock tickers
    
    Returns:
        List of dictionaries with compression data
    """
    logger.info(f"🔍 Stage 2: Checking compression for {len(symbols)} symbols...")
    
    # Get daily data for all symbols
    data_dict = await get_data(symbols, period='3mo', interval='1d')
    
    compressed = []
    
    for symbol, df in data_dict.items():
        if df is None or len(df) < 30:
            continue
        
        try:
            # Calculate indicators
            df = calculate_compression_indicators(df)
            
            # Get latest values
            latest = df.iloc[-1]
            
            # Check compression criteria
            is_compressed = check_compression_criteria(df, latest)
            
            if is_compressed:
                compressed.append({
                    'symbol': symbol,
                    'compression_days': int(latest['compression_days']),
                    'atr_squeeze_pct': float(latest['bb_width_pct']),
                    'volume_ratio': float(latest['volume_ratio']),
                    'distance_to_sma20_pct': float(latest['distance_to_sma20_pct']),
                    'price': float(latest['close']),
                    'data': df  # Keep for next stage
                })
        
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            continue
    
    logger.info(f"✅ Stage 2: {len(compressed)} compressed symbols found")
    
    return compressed

def calculate_compression_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate compression indicators
    
    Args:
        df: OHLCV dataframe
    
    Returns:
        DataFrame with additional indicator columns
    """
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Bollinger Bands
    df['sma20'] = df['close'].rolling(20).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['sma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['sma20'] - (df['std20'] * 2)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    df['bb_width_pct'] = (df['bb_width'] / df['close']) * 100
    
    # Volume ratio
    df['volume_sma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma20']
    
    # Distance to SMA20
    df['distance_to_sma20_pct'] = ((df['close'] - df['sma20']) / df['sma20']) * 100
    
    # Compression days counter
    squeeze_threshold = config['compression']['atr_squeeze_threshold']
    volume_threshold = config['compression']['volume_decline_threshold']
    
    df['is_compressed'] = (
        (df['bb_width_pct'] < squeeze_threshold * 100) &
        (df['volume_ratio'] < volume_threshold)
    )
    
    # Count consecutive compression days
    df['compression_days'] = 0
    compression_counter = 0
    for i in range(len(df)):
        if df['is_compressed'].iloc[i]:
            compression_counter += 1
        else:
            compression_counter = 0
        df.loc[df.index[i], 'compression_days'] = compression_counter
    
    return df

def check_compression_criteria(df: pd.DataFrame, latest: pd.Series) -> bool:
    """
    Check if symbol meets compression criteria
    
    Args:
        df: Full dataframe with indicators
        latest: Latest row (Series)
    
    Returns:
        True if compressed, False otherwise
    """
    cfg = config['compression']
    
    # Criterion 1: ATR squeeze
    if latest['bb_width_pct'] > cfg['atr_squeeze_threshold'] * 100:
        return False
    
    # Criterion 2: Volume decline for min days
    if latest['compression_days'] < cfg['min_squeeze_days']:
        return False
    
    # Criterion 3: Near 20 SMA
    if abs(latest['distance_to_sma20_pct']) > cfg['distance_to_sma20_max_pct']:
        return False
    
    # Criterion 4: Dark pool activity
    # TODO: Integrate with Unusual Whales data
    # For now, we'll skip this check
    
    return True

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Test with a few symbols
        symbols = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'META', 'AMD', 'MSFT', 'AMZN']
        
        print("\n🔍 Testing compression detector...")
        compressed = await detect_compression(symbols)
        
        print(f"\n✅ Found {len(compressed)} compressed symbols:")
        for item in compressed:
            print(f"\n{item['symbol']}:")
            print(f"  Compression days: {item['compression_days']}")
            print(f"  BB width: {item['atr_squeeze_pct']:.2f}%")
            print(f"  Volume ratio: {item['volume_ratio']:.2f}")
            print(f"  Distance to SMA20: {item['distance_to_sma20_pct']:.2f}%")
    
    asyncio.run(test())
