"""
yfinance data fetcher - Downloads OHLCV data in parallel
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from core.logger import get_logger

logger = get_logger(__name__)

class YFinanceFetcher:
    """
    Parallel OHLCV data downloader
    Uses 50 threads to download data for 500 symbols quickly
    """
    
    def __init__(self, max_workers: int = 50):
        self.max_workers = max_workers
        self.cache_dir = Path(__file__).parent.parent / "data/cache/ohlcv"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"YFinance fetcher initialized: {max_workers} parallel workers")
    
    async def fetch_data_for_symbols(
        self,
        symbols: List[str],
        period: str = '1y',
        interval: str = '1d'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols in parallel
        
        Args:
            symbols: List of stock tickers
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            Dictionary: {symbol: DataFrame}
        """
        logger.info(f"📊 Downloading {len(symbols)} symbols ({period}/{interval})...")
        start_time = time.time()
        
        results = {}
        failed = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all downloads
            future_to_symbol = {
                executor.submit(self._fetch_single, symbol, period, interval): symbol
                for symbol in symbols
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results[symbol] = df
                    else:
                        failed.append(symbol)
                except Exception as e:
                    logger.error(f"Error downloading {symbol}: {e}")
                    failed.append(symbol)
        
        duration = time.time() - start_time
        success_rate = len(results) / len(symbols) * 100 if symbols else 0
        
        logger.info(f"✅ Downloaded {len(results)}/{len(symbols)} symbols in {duration:.1f}s ({success_rate:.0f}% success)")
        
        if failed:
            logger.warning(f"❌ Failed: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
        
        return results
    
    def _fetch_single(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol
        
        Args:
            symbol: Stock ticker
            period: Time period
            interval: Data interval
        
        Returns:
            DataFrame with OHLCV data, or None if failed
        """
        try:
            # Check cache first
            cache_file = self.cache_dir / f"{symbol}_{interval}.csv"
            if cache_file.exists():
                # Check if cache is recent (within 1 hour)
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age < 3600:  # 1 hour
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    return df
            
            # Download from yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return None
            
            # Clean data
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # Save to cache
            df.to_csv(cache_file)
            
            return df
            
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current/latest price for a symbol
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Current price, or None if unavailable
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if data.empty:
                return None
            
            return float(data['Close'].iloc[-1])
            
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
    
    async def get_multiple_timeframes(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Get data for multiple timeframes (for Velez multi-TF scoring)
        
        Args:
            symbols: List of stock tickers
        
        Returns:
            Nested dict: {symbol: {timeframe: DataFrame}}
        """
        logger.info(f"📊 Downloading multi-timeframe data for {len(symbols)} symbols...")
        
        results = {}
        
        timeframes = {
            'weekly': ('2y', '1wk'),
            'daily': ('1y', '1d'),
            'four_hour': ('3mo', '1h'),  # yfinance doesn't have 4h, use 1h
            'one_hour': ('1mo', '1h'),
        }
        
        for tf_name, (period, interval) in timeframes.items():
            logger.info(f"  Fetching {tf_name}...")
            tf_data = await self.fetch_data_for_symbols(symbols, period, interval)
            
            for symbol, df in tf_data.items():
                if symbol not in results:
                    results[symbol] = {}
                results[symbol][tf_name] = df
        
        logger.info(f"✅ Multi-timeframe data complete")
        return results

# Global instance
fetcher = YFinanceFetcher()

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_data(symbols: List[str], period: str = '1y', interval: str = '1d') -> Dict[str, pd.DataFrame]:
    """Convenience function to fetch data"""
    return await fetcher.fetch_data_for_symbols(symbols, period, interval)

async def get_current_prices(symbols: List[str]) -> Dict[str, float]:
    """Get current prices for multiple symbols"""
    prices = {}
    for symbol in symbols:
        price = await fetcher.get_current_price(symbol)
        if price:
            prices[symbol] = price
    return prices

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Test with a few symbols
        symbols = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'META']
        
        print("\n1. Testing single timeframe download...")
        data = await get_data(symbols, period='1y', interval='1d')
        print(f"   Got data for {len(data)} symbols")
        
        if 'AAPL' in data:
            print(f"\n   AAPL data shape: {data['AAPL'].shape}")
            print(data['AAPL'].tail())
        
        print("\n2. Testing current prices...")
        prices = await get_current_prices(symbols)
        for symbol, price in prices.items():
            print(f"   {symbol}: ${price:.2f}")
        
        print("\n3. Testing multi-timeframe download...")
        multi_data = await fetcher.get_multiple_timeframes(symbols[:2])
        print(f"   Got multi-TF data for {len(multi_data)} symbols")
        
        if 'AAPL' in multi_data:
            print(f"   AAPL timeframes: {list(multi_data['AAPL'].keys())}")
    
    asyncio.run(test())
