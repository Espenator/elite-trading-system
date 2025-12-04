"""
Task scheduler - runs scans every 15 minutes
"""

import schedule
import time
from datetime import datetime, time as dt_time
import pytz
from typing import List
import asyncio

from core.logger import get_logger
from core.event_bus import event_bus
import yaml
from pathlib import Path

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

class TradingScheduler:
    """
    Manages all scheduled tasks based on time of day
    """
    
    def __init__(self):
        self.timezone = pytz.timezone(config['schedule']['timezone'])
        self.schedule_enabled = config['schedule']['enabled']
        self.is_running = False
        
        logger.info(f"Scheduler initialized (TZ: {self.timezone})")
    
    def is_market_hours(self) -> bool:
        """Check if currently in market hours"""
        now = datetime.now(self.timezone).time()
        
        market_start = dt_time(9, 30)  # 9:30 AM
        market_end = dt_time(16, 0)    # 4:00 PM
        
        return market_start <= now <= market_end
    
    def is_pre_market(self) -> bool:
        """Check if in pre-market hours"""
        now = datetime.now(self.timezone).time()
        
        pre_start = dt_time(4, 0)   # 4:00 AM
        pre_end = dt_time(9, 30)    # 9:30 AM
        
        return pre_start <= now < pre_end
    
    def is_after_hours(self) -> bool:
        """Check if in after-hours"""
        now = datetime.now(self.timezone).time()
        
        ah_start = dt_time(16, 0)  # 4:00 PM
        ah_end = dt_time(20, 0)    # 8:00 PM
        
        return ah_start < now <= ah_end
    
    def is_overnight(self) -> bool:
        """Check if overnight (no trading)"""
        return not (self.is_market_hours() or self.is_pre_market() or self.is_after_hours())
    
    def setup_schedules(self):
        """Setup all scheduled tasks"""
        
        # Market Hours (9:30 AM - 4:00 PM)
        schedule.every(15).minutes.do(self.market_hours_scan)
        schedule.every(1).minutes.do(self.position_check)
        schedule.every(5).minutes.do(self.scrape_unusual_whales)
        
        # Pre-Market (4:00 AM - 9:30 AM)
        schedule.every(15).minutes.do(self.pre_market_scan)
        
        # After-Hours (4:00 PM - 8:00 PM)
        schedule.every(15).minutes.do(self.after_hours_scan)
        
        # Overnight (8:00 PM - 4:00 AM)
        schedule.every(30).minutes.do(self.check_futures)
        
        # Daily tasks
        schedule.every().day.at("07:00").do(self.update_market_regime)
        schedule.every().sunday.at("23:00").do(self.ml_retraining)
        
        logger.info("✅ All schedules configured")
    
    def market_hours_scan(self):
        """Full scan during market hours"""
        if not self.is_market_hours() or not self.schedule_enabled:
            return
        
        logger.info("🔍 Market hours scan starting...")
        try:
            asyncio.run(run_full_scan())
        except Exception as e:
            logger.error(f"Error in market scan: {e}")
    
    def pre_market_scan(self):
        """Pre-market scan (fewer symbols)"""
        if not self.is_pre_market() or not self.schedule_enabled:
            return
        
        logger.info("🌅 Pre-market scan starting...")
        # TODO: Implement pre-market logic
    
    def after_hours_scan(self):
        """After-hours scan"""
        if not self.is_after_hours() or not self.schedule_enabled:
            return
        
        logger.info("🌆 After-hours scan starting...")
        # TODO: Implement after-hours logic
    
    def position_check(self):
        """Check all open positions (every 1 minute)"""
        if not self.is_market_hours() or not self.schedule_enabled:
            return
        
        # This runs every minute so we don't log it (too noisy)
        try:
            from backend.paper_portfolio import check_positions
            check_positions()
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    def scrape_unusual_whales(self):
        """Scrape Unusual Whales data"""
        if not (self.is_market_hours() or self.is_pre_market()) or not self.schedule_enabled:
            return
        
        logger.info("🐋 Scraping Unusual Whales...")
        # TODO: Implement scraping
    
    def check_futures(self):
        """Check futures overnight"""
        if not self.is_overnight() or not self.schedule_enabled:
            return
        
        logger.info("📊 Checking futures...")
        # TODO: Implement futures check
    
    def update_market_regime(self):
        """Update VIX, breadth, regime (daily at 7 AM)"""
        logger.info("📈 Updating market regime...")
        # TODO: Implement market regime update
    
    def ml_retraining(self):
        """Retrain ML models (Sunday 11 PM)"""
        logger.info("🤖 ML retraining starting...")
        # TODO: Implement ML retraining
    
    def start(self):
        """Start the scheduler loop"""
        self.is_running = True
        self.setup_schedules()
        
        logger.info("=" * 70)
        logger.info("⏰ SCHEDULER STARTED")
        logger.info("=" * 70)
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("⏰ Scheduler stopped")

# =============================================================================
# SCAN FUNCTIONS
# =============================================================================

async def run_full_scan() -> List:
    """
    Run complete market scan
    
    Returns:
        List of Signal objects
    """
    from datetime import datetime
    
    logger.info("🔍 Starting full market scan...")
    start_time = datetime.now()
    
    signals = []
    
    try:
        # Stage 1: Universe filter (8,500 → 500)
        logger.info("Stage 1: Universe filter...")
        from data_collection.finviz_scraper import get_universe
        universe = await get_universe()
        logger.info(f"  → {len(universe)} symbols")
        
        # Stage 2: Compression detection (500 → 100)
        logger.info("Stage 2: Compression detection...")
        from signal_generation.compression_detector import detect_compression
        compressed = await detect_compression(universe)
        logger.info(f"  → {len(compressed)} compressed symbols")
        
        # Stage 3: Ignition detection (100 → 40)
        logger.info("Stage 3: Ignition detection...")
        from signal_generation.ignition_detector import detect_ignitions
        ignitions = await detect_ignitions(compressed)
        logger.info(f"  → {len(ignitions)} fresh ignitions")
        
        # Stage 4: Calculate scores
        logger.info("Stage 4: Scoring...")
        from signal_generation.composite_scorer import score_candidates
        signals = await score_candidates(ignitions)
        logger.info(f"  → {len(signals)} final signals")
        
        # Stage 5: Scrape Unusual Whales for top 40
        logger.info("Stage 5: Unusual Whales enrichment...")
        from data_collection.unusual_whales_scraper import enrich_signals
        signals = await enrich_signals(signals[:40])
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Scan complete in {duration:.1f}s")
        
        # Publish event
        event_bus.publish('scan_complete', {
            'signal_count': len(signals),
            'duration_sec': duration
        })
        
        return signals
        
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        return []

# =============================================================================
# RUN SCHEDULER (if executed directly)
# =============================================================================

if __name__ == "__main__":
    scheduler = TradingScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.stop()
