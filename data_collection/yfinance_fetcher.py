"""
yfinance data fetcher - Downloads OHLCV data with retry logic
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

from core.logger import get_logger

logger = get_logger(__name__)

class YFinanceFetcher:
    """
    Parallel OHLCV data downloader with rate limiting
    """
    
    def __init__(self, max_workers: int = 10):
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
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d)
        
        Returns:
            Dictionary: {symbol: DataFrame}
        """
        logger.info(f"📊 Downloading {len(symbols)} symbols ({period}/{interval})...")
        start_time = time.time()
        
        results = {}
        failed = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(self._fetch_single, symbol, period, interval): symbol
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results[symbol] = df
                    else:
                        failed.append(symbol)
                except Exception as e:
                    logger.debug(f"Error downloading {symbol}: {e}")
                    failed.append(symbol)
        
        duration = time.time() - start_time
        success_rate = len(results) / len(symbols) * 100 if symbols else 0
        
        logger.info(f"✅ Downloaded {len(results)}/{len(symbols)} symbols in {duration:.1f}s ({success_rate:.0f}% success)")
        
        if failed and len(failed) <= 10:
            logger.warning(f"❌ Failed: {', '.join(failed)}")
        elif failed:
            logger.warning(f"❌ Failed: {', '.join(failed[:10])}... ({len(failed)} total)")
        
        return results
    
    def _fetch_single(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol with retry and rate limiting
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(0.05, 0.15))
                
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval)
                
                if df.empty:
                    return None
                
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                
                return df
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(0.5, 1.0))
                    continue
                else:
                    return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current/latest price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if data.empty:
                return None
            
            return float(data['Close'].iloc[-1])
            
        except Exception as e:
            logger.debug(f"Failed to get current price for {symbol}: {e}")
            return None

# Global instance
fetcher = YFinanceFetcher()

# Convenience functions
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

