"""
Test script to populate symbol universe in database
Run this ONCE to download all qualifying symbols from Finviz/yfinance
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 80)
    print("🚀 ELITE TRADING SYSTEM - UNIVERSE POPULATION")
    print("=" * 80)
    print()
    print("This will download ALL qualifying symbols from:")
    print("  - Finviz Elite API (Tier 1 filters)")
    print("  - yfinance (validation & enrichment)")
    print()
    print("Filters:")
    print("  - Price: $10 - $500,000")
    print("  - Volume: 500K+ avg daily")
    print("  - Market Cap: $1B+")
    print("  - Excludes: Leveraged ETFs, micro-caps")
    print()
    print("Expected result: ~2,000-3,000 quality stocks")
    print("Estimated time: 15-30 minutes")
    print()
    print("=" * 80)
    
    input("Press ENTER to start population...")
    
    print()
    print("Importing database module...")
    
    # Import here to avoid circular imports
    from database import populate_symbols_from_apis
    
    print("Starting population...")
    
    # Run population (it's not async)
    populate_symbols_from_apis()
    
    print()
    print("=" * 80)
    print("✅ UNIVERSE POPULATION COMPLETE!")
    print("=" * 80)
    print()
    print("Next step: Restart backend to see symbol count")
    print()

if __name__ == "__main__":
    main()

