"""
Model Trainer - Train XGBoost models on historical data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from typing import Dict, Tuple
from datetime import datetime

from backend.core.logger import get_logger

logger = get_logger(__name__)

class ModelTrainer:
    """
    Train ML models to predict trade outcomes
    Uses XGBoost for classification (WIN/LOSS)
    """
    
    def __init__(self):
        self.model = None
        self.model_path = Path(__file__).parent.parent / "data/models/xgboost_model.pkl"
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing model
        self._load_model()
    
    def train(self, trade_data: pd.DataFrame) -> Dict:
        """
        Train model on historical trades
        
        Args:
            trade_data: DataFrame with features and outcomes
        
        Returns:
            Dict with training metrics
        """
        logger.info(f"Training model on {len(trade_data)} trades...")
        
        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, classification_report
            
            # Prepare features
            X, y = self._prepare_features(trade_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train XGBoost
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                objective='binary:logistic',
                random_state=42
            )
            
            self.model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model
            self._save_model()
            
            logger.info(f"✅ Model trained: {accuracy:.1%} accuracy")
            
            return {
                'accuracy': accuracy,
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            logger.error("XGBoost not installed. Run: pip install xgboost")
            return {}
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {}
    
    def predict(self, features: Dict) -> float:
        """
        Predict win probability for a signal
        
        Args:
            features: Signal features
        
        Returns:
            Win probability (0-1)
        """
        if self.model is None:
            return 0.5  # Neutral if no model
        
        try:
            # Convert to DataFrame
            X = pd.DataFrame([features])
            
            # Predict probability
            proba = self.model.predict_proba(X)[0][1]
            
            return proba
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 0.5
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extract features from trade data
        
        Returns:
            (X, y) where X is features and y is outcome (0/1)
        """
        # Features to use
        feature_cols = [
            'velez_score',
            'explosive_signal',
            'compression_days',
            'volume_ratio',
            'fresh_ignition_mins',
            'whale_sentiment_score'
        ]
        
        # Create feature DataFrame
        X = pd.DataFrame()
        
        for col in feature_cols:
            if col in df.columns:
                X[col] = df[col]
            else:
                X[col] = 0  # Fill missing with 0
        
        # Target variable (WIN = 1, LOSS = 0)
        y = (df['outcome'] == 'WIN').astype(int)
        
        return X, y
    
    def _save_model(self):
        """Save trained model to disk"""
        try:
            joblib.dump(self.model, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load model from disk"""
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Model loaded from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

# Global instance
trainer = ModelTrainer()

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    # Create mock training data
    mock_data = pd.DataFrame({
        'velez_score': np.random.uniform(60, 95, 100),
        'explosive_signal': np.random.choice([0, 1], 100),
        'compression_days': np.random.randint(3, 15, 100),
        'volume_ratio': np.random.uniform(1.2, 2.5, 100),
        'fresh_ignition_mins': np.random.randint(5, 45, 100),
        'whale_sentiment_score': np.random.uniform(40, 90, 100),
        'outcome': np.random.choice(['WIN', 'LOSS'], 100, p=[0.65, 0.35])
    })
    
    print("\n🤖 Testing model trainer...")
    metrics = trainer.train(mock_data)
    
    if metrics:
        print(f"\n✅ Training complete:")
        print(f"   Accuracy: {metrics['accuracy']:.1%}")
        print(f"   Training samples: {metrics['train_samples']}")
        print(f"   Test samples: {metrics['test_samples']}")
        
        # Test prediction
        test_signal = {
            'velez_score': 88.0,
            'explosive_signal': 1,
            'compression_days': 7,
            'volume_ratio': 1.9,
            'fresh_ignition_mins': 18,
            'whale_sentiment_score': 75.0
        }
        
        prob = trainer.predict(test_signal)
        print(f"\n   Test prediction: {prob:.1%} win probability")
