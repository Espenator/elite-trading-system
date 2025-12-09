"""
Unusual Whales API Client - PRODUCTION VERSION
Provides real-time stock quotes, options flow, and dark pool data

API Key: d1cb154c-7988-41c6-ac00-09379ae7395c (HARDCODED)
"""
import requests
import yaml
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from backend.core.logger import get_logger

logger = get_logger(__name__)

# HARDCODED PRODUCTION API KEY
UNUSUAL_WHALES_API_KEY = "d1cb154c-7988-41c6-ac00-09379ae7395c"

class UnusualWhalesClient:
    """Unusual Whales API Client with hardcoded production credentials"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Try to load from config first, fallback to hardcoded
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            uw_config = config.get('api_credentials', {}).get('unusual_whales', {})
            
            self.api_key = uw_config.get('api_key', UNUSUAL_WHALES_API_KEY)
            self.base_url = uw_config.get('base_url', 'https://api.unusualwhales.com/api')
            self.enabled = uw_config.get('enabled', True)
            
        except Exception as e:
            logger.warning(f"Could not load config, using hardcoded API key: {e}")
            self.api_key = UNUSUAL_WHALES_API_KEY
            self.base_url = 'https://api.unusualwhales.com/api'
            self.enabled = True
        
        if not self.api_key:
            logger.error("No Unusual Whales API key found!")
            self.enabled = False
        else:
            logger.info(f"✅ Unusual Whales client initialized (API key: {self.api_key[:8]}...)")
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for a symbol"""
        if not self.enabled:
            logger.warning("Unusual Whales API is disabled")
            return None
        
        try:
            url = f"{self.base_url}/stock/{symbol}/quote"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            logger.info(f"📊 Fetching real-time quote for {symbol} from Unusual Whales...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                price = data.get('last', data.get('price', 0))
                logger.info(f"✅ Got real-time quote for {symbol}: ${price:.2f}")
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'last': price,
                    'bid': data.get('bid', price),
                    'ask': data.get('ask', price),
                    'volume': data.get('volume', 0),
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'unusual_whales'
                }
            
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("❌ Unusual Whales API key is invalid or expired")
            elif e.response.status_code == 404:
                logger.warning(f"⚠️ Symbol {symbol} not found on Unusual Whales")
            else:
                logger.error(f"❌ HTTP error {e.response.status_code}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get quote for {symbol}: {e}")
            return None
    
    def get_options_flow(self, symbol: str, min_premium: float = 100000) -> List[Dict]:
        """Get recent options flow for a symbol (whale trades)"""
        if not self.enabled:
            logger.warning("Unusual Whales API is disabled")
            return []
        
        try:
            url = f"{self.base_url}/option-contracts/{symbol}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            params = {
                "min_premium": min_premium,
                "date_from": (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
            }
            
            logger.info(f"🐋 Fetching options flow for {symbol} (min premium: ${min_premium:,.0f})...")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list):
                logger.info(f"✅ Got {len(data)} options flow alerts for {symbol}")
                return data
            elif isinstance(data, dict) and 'data' in data:
                logger.info(f"✅ Got {len(data['data'])} options flow alerts for {symbol}")
                return data['data']
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to get options flow for {symbol}: {e}")
            return []
    
    def get_dark_pool(self, symbol: str, days: int = 7) -> List[Dict]:
        """Get dark pool activity for a symbol"""
        if not self.enabled:
            logger.warning("Unusual Whales API is disabled")
            return []
        
        try:
            url = f"{self.base_url}/darkpool/{symbol}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            params = {
                "date_from": (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
            }
            
            logger.info(f"🌑 Fetching dark pool data for {symbol} (last {days} days)...")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list):
                logger.info(f"✅ Got {len(data)} dark pool blocks for {symbol}")
                return data
            elif isinstance(data, dict) and 'data' in data:
                logger.info(f"✅ Got {len(data['data'])} dark pool blocks for {symbol}")
                return data['data']
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to get dark pool for {symbol}: {e}")
            return []
    
    def get_market_tide(self) -> Optional[Dict]:
        """Get overall market sentiment from options flow"""
        if not self.enabled:
            logger.warning("Unusual Whales API is disabled")
            return None
        
        try:
            url = f"{self.base_url}/market/tide"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            logger.info("🌊 Fetching market tide data...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"✅ Got market tide: {data}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get market tide: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if API connection is working"""
        try:
            logger.info("🔍 Testing Unusual Whales API connection...")
            
            # Test with SPY quote
            quote = self.get_quote('SPY')
            
            if quote:
                logger.info(f"✅ API connection successful! SPY price: ${quote['price']:.2f}")
                return True
            else:
                logger.error("❌ API connection failed - no data returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
            return False


# Module-level test function
if __name__ == "__main__":
    print("Testing Unusual Whales API Client...\n")
    
    client = UnusualWhalesClient()
    
    if client.test_connection():
        print("\n✅ All tests passed!")
        
        # Test options flow
        print("\nTesting options flow for NVDA...")
        flow = client.get_options_flow('NVDA', min_premium=250000)
        print(f"Found {len(flow)} whale trades")
        
        # Test dark pool
        print("\nTesting dark pool for AAPL...")
        dp = client.get_dark_pool('AAPL', days=3)
        print(f"Found {len(dp)} dark pool blocks")
        
    else:
        print("\n❌ Tests failed!")
