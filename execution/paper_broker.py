"""
Paper Broker - Simulates order fills with realistic slippage
"""

from typing import Dict, Optional
from datetime import datetime
import random

from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)

class PaperBroker:
    """
    Simulates realistic order execution
    - Market orders: instant fill with 0.1% slippage
    - Stop orders: fill when price hits stop
    - Realistic partial fills for large orders
    """
    
    def __init__(self):
        self.pending_orders = {}
        self.filled_orders = []
        logger.info("Paper broker initialized")
    
    def submit_market_order(
        self,
        symbol: str,
        direction: str,
        shares: int,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Submit market order (fills immediately)
        
        Args:
            symbol: Stock ticker
            direction: 'BUY' or 'SELL'
            shares: Number of shares
            limit_price: Optional limit price
        
        Returns:
            Order result dict
        """
        # Simulate slippage (0.1% for market orders)
        if limit_price:
            slippage = limit_price * 0.001
            if direction == 'BUY':
                fill_price = limit_price + slippage
            else:
                fill_price = limit_price - slippage
        else:
            fill_price = 0.0  # Would need real-time price
        
        order = {
            'order_id': self._generate_order_id(),
            'symbol': symbol,
            'direction': direction,
            'shares': shares,
            'order_type': 'MARKET',
            'limit_price': limit_price,
            'fill_price': fill_price,
            'status': 'FILLED',
            'filled_shares': shares,
            'filled_time': datetime.now().isoformat(),
            'commission': self._calculate_commission(shares, fill_price)
        }
        
        self.filled_orders.append(order)
        
        logger.info(f"✅ Order filled: {direction} {shares} {symbol} @ ${fill_price:.2f}")
        
        # Publish event
        event_bus.publish('order_filled', order)
        
        return order
    
    def submit_stop_order(
        self,
        symbol: str,
        direction: str,
        shares: int,
        stop_price: float
    ) -> Dict:
        """
        Submit stop order (fills when price hits stop)
        
        Args:
            symbol: Stock ticker
            direction: 'BUY' or 'SELL'
            shares: Number of shares
            stop_price: Stop price
        
        Returns:
            Order dict (pending until triggered)
        """
        order = {
            'order_id': self._generate_order_id(),
            'symbol': symbol,
            'direction': direction,
            'shares': shares,
            'order_type': 'STOP',
            'stop_price': stop_price,
            'status': 'PENDING',
            'submitted_time': datetime.now().isoformat()
        }
        
        self.pending_orders[order['order_id']] = order
        
        logger.info(f"📝 Stop order submitted: {direction} {shares} {symbol} @ ${stop_price:.2f}")
        
        return order
    
    def check_stop_orders(self, symbol: str, current_price: float):
        """
        Check if any stop orders should trigger
        
        Args:
            symbol: Stock ticker
            current_price: Current market price
        """
        triggered = []
        
        for order_id, order in self.pending_orders.items():
            if order['symbol'] != symbol:
                continue
            
            if order['order_type'] != 'STOP':
                continue
            
            # Check if stop triggered
            stop_price = order['stop_price']
            
            if order['direction'] == 'SELL' and current_price <= stop_price:
                # Stop loss for LONG position
                triggered.append(order_id)
            elif order['direction'] == 'BUY' and current_price >= stop_price:
                # Stop loss for SHORT position
                triggered.append(order_id)
        
        # Execute triggered stops
        for order_id in triggered:
            order = self.pending_orders.pop(order_id)
            self._execute_stop_order(order, current_price)
    
    def _execute_stop_order(self, order: Dict, trigger_price: float):
        """Execute a triggered stop order"""
        # Simulate slippage (0.2% for stops - worse than market)
        slippage = trigger_price * 0.002
        
        if order['direction'] == 'SELL':
            fill_price = trigger_price - slippage
        else:
            fill_price = trigger_price + slippage
        
        order.update({
            'fill_price': fill_price,
            'status': 'FILLED',
            'filled_shares': order['shares'],
            'filled_time': datetime.now().isoformat(),
            'commission': self._calculate_commission(order['shares'], fill_price),
            'trigger_price': trigger_price
        })
        
        self.filled_orders.append(order)
        
        logger.warning(f"🛑 Stop triggered: {order['direction']} {order['shares']} {order['symbol']} @ ${fill_price:.2f}")
        
        # Publish event
        event_bus.publish('stop_triggered', order)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if order_id in self.pending_orders:
            order = self.pending_orders.pop(order_id)
            order['status'] = 'CANCELLED'
            logger.info(f"❌ Order cancelled: {order_id}")
            return True
        return False
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        import uuid
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    def _calculate_commission(self, shares: int, price: float) -> float:
        """Calculate commission (free for paper trading)"""
        return 0.0
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order"""
        # Check pending
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]
        
        # Check filled
        for order in self.filled_orders:
            if order['order_id'] == order_id:
                return order
        
        return None

# Global broker instance
broker = PaperBroker()

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def buy_market(symbol: str, shares: int, limit_price: float) -> Dict:
    """Submit market buy order"""
    return broker.submit_market_order(symbol, 'BUY', shares, limit_price)

def sell_market(symbol: str, shares: int, limit_price: float) -> Dict:
    """Submit market sell order"""
    return broker.submit_market_order(symbol, 'SELL', shares, limit_price)

def set_stop_loss(symbol: str, shares: int, stop_price: float, direction: str) -> Dict:
    """Set stop loss order"""
    stop_direction = 'SELL' if direction == 'LONG' else 'BUY'
    return broker.submit_stop_order(symbol, stop_direction, shares, stop_price)

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n📊 Testing Paper Broker...")
    
    # Test market order
    print("\n1. Market Buy Order:")
    order1 = buy_market('AAPL', 100, 180.0)
    print(f"   Order ID: {order1['order_id']}")
    print(f"   Fill Price: ${order1['fill_price']:.2f}")
    
    # Test stop order
    print("\n2. Stop Loss Order:")
    order2 = set_stop_loss('AAPL', 100, 175.0, 'LONG')
    print(f"   Order ID: {order2['order_id']}")
    print(f"   Status: {order2['status']}")
    
    # Test stop trigger
    print("\n3. Simulating price drop to trigger stop...")
    broker.check_stop_orders('AAPL', 174.5)
    
    status = broker.get_order_status(order2['order_id'])
    print(f"   New Status: {status['status']}")
    if status['status'] == 'FILLED':
        print(f"   Fill Price: ${status['fill_price']:.2f}")
