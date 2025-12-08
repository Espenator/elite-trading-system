"""
Trading API Routes
Endpoints for trade execution and order management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

router = APIRouter()

class TradeRequest(BaseModel):
    ticker: str
    side: Literal['buy', 'sell']
    quantity: int

class TradeResponse(BaseModel):
    order_id: str
    ticker: str
    side: str
    quantity: int
    price: float
    timestamp: str
    status: str

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """Execute a paper trade"""
    try:
        # Import paper broker
        from execution.paper_broker import PaperBroker
        
        broker = PaperBroker()
        
        # Execute trade
        order = broker.place_order(
            ticker=trade.ticker,
            side=trade.side,
            quantity=trade.quantity
        )
        
        return TradeResponse(
            order_id=order['order_id'],
            ticker=order['ticker'],
            side=order['side'],
            quantity=order['quantity'],
            price=order['fill_price'],
            timestamp=datetime.now().isoformat(),
            status=order['status']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
async def get_portfolio():
    """Get current portfolio positions"""
    try:
        from execution.paper_broker import PaperBroker
        
        broker = PaperBroker()
        portfolio = broker.get_portfolio()
        
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_orders():
    """Get order history"""
    try:
        from execution.paper_broker import PaperBroker
        
        broker = PaperBroker()
        orders = broker.get_order_history()
        
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
