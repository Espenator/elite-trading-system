"""
Elite Trading System - Main Entry Point
=======================================

Run this file to start the complete trading system.

Usage:
    python run.py

Author: Elite Trading Team
Date: December 5, 2025
"""

import sys
import logging
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, str(Path(__file__).parent))

from core import main

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                                                                       ║
    ║               ELITE TRADING SYSTEM v1.0                              ║
    ║                                                                       ║
    ║   🚀 Real-time ML Price Predictions                                  ║
    ║   📊 Unusual Whales Flow Analysis                                    ║
    ║   🎯 Multi-Horizon Predictions (1H, 1D, 1W)                          ║
    ║   ⚡ TimescaleDB + XGBoost                                           ║
    ║                                                                       ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    
    Starting system...
    """)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ System shutdown complete")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        logging.exception("Fatal error in main")
        sys.exit(1)
