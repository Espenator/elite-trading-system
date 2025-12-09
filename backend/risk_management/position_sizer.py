"""
Position Sizer - Van Tharp R-based sizing
"""

from typing import Dict
import yaml
from pathlib import Path

from backend.core.logger import get_logger

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_price: float,
    direction: str,
    signal_score: float = 80.0
) -> Dict:
    """
    Calculate position size using Van Tharp R-based method
    
    Args:
        capital: Available capital
        entry_price: Entry price
        stop_price: Stop loss price
        direction: 'LONG' or 'SHORT'
        signal_score: Composite score (affects sizing)
    
    Returns:
        Dict with shares, cost, risk_amount, r_value
    """
    # Get risk per trade from config (adjusted by trading style)
    style = config['user_preferences']['trading_style']
    risk_per_trade_pct = config['user_preferences']['risk_per_trade_pct'][style]
    
    # Adjust based on signal quality
    if signal_score >= 90:
        risk_multiplier = 1.2  # Risk more on high-quality signals
    elif signal_score >= 80:
        risk_multiplier = 1.0  # Normal risk
    else:
        risk_multiplier = 0.8  # Risk less on marginal signals
    
    adjusted_risk_pct = risk_per_trade_pct * risk_multiplier
    risk_amount = capital * (adjusted_risk_pct / 100)
    
    # Calculate risk per share
    risk_per_share = abs(entry_price - stop_price)
    
    if risk_per_share == 0:
        logger.error("Risk per share is 0 - cannot size position")
        return None
    
    # Calculate shares
    shares = int(risk_amount / risk_per_share)
    
    # Ensure we can afford it
    cost = shares * entry_price
    max_position_pct = config['account']['max_position_pct']
    max_cost = capital * (max_position_pct / 100)
    
    if cost > max_cost:
        # Reduce shares to fit max position size
        shares = int(max_cost / entry_price)
        cost = shares * entry_price
        risk_amount = shares * risk_per_share
    
    # Ensure minimum 1 share
    shares = max(1, shares)
    cost = shares * entry_price
    
    return {
        'shares': shares,
        'cost': cost,
        'risk_amount': risk_amount,
        'risk_per_share': risk_per_share,
        'risk_pct': (risk_amount / capital) * 100,
        'r_value': risk_per_share  # 1R = risk_per_share
    }

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    capital = 1_000_000
    entry = 180.0
    stop = 175.0
    
    result = calculate_position_size(capital, entry, stop, 'LONG', signal_score=85)
    
    print("\n📊 Position Sizing Test:")
    print(f"   Capital: ${capital:,.0f}")
    print(f"   Entry: ${entry:.2f}")
    print(f"   Stop: ${stop:.2f}")
    print(f"\n   Result:")
    print(f"   Shares: {result['shares']:,}")
    print(f"   Cost: ${result['cost']:,.0f}")
    print(f"   Risk: ${result['risk_amount']:,.0f} ({result['risk_pct']:.2f}%)")
    print(f"   1R = ${result['r_value']:.2f}")
