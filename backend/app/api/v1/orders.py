"""Orders API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from app.services.database import db_service

router = APIRouter()


class OrderCreate(BaseModel):
    """Order creation request model."""
    symbol: str = Field(..., description="Stock symbol")
    order_type: str = Field(..., description="Order type (Limit, Market, Stop, Stop Limit)")
    side: str = Field(..., description="Order side (buy, sell)")
    quantity: int = Field(..., gt=0, description="Quantity of shares")
    price: float = Field(..., gt=0, description="Price per share")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    required_margin: Optional[float] = Field(None, description="Required margin")
    potential_pnl: Optional[float] = Field(None, description="Potential profit/loss")


@router.post("/", response_model=Dict)
async def create_order(order: OrderCreate):
    """
    Create a new order.
    
    Returns the created order with ID and timestamp.
    """
    try:
        created_order = db_service.create_order(
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            estimated_cost=order.estimated_cost,
            required_margin=order.required_margin,
            potential_pnl=order.potential_pnl
        )
        return created_order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


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

