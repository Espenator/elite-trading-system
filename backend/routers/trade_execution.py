"""
Trade Execution API Router
Handles order execution, positions, order book, and real-time trade data.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
import asyncio
import json
import random
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trade-execution", tags=["trade-execution"])

# ─── Models ─────────────────────────────────────────────────

class PortfolioResponse(BaseModel):
    value: float = 1580420.55
    dailyPnl: float = 12500.80
    dailyPnlPct: float = 0.35
    status: str = "ELITE"
    latency: int = 8

class OrderRequest(BaseModel):
    symbol: str = "SPX"
    side: Literal["buy", "sell"] = "buy"
    type: Literal["market", "limit", "stop", "stop_limit"] = "market"
    quantity: int = 10
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

class AdvancedOrderRequest(BaseModel):
    symbol: str = "SPX"
    strategy: str = "Iron Condor"
    callStrikes: Optional[dict] = None
    putStrikes: Optional[dict] = None
    quantity: int = 10
    limitPrice: Optional[float] = None
    stopPrice: Optional[float] = None

class ClosePositionRequest(BaseModel):
    symbol: str
    side: str

class AdjustPositionRequest(BaseModel):
    symbol: str
    side: str
    new_quantity: Optional[int] = None
    new_stop: Optional[float] = None

class OrderResponse(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    type: str
    quantity: int
    filled_price: Optional[float] = None
    timestamp: str
    message: str

class PositionResponse(BaseModel):
    symbol: str
    side: str
    quantity: int
    avgPrice: float
    currentPrice: float
    pnl: float

class OrderBookEntry(BaseModel):
    price: str
    bid: str
    size: int
    total: int

class PriceLadderEntry(BaseModel):
    row: int
    price: str
    size: int
    bidSize: int
    askSize: int

class NewsFeedEntry(BaseModel):
    time: str
    text: str
    type: str

class SystemStatusEntry(BaseModel):
    time: str
    text: str
    type: str


# ─── In-Memory State ───────────────────────────────────────

_positions: List[dict] = [
    {"symbol": "SPX", "side": "Long", "quantity": 50, "avgPrice": 4435.00, "currentPrice": 4450.25, "pnl": 7625.00},
    {"symbol": "SPX", "side": "Short", "quantity": 50, "avgPrice": 4435.00, "currentPrice": 4450.25, "pnl": 7625.00},
]

_order_counter = 123456
_system_log: List[dict] = [
    {"time": "09:30:12", "text": "Order #123456 executed successfully (SPX, Buy, 50 contracts).", "type": "success"},
    {"time": "09:30:08", "text": "Connected to market data feed: Latency 8ms.", "type": "info"},
    {"time": "09:30:02", "text": "Warning: High market volatility detected.", "type": "warning"},
    {"time": "09:30:00", "text": "System initialized. All services online.", "type": "success"},
    {"time": "09:29:55", "text": "User Logged In: ELITE status confirmed.", "type": "info"},
]

_news_feed: List[dict] = [
    {"time": "09:30:05", "text": "FED official comments on interest rates cause market volatility.", "type": "warning"},
    {"time": "09:25:45", "text": "Strong economic data released, boosting sentiment.", "type": "positive"},
    {"time": "09:15:30", "text": "Breaking: Geopolitical tensions escalate, impacting oil prices.", "type": "negative"},
    {"time": "09:10:15", "text": "Earnings Alert: XYZ Inc. reports Q2 results, beats estimates.", "type": "positive"},
]

_ws_clients: List[WebSocket] = []


# ─── Helper Functions ───────────────────────────────────────

def _generate_order_book(symbol: str = "SPX") -> List[dict]:
    base_price = 4450.25
    entries = []
    for i in range(20):
        price = base_price - i * 0.25
        entries.append({
            "price": f"{price:.2f}",
            "bid": f"{price - 0.25:.2f}",
            "size": random.randint(10, 150),
            "total": random.randint(100, 900),
        })
    return entries

def _generate_price_ladder(symbol: str = "SPX") -> List[dict]:
    base = 4450.00
    entries = []
    for i in range(20):
        price = base + (random.random() - 0.5) * 10
        entries.append({
            "row": i + 1,
            "price": f"{price:.2f}",
            "size": random.randint(0, 30),
            "bidSize": random.randint(0, 15),
            "askSize": random.randint(0, 15),
        })
    return entries

def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")

async def _broadcast(msg: dict):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


# ─── REST Endpoints ─────────────────────────────────────────

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get portfolio summary including value, P/L, status, and latency."""
    pnl_variance = random.uniform(-200, 200)
    return PortfolioResponse(
        value=1580420.55 + pnl_variance * 10,
        dailyPnl=12500.80 + pnl_variance,
        dailyPnlPct=round(0.35 + pnl_variance / 35000, 4),
        status="ELITE",
        latency=random.randint(5, 12),
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions():
    """Get all live positions."""
    for pos in _positions:
        pos["currentPrice"] = round(pos["avgPrice"] + random.uniform(-5, 15), 2)
        pos["pnl"] = round((pos["currentPrice"] - pos["avgPrice"]) * pos["quantity"] * (1 if pos["side"] == "Long" else -1), 2)
    return _positions


@router.post("/positions/close", response_model=OrderResponse)
async def close_position(req: ClosePositionRequest):
    """Close a specific position."""
    global _order_counter
    _order_counter += 1

    closed = None
    for i, pos in enumerate(_positions):
        if pos["symbol"] == req.symbol and pos["side"] == req.side:
            closed = _positions.pop(i)
            break

    if not closed:
        raise HTTPException(status_code=404, detail=f"Position {req.symbol} {req.side} not found")

    log_entry = {"time": _now_str(), "text": f"Position closed: {req.symbol} {req.side} x{closed['quantity']}", "type": "success"}
    _system_log.insert(0, log_entry)
    await _broadcast({"type": "system_status", "payload": log_entry})
    await _broadcast({"type": "positions", "payload": _positions})

    return OrderResponse(
        order_id=f"#{_order_counter}",
        status="filled",
        symbol=req.symbol,
        side="sell" if req.side == "Long" else "buy",
        type="market",
        quantity=closed["quantity"],
        filled_price=closed["currentPrice"],
        timestamp=_now_str(),
        message=f"Position {req.symbol} {req.side} closed at {closed['currentPrice']:.2f}",
    )


@router.post("/positions/adjust")
async def adjust_position(req: AdjustPositionRequest):
    """Adjust an existing position (stop loss, quantity, etc.)."""
    for pos in _positions:
        if pos["symbol"] == req.symbol and pos["side"] == req.side:
            if req.new_quantity:
                pos["quantity"] = req.new_quantity
            log_entry = {"time": _now_str(), "text": f"Position adjusted: {req.symbol} {req.side}", "type": "info"}
            _system_log.insert(0, log_entry)
            await _broadcast({"type": "system_status", "payload": log_entry})
            return {"status": "adjusted", "position": pos}
    raise HTTPException(status_code=404, detail="Position not found")


@router.get("/order-book", response_model=List[OrderBookEntry])
async def get_order_book(symbol: str = Query("SPX")):
    """Get live order book for symbol."""
    return _generate_order_book(symbol)


@router.get("/price-ladder", response_model=List[PriceLadderEntry])
async def get_price_ladder(symbol: str = Query("SPX")):
    """Get multi-price ladder for symbol."""
    return _generate_price_ladder(symbol)


@router.post("/orders", response_model=OrderResponse)
async def execute_order(order: OrderRequest):
    """Execute a standard order (market, limit, stop)."""
    global _order_counter
    _order_counter += 1

    base_price = 4450.25
    filled_price = base_price if order.type == "market" else (order.limit_price or base_price)

    # Add to positions
    side = "Long" if order.side == "buy" else "Short"
    new_pos = {
        "symbol": order.symbol,
        "side": side,
        "quantity": order.quantity,
        "avgPrice": filled_price,
        "currentPrice": filled_price,
        "pnl": 0.0,
    }

    # Merge with existing position if same symbol/side
    merged = False
    for pos in _positions:
        if pos["symbol"] == order.symbol and pos["side"] == side:
            total_qty = pos["quantity"] + order.quantity
            pos["avgPrice"] = round((pos["avgPrice"] * pos["quantity"] + filled_price * order.quantity) / total_qty, 2)
            pos["quantity"] = total_qty
            merged = True
            break

    if not merged:
        _positions.append(new_pos)

    msg = f"Order #{_order_counter} executed successfully ({order.symbol}, {order.side.title()}, {order.quantity} contracts)."
    log_entry = {"time": _now_str(), "text": msg, "type": "success"}
    _system_log.insert(0, log_entry)

    await _broadcast({"type": "order_executed", "payload": {"message": msg}})
    await _broadcast({"type": "positions", "payload": _positions})

    return OrderResponse(
        order_id=f"#{_order_counter}",
        status="filled",
        symbol=order.symbol,
        side=order.side,
        type=order.type,
        quantity=order.quantity,
        filled_price=filled_price,
        timestamp=_now_str(),
        message=msg,
    )


@router.post("/orders/advanced", response_model=OrderResponse)
async def execute_advanced_order(order: AdvancedOrderRequest):
    """Execute an advanced multi-leg options order (Iron Condor, spreads, etc.)."""
    global _order_counter
    _order_counter += 1

    filled_price = order.limitPrice or 1.55
    msg = f"{order.strategy} executed: {order.symbol} x{order.quantity} @ ${filled_price:.2f}"
    log_entry = {"time": _now_str(), "text": msg, "type": "success"}
    _system_log.insert(0, log_entry)

    await _broadcast({"type": "order_executed", "payload": {"message": msg}})

    return OrderResponse(
        order_id=f"#{_order_counter}",
        status="filled",
        symbol=order.symbol,
        side="buy",
        type="advanced",
        quantity=order.quantity,
        filled_price=filled_price,
        timestamp=_now_str(),
        message=msg,
    )


@router.get("/news-feed", response_model=List[NewsFeedEntry])
async def get_news_feed(limit: int = Query(20, ge=1, le=100)):
    """Get market news feed."""
    return _news_feed[:limit]


@router.get("/system-status", response_model=List[SystemStatusEntry])
async def get_system_status():
    """Get system status log."""
    return _system_log[:20]


# ─── WebSocket ──────────────────────────────────────────────

@router.websocket("/ws/trade-execution")
async def trade_execution_ws(websocket: WebSocket):
    """Real-time WebSocket for trade execution updates."""
    await websocket.accept()
    _ws_clients.append(websocket)
    logger.info(f"[TradeExecution WS] Client connected. Total: {len(_ws_clients)}")

    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(2)
            try:
                await websocket.send_json({
                    "type": "price_ladder",
                    "payload": _generate_price_ladder(),
                })
                await websocket.send_json({
                    "type": "order_book",
                    "payload": _generate_order_book(),
                })
            except Exception:
                break
    except WebSocketDisconnect:
        logger.info("[TradeExecution WS] Client disconnected")
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
