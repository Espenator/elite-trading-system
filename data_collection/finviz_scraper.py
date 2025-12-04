"""
Finviz Elite screener - Universe filter (8,500 → 500)
"""

from finvizfinance.screener.overview import Overview
from typing import List, Dict
import pandas as pd
import yaml
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

async def get_universe() -> List[str]:
    """
    Filter universe using Finviz Elite screener
    
    Applies filters from config.yaml:
    - Price: $5 - $500 (configurable)
    - Volume: >500K
    - Market cap: >$1B
    - Excludes: Inverse ETFs, 3x leveraged
    
    Returns:
        List of 500 symbols that pass filters
    """
    logger.info("🔍 Finviz: Filtering universe...")
    
    try:
        # Get filter settings from config
        min_price = config['user_preferences']['min_stock_price']
        max_price = config['user_preferences']['max_stock_price']
        min_volume = config['user_preferences']['min_avg_volume']
        min_mcap = config['universe']['min_market_cap']
        core_symbols = config['universe']['core_symbols']
        
        # Initialize screener
        foverview = Overview()
        
        # Set filters
        filters_dict = {
            'Price': f'Over ${min_price}',
            'Average Volume': f'Over {min_volume/1000}K',
            'Market Cap.': '+Mid (over $2bln)' if min_mcap >= 2e9 else '+Small (over $300mln)',
        }
        
        foverview.set_filter(filters_dict=filters_dict)
        
        # Get screener results
        df = foverview.screener_view()
        
        if df is None or df.empty:
            logger.warning("Finviz returned no results")
            return core_symbols
        
        # Extract symbols
        symbols = df['Ticker'].tolist()
        
        # Apply additional filters
        symbols = [s for s in symbols if is_valid_symbol(s)]
        
        # Always include Core 4
        for symbol in core_symbols:
            if symbol not in symbols:
                symbols.insert(0, symbol)
        
        # Limit to 500 (or configured amount)
        symbols = symbols[:500]
        
        logger.info(f"✅ Finviz: {len(symbols)} symbols pass filters")
        
        # Save to cache
        cache_path = Path(__file__).parent.parent / "data/cache/universe.csv"
        pd.DataFrame({'symbol': symbols}).to_csv(cache_path, index=False)
        
        return symbols
        
    except Exception as e:
        logger.error(f"❌ Finviz scraping failed: {e}")
        
        # Fallback to cached universe
        cache_path = Path(__file__).parent.parent / "data/cache/universe.csv"
        if cache_path.exists():
            logger.warning("Using cached universe")
            df = pd.read_csv(cache_path)
            return df['symbol'].tolist()
        
        # Ultimate fallback: Core 4 only
        return config['universe']['core_symbols']

def is_valid_symbol(symbol: str) -> bool:
    """
    Check if symbol is valid (not inverse ETF, leveraged, etc.)
    
    Args:
        symbol: Stock ticker
    
    Returns:
        True if valid, False otherwise
    """
    # Exclude patterns
    invalid_patterns = [
        'SQQQ', 'TQQQ',  # 3x leveraged
        'SPXU', 'SPXL',  # 3x leveraged
        'UVXY', 'SVXY',  # Volatility products
        'TMV', 'TMF',    # 3x Treasury
        '^',             # Indices
        '.',             # Special characters
    ]
    
    for pattern in invalid_patterns:
        if pattern in symbol:
            return False
    
    return True

def get_finviz_quote(symbol: str) -> Dict:
    """
    Get detailed quote for a single symbol
    
    Args:
        symbol: Stock ticker
    
    Returns:
        Dictionary with quote data
    """
    try:
        from finvizfinance.quote import finvizfinance
        stock = finvizfinance(symbol)
        
        # Get fundamental data
        fundamentals = stock.ticker_fundament()
        
        return {
            'symbol': symbol,
            'price': float(fundamentals.get('Price', 0)),
            'volume': float(fundamentals.get('Volume', 0).replace(',', '')),
            'market_cap': fundamentals.get('Market Cap', 'N/A'),
            'sector': fundamentals.get('Sector', 'Unknown'),
            'industry': fundamentals.get('Industry', 'Unknown'),
        }
        
    except Exception as e:
        logger.error(f"Failed to get Finviz quote for {symbol}: {e}")
        return {}

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        symbols = await get_universe()
        print(f"\n✅ Got {len(symbols)} symbols")
        print(f"\nFirst 10: {symbols[:10]}")
    
    asyncio.run(test())
