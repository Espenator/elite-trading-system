"""
Elite Trading System - Core Orchestrator
========================================

Main orchestration engine that coordinates all system components:
- Data ingestion (Unusual Whales API, YFinance, Finviz)
- Prediction generation
- Prediction resolution
- Model accuracy tracking
- Real-time updates

Runs 24/7 with scheduled tasks and multi-threading.

Author: Elite Trading Team
Date: December 5, 2025
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.database import get_db_manager
# Note: data_ingestion may need to be created or mapped to data_collection
# from backend.data_collection import UnusualWhalesClient, YFinanceClient, FinvizClient
from backend.prediction_engine import create_prediction_engine

logger = logging.getLogger(__name__)


class SystemOrchestrator:
    """
    Core orchestrator for the Elite Trading System.
    
    Manages:
    1. Data ingestion from Unusual Whales, YFinance, Finviz
    2. Real-time prediction generation
    3. Prediction outcome resolution
    4. Model performance tracking
    5. System health monitoring
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the orchestrator."""
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        
        # System state
        self.is_running = False
        self.start_time = None
        self.threads = []
        
        # Component initialization
        logger.info("Initializing Elite Trading System components...")
        
        self.db = get_db_manager()
        self.uw_client = UnusualWhalesClient()
        self.yf_client = YFinanceClient(self.db)
        self.finviz_client = FinvizClient(self.db)
        self.prediction_engine = create_prediction_engine(self.db, self.config)
        
        # Configuration
        self.uw_config = self.config.get('unusual_whales', {})
        self.pred_config = self.config.get('prediction_engine', {})
        self.symbols_config = self.config.get('symbols', {})
        self.finviz_config = self.config.get('finviz', {})
        
        # Polling intervals (seconds)
        self.polling_intervals = self.uw_config.get('polling', {})
        self.prediction_intervals = self.pred_config.get('update_intervals', {})
        self.price_intervals = self.config.get('price_data', {}).get('update_intervals', {})
        
        # Statistics
        self.stats = {
            'flow_records_ingested': 0,
            'price_records_updated': 0,
            'universe_size': 0,
            'predictions_generated': 0,
            'predictions_resolved': 0,
            'last_data_fetch': None,
            'last_price_update': None,
            'last_universe_refresh': None,
            'last_prediction_update': None,
            'last_resolution_check': None,
            'errors': 0
        }
        
        logger.info("✅ System Orchestrator initialized")
    
    def _find_config(self) -> str:
        """Find config.yaml."""
        possible_paths = [
            'config/config.yaml',
            '../config/config.yaml',
            str(Path(__file__).parent.parent / 'config' / 'config.yaml')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("config.yaml not found")
    
    def _load_config(self) -> Dict:
        """Load configuration."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # ═══════════════════════════════════════════════════════════════════════
    # DATA INGESTION - UNUSUAL WHALES
    # ═══════════════════════════════════════════════════════════════════════
    
    def ingest_options_flow(self):
        """Ingest options flow data from Unusual Whales."""
        try:
            logger.info("Fetching options flow...")
            
            flow_data = self.uw_client.get_options_flow(limit=100)
            
            if not flow_data:
                logger.warning("No options flow data received")
                return
            
            self.stats['flow_records_ingested'] += len(flow_data)
            self.stats['last_data_fetch'] = datetime.now()
            
            logger.info(f"✅ Received {len(flow_data)} options flow records")
            
        except Exception as e:
            logger.error(f"Options flow ingestion failed: {e}")
            self.stats['errors'] += 1
    
    def ingest_darkpool(self):
        """Ingest dark pool data."""
        try:
            logger.info("Fetching dark pool trades...")
            
            darkpool_data = self.uw_client.get_darkpool_trades(limit=50)
            
            if not darkpool_data:
                logger.warning("No dark pool data received")
                return
            
            logger.info(f"✅ Received {len(darkpool_data)} dark pool records")
            
        except Exception as e:
            logger.error(f"Dark pool ingestion failed: {e}")
            self.stats['errors'] += 1
    
    def ingest_market_tide(self):
        """Ingest market-wide sentiment data."""
        try:
            logger.info("Fetching market tide...")
            
            tide_data = self.uw_client.get_market_tide()
            
            if not tide_data:
                logger.warning("No market tide data received")
                return
            
            logger.info(f"✅ Market tide data received")
            
        except Exception as e:
            logger.error(f"Market tide ingestion failed: {e}")
            self.stats['errors'] += 1
    
    def ingest_all_data(self):
        """Ingest all Unusual Whales data types."""
        logger.info("=" * 60)
        logger.info("STARTING DATA INGESTION CYCLE")
        logger.info("=" * 60)
        
        self.ingest_options_flow()
        time.sleep(2)  # Rate limiting
        
        self.ingest_darkpool()
        time.sleep(2)
        
        self.ingest_market_tide()
        
        logger.info("✅ Data ingestion cycle complete")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PRICE DATA UPDATES
    # ═══════════════════════════════════════════════════════════════════════
    
    def update_core_prices(self):
        """Update prices for Core 4 symbols."""
        try:
            logger.info("Updating Core 4 prices...")
            
            core_symbols = self.symbols_config.get('core_4', ['SPY', 'QQQ', 'IBIT', 'ETHT'])
            
            successful = self.yf_client.batch_fetch_and_store(core_symbols, period='5d')
            
            self.stats['price_records_updated'] += successful
            self.stats['last_price_update'] = datetime.now()
            
            logger.info(f"✅ Updated prices for {successful}/{len(core_symbols)} core symbols")
            
        except Exception as e:
            logger.error(f"Core price update failed: {e}")
            self.stats['errors'] += 1
    
    def refresh_universe_daily(self):
        """Daily universe refresh from Finviz (runs once at 7 AM)."""
        try:
            logger.info("=" * 60)
            logger.info("DAILY UNIVERSE REFRESH FROM FINVIZ")
            logger.info("=" * 60)
            
            # Get configuration
            min_price = self.finviz_config.get('min_price', 5.0)
            min_volume = self.finviz_config.get('min_volume', 500000)
            max_symbols = self.finviz_config.get('max_symbols', 8500)
            
            # Fetch universe
            symbols = self.finviz_client.get_universe_all(
                min_price=min_price,
                min_volume=min_volume,
                max_symbols=max_symbols
            )
            
            self.stats['universe_size'] = len(symbols)
            self.stats['last_universe_refresh'] = datetime.now()
            
            logger.info(f"✅ Universe refresh complete: {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Universe refresh failed: {e}")
            self.stats['errors'] += 1
    
    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTION GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_predictions_for_core_symbols(self):
        """Generate predictions for core 4 symbols."""
        try:
            logger.info("Generating predictions for core symbols...")
            
            core_symbols = self.symbols_config.get('core_4', ['SPY', 'QQQ', 'IBIT', 'ETHT'])
            
            successful = self.prediction_engine.generate_predictions_batch(core_symbols)
            
            self.stats['predictions_generated'] += successful
            self.stats['last_prediction_update'] = datetime.now()
            
            logger.info(f"✅ Generated {successful}/{len(core_symbols)} core predictions")
            
        except Exception as e:
            logger.error(f"Core predictions failed: {e}")
            self.stats['errors'] += 1
    
    def resolve_predictions_all_horizons(self):
        """Resolve predictions for all time horizons."""
        try:
            logger.info("Resolving predictions...")
            
            horizons = ['1H', '1D', '1W']
            total_resolved = 0
            
            for horizon in horizons:
                resolved = self.prediction_engine.resolve_predictions(horizon)
                total_resolved += resolved
            
            self.stats['predictions_resolved'] += total_resolved
            self.stats['last_resolution_check'] = datetime.now()
            
            logger.info(f"✅ Resolved {total_resolved} predictions")
            
            # Update model accuracy after resolution
            if total_resolved > 0:
                self.prediction_engine.update_model_accuracy_all()
            
        except Exception as e:
            logger.error(f"Prediction resolution failed: {e}")
            self.stats['errors'] += 1
    
    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEM HEALTH & MONITORING
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_system_health(self):
        """Check health of all system components."""
        logger.info("Performing system health check...")
        
        health = {
            'database': False,
            'unusual_whales': False,
            'yfinance': False,
            'finviz': False,
            'prediction_engine': False,
            'timestamp': datetime.now()
        }
        
        # Database health
        try:
            health['database'] = self.db.health_check()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Unusual Whales API
        try:
            health['unusual_whales'] = self.uw_client.test_connection()
        except Exception as e:
            logger.error(f"Unusual Whales health check failed: {e}")
        
        # YFinance (simple test)
        try:
            test_price = self.yf_client.get_current_price('SPY')
            health['yfinance'] = test_price is not None
        except Exception as e:
            logger.error(f"YFinance health check failed: {e}")
        
        # Finviz (check circuit breaker state)
        try:
            finviz_health = self.finviz_client.get_health_status()
            health['finviz'] = finviz_health['circuit_breaker_state'] != 'OPEN'
        except Exception as e:
            logger.error(f"Finviz health check failed: {e}")
        
        # Prediction engine
        try:
            health['prediction_engine'] = True if self.prediction_engine else False
        except Exception as e:
            logger.error(f"Prediction engine health check failed: {e}")
        
        # Log results
        healthy_count = sum(1 for v in health.values() if isinstance(v, bool) and v)
        total_count = sum(1 for v in health.values() if isinstance(v, bool))
        
        if healthy_count == total_count:
            logger.info(f"✅ All systems healthy ({healthy_count}/{total_count})")
        else:
            logger.warning(f"⚠️ System health: {healthy_count}/{total_count} healthy")
        
        return health
    
    def print_statistics(self):
        """Print system statistics."""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        print("\n" + "=" * 80)
        print("ELITE TRADING SYSTEM - STATISTICS")
        print("=" * 80)
        print(f"Status: {'RUNNING' if self.is_running else 'STOPPED'}")
        print(f"Uptime: {uptime}")
        print(f"Start Time: {self.start_time}")
        print(f"\n--- Data Ingestion ---")
        print(f"Flow Records Ingested: {self.stats['flow_records_ingested']:,}")
        print(f"Price Records Updated: {self.stats['price_records_updated']:,}")
        print(f"Universe Size: {self.stats['universe_size']:,}")
        print(f"Last Data Fetch: {self.stats['last_data_fetch']}")
        print(f"Last Price Update: {self.stats['last_price_update']}")
        print(f"Last Universe Refresh: {self.stats['last_universe_refresh']}")
        print(f"\n--- Predictions ---")
        print(f"Predictions Generated: {self.stats['predictions_generated']:,}")
        print(f"Predictions Resolved: {self.stats['predictions_resolved']:,}")
        print(f"Last Prediction Update: {self.stats['last_prediction_update']}")
        print(f"Last Resolution Check: {self.stats['last_resolution_check']}")
        
        if hasattr(self, 'prediction_engine'):
            print(f"\n--- Model Accuracy ---")
            for horizon, accuracy in self.prediction_engine.model_accuracy.items():
                print(f"{horizon}: {accuracy:.1f}%")
        
        print(f"\n--- System ---")
        print(f"Errors: {self.stats['errors']}")
        print(f"Active Threads: {threading.active_count()}")
        print("=" * 80 + "\n")
    
    # ═══════════════════════════════════════════════════════════════════════
    # SCHEDULING
    # ═══════════════════════════════════════════════════════════════════════
    
    def setup_schedules(self):
        """Setup all scheduled tasks."""
        logger.info("Setting up schedules...")
        
        # Data ingestion schedules
        options_flow_interval = self.polling_intervals.get('options_flow_seconds', 60)
        darkpool_interval = self.polling_intervals.get('darkpool_seconds', 60)
        market_tide_interval = self.polling_intervals.get('market_tide_seconds', 300)
        
        schedule.every(options_flow_interval).seconds.do(self.ingest_options_flow)
        schedule.every(darkpool_interval).seconds.do(self.ingest_darkpool)
        schedule.every(market_tide_interval).seconds.do(self.ingest_market_tide)
        
        # Price data schedules
        price_update_interval = self.price_intervals.get('core_symbols', 300)  # 5 minutes
        schedule.every(price_update_interval).seconds.do(self.update_core_prices)
        
        # Daily universe refresh (7 AM only)
        schedule.every().day.at("07:00").do(self.refresh_universe_daily)
        
        # Prediction schedules
        pred_1h_interval = self.prediction_intervals.get('prediction_1h', 300)  # 5 minutes
        pred_resolution_interval = self.prediction_intervals.get('resolution_1h', 60)  # 1 minute
        
        schedule.every(pred_1h_interval).seconds.do(self.generate_predictions_for_core_symbols)
        schedule.every(pred_resolution_interval).seconds.do(self.resolve_predictions_all_horizons)
        
        # Health & stats
        schedule.every(5).minutes.do(self.check_system_health)
        schedule.every(15).minutes.do(self.print_statistics)
        
        logger.info("✅ Schedules configured")
    
    def run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Starting scheduler loop...")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self.stats['errors'] += 1
                time.sleep(5)
    
    # ═══════════════════════════════════════════════════════════════════════
    # MAIN CONTROL
    # ═══════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the orchestrator."""
        if self.is_running:
            logger.warning("System already running")
            return
        
        logger.info("=" * 80)
        logger.info("STARTING ELITE TRADING SYSTEM")
        logger.info("=" * 80)
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # Initial health check
        self.check_system_health()
        
        # Initial data fetch
        logger.info("Performing initial data fetch...")
        self.ingest_all_data()
        
        # Initial price update
        logger.info("Updating Core 4 prices...")
        self.update_core_prices()
        
        # Initial predictions
        logger.info("Generating initial predictions...")
        self.generate_predictions_for_core_symbols()
        
        # Setup schedules
        self.setup_schedules()
        
        # Start scheduler in main thread
        logger.info("✅ System started successfully")
        logger.info("Press Ctrl+C to stop")
        
        try:
            self.run_scheduler()
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
            self.stop()
    
    def stop(self):
        """Stop the orchestrator."""
        logger.info("Stopping Elite Trading System...")
        
        self.is_running = False
        
        # Print final stats
        self.print_statistics()
        
        logger.info("✅ System stopped")
    
    def run_once(self):
        """Run one complete cycle (for testing)."""
        logger.info("Running single cycle...")
        
        self.check_system_health()
        self.ingest_all_data()
        self.update_core_prices()
        self.generate_predictions_for_core_symbols()
        self.resolve_predictions_all_horizons()
        self.print_statistics()
        
        logger.info("✅ Single cycle complete")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                                                                       ║
    ║               ELITE TRADING SYSTEM v1.0                              ║
    ║                                                                       ║
    ║   🧠 Real-time ML Price Predictions                                  ║
    ║   🐋 Unusual Whales Flow Analysis                                    ║
    ║   📊 Multi-Horizon Predictions (1H, 1D, 1W)                          ║
    ║   💰 YFinance Price Data                                             ║
    ║   🔍 Finviz Universe Builder                                         ║
    ║                                                                       ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize orchestrator
    orchestrator = SystemOrchestrator()
    
    # Start system
    try:
        orchestrator.start()
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        orchestrator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        orchestrator.stop()
        raise


if __name__ == "__main__":
    main()

