"""
Data Collection Orchestrator - Unified API-First Approach
Coordinates all data providers (Finviz Elite, Unusual Whales, yfinance)
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.logger import get_logger
except:
    logging.basicConfig(level=logging.INFO)
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

# Import data providers
from backend.data_collection.finviz_scraper import FinvizEliteClient, get_universe
from backend.data_collection.unusual_whales_api_client import UnusualWhalesClient


class DataCollectionOrchestrator:
    """Unified orchestrator for all data collection APIs"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("?? DATA COLLECTION ORCHESTRATOR - INITIALIZING")
        logger.info("=" * 80)
        
        self.finviz_client = None
        self.whales_client = None
        self.collection_timestamp = datetime.now()
        
    async def __aenter__(self):
        self.finviz_client = FinvizEliteClient()
        self.whales_client = UnusualWhalesClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def collect_stock_universe(self, regime: str = "GREEN") -> List[str]:
        """Collect universe from Finviz Elite API"""
        logger.info("")
        logger.info("?? COLLECTION STAGE 1: Stock Universe")
        logger.info("-" * 80)
        
        try:
            async with self.finviz_client:
                symbols = await self.finviz_client.get_screener_results(regime)
                logger.info(f"? Retrieved {len(symbols)} symbols from Finviz Elite")
                return symbols
        except Exception as e:
            logger.error(f"? Failed to collect universe: {e}")
            return []

    async def collect_whale_data(self) -> Dict:
        """Collect whale activity data"""
        logger.info("")
        logger.info("?? COLLECTION STAGE 2: Whale Activity Data")
        logger.info("-" * 80)
        
        try:
            async with self.whales_client:
                dark_pool = await self.whales_client.get_dark_pool_data(limit=100)
                options_flow = await self.whales_client.get_options_flow(limit=100)
                
                logger.info(f"? Retrieved {len(dark_pool)} dark pool records")
                logger.info(f"? Retrieved {len(options_flow)} options flow records")
                
                return {
                    'dark_pool': dark_pool,
                    'options_flow': options_flow
                }
        except Exception as e:
            logger.error(f"? Failed to collect whale data: {e}")
            return {}

    async def collect_all_data(self, regime: str = "GREEN") -> Dict:
        """Collect all data from all providers"""
        logger.info("=" * 80)
        logger.info("?? STARTING UNIFIED DATA COLLECTION")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {self.collection_timestamp}")
        logger.info("")

        async with FinvizEliteClient() as finviz, UnusualWhalesClient() as whales:
            # Stage 1: Get stock universe
            universe = await finviz.get_screener_results(regime)
            
            # Stage 2: Get whale data
            dark_pool = await whales.get_dark_pool_data(limit=100)
            options_flow = await whales.get_options_flow(limit=100)
            
            result = {
                'timestamp': self.collection_timestamp.isoformat(),
                'regime': regime,
                'universe': {
                    'count': len(universe),
                    'symbols': universe[:100]  # First 100 for verification
                },
                'whale_data': {
                    'dark_pool_count': len(dark_pool),
                    'options_flow_count': len(options_flow),
                    'dark_pool_sample': dark_pool[:5] if dark_pool else [],
                    'options_flow_sample': options_flow[:5] if options_flow else []
                }
            }
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("? UNIFIED DATA COLLECTION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Universe: {result['universe']['count']} symbols")
            logger.info(f"Dark Pool: {result['whale_data']['dark_pool_count']} records")
            logger.info(f"Options Flow: {result['whale_data']['options_flow_count']} records")
            logger.info("")
            
            return result


# Factory function
async def collect_market_data(regime: str = "GREEN") -> Dict:
    """Unified market data collection"""
    async with DataCollectionOrchestrator() as orchestrator:
        return await orchestrator.collect_all_data(regime)


# Test/CLI usage
if __name__ == "__main__":
    async def main():
        print("=" * 80)
        print("?? TESTING DATA COLLECTION ORCHESTRATOR")
        print("=" * 80)
        print("")
        
        data = await collect_market_data("GREEN")
        
        print(f"?? Collection Results:")
        print(f"   Universe: {data['universe']['count']} symbols")
        print(f"   Dark Pool: {data['whale_data']['dark_pool_count']} records")
        print(f"   Options Flow: {data['whale_data']['options_flow_count']} records")

    asyncio.run(main())
