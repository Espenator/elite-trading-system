
"""
momentum_scanner.py - Main Scanner Integration
UPDATED: November 25, 2025 - Elite Pattern Scanner Integration
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import config
from swing_trading_elite_engine import SwingTradingScanner, convert_pattern_signals_to_trading_signals
from resources import FinvizEliteAPI, MarketRegimeDetector
from data_models import TradingSignal

logger = logging.getLogger(__name__)

class MomentumScanner:
    """Wrapper for elite swing trading scanner"""
    
    def __init__(self):
        self.scanner = SwingTradingScanner()
        self.finviz = FinvizEliteAPI()
        self.regime_detector = MarketRegimeDetector()
        logger.info("Elite MomentumScanner initialized")
    
    def run_scan(self) -> Dict[str, Any]:
        """Run complete scan with elite patterns"""
        logger.info("="*80)
        logger.info("ELITE SWING TRADING SCAN")
        logger.info("="*80)
        
        # Step 1: Market Regime
        regime = self.regime_detector.detect_regime()
        self.scanner.current_vix = regime['vix']
        logger.info(f"Regime: {regime['regime']} | VIX: {regime['vix']:.1f} | Confidence: {regime['confidence']}%")
        
        # Step 2: Gather candidates
        long_candidates = self.finviz.scan_fade_long(regime['vix'])[:config.MAX_FRACTAL_CANDIDATES]
        short_candidates = self.finviz.scan_fade_short(regime['vix'])[:config.MAX_FRACTAL_CANDIDATES]
        long_candidates.extend(config.CORE_SYMBOLS)
        short_candidates.extend(config.CORE_SYMBOLS)
        
        logger.info(f"Candidates: {len(long_candidates)} LONG | {len(short_candidates)} SHORT")
        
        # Step 3: Elite scan with default user params
        user_params = {
            'FRACTAL_WINDOW': config.FRACTAL_WINDOW,
            'FRACTAL_LOOKBACK': config.FRACTAL_LOOKBACK,
            'STAIRCASE_WINDOW': config.STAIRCASE_WINDOW,
            'GARCH_WINDOW': config.GARCH_WINDOW,
            'BASE_RSI_THRESHOLD': config.BASE_RSI_THRESHOLD,
            'VOL_CLUSTERING_THRESHOLD': config.VOL_CLUSTERING_THRESHOLD
        }
        
        long_signals = self.scanner.scan_symbols(list(set(long_candidates)), 'LONG', user_params)
        short_signals = self.scanner.scan_symbols(list(set(short_candidates)), 'SHORT', user_params)
        
        logger.info(f"Elite Signals: {len(long_signals)} LONG | {len(short_signals)} SHORT")
        
        # Convert to TradingSignal format for compatibility
        long_trading = convert_pattern_signals_to_trading_signals(long_signals)
        short_trading = convert_pattern_signals_to_trading_signals(short_signals)
        
        return {
            'regime': regime,
            'long_signals': long_trading,
            'short_signals': short_trading,
            'long_pattern_signals': long_signals,  # Keep pattern details
            'short_pattern_signals': short_signals
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)
    scanner = MomentumScanner()
    results = scanner.run_scan()
    print(f"\n{'='*80}")
    print(f"SCAN COMPLETE")
    print(f"{'='*80}")
    print(f"Found {len(results['long_signals'])} LONG + {len(results['short_signals'])} SHORT signals")



