"""
Alpaca Broker - Real broker integration with paper/live trading
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

from backend.core.logger import get_logger
from backend.core.event_bus import event_bus

load_dotenv()
logger = get_logger(__name__)

class AlpacaBroker:
    """
    Alpaca API Broker Integration
    - Paper trading mode by default
    - Real-time order execution
    - Bracket orders with stop-loss and take-profit
    - Position tracking
    """
    
    def __init__(self, paper: bool = True):
        """
        Initialize Alpaca broker
        
        Args:
            paper: Use paper trading if True, live trading if False
        """
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.paper = paper
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials not found in .env file")
        
        # Initialize trading client
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper
        )
        
        # Initialize data client for real-time quotes
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        mode = "PAPER" if paper else "LIVE"
        logger.info(f"✅ Alpaca broker initialized in {mode} mode")
    
    def submit_market_order(
        self,
        symbol: str,
        direction: str,
        shares: int,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Submit market order
        
        Args:
            symbol: Stock ticker
            direction: 'BUY' or 'SELL'
            shares: Number of shares
            limit_price: Not used for market orders (kept for compatibility)
        
        Returns:
            Order result dict
        """
        try:
            # Convert direction to Alpaca format
            side = OrderSide.BUY if direction.upper() == 'BUY' else OrderSide.SELL
            
            # Create market order request
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.trading_client.submit_order(order_data)
            
            # Convert to our format
            result = self._convert_order_to_dict(order)
            
            logger.info(f"✅ Market order submitted: {direction} {shares} {symbol} - Order ID: {order.id}")
            
            # Publish event
            event_bus.publish('order_submitted', result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to submit market order: {e}")
            raise
    
    def submit_bracket_order(
        self,
        symbol: str,
        direction: str,
        shares: int,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Submit bracket order with stop-loss and optional take-profit
        
        Args:
            symbol: Stock ticker
            direction: 'BUY' or 'SELL'
            shares: Number of shares
            entry_price: Limit entry price
            stop_loss: Stop loss price
            take_profit: Optional take profit price
        
        Returns:
            Order result dict
        """
        try:
            side = OrderSide.BUY if direction.upper() == 'BUY' else OrderSide.SELL
            
            # Create limit order with stop loss
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY,
                limit_price=entry_price,
                stop_loss=StopLossRequest(stop_price=stop_loss)
            )
            
            # Add take profit if provided
            if take_profit:
                order_data.take_profit = TakeProfitRequest(limit_price=take_profit)
            
            # Submit order
            order = self.trading_client.submit_order(order_data)
            
            result = self._convert_order_to_dict(order)
            
            logger.info(f"✅ Bracket order submitted: {direction} {shares} {symbol} @ ${entry_price:.2f} (Stop: ${stop_loss:.2f})")
            
            event_bus.publish('bracket_order_submitted', result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to submit bracket order: {e}")
            raise
    
    def submit_stop_order(
        self,
        symbol: str,
        direction: str,
        shares: int,
        stop_price: float
    ) -> Dict:
        """
        Submit stop order
        
        Args:
            symbol: Stock ticker
            direction: 'BUY' or 'SELL'
            shares: Number of shares
            stop_price: Stop trigger price
        
        Returns:
            Order dict
        """
        try:
            side = OrderSide.BUY if direction.upper() == 'BUY' else OrderSide.SELL
            
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY,
                stop_loss=StopLossRequest(stop_price=stop_price)
            )
            
            order = self.trading_client.submit_order(order_data)
            result = self._convert_order_to_dict(order)
            
            logger.info(f"📝 Stop order submitted: {direction} {shares} {symbol} @ ${stop_price:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to submit stop order: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"❌ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order"""
        try:
            order = self.trading_client.get_order_by_id(order_id)
            return self._convert_order_to_dict(order)
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return None
    
    def get_portfolio(self) -> Dict:
        """Get current portfolio positions"""
        try:
            account = self.trading_client.get_account()
            positions = self.trading_client.get_all_positions()
            
            return {
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'qty': int(pos.qty),
                        'avg_entry_price': float(pos.avg_entry_price),
                        'current_price': float(pos.current_price),
                        'market_value': float(pos.market_value),
                        'unrealized_pl': float(pos.unrealized_pl),
                        'unrealized_plpc': float(pos.unrealized_plpc),
                        'side': pos.side
                    }
                    for pos in positions
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            return {}
    
    def get_order_history(self, limit: int = 100) -> List[Dict]:
        """Get recent order history"""
        try:
            request = GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                limit=limit
            )
            orders = self.trading_client.get_orders(request)
            return [self._convert_order_to_dict(order) for order in orders]
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[symbol]
            return float(quote.ask_price)
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
    
    def _convert_order_to_dict(self, order) -> Dict:
        """Convert Alpaca order object to dict"""
        return {
            'order_id': str(order.id),
            'symbol': order.symbol,
            'direction': order.side.value,
            'shares': int(order.qty) if order.qty else 0,
            'order_type': order.order_type.value,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'stop_price': float(order.stop_price) if order.stop_price else None,
            'fill_price': float(order.filled_avg_price) if order.filled_avg_price else None,
            'status': order.status.value,
            'filled_shares': int(order.filled_qty) if order.filled_qty else 0,
            'submitted_time': str(order.submitted_at) if order.submitted_at else None,
            'filled_time': str(order.filled_at) if order.filled_at else None,
            'commission': 0.0  # Alpaca is commission-free
        }

# Global broker instance
broker = None

def get_broker(paper: bool = True) -> AlpacaBroker:
    """Get or create broker instance"""
    global broker
    if broker is None:
        broker = AlpacaBroker(paper=paper)
    return broker

# =============================================================================
# CONVENIENCE FUNCTIONS (Compatible with paper_broker.py)
# =============================================================================

def buy_market(symbol: str, shares: int, limit_price: float = None) -> Dict:
    """Submit market buy order"""
    return get_broker().submit_market_order(symbol, 'BUY', shares, limit_price)

def sell_market(symbol: str, shares: int, limit_price: float = None) -> Dict:
    """Submit market sell order"""
    return get_broker().submit_market_order(symbol, 'SELL', shares, limit_price)

def set_stop_loss(symbol: str, shares: int, stop_price: float, direction: str) -> Dict:
    """Set stop loss order"""
    stop_direction = 'SELL' if direction == 'LONG' else 'BUY'
    return get_broker().submit_stop_order(symbol, stop_direction, shares, stop_price)

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n📊 Testing Alpaca Broker (Paper Trading)...\n")
    
    try:
        broker = get_broker(paper=True)
        
        # Test portfolio
        print("1. Getting Portfolio:")
        portfolio = broker.get_portfolio()
        print(f"   Cash: ${portfolio['cash']:.2f}")
        print(f"   Buying Power: ${portfolio['buying_power']:.2f}")
        print(f"   Portfolio Value: ${portfolio['portfolio_value']:.2f}")
        
        # Test current price
        print("\n2. Getting Current Price:")
        price = broker.get_current_price('AAPL')
        print(f"   AAPL: ${price:.2f}")
        
        # Test market order (uncomment to execute)
        # print("\n3. Submitting Test Market Order:")
        # order = buy_market('AAPL', 1)
        # print(f"   Order ID: {order['order_id']}")
        # print(f"   Status: {order['status']}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
