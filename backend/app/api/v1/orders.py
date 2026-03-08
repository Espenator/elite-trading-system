"""Orders API endpoints — full Alpaca v2 order lifecycle.

Endpoints:
  POST   /orders/advanced   → create_order (bracket/OCO/OTO/trailing/notional)
  PATCH  /orders/{id}       → replace_order (amend open order)
  DELETE /orders/{id}       → cancel single order
  DELETE /orders            → cancel ALL open orders
  GET    /orders            → list open orders from Alpaca
  GET    /orders/recent     → recent orders from local DB
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Body, Depends, Request
from app.core.security import require_auth, require_role
# slowapi rate limiting handled at app level (main.py)
# from slowapi.util import get_remote_address  # moved to app-level

# _limiter removed — rate limiting handled at app level
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from app.services.database import db_service
from app.services.alpaca_service import alpaca_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic models ─────────────────────────────────────────────────────
class AdvancedOrderRequest(BaseModel):
    """Full Alpaca v2 order request."""
    symbol: str
    side: str = "buy"
    type: str = "market"
    time_in_force: str = "day"
    qty: Optional[str] = None
    notional: Optional[str] = None
    limit_price: Optional[str] = None
    stop_price: Optional[str] = None
    trail_price: Optional[str] = None
    trail_percent: Optional[str] = None
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    order_class: Optional[str] = None
    take_profit: Optional[Dict[str, Any]] = None
    stop_loss: Optional[Dict[str, Any]] = None


class ReplaceOrderRequest(BaseModel):
    """PATCH fields for order replacement."""
    qty: Optional[str] = None
    limit_price: Optional[str] = None
    stop_price: Optional[str] = None
    trail: Optional[str] = None
    time_in_force: Optional[str] = None
    client_order_id: Optional[str] = None



# ── Input Validation Models (Audit Task 13) ──────────────────────────────
import re

# Valid stock symbol pattern: 1-10 uppercase letters, optionally with dots (BRK.A)
_SYMBOL_PATTERN = re.compile(r'^[A-Z]{1,10}(\.[A-Z]{1,2})?$')

def _validate_symbol(symbol: str) -> str:
    """Validate and normalize a stock symbol."""
    if not symbol or not isinstance(symbol, str):
        raise HTTPException(status_code=422, detail="Symbol is required")
    symbol = symbol.strip().upper()
    if not _SYMBOL_PATTERN.match(symbol):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid symbol format: '{symbol}'. Expected 1-10 uppercase letters."
        )
    return symbol

def _validate_order_status(status: str) -> str:
    """Validate order status parameter before forwarding to Alpaca."""
    valid = {"open", "closed", "all", "new", "filled", "partially_filled",
             "canceled", "expired", "pending_new", "accepted", "replaced"}
    if status and status.lower() not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid order status: '{status}'. Valid: {sorted(valid)}"
        )
    return status.lower() if status else "open"

def _validate_limit(limit: int) -> int:
    """Validate order list limit parameter."""
    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=422,
            detail=f"Limit must be between 1 and 500, got {limit}"
        )
    return limit

# ── Advanced order creation ─────────────────────────────────────────────
@router.post("/advanced", response_model=Dict, dependencies=[Depends(require_auth)])
# Rate limited by app-level limiter (200/min) in main.py
async def create_advanced_order(request: Request, req: AdvancedOrderRequest):
    """Submit any Alpaca v2 order: simple, bracket, OCO, OTO, trailing."""
        # ── Alignment Preflight Gate ─────────────────────────────────────
    # Every order MUST pass alignment before reaching the broker.
    # This gate cannot be bypassed by calling /orders/advanced directly.
    from app.api.v1.alignment import run_preflight, PreflightRequest
    preflight_req = PreflightRequest(
        symbol=req.symbol,
        side=req.side,
        quantity=float(req.qty) if req.qty else 1.0,
        strategy="advanced_order",
    )
    verdict = await run_preflight(preflight_req)
    if not verdict.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ALIGNMENT_BLOCKED",
                "blockedBy": verdict.blockedBy,
                "summary": verdict.summary,
                "checks": [c.model_dump() for c in verdict.checks],
            },
        )
    logger.info("Alignment preflight PASSED for %s %s %s", req.side, req.qty, req.symbol)

    try:
        result = await alpaca_service.create_order(
            symbol=req.symbol,
            qty=req.qty,
            notional=req.notional,
            side=req.side,
            type=req.type,
            time_in_force=req.time_in_force,
            limit_price=req.limit_price,
            stop_price=req.stop_price,
            trail_price=req.trail_price,
            trail_percent=req.trail_percent,
            extended_hours=req.extended_hours,
            client_order_id=req.client_order_id,
            order_class=req.order_class,
            take_profit=req.take_profit,
            stop_loss=req.stop_loss,
        )
        if result is None:
            raise HTTPException(status_code=502, detail="Alpaca API returned no response")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_advanced_order failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Order failed: {e}")


# ── Replace / amend order ───────────────────────────────────────────────
@router.patch("/{order_id}", response_model=Dict, dependencies=[Depends(require_auth)])
async def replace_order(order_id: str, req: ReplaceOrderRequest):
    """PATCH /v2/orders/{id} — amend qty, price, trail, or TIF."""
    try:
        result = await alpaca_service.replace_order(
            order_id=order_id,
            qty=req.qty,
            limit_price=req.limit_price,
            stop_price=req.stop_price,
            trail=req.trail,
            time_in_force=req.time_in_force,
            client_order_id=req.client_order_id,
        )
        if result is None:
            raise HTTPException(status_code=400, detail="No fields to update or Alpaca returned nothing")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("replace_order failed: %s", e)
        raise HTTPException(status_code=502, detail="Broker unavailable")


# ── Cancel single order ────────────────────────────────────────────────
@router.delete("/{order_id}", dependencies=[Depends(require_auth)])
async def cancel_order(order_id: str):
    """Cancel a single open order."""
    try:
        result = await alpaca_service.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id, "detail": result}
    except Exception as e:
        logger.error("cancel_order failed: %s", e)
        raise HTTPException(status_code=502, detail="Broker unavailable")


# ── Cancel ALL open orders ──────────────────────────────────────────────
@router.delete("/", dependencies=[Depends(require_auth)])
async def cancel_all_orders():
    """Cancel all open orders."""
    try:
        result = await alpaca_service.cancel_all_orders()
        return {"status": "all_cancelled", "detail": result}
    except Exception as e:
        logger.error("cancel_all_orders failed: %s", e)
        raise HTTPException(status_code=502, detail="Broker unavailable")


# ── List open orders from Alpaca ─────────────────────────────────────────
@router.get("/")
async def get_orders(status: str = "open", limit: int = 50):
    """GET open/closed/all orders from Alpaca."""
    try:
        result = await alpaca_service.get_orders(status=status, limit=limit)
        if result is None:
            return []
        return result
    except Exception as e:
        logger.error("get_orders failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Broker unavailable: {e}")


# ── Recent orders from local DB ─────────────────────────────────────────
@router.get("/recent", response_model=List[Dict])
async def get_recent_orders(limit: int = 10):
    """Get recent orders from local database."""
    try:
        return db_service.get_recent_orders(limit=limit)
    except Exception as e:
        logger.error("get_recent_orders failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Order database unavailable: {e}")


# ── Close position ────────────────────────────────────────────────────
@router.post("/close", dependencies=[Depends(require_auth)])
async def close_position(
    symbol: Optional[str] = None,
    request: Request = None,
):
    """Close a specific position via Alpaca. Symbol via query param or JSON body."""
    sym = symbol
    if not sym:
        try:
            body = await request.json()
            sym = body.get("symbol")
        except Exception:
            pass
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")
    try:
        result = await alpaca_service.close_position(sym)
        return result or {"status": "closed", "symbol": sym}
    except Exception as e:
        logger.error("close_position failed: %s", e)
        raise HTTPException(status_code=502, detail="Broker unavailable")


# ── Adjust position ───────────────────────────────────────────────────
@router.post("/adjust", dependencies=[Depends(require_auth)])
async def adjust_position(symbol: str = Body(...), qty: str = Body(None), side: str = Body("buy")):
    """Adjust an existing position size."""
    try:
        result = await alpaca_service.create_order(
            symbol=symbol, qty=qty, side=side, type="market", time_in_force="day"
        )
        return result or {"status": "adjusted", "symbol": symbol}
    except Exception as e:
        logger.error("adjust_position failed: %s", e)
        raise HTTPException(status_code=502, detail="Broker unavailable")


# ── Flatten all positions ─────────────────────────────────────────────
@router.post("/flatten-all", dependencies=[Depends(require_role("admin"))])
async def flatten_all():
    """Liquidate all open positions."""
    try:
        result = await alpaca_service.close_all_positions()
        return result or {"status": "all_flattened"}
    except Exception as e:
        logger.error("flatten_all failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Broker unavailable: {type(e).__name__}")


# ── Emergency stop ────────────────────────────────────────────────────
@router.post("/emergency-stop", dependencies=[Depends(require_role("admin"))])
async def emergency_stop():
    """Cancel all orders and close all positions immediately."""
    errors = []
    try:
        await alpaca_service.cancel_all_orders()
    except Exception as e:
        logger.error("emergency_stop cancel_orders failed: %s", e)
        errors.append("cancel_orders failed")
    try:
        await alpaca_service.close_all_positions()
    except Exception as e:
        logger.error("emergency_stop close_positions failed: %s", e)
        errors.append("close_positions failed")
    return {"status": "emergency_stop_executed", "errors": errors if errors else None}
