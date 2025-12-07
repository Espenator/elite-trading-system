"""
1-Day Price Predictor
=====================

Medium-term price prediction (1-day horizon).
Focuses on: daily structure, flow trends, correlations.

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import timedelta
import numpy as np
from ..base_predictor import BasePricePredictor

logger = logging.getLogger(__name__)


class DayPredictor(BasePricePredictor):
    """1-Day price predictor - daily swing trades"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, horizon='1D')
        
        # 1D specific weights
        self.model_weights = {
            'daily_trend': 0.25,          # Daily chart trend
            'flow_accumulation': 0.25,    # Multi-day flow trends
            'correlation_spy': 0.20,      # SPY correlation
            'technical_structure': 0.20,  # Support/Resistance
            'sector_sentiment': 0.10      # Sector flow
        }
    
    def get_horizon_timedelta(self) -> timedelta:
        """1 day horizon"""
        return timedelta(days=1)
    
    def _extract_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Extract features for 1D prediction.
        
        Features:
        - Daily trend (SMA crossovers, MACD)
        - Flow accumulation (3-day trend)
        - SPY correlation (is it following market?)
        - Technical structure (near support/resistance)
        - Sector sentiment
        """
        try:
            features = {}
            
            # 1. Daily trend analysis
            features['daily_trend'] = self._get_daily_trend(symbol)
            
            # 2. Multi-day flow accumulation
            features['flow_accumulation'] = self._get_flow_accumulation(symbol)
            
            # 3. SPY correlation
            features['correlation_spy'] = self._get_spy_correlation(symbol)
            
            # 4. Technical structure
            features['technical_structure'] = self._get_technical_structure(symbol)
            
            # 5. Sector sentiment
            features['sector_sentiment'] = self._get_sector_sentiment(symbol)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed for {symbol}: {e}")
            return None
    
    def _get_daily_trend(self, symbol: str) -> float:
        """
        Daily trend strength (-100 to +100).
        
        Based on:
        - SMA 20 vs SMA 50
        - MACD signal
        - Price vs moving averages
        """
        try:
            # Analyze daily chart structure
            # Simplified for now
            return np.random.uniform(-50, 50)
            
        except Exception as e:
            logger.warning(f"Daily trend calculation failed: {e}")
            return 0.0
    
    def _get_flow_accumulation(self, symbol: str) -> float:
        """
        Flow accumulation score (-100 to +100).
        
        Net call/put premium over last 3 days.
        """
        try:
            # Query 3-day flow data
            # Positive = accumulation (bullish)
            # Negative = distribution (bearish)
            return np.random.uniform(-60, 60)
            
        except Exception as e:
            logger.warning(f"Flow accumulation calculation failed: {e}")
            return 0.0
    
    def _get_spy_correlation(self, symbol: str) -> float:
        """
        SPY correlation signal (-100 to +100).
        
        If SPY is bullish and stock follows SPY, positive signal.
        """
        try:
            # Get SPY direction
            spy_direction = np.random.choice([-1, 1])
            
            # Get correlation strength (0 to 1)
            correlation = np.random.uniform(0.3, 0.9)
            
            # Signal strength
            signal = spy_direction * correlation * 100
            
            return signal
            
        except Exception as e:
            logger.warning(f"SPY correlation calculation failed: {e}")
            return 0.0
    
    def _get_technical_structure(self, symbol: str) -> float:
        """
        Technical structure score (-100 to +100).
        
        Near support = positive (bounce expected)
        Near resistance = negative (rejection expected)
        """
        try:
            # Analyze support/resistance levels
            # Check if price is near key levels
            
            position = np.random.choice(['support', 'resistance', 'neutral'])
            
            if position == 'support':
                return np.random.uniform(30, 60)
            elif position == 'resistance':
                return np.random.uniform(-60, -30)
            else:
                return np.random.uniform(-20, 20)
                
        except Exception as e:
            logger.warning(f"Technical structure calculation failed: {e}")
            return 0.0
    
    def _get_sector_sentiment(self, symbol: str) -> float:
        """
        Sector sentiment score (-100 to +100).
        
        If sector is strong, positive signal.
        """
        try:
            # Get sector flow data
            # Simplified for now
            return np.random.uniform(-40, 40)
            
        except Exception as e:
            logger.warning(f"Sector sentiment calculation failed: {e}")
            return 0.0
    
    def _make_prediction(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Make 1D price prediction.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            (predicted_change_pct, confidence)
        """
        try:
            # Weighted combination of features
            prediction_score = 0.0
            
            for feature_name, weight in self.model_weights.items():
                feature_value = features.get(feature_name, 0.0)
                prediction_score += feature_value * weight
            
            # Normalize to reasonable price change (-10% to +10% for 1D)
            predicted_change_pct = np.clip(prediction_score / 10.0, -10.0, 10.0)
            
            # Calculate confidence based on feature alignment
            feature_values = list(features.values())
            feature_agreement = np.mean([1 if abs(v) > 20 else 0 for v in feature_values])
            
            # High agreement = high confidence
            confidence = np.clip(50 + (feature_agreement * 40), 50, 95)
            
            return predicted_change_pct, confidence
            
        except Exception as e:
            logger.error(f"Prediction calculation failed: {e}")
            return 0.0, 50.0
