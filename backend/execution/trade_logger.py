"""
Trade Logger - Logs every trade for ML training
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict

from backend.core.logger import get_logger

logger = get_logger(__name__)

class TradeLogger:
    """
    Logs all trades to CSV for ML training
    """
    
    def __init__(self):
        self.log_file = Path(__file__).parent.parent / "data/logs/trades.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Trade logger initialized: {self.log_file}")
    
    def log_trade(self, trade: Dict):
        """
        Log a completed trade
        
        Args:
            trade: Trade dictionary with all details
        """
        try:
            # Convert to DataFrame row
            df = pd.DataFrame([trade])
            
            # Append to CSV
            if self.log_file.exists():
                df.to_csv(self.log_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.log_file, mode='w', header=True, index=False)
            
            logger.info(f"Trade logged: {trade['symbol']} {trade['outcome']}")
            
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    def get_all_trades(self) -> pd.DataFrame:
        """Load all logged trades"""
        if self.log_file.exists():
            return pd.read_csv(self.log_file)
        return pd.DataFrame()

# Global instance
trade_logger = TradeLogger()
