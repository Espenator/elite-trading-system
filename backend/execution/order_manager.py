"""
Order Manager - Tracks all orders and their lifecycle
"""

from typing import List, Dict, Optional
from datetime import datetime

from backend.core.logger import get_logger

logger = get_logger(__name__)

class OrderManager:
    """
    Centralized order tracking
    """
    
    def __init__(self):
        self.orders: List[Dict] = []
        logger.info("Order manager initialized")
    
    def add_order(self, order: Dict):
        """Add order to tracking"""
        self.orders.append(order)
        logger.debug(f"Order added: {order['order_id']}")
    
    def get_orders_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all orders for a symbol"""
        return [o for o in self.orders if o['symbol'] == symbol]
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        return [o for o in self.orders if o['status'] == 'PENDING']
    
    def get_filled_orders(self) -> List[Dict]:
        """Get all filled orders"""
        return [o for o in self.orders if o['status'] == 'FILLED']

# Global instance
order_manager = OrderManager()
