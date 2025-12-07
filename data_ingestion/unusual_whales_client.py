"""
Unusual Whales API Client - FIXED ENDPOINTS
"""
import os
import requests
import logging
from typing import Optional, Dict, List
import time
from dotenv import load_dotenv

load_dotenv()  # Load .env file

logger = logging.getLogger(__name__)

class UnusualWhalesClient:
    """Unusual Whales API Client with CORRECTED endpoints"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('UNUSUAL_WHALES_API_KEY')
        if not self.api_key:
            raise ValueError("? UNUSUAL_WHALES_API_KEY not found")
        
        self.base_url = "https://api.unusualwhales.com/api"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        self.request_count = 0
        self.minute_start = time.time()
        self.max_requests_per_minute = 55
        
        logger.info(f"? Unusual Whales client initialized - Base: {self.base_url}")

    def _rate_limit_check(self):
        """Enforce API rate limits (60/min)"""
        current_time = time.time()
        
        if current_time - self.minute_start >= 60:
            self.request_count = 0
            self.minute_start = current_time
        
        if self.request_count >= self.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.warning(f"? Rate limit - sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.request_count = 0
                self.minute_start = time.time()
        
        self.request_count += 1

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        self._rate_limit_check()
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"? API call successful: {endpoint}")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"? HTTP {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"? Request failed: {str(e)}")
            return None

    def get_options_flow(self, limit: int = 100) -> Optional[List[Dict]]:
        """? FIXED: /option-trades/flow-alerts"""
        params = {'limit': min(limit, 500)}
        data = self._make_request('/option-trades/flow-alerts', params)
        return data.get('data', []) if data else []

    def get_darkpool_trades(self, limit: int = 50) -> Optional[List[Dict]]:
        """? FIXED: /darkpool/recent"""
        params = {'limit': min(limit, 200)}
        data = self._make_request('/darkpool/recent', params)
        return data.get('data', []) if data else []

    def get_market_tide(self) -> Optional[Dict]:
        """? FIXED: /seasonality/market"""
        return self._make_request('/seasonality/market')

    def test_connection(self) -> bool:
        """Test API connection"""
        logger.info("?? Testing Unusual Whales API connection...")
        data = self.get_market_tide()
        
        if data:
            logger.info("? API connection successful!")
            return True
        else:
            logger.warning("? API connection failed")
            return False
