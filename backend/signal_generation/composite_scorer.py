"""
Enhanced Composite Scorer with Freshness and SHORT Support
Dynamically weights scores based on regime and direction
"""

from typing import Dict, List
from backend.core.logger import get_logger

logger = get_logger(__name__)


class CompositeScorer:
    """
    Combines multiple scoring dimensions into final composite score
    Now includes Freshness (Stage 2 detection) and SHORT bias support
    """
    
    def __init__(self, regime: str = "YELLOW", custom_weights: Dict[str, float] = None):
        self.regime = regime
        self.custom_weights = custom_weights
        self.weights = self._get_regime_weights(regime, custom_weights)
        logger.info(f"📊 Composite Scorer initialized for {regime} regime")
        logger.info(f"Weights: {self.weights}")
    
    def _get_regime_weights(self, regime: str, custom: Dict[str, float] = None) -> Dict[str, float]:
        """
        Get scoring weights by regime
        FRESHNESS gets highest weight - we want Stage 2, not Stage 3!
        """
        
        # Default weights by regime
        if regime == "GREEN":
            default_weights = {
                'bible_score': 0.20,       # ↓ Reduced
                'structure_score': 0.20,   # ↓ Reduced
                'freshness_score': 0.35,   # ⭐ NEW - HIGHEST!
                'ignition_quality': 0.15,  # ⭐ NEW
                'momentum_score': 0.05,    # ↓ Reduced
                'volume_score': 0.05,      # ↓ Reduced
            }
        elif regime == "YELLOW":
            default_weights = {
                'bible_score': 0.25,
                'structure_score': 0.20,
                'freshness_score': 0.30,   # ⭐ NEW - HIGHEST!
                'ignition_quality': 0.15,  # ⭐ NEW
                'momentum_score': 0.05,
                'volume_score': 0.05,
            }
        elif regime == "RED":
            default_weights = {
                'bible_score': 0.30,
                'structure_score': 0.30,
                'freshness_score': 0.20,   # ⭐ NEW
                'ignition_quality': 0.10,  # ⭐ NEW
                'momentum_score': 0.05,
                'volume_score': 0.05,
            }
        elif regime == "SHORT":
            # SHORT regime - inverted priorities
            default_weights = {
                'bible_score': 0.25,
                'structure_score': 0.25,
                'freshness_score': 0.25,   # ⭐ Still important for timing
                'ignition_quality': 0.15,  # ⭐ Quality matters
                'momentum_score': 0.05,    # Less important
                'volume_score': 0.05,
            }
        else:
            logger.warning(f"Unknown regime '{regime}', using YELLOW weights")
            default_weights = self._get_regime_weights("YELLOW")
        
        # Override with custom weights if provided
        if custom:
            logger.info(f"🎛️ Applying custom weights: {custom}")
            for key, value in custom.items():
                if key in default_weights:
                    default_weights[key] = value
        
        # Normalize to ensure sum = 1.0
        total = sum(default_weights.values())
        if total != 1.0:
            logger.warning(f"Weights sum to {total}, normalizing to 1.0")
            default_weights = {k: v/total for k, v in default_weights.items()}
        
        return default_weights
    
    def calculate_composite_scores(self, bible_results: Dict[str, Dict],
                                   technical_results: Dict[str, Dict]) -> List[Dict]:
        """
        Calculate composite scores for all symbols
        
        Args:
            bible_results: {symbol: {total_score, fractal_score, volume_quality, staircase_score}}
            technical_results: {symbol: {structure_score, freshness_score, ignition_quality, ...}}
        
        Returns:
            List of scored symbols with composite scores
        """
        
        results = []
        
        for symbol in bible_results.keys():
            if symbol not in technical_results:
                continue
            
            bible = bible_results[symbol]
            tech = technical_results[symbol]
            
            # Extract scores
            bible_score = bible.get('total_score', 0)
            structure_score = tech.get('structure_score', 0)
            freshness_score = tech.get('freshness_score', 0)  # ⭐ NEW
            ignition_quality = tech.get('ignition_quality', 0)  # ⭐ NEW
            
            # Calculate momentum and volume scores
            momentum_score = self._calculate_momentum_score(tech)
            volume_score = self._calculate_volume_score(tech)
            
            # Detect bias
            bias = tech.get('bias', 'LONG')
            
            # For SHORT bias, invert scoring logic
            if bias == 'SHORT':
                adjusted_scores = self._calculate_short_scores(tech)
                bible_score = adjusted_scores.get('bible_score', bible_score)
                structure_score = adjusted_scores.get('structure_score', structure_score)
                momentum_score = adjusted_scores.get('momentum_score', momentum_score)
            
            # Weighted composite
            composite = (
                (bible_score * self.weights['bible_score']) +
                (structure_score * self.weights['structure_score']) +
                (freshness_score * self.weights['freshness_score']) +  # ⭐ NEW!
                (ignition_quality * self.weights['ignition_quality']) +  # ⭐ NEW!
                (momentum_score * self.weights['momentum_score']) +
                (volume_score * self.weights['volume_score'])
            )
            
            results.append({
                'symbol': symbol,
                'composite_score': round(composite, 2),
                'bible_score': round(bible_score, 2),
                'structure_score': round(structure_score, 2),
                'freshness_score': round(freshness_score, 2),  # ⭐ NEW
                'ignition_quality': round(ignition_quality, 2),  # ⭐ NEW
                'ignition_stage': tech.get('ignition_stage', 'UNKNOWN'),  # ⭐ NEW
                'momentum_score': round(momentum_score, 2),
                'volume_score': round(volume_score, 2),
                'structure_pass': tech.get('structure_pass', False),
                'bias': bias,
                'price': tech.get('price', 0),
                
                # Freshness details for display
                'price_move_pct': tech.get('price_move_pct', 0),
                'volume_ratio': tech.get('volume_ratio', 1.0),
                'williams_r': tech.get('williams_r', -50),
                'sma20_distance': tech.get('sma20_distance', 0),
                'minutes_since_breakout': tech.get('minutes_since_breakout', 0),
                
                # Original technical fields
                'rsi': tech.get('rsi', 50),
                'adx': tech.get('adx', 0),
                'atr': tech.get('atr', 0),
                'rel_volume': tech.get('rel_volume', 1.0),
                'perf_week': tech.get('perf_week', 0),
                'higher_low': tech.get('higher_low', False),
                
                # Bible component scores
                'fractal_score': bible.get('fractal_score', 0),
                'volume_quality': bible.get('volume_quality', 0),
                'staircase_score': bible.get('staircase_score', 0),
            })
        
        # Sort by composite score descending
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        logger.info(f"✅ Calculated composite scores for {len(results)} symbols")
        if results:
            logger.info(f"Top score: {results[0]['symbol']} = {results[0]['composite_score']}")
        
        return results
    
    def _calculate_momentum_score(self, tech: Dict) -> float:
        """Calculate momentum component score"""
        
        score = 50.0  # Base
        
        rsi = tech.get('rsi', 50)
        adx = tech.get('adx', 0)
        perf_week = tech.get('perf_week', 0)
        
        # RSI component (50-70 = strong for longs)
        if 50 <= rsi <= 70:
            score += 30
        elif rsi > 70:
            score += 10  # Overbought
        elif rsi < 40:
            score -= 20  # Weak
        
        # ADX component (>25 = strong trend)
        if adx > 25:
            score += 20
        
        # Weekly performance
        if perf_week > 5:
            score += 10
        elif perf_week < -5:
            score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_volume_score(self, tech: Dict) -> float:
        """Calculate volume component score"""
        
        rel_volume = tech.get('rel_volume', 1.0)
        
        if rel_volume >= 2.5:
            return 100  # Exceptional
        elif rel_volume >= 2.0:
            return 80
        elif rel_volume >= 1.5:
            return 60
        elif rel_volume >= 1.0:
            return 40
        else:
            return 20
    
    def _calculate_short_scores(self, tech: Dict) -> Dict[str, float]:
        """
        Inverted scoring logic for SHORT bias
        What's bad for longs is good for shorts
        """
        
        adjusted = {}
        
        # Williams %R: Want OVERBOUGHT (-20 to 0) for shorts
        williams_r = tech.get('williams_r', -50)
        if williams_r > -20:
            adjusted['momentum_score'] = 80  # Very overbought
        elif williams_r > -30:
            adjusted['momentum_score'] = 60  # Overbought
        else:
            adjusted['momentum_score'] = 20  # Not a good short
        
        # RSI: Want OVERBOUGHT (> 70) for shorts
        rsi = tech.get('rsi', 50)
        if rsi > 70:
            adjusted['momentum_score'] = (adjusted.get('momentum_score', 50) + 80) / 2
        
        # Price vs SMA20: Want BELOW for shorts
        sma20_dist = tech.get('sma20_distance', 0)
        price = tech.get('price', 0)
        above_sma20 = tech.get('above_sma20', True)
        
        if not above_sma20:  # Below SMA20 = good for short
            adjusted['structure_score'] = 80
        else:
            adjusted['structure_score'] = 30  # Above SMA = not ideal short
        
        return adjusted


# Global instance
scorer = CompositeScorer()


def calculate_scores(bible_results: Dict, technical_results: Dict, 
                    regime: str = "YELLOW", custom_weights: Dict = None) -> List[Dict]:
    """
    Convenience function to calculate composite scores
    
    Usage:
        scores = calculate_scores(bible_data, tech_data, regime="GREEN")
    """
    scorer_instance = CompositeScorer(regime=regime, custom_weights=custom_weights)
    return scorer_instance.calculate_composite_scores(bible_results, technical_results)
