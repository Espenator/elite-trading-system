"""
Trading API Routes
Endpoints for trade execution and order management
Now supports both Paper and Alpaca trading
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

from backend.execution.unified_broker import get_broker
from backend.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

class TradeRequest(BaseModel):
    ticker: str
    side: Literal['buy', 'sell']
    quantity: int
    order_type: Literal['market', 'limit'] = 'market'
    limit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradeResponse(BaseModel):
    order_id: str
    ticker: str
    side: str
    quantity: int
    price: Optional[float]
    timestamp: str
    status: str

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """
    Execute a trade (paper or live based on TRADING_MODE env)
    
    Supports:
    - Market orders
    - Limit orders
    - Stop loss orders
    - Take profit orders
    - Bracket orders (entry + stop + target)
    """
    try:
        broker = get_broker()
        
        logger.info(f"Executing {trade.order_type} order: {trade.side.upper()} {trade.quantity} {trade.ticker}")
        
        # Execute trade
        order = broker.place_order(
            ticker=trade.ticker,
            side=trade.side,
            quantity=trade.quantity,
            order_type=trade.order_type,
            limit_price=trade.limit_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit
        )
        
        return TradeResponse(
            order_id=order['order_id'],
            ticker=order['ticker'],
            side=order['side'],
            quantity=order['quantity'],
            price=order.get('filled_avg_price') or order.get('fill_price'),
            timestamp=datetime.now().isoformat(),
            status=order['status']
        )
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
async def get_portfolio():
    """
    Get current portfolio positions
    
    Returns:
    - Cash balance
    - Buying power
    - Open positions with P&L
    - Portfolio value
    """
    try:
        broker = get_broker()
        portfolio = broker.get_portfolio()
        return portfolio
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_orders(limit: int = 100):
    """
    Get order history
    
    Args:
        limit: Maximum number of orders to return (default 100)
    """
    try:
        broker = get_broker()
        orders = broker.get_order_history(limit=limit)
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """
    Cancel a pending order
    
    Args:
        order_id: Order ID to cancel
    """
    try:
        broker = get_broker()
        success = broker.cancel_order(order_id)
        
        if success:
            return {"message": f"Order {order_id} cancelled successfully", "order_id": order_id}
        else:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found or already filled")
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/positions/{ticker}")
async def close_position(ticker: str):
    """
    Close an open position
    
    Args:
        ticker: Stock symbol to close
    """
    try:
        broker = get_broker()
        success = broker.close_position(ticker)
        
        if success:
            return {"message": f"Position {ticker} closed successfully", "ticker": ticker}
        else:
            raise HTTPException(status_code=404, detail=f"Position {ticker} not found")
    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price/{ticker}")
async def get_current_price(ticker: str):
    """
    Get current market price for a ticker
    
    Args:
        ticker: Stock symbol
    """
    try:
        broker = get_broker()
        price = broker.get_current_price(ticker)
        
        if price is not None:
            return {"ticker": ticker, "price": price, "timestamp": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=404, detail=f"Price not available for {ticker}")
    except Exception as e:
        logger.error(f"Failed to get price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_trading_status():
    """
    Get current trading mode and broker status
    """
    try:
        broker = get_broker()
        portfolio = broker.get_portfolio()
        
        return {
            "mode": broker.mode,
            "connected": broker.alpaca_client is not None if hasattr(broker, 'alpaca_client') else False,
            "buying_power": portfolio.get('buying_power', 0),
            "portfolio_value": portfolio.get('portfolio_value', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
