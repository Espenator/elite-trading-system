"""
Regime Manager - Adjusts risk based on VIX and market breadth
"""

import yaml
from pathlib import Path
from typing import Dict

from core.logger import get_logger

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

def get_current_regime() -> Dict:
    """
    Determine current market regime
    
    Returns:
        Dict with regime, risk_pct, description
    """
    vix = config['market']['vix_level']
    breadth = config['market']['breadth_ratio']
    
    # GREEN: VIX < 20
    if vix < config['market']['green_vix_max']:
        return {
            'regime': 'GREEN',
            'risk_pct': config['market']['green_risk_pct'],
            'description': 'Low volatility - Normal trading',
            'color': '🟢'
        }
    
    # YELLOW: VIX 20-30
    elif vix < config['market']['yellow_vix_max']:
        return {
            'regime': 'YELLOW',
            'risk_pct': config['market']['yellow_risk_pct'],
            'description': 'Elevated volatility - Reduced risk',
            'color': '🟡'
        }
    
    # RED: VIX > 30
    else:
        # Check for recovery (VIX RSI < 40)
        vix_rsi = config['market'].get('vix_rsi_14', 50)
        
        if vix_rsi < 40:
            return {
                'regime': 'RED_RECOVERY',
                'risk_pct': config['market']['red_recovery_risk_pct'],
                'description': 'High vol but recovering - Small positions',
                'color': '🟠'
            }
        else:
            return {
                'regime': 'RED',
                'risk_pct': config['market']['red_risk_pct'],
                'description': 'High volatility - NO TRADING',
                'color': '🔴'
            }

def should_trade() -> bool:
    """Check if we should trade in current regime"""
    regime = get_current_regime()
    return regime['risk_pct'] > 0

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    regime = get_current_regime()
    
    print("\n📊 Current Market Regime:")
    print(f"   {regime['color']} {regime['regime']}")
    print(f"   Risk per trade: {regime['risk_pct']}%")
    print(f"   Description: {regime['description']}")
    print(f"\n   Should trade? {'✅ YES' if should_trade() else '❌ NO'}")
