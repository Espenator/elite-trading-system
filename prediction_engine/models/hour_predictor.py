"""
1-Hour Price Predictor
======================

Short-term price prediction (1-hour horizon).
Focuses on: momentum, flow activity, volatility.

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import timedelta
import numpy as np
from ..base_predictor import BasePricePredictor

logger = logging.getLogger(__name__)


class HourPredictor(BasePricePredictor):
    """1-Hour price predictor - short-term momentum"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, horizon='1H')
        
        # 1H specific weights
        self.model_weights = {
            'price_momentum': 0.30,      # Recent price action
            'flow_sentiment': 0.25,       # Options flow (last hour)
            'volume_surge': 0.20,         # Volume spikes
            'technical_rsi': 0.15,        # RSI momentum
            'volatility': 0.10            # Volatility expansion
        }
    
    def get_horizon_timedelta(self) -> timedelta:
        """1 hour horizon"""
        return timedelta(hours=1)
    
    def _extract_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Extract features for 1H prediction.
        
        Features:
        - Price momentum (last 5-15 minutes)
        - Options flow sentiment (last hour)
        - Volume surge vs average
        - RSI (14-period on 5m chart)
        - ATR (volatility)
        """
        try:
            features = {}
            
            # 1. Price momentum (last 15 minutes)
            features['price_momentum'] = self._get_price_momentum(symbol)
            
            # 2. Options flow sentiment (last hour)
            features['flow_sentiment'] = self._get_flow_sentiment(symbol)
            
            # 3. Volume surge
            features['volume_surge'] = self._get_volume_surge(symbol)
            
            # 4. RSI momentum
            features['technical_rsi'] = self._get_rsi_signal(symbol)
            
            # 5. Volatility
            features['volatility'] = self._get_volatility_signal(symbol)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed for {symbol}: {e}")
            return None
    
    def _get_price_momentum(self, symbol: str) -> float:
        """
        Calculate price momentum score (-100 to +100).
        
        Based on recent price changes (last 15 minutes).
        """
        try:
            # Get recent prices (would query database in production)
            # For now, return random for testing
            return np.random.uniform(-50, 50)
            
        except Exception as e:
            logger.warning(f"Price momentum calculation failed: {e}")
            return 0.0
    
    def _get_flow_sentiment(self, symbol: str) -> float:
        """
        Calculate options flow sentiment score (-100 to +100).
        
        Based on:
        - Call vs Put premium (last hour)
        - Whale activity
        - Sweep activity
        """
        try:
            # Query options flow from database
            # Simplified for now
            return np.random.uniform(-50, 50)
            
        except Exception as e:
            logger.warning(f"Flow sentiment calculation failed: {e}")
            return 0.0
    
    def _get_volume_surge(self, symbol: str) -> float:
        """
        Calculate volume surge score (0 to 100).
        
        Current volume vs 20-period average.
        """
        try:
            # Compare current volume to average
            # Simplified for now
            return np.random.uniform(0, 100)
            
        except Exception as e:
            logger.warning(f"Volume surge calculation failed: {e}")
            return 50.0
    
    def _get_rsi_signal(self, symbol: str) -> float:
        """
        Calculate RSI momentum signal (-100 to +100).
        
        RSI > 70: Overbought (negative signal)
        RSI < 30: Oversold (positive signal)
        """
        try:
            # Calculate RSI from recent prices
            # Simplified for now
            rsi = np.random.uniform(30, 70)
            
            if rsi > 70:
                return -50  # Overbought
            elif rsi < 30:
                return 50   # Oversold
            else:
                return 0    # Neutral
                
        except Exception as e:
            logger.warning(f"RSI calculation failed: {e}")
            return 0.0
    
    def _get_volatility_signal(self, symbol: str) -> float:
        """
        Calculate volatility signal (-100 to +100).
        
        Expanding volatility = higher uncertainty
        """
        try:
            # Calculate ATR or Bollinger Band width
            # Simplified for now
            return np.random.uniform(-30, 30)
            
        except Exception as e:
            logger.warning(f"Volatility calculation failed: {e}")
            return 0.0
    
    def _make_prediction(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Make 1H price prediction.
        
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
            
            # Normalize to reasonable price change (-5% to +5% for 1H)
            predicted_change_pct = np.clip(prediction_score / 20.0, -5.0, 5.0)
            
            # Calculate confidence based on feature alignment
            feature_values = list(features.values())
            feature_std = np.std(feature_values)
            
            # High agreement (low std) = high confidence
            confidence = np.clip(100 - feature_std, 50, 95)
            
            return predicted_change_pct, confidence
            
        except Exception as e:
            logger.error(f"Prediction calculation failed: {e}")
            return 0.0, 50.0
