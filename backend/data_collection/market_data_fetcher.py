"""
Market data fetcher - VIX, breadth, futures, etc.
"""

import yfinance as yf
from typing import Dict
from datetime import datetime

from backend.core.logger import get_logger

logger = get_logger(__name__)

async def get_market_data() -> Dict:
    """
    Get current market conditions
    
    Returns:
        Dictionary with VIX, SPY, QQQ, breadth, etc.
    """
    try:
        data = {}
        
        # VIX
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period='1d')
        if not vix_data.empty:
            data['vix'] = float(vix_data['Close'].iloc[-1])
        
        # SPY
        spy = yf.Ticker("SPY")
        spy_data = spy.history(period='5d')
        if not spy_data.empty:
            data['spy_price'] = float(spy_data['Close'].iloc[-1])
            data['spy_change_pct'] = ((spy_data['Close'].iloc[-1] / spy_data['Close'].iloc[0]) - 1) * 100
        
        # QQQ
        qqq = yf.Ticker("QQQ")
        qqq_data = qqq.history(period='5d')
        if not qqq_data.empty:
            data['qqq_price'] = float(qqq_data['Close'].iloc[-1])
            data['qqq_change_pct'] = ((qqq_data['Close'].iloc[-1] / qqq_data['Close'].iloc[0]) - 1) * 100
        
        # TODO: Get breadth ratio from Finviz
        data['breadth_ratio'] = 0.28  # Placeholder
        
        data['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"📊 Market data: VIX={data.get('vix', 0):.2f}, SPY={data.get('spy_change_pct', 0):.2f}%")
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to get market data: {e}")
        return {}
