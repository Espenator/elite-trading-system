
"""
Signal Runner - Automated signal generation every 5 minutes
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from signal_generation.signal_aggregator import signal_aggregator


def print_header():
    """Print startup header"""
    print("\n" + "="*70)
    print("          ELITE TRADER - SIGNAL RUNNER")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Interval: Every 5 minutes")
    print("="*70 + "\n")


async def run_signal_generation():
    """Run signal generation cycle"""
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting signal generation...")
        
        result = await signal_aggregator.generate_and_store_signals()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Generation complete:")
        print(f"  - Scanned: {result.get('total_scanned', 0)} tickers")
        print(f"  - Generated: {result.get('signals_generated', 0)} signals")
        print(f"  - Written: {result.get('signals_written', 0)} to database")
        print(f"  - Tiers: {result.get('tier_counts', {})}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Next run in 5 minutes...\n")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Signal generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main runner loop"""
    print_header()
    
    # Run immediately on startup
    await run_signal_generation()
    
    # Then run every 5 minutes
    while True:
        await asyncio.sleep(300)  # 5 minutes
        await run_signal_generation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Signal Runner stopped by user.")
        print("="*70 + "\n")
