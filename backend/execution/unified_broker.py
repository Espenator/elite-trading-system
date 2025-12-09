"""
Unified Broker - Single interface for Paper and Alpaca trading
Automatically switches based on TRADING_MODE environment variable
"""

import os
from typing import Dict, Optional, List, Literal
from datetime import datetime
from dotenv import load_dotenv

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopLossRequest,
        TakeProfitRequest,
        GetOrdersRequest
    )
    from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

from backend.core.logger import get_logger
from backend.core.event_bus import event_bus

load_dotenv()
logger = get_logger(__name__)

class UnifiedBroker:
    """
    Unified broker interface that works with both Paper and Alpaca
    Seamlessly switches between modes based on configuration
    """
    
    def __init__(self):
        self.mode = os.getenv('TRADING_MODE', 'paper').lower()
        self.alpaca_client = None
        self.data_client = None
        
        if self.mode in ['alpaca', 'alpaca_paper', 'live']:
            if not ALPACA_AVAILABLE:
                logger.error("Alpaca SDK not installed. Run: pip install alpaca-py")
                logger.info("Falling back to paper trading mode")
                self.mode = 'paper'
            else:
                self._init_alpaca()
        
        if self.mode == 'paper':
            self._init_paper_broker()
        
        logger.info(f"✅ Unified Broker initialized in {self.mode.upper()} mode")
    
    def _init_alpaca(self):
        """Initialize Alpaca API clients"""
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            logger.error("Alpaca API credentials not found. Falling back to paper mode.")
            self.mode = 'paper'
            return
        
        try:
            # Paper trading always uses paper endpoint
            paper_mode = self.mode != 'live'
            
            self.alpaca_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper_mode
            )
            
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key
            )
            
            # Test connection
            account = self.alpaca_client.get_account()
            logger.info(f"📊 Alpaca connected - Account: {account.account_number}")
            logger.info(f"💰 Buying Power: ${float(account.buying_power):,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca: {e}")
            logger.info("Falling back to paper trading mode")
            self.mode = 'paper'
            self.alpaca_client = None
    
    def _init_paper_broker(self):
        """Initialize simulated paper broker"""
        from backend.execution.paper_broker import PaperBroker
        self.paper_broker = PaperBroker()
    
    def place_order(
        self,
        ticker: str,
        side: Literal['buy', 'sell'],
        quantity: int,
        order_type: Literal['market', 'limit'] = 'market',
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Universal order placement method
        
        Args:
            ticker: Stock symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market' or 'limit'
            limit_price: Limit price (for limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
        
        Returns:
            Order confirmation dict
        """
        if self.mode == 'paper':
            return self._place_paper_order(ticker, side, quantity, limit_price)
        else:
            return self._place_alpaca_order(
                ticker, side, quantity, order_type,
                limit_price, stop_loss, take_profit
            )
    
    def _place_paper_order(self, ticker: str, side: str, quantity: int, price: float) -> Dict:
        """Place order using paper broker"""
        direction = 'BUY' if side.lower() == 'buy' else 'SELL'
        return self.paper_broker.submit_market_order(ticker, direction, quantity, price)
    
    def _place_alpaca_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> Dict:
        """Place order using Alpaca API"""
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            if order_type == 'market':
                order_request = MarketOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY
                )
            else:
                order_request = LimitOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price
                )
            
            # Add stop loss if provided
            if stop_loss:
                order_request.stop_loss = StopLossRequest(stop_price=stop_loss)
            
            # Add take profit if provided
            if take_profit:
                order_request.take_profit = TakeProfitRequest(limit_price=take_profit)
            
            order = self.alpaca_client.submit_order(order_request)
            
            result = {
                'order_id': str(order.id),
                'ticker': order.symbol,
                'side': side,
                'quantity': int(order.qty),
                'order_type': order_type,
                'status': order.status.value,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': str(order.submitted_at),
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
            logger.info(f"✅ {order_type.upper()} order placed: {side.upper()} {quantity} {ticker} - Order ID: {order.id}")
            event_bus.publish('order_placed', result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Alpaca order failed: {e}")
            raise
    
    def get_portfolio(self) -> Dict:
        """Get current portfolio positions and account info"""
        if self.mode == 'paper':
            return self._get_paper_portfolio()
        else:
            return self._get_alpaca_portfolio()
    
    def _get_paper_portfolio(self) -> Dict:
        """Get paper portfolio (simulated)"""
        return {
            'cash': 1000000.0,
            'portfolio_value': 1000000.0,
            'buying_power': 1000000.0,
            'positions': []
        }
    
    def _get_alpaca_portfolio(self) -> Dict:
        """Get Alpaca portfolio"""
        try:
            account = self.alpaca_client.get_account()
            positions = self.alpaca_client.get_all_positions()
            
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
                        'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                        'side': pos.side
                    }
                    for pos in positions
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca portfolio: {e}")
            return {}
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current market price for a ticker"""
        if self.mode == 'paper':
            # For paper mode, use yfinance or return None
            return None
        
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[ticker]
            # Use mid-point of bid/ask
            return (float(quote.bid_price) + float(quote.ask_price)) / 2
        except Exception as e:
            logger.error(f"Failed to get price for {ticker}: {e}")
            return None
    
    def get_order_history(self, limit: int = 100) -> List[Dict]:
        """Get recent order history"""
        if self.mode == 'paper':
            return self.paper_broker.filled_orders if hasattr(self, 'paper_broker') else []
        
        try:
            request = GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                limit=limit
            )
            orders = self.alpaca_client.get_orders(request)
            return [
                {
                    'order_id': str(order.id),
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'qty': int(order.qty),
                    'status': order.status.value,
                    'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'submitted_at': str(order.submitted_at)
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if self.mode == 'paper':
            return self.paper_broker.cancel_order(order_id) if hasattr(self, 'paper_broker') else False
        
        try:
            self.alpaca_client.cancel_order_by_id(order_id)
            logger.info(f"❌ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def close_position(self, ticker: str) -> bool:
        """Close an open position"""
        if self.mode == 'paper':
            logger.info(f"Paper mode: Simulating close position for {ticker}")
            return True
        
        try:
            self.alpaca_client.close_position(ticker)
            logger.info(f"✅ Position closed: {ticker}")
            return True
        except Exception as e:
            logger.error(f"Failed to close position for {ticker}: {e}")
            return False

# Global broker instance (singleton)
_broker = None

def get_broker() -> UnifiedBroker:
    """Get or create the global broker instance"""
    global _broker
    if _broker is None:
        _broker = UnifiedBroker()
    return _broker

def reset_broker():
    """Reset broker instance (useful for testing)"""
    global _broker
    _broker = None
