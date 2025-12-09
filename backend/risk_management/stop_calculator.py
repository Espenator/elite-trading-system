"""
Stop Calculator - ATR-based trailing stops
"""

import pandas as pd
import yaml
from pathlib import Path

from backend.core.logger import get_logger

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

def calculate_trailing_stop(
    entry_price: float,
    current_price: float,
    direction: str,
    atr: float,
    unrealized_pnl: float,
    risk_amount: float
) -> float:
    """
    Calculate trailing stop price
    
    Rules:
    - Initial stop: ATR-based (2.5x for momentum)
    - Trail activates at 1R profit
    - Trail distance: 3% (configurable by style)
    
    Args:
        entry_price: Entry price
        current_price: Current market price
        direction: 'LONG' or 'SHORT'
        atr: Average True Range (14-period)
        unrealized_pnl: Current P&L
        risk_amount: Initial risk amount (1R)
    
    Returns:
        New stop price
    """
    style = config['user_preferences']['trading_style']
    trail_pct = config['user_preferences']['trailing_stop_pct'][style] / 100
    
    # Check if we're in profit (>= 1R)
    if unrealized_pnl >= risk_amount:
        # Trail from current price
        if direction == 'LONG':
            new_stop = current_price * (1 - trail_pct)
        else:
            new_stop = current_price * (1 + trail_pct)
        
        return new_stop
    else:
        # Use original ATR-based stop
        multiplier = config['risk']['atr_multiplier_momentum']
        
        if direction == 'LONG':
            original_stop = entry_price - (atr * multiplier)
        else:
            original_stop = entry_price + (atr * multiplier)
        
        return original_stop

def should_move_to_breakeven(
    unrealized_pnl: float,
    risk_amount: float
) -> bool:
    """
    Check if stop should be moved to breakeven
    
    Returns True if profit >= 1R
    """
    return unrealized_pnl >= risk_amount

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    entry = 180.0
    current = 185.0
    direction = 'LONG'
    atr = 3.5
    pnl = 5000
    risk = 4000  # 1R = $4000
    
    new_stop = calculate_trailing_stop(entry, current, direction, atr, pnl, risk)
    
    print("\n📊 Trailing Stop Test:")
    print(f"   Entry: ${entry:.2f}")
    print(f"   Current: ${current:.2f}")
    print(f"   P&L: ${pnl:,.0f} ({pnl/risk:.2f}R)")
    print(f"\n   New Stop: ${new_stop:.2f}")
    
    if should_move_to_breakeven(pnl, risk):
        print(f"   ✅ Move to breakeven ({entry:.2f})")
