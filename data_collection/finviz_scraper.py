"""
Finviz Elite API Client
Uses the official Finviz Elite export API with API key authentication

Account: Espen@embodier.ai
API Key: 4475cd42-70ea-4fa7-9630-0d9cd30d9620
"""
import aiohttp
import asyncio
import pandas as pd
from io import StringIO
from typing import List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class FinvizScraper:
    """Finviz Elite API client using export.ashx endpoint"""
    
    def __init__(self, api_key: str = None, email: str = None, password: str = None):
        self.api_key = api_key or "4475cd42-70ea-4fa7-9630-0d9cd30d9620"
        self.email = email or "Espen@embodier.ai"
        self.password = password or "Eastsound1!#"
        self.base_url = "https://elite.finviz.com/export.ashx"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Create aiohttp session"""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Elite Trading System/1.0',
                'Accept': 'text/csv'
            }
        )
        logger.info("✅ Finviz Elite API initialized")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session"""
        if self.session:
            await self.session.close()
    
    def _build_filters(self, regime: str) -> str:
        """Build filter string based on regime"""
        base_filters = {
            'sh_avgvol_o100': None,
            'sh_price_o5': None,
            'sh_opt_option': None,
            'ft_ipo_no': None,
            'geo_usa': None
        }
        
        if regime == "YELLOW":
            base_filters['sh_avgvol_o500'] = None
            base_filters['sh_price_o10'] = None
            base_filters['ta_sma20_pa'] = None
            
        elif regime == "RED":
            base_filters['sh_avgvol_o500'] = None
            base_filters['sh_price_o10'] = None
            base_filters['ta_sma20_pb'] = None
            base_filters['ta_rsi_ob30'] = None
            
        elif regime == "SHORT":
            base_filters['sh_avgvol_o500'] = None
            base_filters['sh_price_o10'] = None
            base_filters['ta_sma20_pb'] = None
            base_filters['ta_sma50_pb'] = None
            base_filters['ta_perf_1wdown'] = None
        
        return ','.join(base_filters.keys())
    
    async def get_screener_results(self, regime: str = "GREEN", max_results: int = 1000) -> List[str]:
        """Fetch stock universe using Finviz Elite Export API"""
        try:
            filters = self._build_filters(regime)
            
            params = {
                'v': '111',
                'f': filters,
                'auth': self.api_key,
                'c': '0,1,2,3,4,5,6',
                'o': '-volume'
            }
            
            logger.info(f"📊 Fetching {regime} universe from Finviz Elite API")
            logger.info(f"   API Key: {self.api_key[:20]}...")
            logger.info(f"   Account: {self.email}")
            
            async with self.session.get(self.base_url, params=params, timeout=60) as response:
                
                if response.status == 401:
                    logger.error("❌ API authentication failed - check API key")
                    return []
                    
                if response.status == 429:
                    logger.error("❌ Rate limit exceeded - waiting before retry")
                    await asyncio.sleep(60)
                    return []
                    
                if response.status != 200:
                    logger.error(f"❌ API request failed: status {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text[:200]}")
                    return []
                
                csv_data = await response.text()
                
                if not csv_data or len(csv_data) < 10:
                    logger.warning("⚠️ Empty response from Finviz API")
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
                
                logger.info(f"✅ Finviz Elite API: {len(symbols)} stocks")
                
                if symbols:
                    logger.info(f"   Sample: {symbols[:10]}")
                
                return symbols
                
        except asyncio.TimeoutError:
            logger.error("⏱️ Finviz API timeout")
            return []
        except pd.errors.EmptyDataError:
            logger.error("❌ No data returned from Finviz API")
            return []
        except Exception as e:
            logger.error(f"❌ Finviz API error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_stock_data(self, symbols: List[str]) -> pd.DataFrame:
        """Get detailed stock data for specific symbols"""
        try:
            ticker_list = ','.join(symbols[:100])
            
            params = {
                'v': '152',
                't': ticker_list,
                'auth': self.api_key,
                'c': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20'
            }
            
            async with self.session.get(self.base_url, params=params, timeout=30) as response:
                
                if response.status != 200:
                    logger.error(f"❌ Failed to fetch stock data: {response.status}")
                    return pd.DataFrame()
                
                csv_data = await response.text()
                df = pd.read_csv(StringIO(csv_data))
                
                logger.info(f"✅ Fetched data for {len(df)} stocks")
                return df
                
        except Exception as e:
            logger.error(f"❌ Error fetching stock data: {e}")
            return pd.DataFrame()

    async def scrape_regime(self, regime: str, max_results: int = 1000) -> List[str]:
        """Backward compatibility wrapper"""
        return await self.get_screener_results(regime, max_results)


async def get_universe(regime: str = "GREEN", max_results: int = 1000) -> List[str]:
    """Get stock universe for a regime using API"""
    async with FinvizScraper() as scraper:
        return await scraper.get_screener_results(regime, max_results)


if __name__ == "__main__":
    async def test():
        print("=" * 70)
        print("🧪 Testing Finviz Elite API")
        print("=" * 70)
        print(f"Account: Espen@embodier.ai")
        print(f"API Key: 4475cd42-70ea-4fa7-9630-0d9cd30d9620")
        print("=" * 70)
        
        async with FinvizScraper() as scraper:
            print("\n🟢 Testing GREEN regime...")
            symbols = await scraper.get_screener_results("GREEN", max_results=100)
            print(f"Result: {len(symbols)} symbols")
            if symbols:
                print(f"Sample: {symbols[:20]}")
            
            if symbols:
                print("\n📊 Fetching detailed data for first 10 symbols...")
                data = await scraper.get_stock_data(symbols[:10])
                if not data.empty:
                    print(f"✅ Got {len(data)} rows × {len(data.columns)} columns")
                    print(f"Columns: {list(data.columns)[:10]}")
                else:
                    print("❌ No detailed data returned")
        
        print("\n" + "=" * 70)
        print("✅ Test complete")
        print("=" * 70)
    
    asyncio.run(test())

