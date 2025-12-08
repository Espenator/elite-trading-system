"""
Composite Signal Scorer - Bible Compatible
Works with Finviz Elite API data (no external dependencies)
"""

from typing import Dict
from core.logger import get_logger

logger = get_logger(__name__)


class CompositeScorer:
    """
    Multi-factor scoring system optimized for Finviz data
    """
    
    def __init__(self):
        self.weights = {
            'bible': 0.30,         # 30% - Bible pre-filter score
            'volume': 0.25,        # 25% - Volume surge
            'momentum': 0.25,      # 25% - Price momentum
            'quality': 0.20,       # 20% - Market cap & fundamentals
        }
    
    def score_signal(self, symbol: str, data: Dict) -> float:
        """
        Calculate composite score using available Finviz data
        
        Args:
            symbol: Stock ticker
            data: Dict with Finviz data
        
        Returns:
            Score from 0-100
        """
        try:
            score = 0.0
            
            # 1. BIBLE SCORE (30%)
            bible_score = data.get('bible_score', 50.0)
            score += (bible_score / 100.0) * 30
            
            # 2. VOLUME SCORING (25%)
            volume_score = self._score_volume(data)
            score += volume_score * 25
            
            # 3. MOMENTUM SCORING (25%)
            momentum_score = self._score_momentum(data)
            score += momentum_score * 25
            
            # 4. QUALITY SCORING (20%)
            quality_score = self._score_quality(data)
            score += quality_score * 20
            
            logger.debug(f"{symbol}: Bible={bible_score:.1f} Vol={volume_score:.2f} Mom={momentum_score:.2f} Qual={quality_score:.2f} -> Total={score:.1f}")
            
            return round(score, 1)
            
        except Exception as e:
            logger.error(f"Error scoring {symbol}: {e}")
            return 50.0
    
    def _score_volume(self, data: Dict) -> float:
        """Score volume (0.0-1.0)"""
        score = 0.0
        
        volume = data.get('volume', 0)
        
        # Absolute volume quality
        if volume >= 10_000_000:
            score += 0.4
        elif volume >= 5_000_000:
            score += 0.3
        elif volume >= 2_000_000:
            score += 0.2
        elif volume >= 1_000_000:
            score += 0.1
        
        # Volume quality score (already calculated by Finviz scraper)
        volume_quality = data.get('volume_quality', 0.0)
        if volume_quality >= 10:  # 10M+ shares
            score += 0.3
        elif volume_quality >= 5:   # 5M+ shares
            score += 0.2
        elif volume_quality >= 2:   # 2M+ shares
            score += 0.1
        
        # Explosive volume bonus
        if volume >= 5_000_000 and data.get('change_pct', 0) >= 3.0:
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_momentum(self, data: Dict) -> float:
        """Score momentum (0.0-1.0)"""
        score = 0.0
        
        # Today's price change
        change_pct = abs(data.get('change_pct', 0.0))
        
        if change_pct >= 10.0:
            score += 0.5
        elif change_pct >= 7.0:
            score += 0.4
        elif change_pct >= 5.0:
            score += 0.35
        elif change_pct >= 3.0:
            score += 0.25
        elif change_pct >= 2.0:
            score += 0.15
        elif change_pct >= 1.0:
            score += 0.1
        
        # Regime bonus
        regime = data.get('regime', 'YELLOW')
        if regime == 'GREEN' and change_pct >= 2.0:
            score += 0.2  # Momentum in momentum regime
        elif regime == 'RED' and change_pct >= 5.0:
            score += 0.3  # Big reversal
        
        return min(score, 1.0)
    
    def _score_quality(self, data: Dict) -> float:
        """Score fundamental quality (0.0-1.0)"""
        score = 0.0
        
        # Market cap
        market_cap = data.get('market_cap', 0)
        
        if market_cap >= 100_000_000_000:  # $100B+ mega
            score += 0.4
        elif market_cap >= 50_000_000_000:  # $50B+ large
            score += 0.35
        elif market_cap >= 10_000_000_000:  # $10B+ mid-large
            score += 0.3
        elif market_cap >= 2_000_000_000:   # $2B+ mid
            score += 0.2
        elif market_cap >= 500_000_000:     # $500M+ small
            score += 0.1
        
        # P/E ratio (if available)
        pe_ratio = data.get('pe_ratio', 0.0)
        if 0 < pe_ratio < 15:
            score += 0.3  # Undervalued
        elif 15 <= pe_ratio < 25:
            score += 0.2  # Fair
        elif 25 <= pe_ratio < 40:
            score += 0.1  # Growth
        
        # Sector (hot sectors)
        sector = data.get('sector', '')
        hot_sectors = ['Technology', 'Healthcare', 'Financial', 'Consumer Cyclical', 'Communication Services']
        if sector in hot_sectors:
            score += 0.3
        
        return min(score, 1.0)


# Global instance
scorer = CompositeScorer()


def score_signal(symbol: str, data: Dict) -> float:
    """Convenience function"""
    return scorer.score_signal(symbol, data)


if __name__ == "__main__":
    # Test
    test_data = {
        'bible_score': 85.0,
        'price': 72.65,
        'change_pct': 18.25,
        'volume': 8_000_000,
        'volume_quality': 8.0,
        'market_cap': 12_000_000_000,
        'pe_ratio': 22.0,
        'sector': 'Technology',
        'regime': 'YELLOW'
    }
    
    score = score_signal('ASTS', test_data)
    print(f"\nTest Score: {score:.1f}/100")

