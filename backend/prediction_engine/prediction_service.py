"""
Prediction Service - Main Orchestrator
=======================================

Manages all prediction models (1H, 1D, 1W).
Handles batch predictions, accuracy tracking, and model updates.

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from .models.hour_predictor import HourPredictor
from .models.day_predictor import DayPredictor
from .models.week_predictor import WeekPredictor

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Central prediction service that manages all predictors.
    
    Responsibilities:
    - Generate predictions for all horizons
    - Track model accuracy
    - Coordinate batch predictions
    - Update model weights (learning loop)
    """
    
    def __init__(self, db_manager):
        """
        Initialize prediction service.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        
        # Initialize all predictors
        logger.info("🧠 Initializing prediction models...")
        
        self.hour_predictor = HourPredictor(db_manager)
        self.day_predictor = DayPredictor(db_manager)
        self.week_predictor = WeekPredictor(db_manager)
        
        self.predictors = {
            '1H': self.hour_predictor,
            '1D': self.day_predictor,
            '1W': self.week_predictor
        }
        
        # Model accuracy tracking
        self.model_accuracy = {
            '1H': 0.0,
            '1D': 0.0,
            '1W': 0.0
        }
        
        logger.info("✅ Prediction service initialized with 3 models (1H, 1D, 1W)")
    
    def predict_symbol(self, symbol: str, horizons: Optional[List[str]] = None) -> Dict:
        """
        Generate predictions for a symbol across all horizons.
        
        Args:
            symbol: Stock ticker
            horizons: List of horizons to predict (default: all)
            
        Returns:
            Dictionary with predictions for each horizon
        """
        if horizons is None:
            horizons = ['1H', '1D', '1W']
        
        predictions = {}
        
        for horizon in horizons:
            predictor = self.predictors.get(horizon)
            if predictor:
                prediction = predictor.predict(symbol)
                if prediction:
                    predictions[horizon] = prediction
        
        logger.info(f"📊 Generated {len(predictions)} predictions for {symbol}")
        
        return predictions
    
    def predict_batch(self, symbols: List[str], horizons: Optional[List[str]] = None) -> Dict:
        """
        Generate predictions for multiple symbols.
        
        Args:
            symbols: List of tickers
            horizons: List of horizons to predict (default: all)
            
        Returns:
            Dictionary: {symbol: {horizon: prediction}}
        """
        if horizons is None:
            horizons = ['1H', '1D', '1W']
        
        all_predictions = {}
        
        for symbol in symbols:
            predictions = self.predict_symbol(symbol, horizons)
            if predictions:
                all_predictions[symbol] = predictions
        
        total_predictions = sum(len(p) for p in all_predictions.values())
        logger.info(f"✅ Batch prediction complete: {total_predictions} predictions for {len(symbols)} symbols")
        
        return all_predictions
    
    def generate_predictions_batch(self, symbols: List[str]) -> int:
        """
        Generate predictions for multiple symbols (returns count).
        
        Args:
            symbols: List of tickers
            
        Returns:
            Number of successful predictions
        """
        predictions = self.predict_batch(symbols)
        return sum(len(p) for p in predictions.values())
    
    def resolve_predictions(self, horizon: str) -> int:
        """
        Resolve expired predictions for a horizon.
        
        Checks predictions that have reached their target time,
        compares predicted vs actual price, and updates accuracy.
        
        Args:
            horizon: Time horizon ('1H', '1D', '1W')
            
        Returns:
            Number of predictions resolved
        """
        try:
            # Query unresolved predictions that have expired
            query = """
                SELECT * FROM predictions
                WHERE horizon = ?
                AND resolved = 0
                AND target_time <= ?
            """
            
            predictions = self.db.execute_query(
                query, 
                (horizon, datetime.now().isoformat())
            )
            
            if not predictions:
                return 0
            
            resolved_count = 0
            correct_count = 0
            
            for pred in predictions:
                # Get actual price at target time
                actual_price = self.db.get_latest_price(pred['symbol'])
                
                if actual_price:
                    # Calculate accuracy
                    predicted_price = pred['predicted_price']
                    error_pct = abs((actual_price - predicted_price) / predicted_price * 100)
                    
                    # Direction correct?
                    predicted_direction = 'UP' if predicted_price > pred['current_price'] else 'DOWN'
                    actual_direction = 'UP' if actual_price > pred['current_price'] else 'DOWN'
                    direction_correct = predicted_direction == actual_direction
                    
                    if direction_correct:
                        correct_count += 1
                    
                    # Update prediction in database
                    update_query = """
                        UPDATE predictions
                        SET actual_price = ?, resolved = 1
                        WHERE id = ?
                    """
                    self.db.execute_query(update_query, (actual_price, pred['id']), fetch=False)
                    
                    resolved_count += 1
            
            # Update model accuracy
            if resolved_count > 0:
                accuracy = (correct_count / resolved_count) * 100
                self.model_accuracy[horizon] = accuracy
                self.predictors[horizon].update_accuracy(accuracy)
                
                logger.info(f"✅ Resolved {resolved_count} {horizon} predictions "
                          f"(Accuracy: {accuracy:.1f}%)")
            
            return resolved_count
            
        except Exception as e:
            logger.error(f"❌ Resolution failed for {horizon}: {e}")
            return 0
    
    def update_model_accuracy_all(self):
        """Update accuracy for all models"""
        for horizon in ['1H', '1D', '1W']:
            self.resolve_predictions(horizon)
    
    def get_model_stats(self) -> Dict:
        """
        Get statistics for all models.
        
        Returns:
            Dictionary with stats for each horizon
        """
        stats = {}
        
        for horizon, predictor in self.predictors.items():
            stats[horizon] = predictor.get_stats()
        
        stats['overall_accuracy'] = self.model_accuracy
        
        return stats
    
    def get_latest_predictions(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Get recent predictions for a symbol.
        
        Args:
            symbol: Stock ticker
            limit: Number of predictions to return
            
        Returns:
            List of prediction dictionaries
        """
        query = """
            SELECT * FROM predictions
            WHERE symbol = ?
            ORDER BY prediction_time DESC
            LIMIT ?
        """
        
        predictions = self.db.execute_query(query, (symbol, limit))
        return predictions or []
    
    def get_best_predictions(self, min_confidence: float = 70.0, limit: int = 10) -> List[Dict]:
        """
        Get highest confidence predictions.
        
        Args:
            min_confidence: Minimum confidence threshold
            limit: Number to return
            
        Returns:
            List of high-confidence predictions
        """
        query = """
            SELECT * FROM predictions
            WHERE confidence >= ?
            AND resolved = 0
            ORDER BY confidence DESC
            LIMIT ?
        """
        
        predictions = self.db.execute_query(query, (min_confidence, limit))
        return predictions or []
    
    def print_stats(self):
        """Print prediction service statistics"""
        stats = self.get_model_stats()
        
        print("\n" + "=" * 60)
        print("PREDICTION ENGINE STATISTICS")
        print("=" * 60)
        
        for horizon in ['1H', '1D', '1W']:
            horizon_stats = stats[horizon]
            print(f"\n{horizon} Model:")
            print(f"  Predictions Made: {horizon_stats['predictions_made']}")
            print(f"  Accuracy: {horizon_stats['accuracy']:.1f}%")
        
        print("\n" + "=" * 60)


# Factory function for compatibility
def create_prediction_engine(db_manager, config=None):
    """
    Create prediction service instance.
    
    Args:
        db_manager: Database manager
        config: Optional configuration (not used yet)
        
    Returns:
        PredictionService instance
    """
    return PredictionService(db_manager)
