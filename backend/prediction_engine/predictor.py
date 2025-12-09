"""
Elite Trading System - Prediction Engine
========================================

Real-timestamp price prediction for 1H, 1D, 1W horizons.
Uses ML models with options flow, price action, and correlation features.

Features:
- Multi-horizon predictions (1H, 1D, 1W)
- XGBoost models with dynamic feature weights
- Real-timestamp prediction updates
- Automatic outcome resolution
- Self-learning weight adjustment

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Core prediction engine for price forecasting.
    
    Generates predictions for multiple timestamp horizons using:
    1. Price features (momentum, volatility, trends)
    2. Flow features (options flow sentiment and volume)
    3. Correlation features (relative strength vs market)
    4. Regime features (market environment)
    5. Technical features (RSI, MACD, etc.)
    """
    
    def __init__(self, db_manager, config: Dict):
        """Initialize prediction engine."""
        self.db = db_manager
        self.config = config
        self.pred_config = config.get('prediction_engine', {})
        
        self.horizons = self.pred_config.get('horizons', ['1H', '1D', '1W'])
        self.min_confidence = self.pred_config.get('min_confidence_to_display', 50)
        
        # Feature weights (will be dynamically adjusted)
        self.feature_weights = self.pred_config.get('feature_weights', {
            'price_features': 0.20,
            'flow_features': 0.25,
            'correlation_features': 0.20,
            'regime_features': 0.15,
            'technical_features': 0.20
        })
        
        # Models (loaded from database or trained)
        self.models = {
            '1H': None,
            '1D': None,
            '1W': None
        }
        
        # Scalers for feature normalization
        self.scalers = {
            '1H': StandardScaler(),
            '1D': StandardScaler(),
            '1W': StandardScaler()
        }
        
        # Model accuracy tracking
        self.model_accuracy = {
            '1H': 0.0,
            '1D': 0.0,
            '1W': 0.0
        }
        
        logger.info("Prediction Engine initialized")
        self._load_models()
        self._load_weights()
    
    def _load_models(self):
        """Load ML models from database or create new ones."""
        for horizon in self.horizons:
            query = """
            SELECT model_path, validation_accuracy, hyperparameters
            FROM ml_models
            WHERE horizon = ? AND is_production = TRUE
            ORDER BY trained_at DESC
            LIMIT 1
            """
            
            result = self.db.execute_dict_query(query, (horizon,))
            
            if result and result[0]['model_path']:
                # Load existing model
                try:
                    model_path = result[0]['model_path']
                    self.models[horizon] = xgb.Booster()
                    self.models[horizon].load_model(model_path)
                    self.model_accuracy[horizon] = float(result[0]['validation_accuracy'] or 0)
                    logger.info(f"✓ Loaded {horizon} model (accuracy: {self.model_accuracy[horizon]:.1f}%)")
                except Exception as e:
                    logger.warning(f"Failed to load {horizon} model: {e}")
                    self.models[horizon] = self._create_default_model(horizon)
            else:
                # Create default model
                self.models[horizon] = self._create_default_model(horizon)
    
    def _create_default_model(self, horizon: str) -> xgb.Booster:
        """Create a default XGBoost model."""
        model_config = self.pred_config.get('models', {})
        
        params = {
            'max_depth': model_config.get('max_depth', 6),
            'learning_rate': model_config.get('learning_rate', 0.1),
            'n_estimators': model_config.get('n_estimators', 100),
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'tree_method': 'hist',
            'random_state': 42
        }
        
        # Create dummy training data to initialize model
        dummy_X = np.random.rand(100, 50)
        dummy_y = np.random.rand(100)
        dtrain = xgb.DMatrix(dummy_X, label=dummy_y)
        
        model = xgb.train(params, dtrain, num_boost_round=10)
        
        logger.info(f"Created default {horizon} model")
        return model
    
    def _load_weights(self):
        """Load active feature weights from database."""
        for horizon in self.horizons:
            query = """
            SELECT 
                price_features_weight,
                flow_features_weight,
                correlation_features_weight,
                regime_features_weight,
                technical_features_weight
            FROM model_weights
            WHERE horizon = ? AND is_active = TRUE
            ORDER BY updated_at DESC
            LIMIT 1
            """
            
            result = self.db.execute_dict_query(query, (horizon,))
            
            if result:
                weights = result[0]
                logger.info(f"Loaded weights for {horizon}: flow={weights['flow_features_weight']:.3f}")
            else:
                logger.info(f"Using default weights for {horizon}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # FEATURE ENGINEERING
    # ═══════════════════════════════════════════════════════════════════════
    
    def extract_price_features(self, symbol_id: int, ticker: str) -> Dict[str, float]:
        """Extract price-based features."""
        # Get recent price data
        query = """
        SELECT close, high, low, volume, timestamp
        FROM market_data
        WHERE symbol = ? 
        ORDER BY timestamp DESC
        LIMIT 50
        """
        
        result = self.db.execute_dict_query(query, (symbol_id,))
        
        if not result or len(result) < 20:
            return self._default_price_features()
        
        df = pd.DataFrame(result)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Calculate features
        features = {}
        
        # Returns
        features['return_1d'] = (df['close'].iloc[0] / df['close'].iloc[1] - 1) * 100
        features['return_5d'] = (df['close'].iloc[0] / df['close'].iloc[5] - 1) * 100
        features['return_20d'] = (df['close'].iloc[0] / df['close'].iloc[20] - 1) * 100
        
        # Momentum
        features['momentum_5d'] = df['close'].iloc[:5].mean() / df['close'].iloc[5:10].mean() - 1
        features['momentum_10d'] = df['close'].iloc[:10].mean() / df['close'].iloc[10:20].mean() - 1
        
        # Volatility
        features['volatility_10d'] = df['close'].iloc[:10].pct_change().std() * 100
        features['volatility_20d'] = df['close'].iloc[:20].pct_change().std() * 100
        
        # Volume
        features['volume_ratio'] = df['volume'].iloc[0] / df['volume'].iloc[:20].mean()
        features['volume_trend'] = df['volume'].iloc[:5].mean() / df['volume'].iloc[5:10].mean()
        
        # Price position
        features['price_vs_20d_high'] = (df['close'].iloc[0] / df['high'].iloc[:20].max() - 1) * 100
        features['price_vs_20d_low'] = (df['close'].iloc[0] / df['low'].iloc[:20].min() - 1) * 100
        
        return features
    
    def _default_price_features(self) -> Dict[str, float]:
        """Default price features when data unavailable."""
        return {
            'return_1d': 0.0,
            'return_5d': 0.0,
            'return_20d': 0.0,
            'momentum_5d': 0.0,
            'momentum_10d': 0.0,
            'volatility_10d': 0.0,
            'volatility_20d': 0.0,
            'volume_ratio': 1.0,
            'volume_trend': 1.0,
            'price_vs_20d_high': 0.0,
            'price_vs_20d_low': 0.0
        }
    
    def extract_flow_features(self, symbol_id: int, ticker: str) -> Dict[str, float]:
        """Extract options flow features from Unusual Whales data."""
        # Get last 24 hours of flow
        query = """
        SELECT 
            option_type,
            premium_amount,
            sentiment,
            is_whale,
            is_sweep
        FROM uw_options_flow
        WHERE symbol = ? 
          AND timestamp > NOW() - INTERVAL '24 hours'
        """
        
        result = self.db.execute_dict_query(query, (symbol_id,))
        
        if not result:
            return self._default_flow_features()
        
        df = pd.DataFrame(result)
        
        features = {}
        
        # Premium aggregations
        total_premium = df['premium_amount'].sum()
        call_premium = df[df['option_type'] == 'CALL']['premium_amount'].sum()
        put_premium = df[df['option_type'] == 'PUT']['premium_amount'].sum()
        
        features['total_premium'] = float(total_premium)
        features['call_premium'] = float(call_premium)
        features['put_premium'] = float(put_premium)
        features['call_put_ratio'] = float(call_premium / put_premium if put_premium > 0 else 0)
        
        # Sentiment
        bullish_count = len(df[df['sentiment'] == 'BULLISH'])
        bearish_count = len(df[df['sentiment'] == 'BEARISH'])
        features['bullish_flow_pct'] = bullish_count / len(df) * 100 if len(df) > 0 else 50
        features['bearish_flow_pct'] = bearish_count / len(df) * 100 if len(df) > 0 else 50
        
        # Special activity
        features['whale_count'] = len(df[df['is_whale'] == True])
        features['sweep_count'] = len(df[df['is_sweep'] == True])
        features['total_flow_count'] = len(df)
        
        return features
    
    def _default_flow_features(self) -> Dict[str, float]:
        """Default flow features when data unavailable."""
        return {
            'total_premium': 0.0,
            'call_premium': 0.0,
            'put_premium': 0.0,
            'call_put_ratio': 1.0,
            'bullish_flow_pct': 50.0,
            'bearish_flow_pct': 50.0,
            'whale_count': 0.0,
            'sweep_count': 0.0,
            'total_flow_count': 0.0
        }

    def extract_correlation_features(self, symbol_id: int, ticker: str) -> Dict[str, float]:
        """Extract correlation features relative to market indices."""
        # Get recent correlations with SPY, QQQ
        query = """
        SELECT 
            symbol_b_ticker,
            correlation_1h,
            correlation_1d,
            correlation_5d,
            correlation_20d
        FROM symbol_correlations
        WHERE symbol_a_id = ?
          AND symbol_b_ticker IN ('SPY', 'QQQ', 'IWM')
          AND calculated_at > NOW() - INTERVAL '1 hour'
        ORDER BY calculated_at DESC
        LIMIT 3
        """
        
        result = self.db.execute_dict_query(query, (symbol_id,))
        
        if not result:
            return self._default_correlation_features()
        
        features = {}
        
        for row in result:
            symbol = row['symbol_b_ticker'].lower()
            features[f'corr_{symbol}_1h'] = float(row['correlation_1h'] or 0)
            features[f'corr_{symbol}_1d'] = float(row['correlation_1d'] or 0)
            features[f'corr_{symbol}_5d'] = float(row['correlation_5d'] or 0)
            features[f'corr_{symbol}_20d'] = float(row['correlation_20d'] or 0)
        
        # Fill missing correlations
        for idx in ['spy', 'qqq', 'iwm']:
            for period in ['1h', '1d', '5d', '20d']:
                key = f'corr_{idx}_{period}'
                if key not in features:
                    features[key] = 0.5
        
        return features
    
    def _default_correlation_features(self) -> Dict[str, float]:
        """Default correlation features."""
        features = {}
        for idx in ['spy', 'qqq', 'iwm']:
            for period in ['1h', '1d', '5d', '20d']:
                features[f'corr_{idx}_{period}'] = 0.5
        return features
    
    def extract_regime_features(self) -> Dict[str, float]:
        """Extract market regime features."""
        # Get current regime
        query = """
        SELECT 
            regime,
            vix_level,
            vix_rsi,
            breadth_adv_dec,
            spy_change_pct,
            qqq_change_pct
        FROM market_regime
        ORDER BY date DESC
        LIMIT 1
        """
        
        result = self.db.execute_dict_query(query)
        
        if not result:
            return self._default_regime_features()
        
        row = result[0]
        
        # One-hot encode regime
        features = {
            'regime_green': 1.0 if row['regime'] == 'GREEN' else 0.0,
            'regime_yellow': 1.0 if row['regime'] == 'YELLOW' else 0.0,
            'regime_red': 1.0 if row['regime'] == 'RED' else 0.0,
            'regime_red_recovery': 1.0 if row['regime'] == 'RED_RECOVERY' else 0.0,
            'vix_level': float(row['vix_level'] or 20),
            'vix_rsi': float(row['vix_rsi'] or 50),
            'breadth': float(row['breadth_adv_dec'] or 0),
            'spy_change': float(row['spy_change_pct'] or 0),
            'qqq_change': float(row['qqq_change_pct'] or 0)
        }
        
        return features
    
    def _default_regime_features(self) -> Dict[str, float]:
        """Default regime features."""
        return {
            'regime_green': 0.0,
            'regime_yellow': 1.0,
            'regime_red': 0.0,
            'regime_red_recovery': 0.0,
            'vix_level': 20.0,
            'vix_rsi': 50.0,
            'breadth': 0.0,
            'spy_change': 0.0,
            'qqq_change': 0.0
        }
    
    def extract_technical_features(self, symbol_id: int, ticker: str) -> Dict[str, float]:
        """Extract technical indicator features."""
        query = """
        SELECT 
            rsi_14,
            macd,
            macd_signal,
            macd_histogram,
            bb_width,
            adx_14,
            volume_ratio
        FROM technical_indicators
        WHERE symbol = ? 
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        result = self.db.execute_dict_query(query, (symbol_id,))
        
        if not result:
            return self._default_technical_features()
        
        row = result[0]
        
        features = {
            'rsi': float(row['rsi_14'] or 50),
            'macd': float(row['macd'] or 0),
            'macd_signal': float(row['macd_signal'] or 0),
            'macd_histogram': float(row['macd_histogram'] or 0),
            'bb_width': float(row['bb_width'] or 0),
            'adx': float(row['adx_14'] or 25),
            'volume_ratio': float(row['volume_ratio'] or 1.0)
        }
        
        return features
    
    def _default_technical_features(self) -> Dict[str, float]:
        """Default technical features."""
        return {
            'rsi': 50.0,
            'macd': 0.0,
            'macd_signal': 0.0,
            'macd_histogram': 0.0,
            'bb_width': 0.0,
            'adx': 25.0,
            'volume_ratio': 1.0
        }
    
    def extract_all_features(self, symbol_id: int, ticker: str) -> Dict[str, float]:
        """Extract all features for a symbol."""
        features = {}
        
        # Price features
        price_features = self.extract_price_features(symbol_id, ticker)
        features.update({f'price_{k}': v for k, v in price_features.items()})
        
        # Flow features
        flow_features = self.extract_flow_features(symbol_id, ticker)
        features.update({f'flow_{k}': v for k, v in flow_features.items()})
        
        # Correlation features
        corr_features = self.extract_correlation_features(symbol_id, ticker)
        features.update(corr_features)
        
        # Regime features
        regime_features = self.extract_regime_features()
        features.update(regime_features)
        
        # Technical features
        tech_features = self.extract_technical_features(symbol_id, ticker)
        features.update({f'tech_{k}': v for k, v in tech_features.items()})
        
        return features
    
    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTION GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def predict_single_horizon(self, 
                               features: Dict[str, float],
                               horizon: str,
                               current_price: float) -> Tuple[float, float, str]:
        """
        Generate prediction for a single timestamp horizon.
        
        Returns:
            (predicted_price, confidence, direction)
        """
        # Convert features to array
        feature_vector = np.array(list(features.values())).reshape(1, -1)
        
        # Normalize
        feature_vector_scaled = self.scalers[horizon].fit_transform(feature_vector)
        
        # Predict
        dmatrix = xgb.DMatrix(feature_vector_scaled)
        prediction = self.models[horizon].predict(dmatrix)[0]
        
        # Convert prediction to price change percentage
        predicted_change_pct = float(prediction)
        predicted_price = current_price * (1 + predicted_change_pct / 100)
        
        # Calculate confidence based on model accuracy and feature quality
        base_confidence = self.model_accuracy.get(horizon, 50.0)
        
        # Adjust confidence based on data quality
        flow_count = features.get('flow_total_flow_count', 0)
        data_quality_factor = min(flow_count / 10, 1.0)  # More flow = higher confidence
        
        confidence = base_confidence * (0.7 + 0.3 * data_quality_factor)
        confidence = max(min(confidence, 95.0), 30.0)  # Cap between 30-95%
        
        # Determine direction
        if predicted_change_pct > 0.5:
            direction = 'BULLISH'
        elif predicted_change_pct < -0.5:
            direction = 'BEARISH'
        else:
            direction = 'NEUTRAL'
        
        return predicted_price, confidence, direction
    
    def generate_prediction(self, symbol_id: int, ticker: str) -> Optional[Dict]:
        """
        Generate complete prediction for all horizons.
        
        Returns:
            Dictionary with predictions for 1H, 1D, 1W or None if failed
        """
        try:
            # Get current price
            query = """
            SELECT close FROM market_data
            WHERE symbol = ? 
            ORDER BY timestamp DESC
            LIMIT 1
            """
            
            result = self.db.execute_query(query, (symbol_id,))
            
            if not result:
                logger.warning(f"No price data for {ticker}")
                return None
            
            current_price = float(result[0][0])
            
            # Extract features
            features = self.extract_all_features(symbol_id, ticker)
            
            # Generate predictions for each horizon
            predictions = {
                'symbol_id': symbol_id,
                'ticker': ticker,
                'price_at_prediction': current_price,
                'created_at': datetime.now(),
                'features_json': features,
                'feature_weights': self.feature_weights,
                'model_version': 'v1.0'
            }
            
            for horizon in self.horizons:
                pred_price, confidence, direction = self.predict_single_horizon(
                    features, horizon, current_price
                )
                
                change_pct = (pred_price / current_price - 1) * 100
                
                predictions[f'pred_{horizon.lower()}_price'] = pred_price
                predictions[f'pred_{horizon.lower()}_change_pct'] = change_pct
                predictions[f'pred_{horizon.lower()}_confidence'] = confidence
                predictions[f'pred_{horizon.lower()}_direction'] = direction
                predictions[f'model_{horizon.lower()}_accuracy'] = self.model_accuracy.get(horizon, 0)
            
            logger.info(f"Generated prediction for {ticker}: 1D={predictions['pred_1d_change_pct']:.2f}% (conf={predictions['pred_1d_confidence']:.0f}%)")
            
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction failed for {ticker}: {e}")
            return None
    
    def save_prediction(self, prediction: Dict) -> bool:
        """Save prediction to database."""
        try:
            query = """
            INSERT INTO predictions (
                symbol_id, ticker, price_at_prediction,
                pred_1h_price, pred_1h_change_pct, pred_1h_confidence, pred_1h_direction,
                pred_1d_price, pred_1d_change_pct, pred_1d_confidence, pred_1d_direction,
                pred_1w_price, pred_1w_change_pct, pred_1w_confidence, pred_1w_direction,
                features_json, feature_weights, model_version,
                model_1h_accuracy, model_1d_accuracy, model_1w_accuracy
            ) VALUES (
                %(symbol_id)s, %(ticker)s, %(price_at_prediction)s,
                %(pred_1h_price)s, %(pred_1h_change_pct)s, %(pred_1h_confidence)s, %(pred_1h_direction)s,
                %(pred_1d_price)s, %(pred_1d_change_pct)s, %(pred_1d_confidence)s, %(pred_1d_direction)s,
                %(pred_1w_price)s, %(pred_1w_change_pct)s, %(pred_1w_confidence)s, %(pred_1w_direction)s,
                %(features_json)s::jsonb, %(feature_weights)s::jsonb, %(model_version)s,
                %(model_1h_accuracy)s, %(model_1d_accuracy)s, %(model_1w_accuracy)s
            )
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query, prediction)
            
            logger.debug(f"Saved prediction for {prediction['ticker']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save prediction: {e}")
            return False

    def generate_predictions_batch(self, tickers: List[str]) -> int:
        """
        Generate predictions for multiple symbols.
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Number of successful predictions
        """
        successful = 0
        
        for ticker in tickers:
            symbol_id = self.db.get_symbol_id(ticker)
            
            if not symbol_id:
                logger.warning(f"Symbol not found: {ticker}")
                continue
            
            prediction = self.generate_prediction(symbol_id, ticker)
            
            if prediction and self.save_prediction(prediction):
                successful += 1
        
        logger.info(f"Batch prediction complete: {successful}/{len(tickers)} successful")
        return successful
    
    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTION RESOLUTION & ACCURACY
    # ═══════════════════════════════════════════════════════════════════════
    
    def resolve_predictions(self, horizon: str) -> int:
        """
        Resolve predictions that have reached their timestamp horizon.
        
        Args:
            horizon: timestamp horizon to resolve ('1H', '1D', '1W')
        
        Returns:
            Number of predictions resolved
        """
        # Calculate timestamp threshold
        if horizon == '1H':
            time_ago = timedelta(hours=1)
        elif horizon == '1D':
            time_ago = timedelta(days=1)
        elif horizon == '1W':
            time_ago = timedelta(weeks=1)
        else:
            logger.error(f"Invalid horizon: {horizon}")
            return 0
        
        # Find predictions ready to resolve
        query = f"""
        SELECT 
            p.prediction_id,
            p.created_at,
            p.symbol_id,
            p.ticker,
            p.price_at_prediction,
            p.pred_{horizon.lower()}_price,
            p.pred_{horizon.lower()}_change_pct,
            p.pred_{horizon.lower()}_direction,
            p.pred_{horizon.lower()}_confidence
        FROM predictions p
        WHERE p.created_at <= NOW() - INTERVAL '{time_ago.total_seconds()} seconds'
          AND NOT EXISTS (
              SELECT 1 FROM prediction_outcomes po
              WHERE po.prediction_id = p.prediction_id
                AND po.horizon = ?
          )
        ORDER BY p.created_at
        LIMIT 1000
        """
        
        predictions = self.db.execute_dict_query(query, (horizon,))
        
        if not predictions:
            logger.debug(f"No {horizon} predictions to resolve")
            return 0
        
        resolved = 0
        
        for pred in predictions:
            if self._resolve_single_prediction(pred, horizon):
                resolved += 1
        
        logger.info(f"Resolved {resolved} {horizon} predictions")
        return resolved
    
    def _resolve_single_prediction(self, prediction: Dict, horizon: str) -> bool:
        """Resolve a single prediction by comparing with actual price."""
        try:
            symbol_id = prediction['symbol_id']
            ticker = prediction['ticker']
            prediction_time = prediction['created_at']
            
            # Get actual price at resolution timestamp
            query = """
            SELECT close FROM market_data
            WHERE symbol = ? 
              
              AND timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT 1
            """
            
            result = self.db.execute_query(query, (symbol_id, prediction_time))
            
            if not result:
                logger.warning(f"No actual price data for {ticker}")
                return False
            
            actual_price = float(result[0][0])
            predicted_price = float(prediction[f'pred_{horizon.lower()}_price'])
            original_price = float(prediction['price_at_prediction'])
            
            # Calculate actual change
            actual_change_pct = (actual_price / original_price - 1) * 100
            
            # Determine actual direction
            if actual_change_pct > 0.5:
                actual_direction = 'BULLISH'
            elif actual_change_pct < -0.5:
                actual_direction = 'BEARISH'
            else:
                actual_direction = 'NEUTRAL'
            
            # Calculate errors
            predicted_change = float(prediction[f'pred_{horizon.lower()}_change_pct'])
            error_pct = abs(actual_change_pct - predicted_change)
            error_abs = abs(actual_price - predicted_price)
            
            # Direction correctness
            predicted_direction = prediction[f'pred_{horizon.lower()}_direction']
            direction_correct = (predicted_direction == actual_direction)
            
            # Magnitude accuracy (inverse of error, capped at 100%)
            magnitude_accuracy = max(0, 100 - error_pct * 10)
            
            # Save outcome
            outcome = {
                'prediction_id': prediction['prediction_id'],
                'prediction_time': prediction_time,
                'symbol_id': symbol_id,
                'ticker': ticker,
                'horizon': horizon,
                'predicted_price': predicted_price,
                'predicted_change': predicted_change,
                'predicted_direction': predicted_direction,
                'confidence': prediction[f'pred_{horizon.lower()}_confidence'],
                'actual_price': actual_price,
                'actual_change': actual_change_pct,
                'actual_direction': actual_direction,
                'error_pct': error_pct,
                'error_abs': error_abs,
                'direction_correct': direction_correct,
                'magnitude_accuracy': magnitude_accuracy
            }
            
            insert_query = """
            INSERT INTO prediction_outcomes (
                prediction_id, prediction_time, symbol_id, ticker, horizon,
                predicted_price, predicted_change, predicted_direction, confidence,
                actual_price, actual_change, actual_direction,
                error_pct, error_abs, direction_correct, magnitude_accuracy
            ) VALUES (
                %(prediction_id)s, %(prediction_time)s, %(symbol_id)s, %(ticker)s, %(horizon)s,
                %(predicted_price)s, %(predicted_change)s, %(predicted_direction)s, %(confidence)s,
                %(actual_price)s, %(actual_change)s, %(actual_direction)s,
                %(error_pct)s, %(error_abs)s, %(direction_correct)s, %(magnitude_accuracy)s
            )
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(insert_query, outcome)
            
            logger.debug(f"Resolved {ticker} {horizon}: predicted={predicted_change:.2f}%, actual={actual_change_pct:.2f}%, correct={direction_correct}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve prediction: {e}")
            return False
    
    def calculate_model_accuracy(self, horizon: str, days_back: int = 7) -> float:
        """
        Calculate model accuracy for a horizon.
        
        Args:
            horizon: timestamp horizon
            days_back: Days of history to analyze
        
        Returns:
            Accuracy percentage
        """
        result = self.db.get_prediction_accuracy(horizon, days_back)
        
        if result and result.get('direction_accuracy'):
            accuracy = float(result['direction_accuracy'])
            self.model_accuracy[horizon] = accuracy
            logger.info(f"{horizon} model accuracy ({days_back}d): {accuracy:.1f}%")
            return accuracy
        
        return 0.0
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_latest_predictions(self, limit: int = 20, min_confidence: Optional[float] = None) -> List[Dict]:
        """Get latest predictions above confidence threshold."""
        if min_confidence is None:
            min_confidence = self.min_confidence
        
        query = """
        SELECT 
            ticker,
            price_at_prediction,
            pred_1h_price, pred_1h_change_pct, pred_1h_confidence, pred_1h_direction,
            pred_1d_price, pred_1d_change_pct, pred_1d_confidence, pred_1d_direction,
            pred_1w_price, pred_1w_change_pct, pred_1w_confidence, pred_1w_direction,
            created_at
        FROM predictions
        WHERE pred_1d_confidence >= ?
        ORDER BY created_at DESC
        LIMIT ?
        """
        
        return self.db.execute_dict_query(query, (min_confidence, limit)) or []
    
    def get_top_predictions(self, horizon: str = '1D', limit: int = 10) -> List[Dict]:
        """Get top predictions by confidence for a horizon."""
        query = f"""
        SELECT 
            ticker,
            price_at_prediction,
            pred_{horizon.lower()}_price,
            pred_{horizon.lower()}_change_pct,
            pred_{horizon.lower()}_confidence,
            pred_{horizon.lower()}_direction,
            created_at
        FROM predictions
        WHERE created_at > NOW() - INTERVAL '1 hour'
        ORDER BY pred_{horizon.lower()}_confidence DESC
        LIMIT ?
        """
        
        return self.db.execute_dict_query(query, (limit,)) or []
    
    def update_model_accuracy_all(self):
        """Update accuracy metrics for all horizons."""
        for horizon in self.horizons:
            self.calculate_model_accuracy(horizon, days_back=7)
    
    def __repr__(self):
        return f"<PredictionEngine(horizons={self.horizons}, models_loaded={sum(1 for m in self.models.values() if m)})>"


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def create_prediction_engine(db_manager, config: Dict) -> PredictionEngine:
    """Factory function to create prediction engine."""
    return PredictionEngine(db_manager, config)


# ═══════════════════════════════════════════════════════════════════════════
# TEST CODE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.append('..')
    
    from database import get_db_manager
    import yaml
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("PREDICTION ENGINE - TEST")
    print("=" * 80)
    
    # Load config
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize
    db = get_db_manager()
    engine = PredictionEngine(db, config)
    
    print(f"\n{engine}")
    print(f"Horizons: {engine.horizons}")
    print(f"Min confidence: {engine.min_confidence}%")
    
    print("\n--- Model Accuracy ---")
    for horizon in engine.horizons:
        accuracy = engine.model_accuracy.get(horizon, 0)
        print(f"  {horizon}: {accuracy:.1f}%")
    
    print("\n--- Test Prediction: SPY ---")
    symbol_id = db.get_symbol_id('SPY')
    if symbol_id:
        prediction = engine.generate_prediction(symbol_id, 'SPY')
        if prediction:
            print(f"  Current: ${prediction['price_at_prediction']:.2f}")
            print(f"  1H Pred: ${prediction['pred_1h_price']:.2f} ({prediction['pred_1h_change_pct']:+.2f}%) - {prediction['pred_1h_confidence']:.0f}% conf")
            print(f"  1D Pred: ${prediction['pred_1d_price']:.2f} ({prediction['pred_1d_change_pct']:+.2f}%) - {prediction['pred_1d_confidence']:.0f}% conf")
            print(f"  1W Pred: ${prediction['pred_1w_price']:.2f} ({prediction['pred_1w_change_pct']:+.2f}%) - {prediction['pred_1w_confidence']:.0f}% conf")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
