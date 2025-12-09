"""
Elite Trading System - Prediction Engine
========================================

Real-time ML price prediction system with self-learning capabilities.

Components:
- Multi-horizon predictors (1H, 1D, 1W)
- Feature aggregation from price + flow data
- Outcome resolution and accuracy tracking
- Dynamic weight adjustment (learning loop)

Author: Elite Trading Team
Date: December 5, 2025
"""

from .base_predictor import BasePricePredictor
from .prediction_service import PredictionService, create_prediction_engine

__version__ = "1.0.0"

__all__ = [
    'BasePricePredictor',
    'PredictionService',
    'create_prediction_engine'
]
