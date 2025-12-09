"""
Scanner Manager - Orchestrates the entire Elite Trading System scan workflow
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from backend.core.logger import get_logger
from backend.core.event_bus import event_bus
from backend.data_collection.finviz_scraper import FinvizScraper
from backend.data_collection.yfinance_fetcher import YFinanceFetcher
from backend.data_collection.technical_calculator import TechnicalCalculator
from scoring.composite_scorer import CompositeScorer

logger = get_logger(__name__)


class ScannerManager:
    """
    Coordinates the scanning workflow:
    1. Get universe from Finviz (regime-filtered)
    2. Fetch OHLCV data from yfinance
    3. Calculate technical indicators
    4. Score candidates using composite scoring
    5. Return final signals
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.finviz_scraper = FinvizScraper()
        self.yfinance_fetcher = YFinanceFetcher()
        self.technical_calculator = TechnicalCalculator()
        
        logger.info("✅ ScannerManager initialized")
    
    async def run_scan(
        self,
        regime: str = "YELLOW",
        min_score: float = 40.0,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Execute complete scan workflow
        
        Args:
            regime: Market regime (GREEN, YELLOW, RED, SHORT)
            min_score: Minimum composite score threshold
            max_results: Maximum number of results to return
            
        Returns:
            List of signal dictionaries with scores and metadata
        """
        
        logger.info(f"🚀 Starting Elite Scan | Regime: {regime} | Min Score: {min_score}")
        
        try:
            # STEP 1: Get filtered universe from Finviz Elite
            logger.info("📊 STEP 1: Fetching Finviz universe...")
            async with self.finviz_scraper as scraper:
                symbols = await scraper.get_screener_results(regime)
            
            if not symbols:
                logger.warning("⚠️ No symbols returned from Finviz")
                return []
            
            logger.info(f"✅ Found {len(symbols)} symbols from Finviz")
            
            # STEP 2: Fetch OHLCV data from yfinance
            logger.info("📈 STEP 2: Fetching market data...")
            ohlcv_data = await self.yfinance_fetcher.fetch_data_for_symbols(
                symbols=symbols,
                period="1y",
                interval="1d"
            )
            
            if not ohlcv_data:
                logger.warning("⚠️ No OHLCV data fetched")
                return []
            
            logger.info(f"✅ Fetched data for {len(ohlcv_data)} symbols")
            
            # STEP 3: Calculate technical indicators
            logger.info("🔬 STEP 3: Calculating technical indicators...")
            technical_results = {}
            
            for symbol, df in ohlcv_data.items():
                try:
                    indicators = self.technical_calculator.calculate_all(df)
                    technical_results[symbol] = {
                        'data': df,
                        'indicators': indicators
                    }
                except Exception as e:
                    logger.debug(f"Failed to calculate indicators for {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Calculated indicators for {len(technical_results)} symbols")
            
            # STEP 4: Score candidates
            logger.info("🎯 STEP 4: Scoring candidates...")
            scorer = CompositeScorer(regime=regime)
            
            signals = []
            for symbol, tech_data in technical_results.items():
                try:
                    score_data = scorer.calculate_composite_score(
                        symbol=symbol,
                        data=tech_data['data'],
                        indicators=tech_data['indicators']
                    )
                    
                    # Filter by minimum score
                    if score_data['composite_score'] >= min_score:
                        signals.append({
                            'symbol': symbol,
                            'regime': regime,
                            'timestamp': datetime.now().isoformat(),
                            **score_data
                        })
                
                except Exception as e:
                    logger.debug(f"Failed to score {symbol}: {e}")
                    continue
            
            # STEP 5: Sort and limit results
            signals.sort(key=lambda x: x['composite_score'], reverse=True)
            final_signals = signals[:max_results]
            
            logger.info(f"✅ Scan complete: {len(final_signals)} ELITE signals found")
            
            # Publish results to event bus
            await event_bus.publish("scan_complete", {
                'regime': regime,
                'signals': final_signals,
                'total_scanned': len(symbols),
                'total_scored': len(signals)
            })
            
            return final_signals
        
        except Exception as e:
            logger.error(f"❌ Scan failed: {e}")
            raise


# Global instance
scanner_manager = None

def get_scanner_manager(config: Dict) -> ScannerManager:
    """Get or create the global scanner manager instance"""
    global scanner_manager
    if scanner_manager is None:
        scanner_manager = ScannerManager(config)
    return scanner_manager

