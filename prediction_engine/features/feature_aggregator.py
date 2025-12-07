"""
Feature Aggregator - Combines Price, Flow, and Correlation Features
Generates comprehensive feature sets for prediction models.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class FeatureSet:
    """Container for aggregated features."""
    symbol: str
    timestamp: datetime
    
    # Price features
    price_current: float
    price_change_1h: Optional[float] = None
    price_change_1d: Optional[float] = None
    price_change_5d: Optional[float] = None
    price_volatility_20: Optional[float] = None
    
    # Volume features
    volume_current: int = 0
    volume_avg_20: Optional[float] = None
    volume_ratio: Optional[float] = None
    volume_surge: bool = False
    
    # Technical features
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_position: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    
    # Momentum features
    momentum_1d: Optional[float] = None
    momentum_5d: Optional[float] = None
    rate_of_change: Optional[float] = None
    
    # Flow features (options/unusual activity)
    put_call_ratio: Optional[float] = None
    unusual_activity: bool = False
    dark_pool_flow: Optional[float] = None
    
    # Correlation features
    spy_correlation: Optional[float] = None
    sector_correlation: Optional[float] = None
    beta: Optional[float] = None
    
    # Market context
    market_regime: Optional[str] = None
    vix: Optional[float] = None
    spy_change: Optional[float] = None
    
    # Pattern features
    compression_detected: bool = False
    ignition_detected: bool = False
    breakout_strength: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_array(self, feature_names: List[str] = None) -> np.ndarray:
        """
        Convert to numpy array for ML models.
        
        Args:
            feature_names: Specific features to include
            
        Returns:
            Numpy array of feature values
        """
        data = self.to_dict()
        
        if feature_names:
            values = [data.get(name, 0.0) for name in feature_names]
        else:
            # Use all numeric features
            values = [v for v in data.values() if isinstance(v, (int, float))]
        
        # Handle None values
        values = [0.0 if v is None else float(v) for v in values]
        
        return np.array(values)


class FeatureAggregator:
    """
    Aggregates features from multiple sources for prediction.
    Combines price, volume, technical, flow, and correlation data.
    """
    
    def __init__(self, query_engine):
        """
        Initialize feature aggregator.
        
        Args:
            query_engine: QueryEngine instance for data access
        """
        self.qe = query_engine
        logger.info("FeatureAggregator initialized")
    
    def aggregate_features(
        self, 
        symbol: str,
        lookback_bars: int = 50
    ) -> FeatureSet:
        """
        Aggregate all features for a symbol.
        
        Args:
            symbol: Stock symbol
            lookback_bars: Number of historical bars to analyze
            
        Returns:
            FeatureSet with all aggregated features
        """
        try:
            logger.debug(f"Aggregating features for {symbol}")
            
            # Get price history
            start_date = datetime.now() - timedelta(days=lookback_bars)
            prices_df = self.qe.get_price_history(symbol, start_date)
            
            if prices_df.empty:
                logger.warning(f"No price data for {symbol}")
                return self._empty_features(symbol)
            
            # Get latest technicals
            technicals_df = self.qe.get_latest_technicals([symbol])
            
            # Build feature set
            features = FeatureSet(
                symbol=symbol,
                timestamp=datetime.now(),
                **self._extract_price_features(prices_df),
                **self._extract_volume_features(prices_df),
                **self._extract_technical_features(technicals_df),
                **self._extract_momentum_features(prices_df),
                **self._extract_flow_features(symbol),
                **self._extract_correlation_features(symbol, prices_df),
                **self._extract_market_context(),
                **self._extract_pattern_features(symbol)
            )
            
            logger.debug(f"Feature aggregation complete for {symbol}")
            return features
            
        except Exception as e:
            logger.error(f"Error aggregating features for {symbol}: {e}")
            return self._empty_features(symbol)
    
    def _extract_price_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract price-based features."""
        if df.empty:
            return {}
        
        try:
            return {
                'price_current': float(df['close'].iloc[-1]),
                'price_change_1d': float(df['close'].pct_change().iloc[-1]) if len(df) > 1 else None,
                'price_change_5d': float(df['close'].pct_change(5).iloc[-1]) if len(df) > 5 else None,
                'price_volatility_20': float(df['close'].pct_change().tail(20).std()) if len(df) >= 20 else None,
            }
        except Exception as e:
            logger.error(f"Error extracting price features: {e}")
            return {}
    
    def _extract_volume_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract volume-based features."""
        if df.empty:
            return {}
        
        try:
            volume_current = int(df['volume'].iloc[-1])
            volume_avg_20 = float(df['volume'].tail(20).mean()) if len(df) >= 20 else None
            volume_ratio = volume_current / volume_avg_20 if volume_avg_20 else None
            
            return {
                'volume_current': volume_current,
                'volume_avg_20': volume_avg_20,
                'volume_ratio': volume_ratio,
                'volume_surge': volume_ratio > 1.5 if volume_ratio else False
            }
        except Exception as e:
            logger.error(f"Error extracting volume features: {e}")
            return {}
    
    def _extract_technical_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract technical indicator features."""
        if df.empty:
            return {}
        
        try:
            row = df.iloc[0]
            return {
                'rsi': float(row['rsi']) if 'rsi' in row else None,
                'macd': float(row['macd']) if 'macd' in row else None,
                'macd_signal': float(row['macd_signal']) if 'macd_signal' in row else None,
                'bb_position': float(row['bb_position']) if 'bb_position' in row else None,
                'sma_20': float(row['sma_20']) if 'sma_20' in row else None,
                'sma_50': float(row['sma_50']) if 'sma_50' in row else None,
                'ema_12': float(row['ema_12']) if 'ema_12' in row else None,
                'ema_26': float(row['ema_26']) if 'ema_26' in row else None,
            }
        except Exception as e:
            logger.error(f"Error extracting technical features: {e}")
            return {}
    
    def _extract_momentum_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract momentum features."""
        if df.empty or len(df) < 2:
            return {}
        
        try:
            # Calculate rate of change
            roc = ((df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100) if len(df) >= 10 else None
            
            return {
                'momentum_1d': float(df['close'].diff().iloc[-1]) if len(df) > 1 else None,
                'momentum_5d': float(df['close'].diff(5).iloc[-1]) if len(df) > 5 else None,
                'rate_of_change': roc
            }
        except Exception as e:
            logger.error(f"Error extracting momentum features: {e}")
            return {}
    
    def _extract_flow_features(self, symbol: str) -> Dict[str, Any]:
        """Extract options flow and unusual activity features."""
        try:
            # Query unusual whales / options data
            flow_data = self.qe.execute_raw_query(
                """
                SELECT put_call_ratio, unusual_activity, dark_pool_flow
                FROM options_flow
                WHERE symbol = :symbol
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                {'symbol': symbol}
            )
            
            if not flow_data.empty:
                row = flow_data.iloc[0]
                return {
                    'put_call_ratio': float(row['put_call_ratio']) if pd.notna(row['put_call_ratio']) else None,
                    'unusual_activity': bool(row['unusual_activity']) if 'unusual_activity' in row else False,
                    'dark_pool_flow': float(row['dark_pool_flow']) if pd.notna(row['dark_pool_flow']) else None
                }
            
            return {}
            
        except Exception as e:
            logger.debug(f"No flow data for {symbol}: {e}")
            return {}
    
    def _extract_correlation_features(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract correlation with market/sector."""
        if df.empty or len(df) < 20:
            return {}
        
        try:
            # Get SPY data for correlation
            start_date = df['timestamp'].min()
            spy_df = self.qe.get_price_history('SPY', start_date)
            
            if not spy_df.empty and len(spy_df) >= 20:
                # Calculate correlation
                merged = pd.merge(
                    df[['timestamp', 'close']],
                    spy_df[['timestamp', 'close']],
                    on='timestamp',
                    suffixes=('_stock', '_spy')
                )
                
                if len(merged) >= 20:
                    correlation = merged['close_stock'].corr(merged['close_spy'])
                    
                    # Calculate beta
                    stock_returns = merged['close_stock'].pct_change()
                    spy_returns = merged['close_spy'].pct_change()
                    covariance = stock_returns.cov(spy_returns)
                    spy_variance = spy_returns.var()
                    beta = covariance / spy_variance if spy_variance != 0 else None
                    
                    return {
                        'spy_correlation': float(correlation) if pd.notna(correlation) else None,
                        'beta': float(beta) if beta and pd.notna(beta) else None
                    }
            
            return {}
            
        except Exception as e:
            logger.debug(f"Error calculating correlations: {e}")
            return {}
    
    def _extract_market_context(self) -> Dict[str, Any]:
        """Extract overall market context features."""
        try:
            # Get latest market data (VIX, SPY change, etc.)
            market_data = self.qe.execute_raw_query(
                """
                SELECT vix, spy_change, market_regime
                FROM market_data
                ORDER BY timestamp DESC
                LIMIT 1
                """
            )
            
            if not market_data.empty:
                row = market_data.iloc[0]
                return {
                    'vix': float(row['vix']) if pd.notna(row['vix']) else None,
                    'spy_change': float(row['spy_change']) if pd.notna(row['spy_change']) else None,
                    'market_regime': str(row['market_regime']) if 'market_regime' in row else None
                }
            
            return {}
            
        except Exception as e:
            logger.debug(f"No market context data: {e}")
            return {}
    
    def _extract_pattern_features(self, symbol: str) -> Dict[str, Any]:
        """Extract pattern detection features."""
        try:
            # Query recent signals from your signal engines
            signals = self.qe.get_recent_signals(hours=24)
            
            symbol_signals = signals[signals['symbol'] == symbol] if not signals.empty else pd.DataFrame()
            
            return {
                'compression_detected': bool(len(symbol_signals[symbol_signals['signal_type'] == 'compression']) > 0),
                'ignition_detected': bool(len(symbol_signals[symbol_signals['signal_type'] == 'ignition']) > 0),
                'breakout_strength': float(symbol_signals['score'].max()) if not symbol_signals.empty else None
            }
            
        except Exception as e:
            logger.debug(f"No pattern data for {symbol}: {e}")
            return {}
    
    def _empty_features(self, symbol: str) -> FeatureSet:
        """Return empty feature set when data is unavailable."""
        return FeatureSet(
            symbol=symbol,
            timestamp=datetime.now(),
            price_current=0.0
        )
    
    def aggregate_batch(self, symbols: List[str]) -> Dict[str, FeatureSet]:
        """
        Aggregate features for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to FeatureSets
        """
        logger.info(f"Aggregating features for {len(symbols)} symbols")
        
        results = {}
        for symbol in symbols:
            try:
                features = self.aggregate_features(symbol)
                results[symbol] = features
            except Exception as e:
                logger.error(f"Failed to aggregate {symbol}: {e}")
                results[symbol] = self._empty_features(symbol)
        
        logger.info(f"Batch aggregation complete: {len(results)} symbols")
        return results


if __name__ == "__main__":
    # Example usage
    from database.timescale_manager import get_db_session
    from database.query_engine import QueryEngine
    
    session = get_db_session()
    qe = QueryEngine(session)
    aggregator = FeatureAggregator(qe)
    
    # Test feature aggregation
    symbols = ['AAPL', 'TSLA', 'NVDA']
    
    print("Aggregating features for", symbols)
    features = aggregator.aggregate_batch(symbols)
    
    for symbol, feat in features.items():
        print(f"\n{symbol} Features:")
        print(f"  Price: ${feat.price_current:.2f}")
        print(f"  RSI: {feat.rsi}")
        print(f"  Volume Ratio: {feat.volume_ratio}")
        print(f"  Compression: {feat.compression_detected}")
    
    qe.close()
