"""
elite_scanner_engine.py - Enhanced Core Scanning Logic
PRODUCTION VERSION - November 25, 2025 (UPDATED)

COMPLETE FIXES:
✅ Removed SMA20 price restriction for LONG (catches more signals)
✅ Relaxed FADE_LONG filters (RSI 40, Gap 1.5%, Vol 1.2x, ADX 12)
✅ Relaxed ROLLOVER_LONG filters (52W 20%, RSI 30-70, ADX 15)
✅ Fixed ROLLOVER scoring (separate logic from FADE)
✅ Fixed CUBE volume bug (1.2x minimum for ROLLOVER)
✅ Fixed SHORT filters (relaxed for transition markets)

ACADEMIC BASIS:
- De Bondt & Thaler (1985): Mean reversion in oversold/overbought
- Balvers & Wu (2006): Momentum and mean reversion dynamics
- Chordia & Subrahmanyam (2004): Volume and liquidity factors
- Cederholm & O'Doherty (2010): 52-week high/low effects
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import numpy as np

import config
from data_models import MarketData, TradingSignal
from resources import YFinanceAPI

logger = logging.getLogger(__name__)


class ExplosiveMoveScanner:
    """
    Enhanced scanning engine for fade and rollover opportunities
    Optimized for transition markets (bull/bear pullbacks)
    """
    
    def __init__(self):
        self.yfinance = YFinanceAPI()
        logger.info("ExplosiveMoveScanner initialized (Transition Mode)")
    
    def scan_symbols(self, symbols: List[str], direction: str) -> List[TradingSignal]:
        """Scan multiple symbols and return qualified signals"""
        logger.info(f"Scanning {len(symbols)} symbols for {direction} setups...")
        
        signals = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {
                executor.submit(self.analyze_symbol, symbol, direction): symbol 
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    signal = future.result()
                    if signal:
                        signals.append(signal)
                        logger.debug(f"{symbol}: {signal.setup_type} detected")
                except Exception as e:
                    logger.debug(f"{symbol}: {e}")
        
        logger.info(f"Found {len(signals)} qualified {direction} signals")
        return signals
    
    def analyze_symbol(self, symbol: str, direction: str) -> Optional[TradingSignal]:
        """Analyze single symbol for fade/rollover opportunities"""
        try:
            data = self.yfinance.fetch_market_data(symbol, period=config.HISTORY_PERIOD)
            if not data or data.history.empty:
                return None
            
            indicators = self.calculate_indicators(data)
            if not indicators:
                return None
            
            setup_type = self.classify_setup(indicators, direction)
            if not setup_type:
                return None
            
            if not self.validate_filters(indicators, setup_type):
                return None
            
            signal = self.create_signal(symbol, indicators, setup_type, direction)
            return signal
            
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None
    
    def calculate_indicators(self, data: MarketData) -> Optional[Dict[str, Any]]:
        """Calculate all technical indicators"""
        try:
            hist = data.history
            if len(hist) < 50:
                return None
            
            close = hist['Close']
            high = hist['High']
            low = hist['Low']
            volume = hist['Volume']
            
            last_price = close.iloc[-1]
            prev_close = close.iloc[-2]
            
            sma20 = close.rolling(window=config.SMA_SHORT).mean().iloc[-1]
            sma50 = close.rolling(window=config.SMA_MID).mean().iloc[-1]
            sma200 = close.rolling(window=config.SMA_LONG).mean().iloc[-1] if len(close) >= 200 else None
            
            rsi = self.calculate_rsi(close.values, config.RSI_PERIOD)
            adx = self.calculate_adx(high.values, low.values, close.values, config.ADX_PERIOD)
            
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            relative_volume = current_volume / avg_volume if avg_volume > 0 else 0
            
            high_52w = close.rolling(window=252).max().iloc[-1] if len(close) >= 252 else close.max()
            low_52w = close.rolling(window=252).min().iloc[-1] if len(close) >= 252 else close.min()
            
            proximity_to_high = last_price / high_52w if high_52w > 0 else 0
            proximity_to_low = last_price / low_52w if low_52w > 0 else 0
            
            if len(close) >= 2:
                try:
                    today_open = hist['Open'].iloc[-1]
                    gap_percent = ((today_open / prev_close) - 1) * 100
                except:
                    gap_percent = 0
            else:
                gap_percent = 0
            
            day_change = ((last_price / prev_close) - 1) * 100 if prev_close > 0 else 0
            week_change = ((last_price / close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
            
            sma20_prev = close.rolling(window=config.SMA_SHORT).mean().iloc[-2]
            crossed_above_sma20 = close.iloc[-2] < sma20_prev and last_price > sma20
            crossed_below_sma20 = close.iloc[-2] > sma20_prev and last_price < sma20
            
            try:
                short_interest = data.info.get('shortPercentOfFloat', 0) * 100
            except:
                short_interest = 0
            
            return {
                'last_price': last_price,
                'prev_close': prev_close,
                'sma20': sma20,
                'sma50': sma50,
                'sma200': sma200,
                'rsi': rsi,
                'adx': adx,
                'relative_volume': relative_volume,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'proximity_to_high': proximity_to_high,
                'proximity_to_low': proximity_to_low,
                'gap_percent': gap_percent,
                'day_change': day_change,
                'week_change': week_change,
                'crossed_above_sma20': crossed_above_sma20,
                'crossed_below_sma20': crossed_below_sma20,
                'short_interest': short_interest,
                'avg_volume': avg_volume,
            }
            
        except Exception as e:
            logger.debug(f"Error calculating indicators: {e}")
            return None
    
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum() / period
            down = -seed[seed < 0].sum() / period
            if down == 0:
                return 100.0
            rs = up / down
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return float(rsi)
        except:
            return 50.0
    
    def calculate_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """Calculate ADX indicator"""
        try:
            tr = np.maximum(high - low, np.maximum(abs(high - np.roll(close, 1)), abs(low - np.roll(close, 1))))
            atr = np.mean(tr[-period:])
            if atr == 0:
                return 0.0
            up_move = high - np.roll(high, 1)
            down_move = np.roll(low, 1) - low
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            plus_di = 100 * (np.mean(plus_dm[-period:]) / atr)
            minus_di = 100 * (np.mean(minus_dm[-period:]) / atr)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
            return float(dx)
        except:
            return 0.0
    
    def classify_setup(self, indicators: Dict[str, Any], direction: str) -> Optional[str]:
        """Classify the setup type based on indicators - UPDATED: Removed SMA20 price restriction"""
        rsi = indicators['rsi']
        gap = indicators['gap_percent']
        prox_high = indicators['proximity_to_high']
        prox_low = indicators['proximity_to_low']
        week_perf = indicators['week_change']
        day_perf = indicators['day_change']
        crossed_above = indicators['crossed_above_sma20']
        crossed_below = indicators['crossed_below_sma20']
        
        if direction == 'LONG':
            # FADE LONG: Oversold bounce - REMOVED SMA20 restriction
            is_fade = (
                rsi < config.FADE_LONG_RSI_MAX and
                gap < -config.FADE_LONG_GAP_MIN and
                indicators['relative_volume'] >= config.FADE_LONG_VOLUME_MIN
            )
            
            # ROLLOVER LONG: Failed breakdown recovery
            is_rollover = (
                prox_low <= (1 + config.ROLLOVER_LONG_52WL_DIST) and
                config.ROLLOVER_LONG_RSI_MIN <= rsi <= config.ROLLOVER_LONG_RSI_MAX and
                crossed_above and
                indicators['adx'] >= config.ROLLOVER_LONG_ADX_MIN
            )
            
            if is_fade:
                return 'FADE_LONG'
            elif is_rollover:
                return 'ROLLOVER_LONG'
        elif direction == 'SHORT':
            is_fade = (
                rsi > config.FADE_SHORT_RSI_MIN and
                gap > config.FADE_SHORT_GAP_MIN and
                week_perf > config.FADE_SHORT_WEEK_PERF_MIN and
                day_perf > config.FADE_SHORT_DAY_PERF_MIN and
                indicators['relative_volume'] >= config.FADE_SHORT_VOLUME_MIN
            )
            is_rollover = (
                prox_high >= (1 - config.ROLLOVER_SHORT_52WH_DIST) and
                config.ROLLOVER_SHORT_RSI_MIN <= rsi <= config.ROLLOVER_SHORT_RSI_MAX and
                crossed_below and
                indicators['adx'] >= config.ROLLOVER_SHORT_ADX_MIN
            )
            if is_fade:
                return 'FADE_SHORT'
            elif is_rollover:
                return 'ROLLOVER_SHORT'
        return None
    
    def validate_filters(self, indicators: Dict[str, Any], setup_type: str) -> bool:
        """Validate signal against minimum filters"""
        if indicators['last_price'] < config.MIN_PRICE:
            return False
        if indicators['avg_volume'] < config.MIN_AVG_VOLUME:
            return False
        if indicators['relative_volume'] < 1.0:
            return False
        if 'FADE' in setup_type:
            if indicators['relative_volume'] < (config.FADE_LONG_VOLUME_MIN if 'LONG' in setup_type else config.FADE_SHORT_VOLUME_MIN):
                return False
            if indicators['adx'] < (config.FADE_LONG_ADX_MIN if 'LONG' in setup_type else config.FADE_SHORT_ADX_MIN):
                return False
        elif 'ROLLOVER' in setup_type:
            if indicators['relative_volume'] < 1.2:
                return False
            if indicators['adx'] < (config.ROLLOVER_LONG_ADX_MIN if 'LONG' in setup_type else config.ROLLOVER_SHORT_ADX_MIN):
                return False
        return True
    
    def create_signal(self, symbol: str, indicators: Dict[str, Any], setup_type: str, direction: str) -> TradingSignal:
        """Create TradingSignal object from indicators"""
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            setup_type=setup_type,
            last_price=indicators['last_price'],
            rsi=indicators['rsi'],
            adx=indicators['adx'],
            relative_volume=indicators['relative_volume'],
            gap_percent=indicators['gap_percent'],
            day_performance=indicators['day_change'],
            week_performance=indicators['week_change'],
            proximity_52w=indicators['proximity_to_high'] if direction == 'SHORT' else indicators['proximity_to_low'],
            sma20=indicators['sma20'],
            sma50=indicators['sma50'],
            sma200=indicators['sma200'],
            short_interest=indicators['short_interest'],
            composite_score=0.0
        )
class ReversalRankingEngine:
    """Academic-Enhanced Ranking Engine - FIXED SCORING"""
    
    def __init__(self):
        self.weights = {
            'rsi_extreme': 0.20,
            'gap_reversal': 0.20,
            '52wk_proximity': 0.15,
            'performance_reversal': 0.10,
            'breakdown_continuation': 0.10,
            'volume_surge': 0.15,
            'short_interest': 0.05,
            'adx_strength': 0.05,
        }
        logger.info("ReversalRankingEngine initialized (Academic-Enhanced):")
        for factor, weight in self.weights.items():
            logger.info(f"  {factor}: {weight*100:.2f}%")
    
    def rank_signals(self, signals: List[TradingSignal], direction: str) -> List[TradingSignal]:
        """Rank signals using composite scoring"""
        if not signals:
            return []
        for signal in signals:
            signal.composite_score = self._calculate_composite_score(signal, direction)
        return sorted(signals, key=lambda x: x.composite_score, reverse=True)
    
    def _calculate_composite_score(self, signal: TradingSignal, direction: str) -> float:
        """Calculate composite score (0-100) - FIXED: Different scoring for FADE vs ROLLOVER"""
        score = 0.0
        
        if direction == 'LONG':
            if 'FADE' in signal.setup_type:
                rsi_score = max(0, (30 - signal.rsi) / 30 * 100) if signal.rsi < 30 else 0
                gap_score = abs(signal.gap_percent) * 10 if signal.gap_percent < 0 else 0
                prox_score = (1 - signal.proximity_52w) * 50 if signal.proximity_52w < 1.2 else 0
                perf_score = abs(signal.week_performance) if signal.week_performance < 0 else 0
                breakdown_score = abs(signal.day_performance) if signal.day_performance < 0 else 0
                volume_score = min(100, (signal.relative_volume - 1) * 50)
                short_score = min(100, signal.short_interest * 5)
                adx_score = min(100, signal.adx * 2)
                
                score = (
                    self.weights['rsi_extreme'] * rsi_score +
                    self.weights['gap_reversal'] * gap_score +
                    self.weights['52wk_proximity'] * prox_score +
                    self.weights['performance_reversal'] * perf_score +
                    self.weights['breakdown_continuation'] * breakdown_score +
                    self.weights['volume_surge'] * volume_score +
                    self.weights['short_interest'] * short_score +
                    self.weights['adx_strength'] * adx_score
                )
            
            elif 'ROLLOVER' in signal.setup_type:
                rsi_score = 100 - abs(signal.rsi - 50) * 2 if 35 <= signal.rsi <= 65 else 0
                prox_score = (1 - signal.proximity_52w) * 100 if signal.proximity_52w < 1.15 else 0
                perf_score = abs(signal.week_performance) if signal.week_performance < 0 else 0
                volume_score = min(100, (signal.relative_volume - 1) * 50)
                short_score = min(100, signal.short_interest * 5)
                adx_score = min(100, signal.adx * 3)
                
                score = (
                    self.weights['rsi_extreme'] * rsi_score * 0.5 +
                    self.weights['52wk_proximity'] * prox_score * 2.0 +
                    self.weights['performance_reversal'] * perf_score +
                    self.weights['volume_surge'] * volume_score +
                    self.weights['short_interest'] * short_score +
                    self.weights['adx_strength'] * adx_score * 1.5
                )
        
        elif direction == 'SHORT':
            if 'FADE' in signal.setup_type:
                rsi_score = max(0, (signal.rsi - 70) / 30 * 100) if signal.rsi > 70 else 0
                gap_score = signal.gap_percent * 10 if signal.gap_percent > 0 else 0
                prox_score = (signal.proximity_52w - 0.85) * 100 if signal.proximity_52w > 0.85 else 0
                perf_score = signal.week_performance if signal.week_performance > 0 else 0
                breakdown_score = signal.day_performance if signal.day_performance > 0 else 0
                volume_score = min(100, (signal.relative_volume - 1) * 50)
                short_score = min(100, signal.short_interest * 5)
                adx_score = min(100, signal.adx * 2)
                
                score = (
                    self.weights['rsi_extreme'] * rsi_score +
                    self.weights['gap_reversal'] * gap_score +
                    self.weights['52wk_proximity'] * prox_score +
                    self.weights['performance_reversal'] * perf_score +
                    self.weights['breakdown_continuation'] * breakdown_score +
                    self.weights['volume_surge'] * volume_score +
                    self.weights['short_interest'] * short_score +
                    self.weights['adx_strength'] * adx_score
                )
            
            elif 'ROLLOVER' in signal.setup_type:
                rsi_score = 100 - abs(signal.rsi - 50) * 2 if 35 <= signal.rsi <= 65 else 0
                prox_score = (signal.proximity_52w - 0.85) * 100 if signal.proximity_52w > 0.85 else 0
                perf_score = signal.week_performance if signal.week_performance > 0 else 0
                volume_score = min(100, (signal.relative_volume - 1) * 50)
                short_score = min(100, signal.short_interest * 5)
                adx_score = min(100, signal.adx * 3)
                
                score = (
                    self.weights['rsi_extreme'] * rsi_score * 0.5 +
                    self.weights['52wk_proximity'] * prox_score * 2.0 +
                    self.weights['performance_reversal'] * perf_score +
                    self.weights['volume_surge'] * volume_score +
                    self.weights['short_interest'] * short_score +
                    self.weights['adx_strength'] * adx_score * 1.5
                )
        
        return min(100, max(0, score))


def merge_and_deduplicate(signals: List[TradingSignal]) -> List[TradingSignal]:
    """Merge signals from multiple scans and remove duplicates"""
    seen = {}
    for signal in signals:
        if signal.symbol not in seen or signal.composite_score > seen[signal.symbol].composite_score:
            seen[signal.symbol] = signal
    return list(seen.values())


def filter_by_regime(signals: List[TradingSignal], regime: Dict[str, Any]) -> List[TradingSignal]:
    """Filter signals based on market regime"""
    regime_type = regime['regime']
    if regime_type == 'TRANSITION':
        return signals
    elif regime_type in ['STRONG_BULL', 'WEAK_BULL']:
        if signals and signals[0].direction == 'SHORT':
            return [s for s in signals if s.composite_score >= 70]
        return signals
    elif regime_type in ['STRONG_BEAR', 'WEAK_BEAR']:
        if signals and signals[0].direction == 'LONG':
            return [s for s in signals if s.composite_score >= 70]
        return signals
    return signals


def calculate_position_size(signal: TradingSignal, regime: Dict[str, Any], base_size: float = 200.0) -> float:
    """Calculate position size based on signal quality and regime"""
    position = base_size
    if signal.composite_score > 80:
        position *= 1.5
    elif signal.composite_score < 50:
        position *= 0.75
    if regime['confidence'] > 80:
        position *= 1.2
    elif regime['confidence'] < 60:
        position *= 0.8
    if regime['vix'] > 30:
        position *= 0.7
    elif regime['vix'] < 15:
        position *= 1.1
    return round(position, 2)


def calculate_stop_loss(signal: TradingSignal, setup_type: str) -> float:
    """Calculate stop loss price based on setup type"""
    price = signal.last_price
    if 'FADE_LONG' in setup_type:
        return round(price * 0.97, 2)
    elif 'FADE_SHORT' in setup_type:
        return round(price * 1.03, 2)
    elif 'ROLLOVER_LONG' in setup_type:
        return round(signal.sma20 * 0.98, 2) if signal.sma20 else round(price * 0.97, 2)
    elif 'ROLLOVER_SHORT' in setup_type:
        return round(signal.sma20 * 1.02, 2) if signal.sma20 else round(price * 1.03, 2)
    else:
        return round(price * 0.97, 2) if signal.direction == 'LONG' else round(price * 1.03, 2)


def calculate_target(signal: TradingSignal, setup_type: str) -> Tuple[float, float]:
    """Calculate target prices (T1 and T2)"""
    price = signal.last_price
    if 'FADE_LONG' in setup_type:
        target1 = signal.sma20 if signal.sma20 else price * 1.05
        target2 = signal.sma50 if signal.sma50 else price * 1.10
    elif 'FADE_SHORT' in setup_type:
        target1 = signal.sma20 if signal.sma20 else price * 0.95
        target2 = price * 0.90
    elif 'ROLLOVER_LONG' in setup_type:
        target1 = price * 1.08
        target2 = price * 1.15
    elif 'ROLLOVER_SHORT' in setup_type:
        target1 = price * 0.92
        target2 = price * 0.85
    else:
        if signal.direction == 'LONG':
            target1 = price * 1.05
            target2 = price * 1.10
        else:
            target1 = price * 0.95
            target2 = price * 0.90
    return (round(target1, 2), round(target2, 2))


def format_signal_summary(signal: TradingSignal, regime: Dict[str, Any]) -> str:
    """Format signal as readable summary string"""
    stop = calculate_stop_loss(signal, signal.setup_type)
    target1, target2 = calculate_target(signal, signal.setup_type)
    position = calculate_position_size(signal, regime)
    
    summary = f"""
{'='*60}
{signal.symbol} - {signal.setup_type}
{'='*60}
Direction: {signal.direction} | Score: {signal.composite_score:.1f}/100
Entry: ${signal.last_price:.2f}
Stop Loss: ${stop:.2f} ({((stop/signal.last_price)-1)*100:.1f}%)
Target 1: ${target1:.2f} ({((target1/signal.last_price)-1)*100:.1f}%)
Target 2: ${target2:.2f} ({((target2/signal.last_price)-1)*100:.1f}%)
Position: ${position:.2f}

Technical:
  RSI: {signal.rsi:.0f} | ADX: {signal.adx:.0f}
  Gap: {signal.gap_percent:.1f}% | Vol: {signal.relative_volume:.1f}x
  Week Perf: {signal.week_performance:.1f}%

Regime: {regime['regime']} | VIX: {regime['vix']:.1f}
"""
    return summary





