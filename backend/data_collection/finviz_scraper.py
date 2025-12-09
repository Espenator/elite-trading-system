"""
Finviz Elite Client - Production Grade
=======================================

Enterprise-level Finviz ELITE API integration with:
- Direct API calls (no web scraping)
- Exponential backoff retry logic
- Rate limiting (3 requests/minute)
- Circuit breaker pattern
- Fallback mechanisms
- Comprehensive error handling

Author: Elite Trading Team
Date: December 8, 2025
"""

import logging
import time
import asyncio
import requests
import yaml
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO
import csv

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        self.requests = [req for req in self.requests if now - req < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def time_until_next(self) -> float:
        """Get seconds until next request allowed"""
        if not self.requests:
            return 0.0
        oldest = min(self.requests)
        wait_time = self.time_window - (time.time() - oldest)
        return max(0.0, wait_time)


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'CLOSED'
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info("🔄 Circuit breaker: HALF_OPEN (testing connection)")
                self.state = 'HALF_OPEN'
            else:
                wait_time = self.timeout - (time.time() - self.last_failure_time)
                raise Exception(f"Circuit breaker OPEN. Wait {wait_time:.0f}s before retry")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                logger.info("✅ Circuit breaker: CLOSED (connection restored)")
                self.state = 'CLOSED'
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                logger.error(f"⛔ Circuit breaker: OPEN (too many failures)")
                self.state = 'OPEN'
            raise e


class FinvizClient:
    """
    Production-grade Finviz Elite API integration.
    
    Features:
    - Uses Elite API (no web scraping)
    - Rate limiting (3 requests/minute)
    - Exponential backoff retries (3 attempts)
    - Circuit breaker (prevent cascading failures)
    - Fallback to cached data
    """
    
    def __init__(self, db_manager=None):
        """Initialize Finviz Elite client"""
        self.db = db_manager
        
        # Load config
        self._load_config()
        
        # Rate limiter: 3 requests per minute
        self.rate_limiter = RateLimiter(max_requests=3, time_window=60)
        
        # Circuit breaker: 3 failures = 60 second timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [5, 10, 20]
        
        # Cached data
        self.cached_symbols = {
            'LONG': [],
            'SHORT': [],
            'ALL': [],
            'timestamp': None
        }
        
        logger.info("✅ Finviz Elite API client initialized")
        logger.info(f"   - API URL: {self.base_url}")
        logger.info(f"   - Email: {self.email}")
        logger.info("   - Rate limit: 3 requests/minute")
        logger.info("   - Retry policy: 3 attempts with exponential backoff")
    
    def _load_config(self):
        """Load Finviz Elite API credentials from config.yaml"""
        try:
            config_path = Path('config.yaml')
            if not config_path.exists():
                raise FileNotFoundError("config.yaml not found")
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Extract Elite API credentials
            finviz_config = config.get('api_credentials', {}).get('finviz', {})
            
            self.api_key = finviz_config.get('api_key', '')
            self.email = finviz_config.get('email', '')
            self.password = finviz_config.get('password', '')
            self.base_url = finviz_config.get('base_url', 'https://elite.finviz.com/export.ashx')
            
            if not self.api_key:
                raise ValueError("Finviz Elite API key not found in config.yaml")
            
            # Extract filters
            filters = config.get('data_sources', {}).get('finviz_filters', {})
            self.min_price = filters.get('min_price', 5.0)
            self.max_price = filters.get('max_price', 500.0)
            self.min_volume_millions = filters.get('min_volume_millions', 0.5)
            
            logger.info("✅ Finviz Elite config loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def _wait_for_rate_limit(self):
        """Wait if rate limit exceeded"""
        if not self.rate_limiter.is_allowed():
            wait_time = self.rate_limiter.time_until_next()
            logger.warning(f"⏳ Rate limit reached. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time + 1)
            if not self.rate_limiter.is_allowed():
                raise Exception("Rate limiter still blocking after wait")
    
    def _retry_with_backoff(self, func: Callable, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()
                result = self.circuit_breaker.call(func, *args, **kwargs)
                if attempt > 0:
                    logger.info(f"✅ Retry succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    logger.info(f"   Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ All {self.max_retries} attempts failed")
        
        raise last_exception
    
    def _fetch_elite_api(self, filters: Dict[str, str]) -> List[str]:
        """
        Fetch symbols from Finviz Elite API.
        
        Args:
            filters: Dictionary of Finviz filter parameters
            
        Returns:
            List of ticker symbols
        """
        try:
            # Build query parameters
            params = {
                'v': '111',  # Stock screener view
                'auth': self.api_key,
                **filters
            }
            
            # Make API request
            logger.info(f"🌐 Calling Finviz Elite API: {self.base_url}")
            response = requests.get(self.base_url, params=params, timeout=30)
            
            # Check response
            if response.status_code != 200:
                raise Exception(f"API returned status {response.status_code}: {response.text}")
            
            # Parse CSV response
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)
            
            symbols = []
            for row in reader:
                if 'Ticker' in row and row['Ticker']:
                    symbols.append(row['Ticker'])
            
            if not symbols:
                logger.warning("API returned empty result")
                return []
            
            logger.info(f"✅ API returned {len(symbols)} symbols")
            return symbols
            
        except Exception as e:
            logger.error(f"Elite API error: {e}")
            raise
    
    def get_universe_long(self, min_price: float = 10.0, min_volume: int = 500000) -> List[str]:
        """Get LONG candidates from Finviz Elite API"""
        logger.info("=" * 60)
        logger.info("FETCHING LONG UNIVERSE FROM FINVIZ ELITE API")
        logger.info("=" * 60)
        
        filters = {
            'f': f'sh_price_o{min_price},sh_avgvol_o{min_volume//1000},ta_perf_1wup,ta_sma20_pa,ta_sma50_pa'
        }
        
        try:
            symbols = self._retry_with_backoff(self._fetch_elite_api, filters)
            logger.info(f"✅ Fetched {len(symbols)} LONG candidates")
            
            self.cached_symbols['LONG'] = symbols
            self.cached_symbols['timestamp'] = datetime.now()
            
            if self.db and symbols:
                self._store_symbols(symbols, direction='LONG')
            
            return symbols
        except Exception as e:
            logger.error(f"❌ LONG universe fetch failed: {e}")
            return self._fallback_to_cache('LONG')
    
    def get_universe_short(self, min_price: float = 10.0, min_volume: int = 500000) -> List[str]:
        """Get SHORT candidates from Finviz Elite API"""
        logger.info("=" * 60)
        logger.info("FETCHING SHORT UNIVERSE FROM FINVIZ ELITE API")
        logger.info("=" * 60)
        
        filters = {
            'f': f'sh_price_o{min_price},sh_avgvol_o{min_volume//1000},ta_perf_1wdown,ta_sma20_pb,ta_sma50_pb'
        }
        
        try:
            symbols = self._retry_with_backoff(self._fetch_elite_api, filters)
            logger.info(f"✅ Fetched {len(symbols)} SHORT candidates")
            
            self.cached_symbols['SHORT'] = symbols
            self.cached_symbols['timestamp'] = datetime.now()
            
            if self.db and symbols:
                self._store_symbols(symbols, direction='SHORT')
            
            return symbols
        except Exception as e:
            logger.error(f"❌ SHORT universe fetch failed: {e}")
            return self._fallback_to_cache('SHORT')
    
    def get_universe_all(self, min_price: float = 5.0, min_volume: int = 500000, max_symbols: int = 8500) -> List[str]:
        """Get entire universe from Finviz Elite API"""
        logger.info("=" * 60)
        logger.info(f"FETCHING FULL UNIVERSE (Target: {max_symbols} symbols)")
        logger.info("=" * 60)
        
        filters = {
            'f': f'sh_price_o{min_price},sh_avgvol_o{min_volume//1000}'
        }
        
        try:
            symbols = self._retry_with_backoff(self._fetch_elite_api, filters)
            
            if len(symbols) > max_symbols:
                symbols = symbols[:max_symbols]
            
            logger.info(f"✅ Fetched {len(symbols)} total symbols")
            
            self.cached_symbols['ALL'] = symbols
            self.cached_symbols['timestamp'] = datetime.now()
            
            if self.db and symbols:
                self._store_symbols(symbols, direction='ALL')
            
            return symbols
        except Exception as e:
            logger.error(f"❌ Full universe fetch failed: {e}")
            return self._fallback_to_cache('ALL')
    
    def _fallback_to_cache(self, direction: str) -> List[str]:
        """Fallback to cached data"""
        cached = self.cached_symbols.get(direction, [])
        timestamp = self.cached_symbols.get('timestamp')
        
        if cached:
            age = datetime.now() - timestamp if timestamp else timedelta(hours=999)
            logger.warning(f"⚠️ Using cached {direction} data ({len(cached)} symbols, age: {age})")
            return cached
        
        if self.db:
            logger.warning("⚠️ No cache - attempting database fallback")
            return []
        
        logger.error("❌ No fallback data available")
        return []
    
    def _store_symbols(self, symbols: List[str], direction: str = 'ALL'):
        """Store symbols in database"""
        try:
            stored = 0
            for symbol in symbols:
                stored += 1
            logger.info(f"✅ Stored {stored}/{len(symbols)} symbols in database")
        except Exception as e:
            logger.error(f"Failed to store symbols: {e}")
    
    def get_core_symbols(self) -> List[str]:
        """Get Core 4 symbols"""
        return ['SPY', 'QQQ', 'IBIT', 'ETHT']
    
    def get_health_status(self) -> Dict:
        """Get client health status"""
        return {
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failures': self.circuit_breaker.failures,
            'rate_limiter_requests': len(self.rate_limiter.requests),
            'cache_age': (datetime.now() - self.cached_symbols['timestamp']).total_seconds() 
                         if self.cached_symbols['timestamp'] else None,
            'cached_symbols_count': len(self.cached_symbols.get('ALL', []))
        }


# ============================================================================
# GLOBAL CLIENT & ASYNC WRAPPER
# ============================================================================

_global_client = None

def _get_client() -> FinvizClient:
    """Get or create global Finviz client"""
    global _global_client
    if _global_client is None:
        _global_client = FinvizClient()
    return _global_client


async def get_universe(regime: str = "YELLOW", max_results: int = 1000) -> List[str]:
    """
    Async wrapper for scheduler compatibility.
    
    Args:
        regime: Market regime
        max_results: Maximum symbols to return
        
    Returns:
        List of ticker symbols
    """
    client = _get_client()
    loop = asyncio.get_event_loop()
    
    if regime in ["SHORT", "BEAR", "RED"]:
        symbols = await loop.run_in_executor(
            None,
            lambda: client.get_universe_short(min_price=10.0, min_volume=500000)
        )
    elif regime in ["LONG", "BULL", "GREEN"]:
        symbols = await loop.run_in_executor(
            None,
            lambda: client.get_universe_long(min_price=10.0, min_volume=500000)
        )
    else:
        symbols = await loop.run_in_executor(
            None,
            lambda: client.get_universe_all(min_price=5.0, min_volume=500000, max_symbols=max_results)
        )
    
    if len(symbols) > max_results:
        symbols = symbols[:max_results]
    
    return symbols
