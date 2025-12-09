"""
Unusual Whales API Client - API-FIRST APPROACH
Uses environment variables for secure credential management
"""

import os
import sys
import asyncio
import aiohttp
import pandas as pd
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


class UnusualWhalesClient:
    """Unusual Whales API client using environment variables"""
    
    def __init__(self):
        # Load credentials from environment variables
        self.api_key = os.getenv('UNUSUAL_WHALES_API_KEY', 'd1cb154c-7988-41c6-ac00-09379ae7395c')
        self.base_url = os.getenv('UNUSUAL_WHALES_API_BASE_URL', 'https://api.unusualwhales.com')
        
        # Optional web scraping credentials (for manual dashboard access)
        self.email = os.getenv('UNUSUAL_WHALES_EMAIL', 'Espen@embodier.ai')
        self.password = os.getenv('UNUSUAL_WHALES_PASSWORD', 'Eastsound1!#')
        self.account_type = os.getenv('UNUSUAL_WHALES_ACCOUNT_TYPE', 'retail_pro')
        
        # Session configuration
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = int(os.getenv('API_TIMEOUT_SECONDS', 60))
        
        logger.info("? Unusual Whales API Client initialized")
        logger.info(f"   Account: {self.email} ({self.account_type})")
        logger.info(f"   API Key: {self.api_key[:20]}...")

    async def __aenter__(self):
        """Create aiohttp session"""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'Elite Trading System/2.0',
                'Accept': 'application/json'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session"""
        if self.session:
            await self.session.close()

    async def get_dark_pool_data(self, limit: int = 100) -> List[Dict]:
        """Fetch dark pool activity from Unusual Whales API"""
        try:
            endpoint = f"{self.base_url}/api/darkpool/recent"
            params = {'limit': limit}
            
            logger.info(f"?? Fetching dark pool data from Unusual Whales API")
            logger.info(f"   Endpoint: {endpoint}")
            
            async with self.session.get(
                endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 401:
                    logger.error("? API authentication failed - check API key")
                    return []
                
                if response.status != 200:
                    logger.error(f"? API request failed: status {response.status}")
                    return []
                
                data = await response.json()
                logger.info(f"? Retrieved {len(data.get('data', []))} dark pool records")
                return data.get('data', [])

        except Exception as e:
            logger.error(f"? Error fetching dark pool data: {e}")
            return []

    async def get_options_flow(self, limit: int = 100) -> List[Dict]:
        """Fetch options flow from Unusual Whales API"""
        try:
            endpoint = f"{self.base_url}/api/option-trades/flow-alerts"
            params = {'limit': limit}
            
            logger.info(f"?? Fetching options flow from Unusual Whales API")
            
            async with self.session.get(
                endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.error(f"? API request failed: status {response.status}")
                    return []
                
                data = await response.json()
                logger.info(f"? Retrieved {len(data.get('data', []))} options flow records")
                return data.get('data', [])

        except Exception as e:
            logger.error(f"? Error fetching options flow: {e}")
            return []

    async def get_unusual_activity(self, symbol: str = None) -> List[Dict]:
        """Fetch unusual activity alerts"""
        try:
            endpoint = f"{self.base_url}/v1/unusual-activity"
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            logger.info(f"?? Fetching unusual activity from Unusual Whales API")
            
            async with self.session.get(
                endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.error(f"? API request failed: status {response.status}")
                    return []
                
                data = await response.json()
                logger.info(f"? Retrieved unusual activity data")
                return data.get('data', [])

        except Exception as e:
            logger.error(f"? Error fetching unusual activity: {e}")
            return []


# Factory functions
async def get_dark_pool_data(limit: int = 100) -> List[Dict]:
    """Get dark pool data from Unusual Whales API"""
    async with UnusualWhalesClient() as client:
        return await client.get_dark_pool_data(limit)


async def get_options_flow(limit: int = 100) -> List[Dict]:
    """Get options flow from Unusual Whales API"""
    async with UnusualWhalesClient() as client:
        return await client.get_options_flow(limit)


# Test/CLI usage
if __name__ == "__main__":
    async def test():
        print("=" * 70)
        print("?? Testing Unusual Whales API")
        print("=" * 70)
        print(f"Account: {os.getenv('UNUSUAL_WHALES_EMAIL', 'Espen@embodier.ai')}")
        print(f"API Key: {os.getenv('UNUSUAL_WHALES_API_KEY', 'd1cb154c-7988-41c6-ac00-09379ae7395c')[:20]}...")
        print("=" * 70)

        async with UnusualWhalesClient() as client:
            print("\n?? Testing Dark Pool Data...")
            dark_pool = await client.get_dark_pool_data(limit=50)
            print(f"Result: {len(dark_pool)} records")

            print("\n?? Testing Options Flow...")
            options = await client.get_options_flow(limit=50)
            print(f"Result: {len(options)} records")

        print("\n" + "=" * 70)
        print("? Test complete")
        print("=" * 70)

    asyncio.run(test())
