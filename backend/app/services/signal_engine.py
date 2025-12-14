# app/services/signal_engine.py
"""
Signal Detection Engine - Analyzes market data to generate trading signals.
Implements multiple signal strategies and scoring logic.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    MOMENTUM = "momentum"
    VOLUME_SPIKE = "volume_spike"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    BREAKOUT = "breakout"
    VWAP_CROSS = "vwap_cross"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"


class SignalTier(str, Enum):
    T1 = "T1"  # High confidence (score >= 80)
    T2 = "T2"  # Medium confidence (score >= 60)
    T3 = "T3"  # Lower confidence (score < 60)


@dataclass
class Signal:
    """Trading signal with all relevant data"""
    symbol: str
    signal_type: SignalType
    tier: SignalTier
    score: float  # 0-100 composite score
    price: float
    change_pct: float
    volume_ratio: float
    catalyst: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional detailed metrics
    rsi: Optional[float] = None
    momentum: Optional[float] = None
    vwap: Optional[float] = None
    ai_confidence: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'tier': self.tier.value,
            'score': round(self.score, 1),
            'price': self.price,
            'change_pct': round(self.change_pct, 2),
            'volume_ratio': round(self.volume_ratio, 2),
            'catalyst': self.catalyst,
            'timestamp': self.timestamp.isoformat(),
            'rsi': round(self.rsi, 1) if self.rsi else None,
            'momentum': round(self.momentum, 2) if self.momentum else None,
            'vwap': round(self.vwap, 2) if self.vwap else None,
            'ai_confidence': round(self.ai_confidence, 1) if self.ai_confidence else None,
        }


class SignalEngine:
    """
    Analyzes market data and generates trading signals based on multiple strategies.
    """
    
    def __init__(self):
        # Signal thresholds (configurable)
        self.config = {
            # Volume thresholds
            'volume_spike_threshold': 2.0,  # 2x average volume
            'high_volume_threshold': 3.0,   # 3x for stronger signal
            
            # RSI thresholds
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'rsi_extreme_oversold': 20,
            'rsi_extreme_overbought': 80,
            
            # Momentum thresholds (% change)
            'momentum_threshold': 2.0,      # 2% move
            'strong_momentum': 5.0,         # 5% move
            
            # Gap thresholds
            'gap_threshold': 2.0,           # 2% gap
            'strong_gap': 4.0,              # 4% gap
            
            # Minimum score to generate signal
            'min_signal_score': 40,
        }
        
        # Track recently generated signals to avoid duplicates
        self._recent_signals: dict[str, datetime] = {}
        self._signal_cooldown = 60  # seconds between signals for same stock
    
    def analyze(self, market_data: dict) -> Optional[Signal]:
        """
        Analyze market data and generate signal if conditions are met.
        
        Args:
            market_data: Dict containing price, volume, indicators etc.
        
        Returns:
            Signal object if conditions are met, None otherwise
        """
        symbol = market_data.get('symbol', '')
        
        # Check cooldown
        if self._is_in_cooldown(symbol):
            return None
        
        # Calculate component scores
        scores = {
            'volume': self._score_volume(market_data),
            'momentum': self._score_momentum(market_data),
            'rsi': self._score_rsi(market_data),
            'gap': self._score_gap(market_data),
            'vwap': self._score_vwap(market_data),
        }
        
        # Calculate composite score (weighted average)
        weights = {
            'volume': 0.25,
            'momentum': 0.30,
            'rsi': 0.20,
            'gap': 0.15,
            'vwap': 0.10,
        }
        
        composite_score = sum(scores[k] * weights[k] for k in scores)
        
        # Only generate signal if score exceeds minimum
        if composite_score < self.config['min_signal_score']:
            return None
        
        # Determine primary signal type and catalyst
        signal_type, catalyst = self._determine_signal_type(market_data, scores)
        
        # Determine tier based on score
        tier = self._determine_tier(composite_score)
        
        # Create signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            tier=tier,
            score=composite_score,
            price=market_data.get('price', 0),
            change_pct=market_data.get('change_pct', 0),
            volume_ratio=market_data.get('volume_ratio', 1.0),
            catalyst=catalyst,
            rsi=market_data.get('rsi'),
            momentum=market_data.get('momentum'),
            vwap=market_data.get('vwap'),
            ai_confidence=composite_score,  # Use composite as AI confidence
        )
        
        # Record signal timestamp
        self._recent_signals[symbol] = datetime.now()
        
        logger.info(f"Generated {tier.value} signal for {symbol}: {signal_type.value} (score: {composite_score:.1f})")
        
        return signal
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol not in self._recent_signals:
            return False
        
        elapsed = (datetime.now() - self._recent_signals[symbol]).seconds
        return elapsed < self._signal_cooldown
    
    def _score_volume(self, data: dict) -> float:
        """Score based on volume ratio (0-100)"""
        volume_ratio = data.get('volume_ratio', 1.0)
        
        if volume_ratio >= self.config['high_volume_threshold']:
            return 100
        elif volume_ratio >= self.config['volume_spike_threshold']:
            # Scale between 60-100 for 2x-3x volume
            return 60 + (volume_ratio - 2.0) * 40
        elif volume_ratio >= 1.5:
            # Scale between 30-60 for 1.5x-2x volume
            return 30 + (volume_ratio - 1.5) * 60
        else:
            # Below average volume
            return max(0, volume_ratio * 20)
    
    def _score_momentum(self, data: dict) -> float:
        """Score based on price momentum (0-100)"""
        momentum = abs(data.get('momentum', 0))
        change_pct = abs(data.get('change_pct', 0))
        
        # Combine momentum and daily change
        combined = (momentum + change_pct) / 2
        
        if combined >= self.config['strong_momentum']:
            return 100
        elif combined >= self.config['momentum_threshold']:
            # Scale between 60-100 for 2%-5% moves
            return 60 + (combined - 2.0) * 13.33
        elif combined >= 1.0:
            # Scale between 30-60 for 1%-2% moves
            return 30 + (combined - 1.0) * 30
        else:
            return combined * 30
    
    def _score_rsi(self, data: dict) -> float:
        """Score based on RSI indicator (0-100)"""
        rsi = data.get('rsi')
        
        if rsi is None:
            return 50  # Neutral if no RSI data
        
        # Extreme oversold (< 20) or overbought (> 80)
        if rsi <= self.config['rsi_extreme_oversold']:
            return 100
        elif rsi >= self.config['rsi_extreme_overbought']:
            return 90
        # Regular oversold/overbought
        elif rsi <= self.config['rsi_oversold']:
            return 70 + (30 - rsi) * 3  # 70-100 for RSI 30-20
        elif rsi >= self.config['rsi_overbought']:
            return 60 + (rsi - 70) * 3  # 60-90 for RSI 70-80
        # Neutral zone
        else:
            return 40
    
    def _score_gap(self, data: dict) -> float:
        """Score based on gap from previous close (0-100)"""
        change_pct = abs(data.get('change_pct', 0))
        
        if change_pct >= self.config['strong_gap']:
            return 100
        elif change_pct >= self.config['gap_threshold']:
            return 60 + (change_pct - 2.0) * 20
        elif change_pct >= 1.0:
            return 30 + (change_pct - 1.0) * 30
        else:
            return change_pct * 30
    
    def _score_vwap(self, data: dict) -> float:
        """Score based on price relationship to VWAP (0-100)"""
        price = data.get('price', 0)
        vwap = data.get('vwap')
        
        if not vwap or not price:
            return 50  # Neutral if no VWAP data
        
        # Calculate % distance from VWAP
        vwap_dist = abs(price - vwap) / vwap * 100
        
        # Price significantly above/below VWAP
        if vwap_dist >= 2.0:
            return 80 + min(vwap_dist - 2.0, 2.0) * 10
        elif vwap_dist >= 1.0:
            return 60 + (vwap_dist - 1.0) * 20
        else:
            return 40 + vwap_dist * 20
    
    def _determine_signal_type(self, data: dict, scores: dict) -> tuple[SignalType, str]:
        """Determine the primary signal type and generate catalyst description"""
        
        # Find highest scoring component
        max_score_type = max(scores, key=scores.get)
        max_score = scores[max_score_type]
        
        symbol = data.get('symbol', 'Stock')
        change_pct = data.get('change_pct', 0)
        volume_ratio = data.get('volume_ratio', 1.0)
        rsi = data.get('rsi')
        
        # Determine signal type and catalyst based on dominant factor
        if max_score_type == 'volume' and volume_ratio >= 2.0:
            return SignalType.VOLUME_SPIKE, f"Volume spike at {volume_ratio:.1f}x average"
        
        elif max_score_type == 'gap':
            if change_pct >= self.config['gap_threshold']:
                if change_pct > 0:
                    return SignalType.GAP_UP, f"Gap up {change_pct:.1f}% from prev close"
                else:
                    return SignalType.GAP_DOWN, f"Gap down {abs(change_pct):.1f}% from prev close"
        
        elif max_score_type == 'rsi' and rsi:
            if rsi <= self.config['rsi_oversold']:
                return SignalType.RSI_OVERSOLD, f"RSI oversold at {rsi:.0f}"
            elif rsi >= self.config['rsi_overbought']:
                return SignalType.RSI_OVERBOUGHT, f"RSI overbought at {rsi:.0f}"
        
        elif max_score_type == 'vwap':
            price = data.get('price', 0)
            vwap = data.get('vwap', 0)
            if price and vwap:
                direction = "above" if price > vwap else "below"
                return SignalType.VWAP_CROSS, f"Trading {direction} VWAP"
        
        # Default to momentum
        direction = "+" if change_pct > 0 else ""
        return SignalType.MOMENTUM, f"Strong momentum {direction}{change_pct:.1f}% with {volume_ratio:.1f}x vol"
    
    def _determine_tier(self, score: float) -> SignalTier:
        """Determine signal tier based on composite score"""
        if score >= 80:
            return SignalTier.T1
        elif score >= 60:
            return SignalTier.T2
        else:
            return SignalTier.T3
    
    def batch_analyze(self, market_data_list: list[dict]) -> list[Signal]:
        """Analyze multiple stocks and return list of signals"""
        signals = []
        
        for data in market_data_list:
            signal = self.analyze(data)
            if signal:
                signals.append(signal)
        
        # Sort by score (highest first)
        signals.sort(key=lambda s: s.score, reverse=True)
        
        return signals
    
    def update_config(self, **kwargs):
        """Update configuration parameters"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Updated signal config: {key} = {value}")


# Singleton instance
signal_engine = SignalEngine()
