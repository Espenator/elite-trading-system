"""Orders API endpoints."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from app.services.database import db_service
from app.services.alpaca_service import alpaca_service

router = APIRouter()


class OrderCreate(BaseModel):
    """Order creation request model."""
    symbol: str = Field(..., description="Stock symbol")
    order_type: str = Field(..., description="Order type (Limit, Market, Stop, Stop Limit)")
    side: str = Field(..., description="Order side (buy, sell)")
    quantity: int = Field(..., gt=0, description="Quantity of shares")
    price: float = Field(..., ge=0, description="Price per share (optional for Market orders)")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    required_margin: Optional[float] = Field(None, description="Required margin")
    potential_pnl: Optional[float] = Field(None, description="Potential profit/loss")
        kelly_edge: Optional[float] = Field(None, description="Kelly edge for this trade")
    signal_quality: Optional[float] = Field(None, description="Signal quality 0-1")


@router.post("/", response_model=Dict)
async def create_order(order: OrderCreate):
    """
    Create a new order through Alpaca API and save to database.
    
    Returns the created order with ID and timestamp.
    """
    alpaca_order_id = None
    alpaca_status = None
    alpaca_response = None
    alpaca_error = None

        # ----- Kelly Pre-Order Validation -----
    kelly_warnings = []
    from app.core.config import settings
    if order.kelly_edge is not None and order.kelly_edge < settings.SIGNAL_MIN_EDGE:
        kelly_warnings.append(f"Low edge: {order.kelly_edge:.4f} < min {settings.SIGNAL_MIN_EDGE}")
    if order.signal_quality is not None and order.signal_quality < 0.3:
        kelly_warnings.append(f"Low signal quality: {order.signal_quality:.3f}")
    est_cost = (order.price or 0) * order.quantity
    if est_cost > 100_000 * settings.KELLY_MAX_ALLOCATION:
        kelly_warnings.append(f"Position ${est_cost:,.0f} exceeds Kelly max")
    
    # First, try to create order through Alpaca
    try:
        # Determine price and stop_price based on order type
        price_for_alpaca = None
        stop_price_for_alpaca = None
        
        if order.order_type == "Market":
            # Market orders don't need price
            price_for_alpaca = None
        elif order.order_type == "Limit":
            price_for_alpaca = order.price if order.price > 0 else None
        elif order.order_type == "Stop":
            stop_price_for_alpaca = order.price if order.price > 0 else None
        elif order.order_type == "Stop Limit":
            price_for_alpaca = order.price if order.price > 0 else None
            stop_price_for_alpaca = order.price if order.price > 0 else None
        
        alpaca_result = await alpaca_service.create_order(
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=price_for_alpaca,
            stop_price=stop_price_for_alpaca
        )
        
        alpaca_order_id = alpaca_result.get("id")
        alpaca_status = alpaca_result.get("status")
        alpaca_response = json.dumps(alpaca_result)
    except Exception as e:
        # Log error but still save to database
        alpaca_error = str(e)
        alpaca_response = json.dumps({"error": str(e)})
    
    # Save order to database (whether Alpaca succeeded or failed)
    try:
        created_order = db_service.create_order(
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            estimated_cost=order.estimated_cost,
            required_margin=order.required_margin,
            potential_pnl=order.potential_pnl,
                        kelly_edge=order.kelly_edge,
            signal_quality=order.signal_quality,
            alpaca_order_id=alpaca_order_id,
            alpaca_status=alpaca_status,
            alpaca_response=alpaca_response
        )
        
        # If Alpaca failed, include error in response
        if alpaca_error:
            created_order["alpaca_error"] = alpaca_error
            raise HTTPException(
                status_code=400,
                detail=f"Order saved to database but Alpaca API error: {alpaca_error}"
            )
        
                if kelly_warnings:
            created_order["kelly_warnings"] = kelly_warnings
return created_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save order to database: {str(e)}")


@router.get("/recent", response_model=List[Dict])
async def get_recent_orders(limit: int = 10):
    """
    Get recent orders.
    
    Returns the last N orders (default: 10).
    """
    try:
        orders = db_service.get_recent_orders(limit=limit)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


@router.get("/", response_model=List[Dict])
async def get_all_orders():
    """
    Get all orders.
    
    Returns all orders in the database.
    """
    try:
        orders = db_service.get_all_orders()
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


@router.get("/{order_id}", response_model=Dict)
async def get_order(order_id: int):
    """
    Get order by ID.
    
    Returns a specific order by its ID.
    """
    try:
        order = db_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order: {str(e)}")

