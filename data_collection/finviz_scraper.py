"""
Finviz Elite API Client - API-FIRST APPROACH
Uses environment variables for secure credential management
"""

import os
import sys
import asyncio
import aiohttp
import pandas as pd
from io import StringIO
from typing import List, Optional, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.logger import get_logger
except:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class FinvizEliteClient:
    """Finviz Elite API client using environment variables"""
    
    def __init__(self):
        self.api_key = os.getenv('FINVIZ_API_KEY', '4475cd42-70ea-4fa7-9630-0d9cd30d9620')
        self.email = os.getenv('FINVIZ_EMAIL', 'Espen@embodier.ai')
        self.password = os.getenv('FINVIZ_PASSWORD', 'Espen1s!#')
        self.base_url = os.getenv('FINVIZ_EXPORT_ENDPOINT', 'https://elite.finviz.com/export.ashx')
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = int(os.getenv('API_TIMEOUT_SECONDS', 60))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', 3))
        self.retry_delay = int(os.getenv('RETRY_DELAY_SECONDS', 5))
        
        logger.info("Finviz Elite API Client initialized")
        logger.info(f"Account: {self.email}")
        logger.info(f"API Key: {self.api_key[:20]}...")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Elite Trading System/2.0',
                'Accept': 'text/csv'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _build_filters(self, regime: str) -> str:
        base_filters = {
            'sh_avgvol_o100': None,
            'sh_price_o5': None,
            'sh_opt_option': None,
            'ft_ipo_no': None,
            'geo_usa': None
        }

        if regime == "YELLOW":
            base_filters.update({
                'sh_avgvol_o500': None,
                'sh_price_o10': None,
                'ta_sma20_pa': None,
            })
        elif regime == "RED":
            base_filters.update({
                'sh_avgvol_o500': None,
                'sh_price_o10': None,
                'ta_sma20_pb': None,
                'ta_rsi_ob30': None,
            })
        elif regime == "SHORT":
            base_filters.update({
                'sh_avgvol_o500': None,
                'sh_price_o10': None,
                'ta_sma20_pb': None,
                'ta_sma50_pb': None,
                'ta_perf_1wdown': None,
            })

        return ','.join(base_filters.keys())

    async def get_screener_results(self, regime: str = "GREEN", max_results: int = 1000) -> List[str]:
        try:
            filters = self._build_filters(regime)
            params = {
                'v': '111',
                'f': filters,
                'auth': self.api_key,
                'c': '0,1,2,3,4,5,6',
                'o': '-volume'
            }

            logger.info(f"Fetching {regime} universe from Finviz Elite API")
            logger.info(f"Endpoint: {self.base_url}")

            for attempt in range(self.retry_attempts):
                try:
                    async with self.session.get(
                        self.base_url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 401:
                            logger.error("API authentication failed - check API key")
                            return []
                        
                        if response.status == 429:
                            logger.warning(f"Rate limit exceeded - retrying in {self.retry_delay}s...")
                            await asyncio.sleep(self.retry_delay)
                            continue
                        
                        if response.status != 200:
                            logger.error(f"API request failed: status {response.status}")
                            text = await response.text()
                            logger.error(f"Response: {text[:200]}")
                            return []

                        csv_data = await response.text()
                        
                        if not csv_data or len(csv_data) < 10:
                            logger.warning("Empty response from Finviz API")
                            return []

                        df = pd.read_csv(StringIO(csv_data))
                        
                        if 'Ticker' in df.columns:
                            symbols = df['Ticker'].tolist()
                        elif 'Symbol' in df.columns:
                            symbols = df['Symbol'].tolist()
                        else:
                            symbols = df.iloc[:, 0].tolist()

                        symbols = [str(s).strip().upper() for s in symbols if pd.notna(s)]
                        symbols = [s for s in symbols if s and len(s) <= 5 and s.isalpha()]
                        symbols = list(set(symbols))[:max_results]

                        logger.info(f"Finviz Elite API: {len(symbols)} stocks retrieved")
                        if symbols:
                            logger.info(f"Sample: {symbols[:10]}")
                        
                        return symbols

                except asyncio.TimeoutError:
                    logger.warning(f"Finviz API timeout (attempt {attempt + 1}/{self.retry_attempts})")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay)
                    continue

        except Exception as e:
            logger.error(f"Finviz API error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def get_stock_data(self, symbols: List[str]) -> pd.DataFrame:
        try:
            ticker_list = ','.join(symbols[:100])
            params = {
                'v': '152',
                't': ticker_list,
                'auth': self.api_key,
                'c': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20'
            }

            async with self.session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch stock data: {response.status}")
                    return pd.DataFrame()

                csv_data = await response.text()
                df = pd.read_csv(StringIO(csv_data))
                logger.info(f"Fetched data for {len(df)} stocks")
                return df

        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
            return pd.DataFrame()

    async def scrape_regime(self, regime: str, max_results: int = 1000) -> List[str]:
        return await self.get_screener_results(regime, max_results)


async def get_universe(regime: str = "GREEN", max_results: int = 1000) -> List[str]:
    async with FinvizEliteClient() as client:
        return await client.get_screener_results(regime, max_results)


async def get_universe_filtered(
    min_price=10.0,
    max_price=500000.0,
    min_volume=500000,
    min_market_cap=1000000000
) -> List[Dict]:
    logger.info("=" * 80)
    logger.info("FETCHING FILTERED UNIVERSE FROM FINVIZ ELITE API")
    logger.info("=" * 80)
    
    price_str = f"Price ${min_price} to ${max_price:,}"
    vol_str = f"Volume > {min_volume:,}"
    cap_str = f"Market Cap > ${min_market_cap:,}"
    
    logger.info(f"Filters: {price_str}")
    logger.info(f"         {vol_str}")
    logger.info(f"         {cap_str}")

    try:
        async with FinvizEliteClient() as client:
            symbols = await client.get_screener_results("GREEN", 1000)
            logger.info(f"Retrieved {len(symbols)} symbols from Finviz Elite API")
            return [{'symbol': s} for s in symbols]

    except Exception as e:
        logger.error(f"Finviz API error: {e}")
        return []



# Legacy class name alias
FinvizScraper = FinvizEliteClient

if __name__ == "__main__":
    async def test():
        print("=" * 70)
        print("Testing Finviz Elite API")
        print("=" * 70)
        acct = os.getenv('FINVIZ_EMAIL', 'Espen@embodier.ai')
        key = os.getenv('FINVIZ_API_KEY', '4475cd42-70ea-4fa7-9630-0d9cd30d9620')
        print(f"Account: {acct}")
        print(f"API Key: {key[:20]}...")
        print("=" * 70)

        async with FinvizEliteClient() as client:
            print("\nTesting GREEN regime...")
            symbols = await client.get_screener_results("GREEN", max_results=100)
            print(f"Result: {len(symbols)} symbols")
            if symbols:
                print(f"Sample: {symbols[:20]}")

        print("\n" + "=" * 70)
        print("Test complete")
        print("=" * 70)

    asyncio.run(test())

