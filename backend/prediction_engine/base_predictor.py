"""
Base Price Predictor - Abstract Class
======================================

Foundation for all prediction models (1H, 1D, 1W).
Handles feature extraction, prediction logic, and accuracy tracking.

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class BasePricePredictor(ABC):
    """
    Abstract base class for all price predictors.
    
    Subclasses must implement:
    - _extract_features()
    - _make_prediction()
    - get_horizon_timedelta()
    """
    
    def __init__(self, db_manager, horizon: str):
        """
        Initialize predictor.
        
        Args:
            db_manager: Database manager instance
            horizon: Time horizon ('1H', '1D', '1W')
        """
        self.db = db_manager
        self.horizon = horizon
        self.model_weights = self._load_default_weights()
        self.accuracy = 0.0
        self.predictions_made = 0
        
        logger.info(f"✅ {self.__class__.__name__} initialized for {horizon}")
    
    def _load_default_weights(self) -> Dict[str, float]:
        """Load default feature weights"""
        return {
            'price_features': 0.25,
            'flow_features': 0.25,
            'technical_features': 0.20,
            'correlation_features': 0.15,
            'volume_features': 0.15
        }
    
    @abstractmethod
    def _extract_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Extract features for prediction.
        
        Must be implemented by subclass.
        
        Returns:
            Dictionary of feature_name -> value
        """
        pass
    
    @abstractmethod
    def _make_prediction(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Make price prediction based on features.
        
        Must be implemented by subclass.
        
        Args:
            features: Dictionary of features
            
        Returns:
            (predicted_price_change_pct, confidence)
        """
        pass
    
    @abstractmethod
    def get_horizon_timedelta(self) -> timedelta:
        """
        Get time delta for this horizon.
        
        Must be implemented by subclass.
        
        Returns:
            timedelta object (e.g., timedelta(hours=1))
        """
        pass
    
    def predict(self, symbol: str) -> Optional[Dict]:
        """
        Generate prediction for symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Prediction dictionary or None if failed
        """
        try:
            # Get current price
            current_price = self.db.get_latest_price(symbol)
            if not current_price:
                logger.warning(f"No price data for {symbol}")
                return None
            
            # Extract features
            features = self._extract_features(symbol)
            if not features:
                logger.warning(f"Failed to extract features for {symbol}")
                return None
            
            # Make prediction
            price_change_pct, confidence = self._make_prediction(features)
            
            # Calculate predicted price
            predicted_price = current_price * (1 + price_change_pct / 100)
            
            # Determine direction
            if price_change_pct > 0.5:
                direction = 'UP'
            elif price_change_pct < -0.5:
                direction = 'DOWN'
            else:
                direction = 'FLAT'
            
            # Calculate target time
            prediction_time = datetime.now()
            target_time = prediction_time + self.get_horizon_timedelta()
            
            # Build prediction object
            prediction = {
                'symbol': symbol,
                'horizon': self.horizon,
                'prediction_time': prediction_time.isoformat(),
                'target_time': target_time.isoformat(),
                'current_price': float(current_price),
                'predicted_price': float(predicted_price),
                'predicted_change_pct': float(price_change_pct),
                'direction': direction,
                'confidence': float(confidence),
                'features': features,
                'model_weights': self.model_weights,
                'model_accuracy': self.accuracy
            }
            
            # Store in database
            self.db.insert_prediction(symbol, self.horizon, {
                'prediction_time': prediction_time,
                'target_time': target_time,
                'predicted_price': predicted_price,
                'confidence': confidence
            })
            
            self.predictions_made += 1
            
            logger.info(f"✅ {self.horizon} prediction for {symbol}: {direction} "
                       f"{price_change_pct:+.2f}% (confidence: {confidence:.1f}%)")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction failed for {symbol}: {e}")
            return None
    
    def batch_predict(self, symbols: List[str]) -> List[Dict]:
        """
        Generate predictions for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            List of prediction dictionaries
        """
        predictions = []
        
        for symbol in symbols:
            prediction = self.predict(symbol)
            if prediction:
                predictions.append(prediction)
        
        logger.info(f"✅ Generated {len(predictions)}/{len(symbols)} {self.horizon} predictions")
        
        return predictions
    
    def update_accuracy(self, new_accuracy: float):
        """Update model accuracy metric"""
        self.accuracy = new_accuracy
        logger.info(f"📊 {self.horizon} accuracy updated: {new_accuracy:.1f}%")
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update feature weights (learning loop)"""
        self.model_weights.update(new_weights)
        logger.info(f"⚙️ {self.horizon} weights updated")
    
    def get_stats(self) -> Dict:
        """Get predictor statistics"""
        return {
            'horizon': self.horizon,
            'predictions_made': self.predictions_made,
            'accuracy': self.accuracy,
            'weights': self.model_weights
        }
