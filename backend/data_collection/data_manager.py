"""
Unified Data Manager - Coordinates all data sources with rate limiting and caching
"""
import logging
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from threading import Lock
import yfinance as yf
import yaml

logger = logging.getLogger(__name__)

class DataManager:
    """
    Central data coordinator for all market data sources.
    Handles rate limiting, caching, fallbacks, and data normalization.
    """
    
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize data manager with rate limiting and caching"""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Rate limiting
        self.last_request_time = {}
        self.request_lock = Lock()
        
        # Caching (5 minute cache for price data)
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # Data sources priority order
        self.data_sources = ['yfinance', 'unusual_whales']
        
        logger.info("Data Manager initialized")
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _check_rate_limit(self, source: str, min_interval: float = 1.0) -> bool:
        """
        Check if we can make a request to this source without hitting rate limits
        
        Args:
            source: Data source name
            min_interval: Minimum seconds between requests
        
        Returns:
            True if we can proceed, False if we need to wait
        """
        with self.request_lock:
            now = time.time()
            last_request = self.last_request_time.get(source, 0)
            
            if now - last_request < min_interval:
                wait_time = min_interval - (now - last_request)
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {source}")
                time.sleep(wait_time)
            
            self.last_request_time[source] = time.time()
            return True
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if fresh"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self.cache_duration:
                logger.debug(f"Cache hit for {cache_key} (age: {age:.1f}s)")
                return data
            else:
                logger.debug(f"Cache expired for {cache_key}")
                del self.cache[cache_key]
        
        return None
    
    def _cache_data(self, cache_key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[cache_key] = (data, datetime.now())
        logger.debug(f"Cached data for {cache_key}")
    
    def get_market_data(self, symbol: str, period: str = '5d', interval: str = '1h') -> Optional[Dict]:
        """
        Get market data for a symbol with caching and fallbacks
        
        Args:
            symbol: Stock ticker (e.g., 'SPY')
            period: Data period ('1d', '5d', '1mo', etc.)
            interval: Data interval ('1m', '5m', '1h', '1d', etc.)
        
        Returns:
            Dict with OHLCV data and metadata
        """
        cache_key = f"market_{symbol}_{period}_{interval}"
        
        # Check cache first
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        # Try each data source in priority order
        for source in self.data_sources:
            try:
                if source == 'yfinance':
                    data = self._fetch_yfinance(symbol, period, interval)
                elif source == 'unusual_whales':
                    data = self._fetch_unusual_whales(symbol)
                else:
                    continue
                
                if data:
                    self._cache_data(cache_key, data)
                    return data
                    
            except Exception as e:
                logger.warning(f"{source} failed for {symbol}: {e}")
                continue
        
        logger.error(f"All data sources failed for {symbol}")
        return None
    
    def _fetch_yfinance(self, symbol: str, period: str, interval: str) -> Optional[Dict]:
        """
        Fetch data from yfinance with rate limiting
        
        Returns normalized data structure
        """
        self._check_rate_limit('yfinance', min_interval=0.5)
        
        try:
            logger.info(f"Fetching {symbol} from yfinance (period={period}, interval={interval})")
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned from yfinance for {symbol}")
                return None
            
            # Normalize data structure
            current_price = float(df['Close'].iloc[-1])
            
            data = {
                'symbol': symbol,
                'source': 'yfinance',
                'timestamp': datetime.now().isoformat(),
                'price': {
                    'current': round(current_price, 2),
                    'open': round(float(df['Open'].iloc[-1]), 2),
                    'high': round(float(df['High'].iloc[-1]), 2),
                    'low': round(float(df['Low'].iloc[-1]), 2),
                    'close': round(current_price, 2)
                },
                'volume': {
                    'current': int(df['Volume'].iloc[-1]),
                    'average': int(df['Volume'].mean()),
                    'surge': round(df['Volume'].iloc[-1] / df['Volume'].mean(), 2) if df['Volume'].mean() > 0 else 1.0
                },
                'technicals': {
                    'high_5d': round(float(df['High'].max()), 2),
                    'low_5d': round(float(df['Low'].min()), 2),
                    'atr_14': self._calculate_atr(df, period=14)
                },
                'raw_data': df.to_dict()
            }
            
            logger.info(f"Successfully fetched {symbol}: ${current_price}")
            return data
            
        except Exception as e:
            logger.error(f"yfinance error for {symbol}: {e}")
            return None
    
    def _calculate_atr(self, df, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = df['High']
            low = df['Low']
            close = df['Close'].shift(1)
            
            tr1 = high - low
            tr2 = abs(high - close)
            tr3 = abs(low - close)
            
            tr = tr1.combine(tr2, max).combine(tr3, max)
            atr = tr.rolling(window=period).mean().iloc[-1]
            
            return round(float(atr), 2)
        except:
            return 0.0
    
    def _fetch_unusual_whales(self, symbol: str) -> Optional[Dict]:
        """
        Placeholder for Unusual Whales integration
        Will be implemented once API endpoints are confirmed
        """
        logger.debug(f"Unusual Whales not yet implemented for {symbol}")
        return None
    
    def get_batch_market_data(self, symbols: List[str], period: str = '5d', interval: str = '1h') -> Dict[str, Dict]:
        """
        Get market data for multiple symbols efficiently
        
        Args:
            symbols: List of stock tickers
            period: Data period
            interval: Data interval
        
        Returns:
            Dict mapping symbol -> market data
        """
        results = {}
        
        logger.info(f"Fetching batch data for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                data = self.get_market_data(symbol, period, interval)
                if data:
                    results[symbol] = data
                else:
                    logger.warning(f"No data for {symbol}")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(results)}/{len(symbols)} symbols")
        return results
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Cache cleared")


# Global instance
_data_manager = None

def get_data_manager(config_path: str = 'config/config.yaml') -> DataManager:
    """Get or create data manager singleton"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(config_path)
    return _data_manager
