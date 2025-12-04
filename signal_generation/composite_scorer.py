"""
Composite Scorer - Combines all indicators with ML-optimized weights
Final scoring before presenting to user
"""

import pandas as pd
from typing import List, Dict
import yaml
from pathlib import Path

from core.logger import get_logger
from signal_generation.velez_engine import calculate_velez_score
from signal_generation.explosive_growth_engine import check_explosive_growth
from data_collection.yfinance_fetcher import fetcher

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

async def score_candidates(ignitions: List[Dict]) -> List[Dict]:
    """
    Calculate composite scores for all candidates
    
    Combines (from config.yaml):
    - Velez: 30%
    - Explosive Growth: 20%
    - Compression: 15%
    - Dark Pool: 10%
    - Options Flow: 10%
    - Sector Strength: 10%
    - ML Probability: 5%
    
    Args:
        ignitions: List from ignition detector
    
    Returns:
        List of scored signals, sorted by composite score
    """
    logger.info(f"🔍 Stage 4: Scoring {len(ignitions)} candidates...")
    
    # Get multi-timeframe data for Velez
    symbols = [item['symbol'] for item in ignitions]
    multi_tf_data = await fetcher.get_multiple_timeframes(symbols)
    
    signals = []
    
    for item in ignitions:
        symbol = item['symbol']
        
        try:
            # Get multi-TF data
            if symbol not in multi_tf_data:
                logger.debug(f"Skipping {symbol}: no multi-TF data")
                continue
            
            tf_data = multi_tf_data[symbol]
            
            # Calculate Velez score
            velez_scores = calculate_velez_score(
                weekly_df=tf_data.get('weekly', pd.DataFrame()),
                daily_df=tf_data.get('daily', pd.DataFrame()),
                four_hour_df=tf_data.get('four_hour', pd.DataFrame()),
                one_hour_df=tf_data.get('one_hour', pd.DataFrame())
            )
            
            # Check Explosive Growth
            daily_df = tf_data.get('daily', pd.DataFrame())
            is_explosive, explosive_criteria_met, explosive_details = check_explosive_growth(daily_df)
            
            # Calculate compression score
            compression_score = calculate_compression_score(item)
            
            # Get dark pool / options flow scores (if available)
            whale_score = calculate_whale_score(item.get('whale_data'))
            
            # Sector strength (placeholder - would integrate with market data)
            sector_score = 50.0  # Neutral
            
            # ML probability (placeholder - would use trained model)
            ml_prob = 0.70  # 70% predicted win rate
            
            # Calculate composite score
            composite = calculate_composite_score(
                velez_composite=velez_scores['composite'],
                explosive_signal=is_explosive,
                compression_score=compression_score,
                whale_score=whale_score,
                sector_score=sector_score,
                ml_prob=ml_prob
            )
            
            # Determine direction (LONG or SHORT based on structure)
            direction = determine_direction(velez_scores, item)
            
            # Calculate entry/stop/target
            entry_price = item['price']
            stop_price, target_price = calculate_entry_stop_target(
                entry_price=entry_price,
                direction=direction,
                daily_df=daily_df
            )
            
            # Create signal
            signal = {
                'symbol': symbol,
                'direction': direction,
                'score': composite,
                'velez_score': velez_scores,
                'explosive_signal': is_explosive,
                'explosive_criteria_met': explosive_criteria_met,
                'explosive_details': explosive_details,
                'compression_days': item['compression_days'],
                'fresh_ignition': {
                    'volume_ratio': item['volume_ratio'],
                    'move_pct': item['move_pct'],
                    'minutes_since_breakout': item['minutes_since_breakout']
                },
                'whale_data': item.get('whale_data'),
                'entry_price': entry_price,
                'stop_price': stop_price,
                'target_price': target_price,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error scoring {symbol}: {e}")
            continue
    
    # Sort by composite score
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    # Split into LONG and SHORT
    long_signals = [s for s in signals if s['direction'] == 'LONG'][:20]
    short_signals = [s for s in signals if s['direction'] == 'SHORT'][:20]
    
    final_signals = long_signals + short_signals
    
    logger.info(f"✅ Stage 4: {len(long_signals)} LONG + {len(short_signals)} SHORT signals")
    
    return final_signals

def calculate_composite_score(
    velez_composite: float,
    explosive_signal: bool,
    compression_score: float,
    whale_score: float,
    sector_score: float,
    ml_prob: float
) -> float:
    """
    Calculate weighted composite score
    Uses weights from config.yaml (AI can adjust these)
    """
    weights = config['scoring']['weights']
    
    # Convert explosive to 0-100
    explosive_score = 100.0 if explosive_signal else 0.0
    
    # Weighted sum
    composite = (
        velez_composite * weights['velez'] +
        explosive_score * weights['explosive'] +
        compression_score * weights['compression'] +
        whale_score * weights['dark_pool'] +
        whale_score * weights['options_flow'] +  # Using same for now
        sector_score * weights['sector_strength'] +
        (ml_prob * 100) * weights['ml_probability']
    )
    
    return min(100.0, max(0.0, composite))

def calculate_compression_score(item: Dict) -> float:
    """
    Convert compression metrics to 0-100 score
    """
    days = item['compression_days']
    volume_ratio = item.get('volume_ratio', 1.0)
    
    # More compression days = higher score
    days_score = min(100, days * 10)  # 10 days = 100 score
    
    # Lower volume during compression = higher score
    volume_score = (1.0 - min(1.0, volume_ratio)) * 100
    
    return (days_score + volume_score) / 2

def calculate_whale_score(whale_data: Dict) -> float:
    """
    Convert Unusual Whales data to 0-100 score
    """
    if not whale_data:
        return 50.0  # Neutral if no data
    
    sentiment = whale_data.get('sentiment', 'NEUTRAL')
    premium = whale_data.get('total_premium', 0)
    
    # Base score on sentiment
    if sentiment == 'BULLISH':
        score = 75.0
    elif sentiment == 'BEARISH':
        score = 75.0  # Also good for SHORT signals
    else:
        score = 50.0
    
    # Boost based on premium size
    if premium > 10_000_000:  # $10M+
        score += 15
    elif premium > 5_000_000:  # $5M+
        score += 10
    elif premium > 1_000_000:  # $1M+
        score += 5
    
    return min(100.0, score)

def determine_direction(velez_scores: Dict, item: Dict) -> str:
    """
    Determine if signal is LONG or SHORT based on structure
    """
    composite = velez_scores['composite']
    daily_score = velez_scores['daily']
    
    # For now, assume LONG if composite > 50
    # In production, would analyze structure (HH/HL vs LL/LH)
    return 'LONG' if composite >= 50 else 'SHORT'

def calculate_entry_stop_target(
    entry_price: float,
    direction: str,
    daily_df: pd.DataFrame
) -> tuple:
    """
    Calculate stop loss and target prices
    
    Returns:
        (stop_price, target_price)
    """
    if len(daily_df) < 14:
        # Fallback to simple percentage
        if direction == 'LONG':
            stop = entry_price * 0.97  # -3%
            target = entry_price * 1.06  # +6% (2:1 R/R)
        else:
            stop = entry_price * 1.03  # +3%
            target = entry_price * 0.94  # -6%
        
        return stop, target
    
    # Calculate ATR
    df = daily_df.copy()
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    
    # Get ATR multiplier from config
    cfg = config['risk']
    multiplier = cfg['atr_multiplier_momentum']
    
    if direction == 'LONG':
        stop = entry_price - (atr * multiplier)
        target = entry_price + (atr * multiplier * 2)  # 2:1 R/R
    else:
        stop = entry_price + (atr * multiplier)
        target = entry_price - (atr * multiplier * 2)
    
    return stop, target

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Create mock ignition data
        mock_ignitions = [{
            'symbol': 'AAPL',
            'compression_days': 5,
            'price': 180.0,
            'volume_ratio': 1.8,
            'move_pct': 2.1,
            'minutes_since_breakout': 25
        }]
        
        print("\n📊 Testing composite scorer...")
        signals = await score_candidates(mock_ignitions)
        
        if signals:
            print(f"\n✅ Scored {len(signals)} signals:")
            for signal in signals:
                print(f"\n{signal['symbol']} ({signal['direction']}):")
                print(f"  Composite Score: {signal['score']:.1f}")
                print(f"  Velez: {signal['velez_score']['composite']:.1f}")
                print(f"  Explosive: {signal['explosive_signal']}")
                print(f"  Entry: ${signal['entry_price']:.2f}")
                print(f"  Stop: ${signal['stop_price']:.2f}")
                print(f"  Target: ${signal['target_price']:.2f}")
    
    asyncio.run(test())

