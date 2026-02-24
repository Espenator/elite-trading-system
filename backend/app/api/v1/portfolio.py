"""Portfolio API — real positions and trade history from Alpaca.
GET /api/v1/portfolio returns live positions + fill history.
No mock data. No fabricated numbers.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.alpaca_service import alpaca_service
from app.websocket_manager import broadcast_ws

logger = logging.getLogger(__name__)
router = APIRouter()


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely parse a string or number to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _format_position(pos: Dict, idx: int) -> Dict:
    """Map Alpaca Position object to the frontend contract.
    Keeps both Dashboard shape (symbol, entryPrice, currentPrice, quantity)
    and Trades shape (ticker, entry, current, qty) for compatibility."""
    symbol = (pos.get("symbol") or "").upper()
    qty = _safe_float(pos.get("qty"))
    cost_basis = _safe_float(pos.get("cost_basis"))
    entry_price = round(cost_basis / qty, 4) if qty else 0.0
    current_price = _safe_float(pos.get("current_price"))
    unrealized_pl = _safe_float(pos.get("unrealized_pl"))
    unrealized_plpc = _safe_float(pos.get("unrealized_plpc"))
    side_raw = (pos.get("side") or "long").lower()
    side_display = "Long" if side_raw == "long" else "Short"
    change_today = _safe_float(pos.get("change_today"))
    market_value = _safe_float(pos.get("market_value"))
    lastday_price = _safe_float(pos.get("lastday_price"))
    asset_id = pos.get("asset_id", "")

    return {
        "id": idx + 1,
        "symbol": symbol,
        "ticker": symbol,
        "side": side_display,
        "quantity": _safe_int(qty),
        "qty": _safe_int(qty),
        "entryPrice": round(entry_price, 2),
        "entry": round(entry_price, 2),
        "currentPrice": round(current_price, 2),
        "current": round(current_price, 2),
        "unrealizedPnL": round(unrealized_pl, 2),
        "pnl": round(unrealized_pl, 2),
        "pnlPct": round(unrealized_plpc * 100, 2),
        "marketValue": round(market_value, 2),
        "costBasis": round(cost_basis, 2),
        "changeToday": round(change_today * 100, 4),
        "lastdayPrice": round(lastday_price, 2),
        "stop": None,
        "target": None,
        "signal": None,
        "assetId": asset_id,
    }


def _format_fill(fill: Dict, idx: int) -> Dict:
    """Map an Alpaca FILL activity to the frontend history shape."""
    symbol = (fill.get("symbol") or "").upper()
    side_raw = (fill.get("side") or "").lower()
    side_display = "Long" if side_raw == "buy" else "Short"
    price = _safe_float(fill.get("price"))
    qty = _safe_int(fill.get("qty"))
    tx_time = fill.get("transaction_time") or ""
    order_id = fill.get("order_id") or ""

    date_str = ""
    if tx_time:
        try:
            dt = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d")
        except Exception:
            date_str = tx_time[:10]

    return {
        "id": idx + 1,
        "ticker": symbol,
        "side": side_display,
        "qty": qty,
        "entry": round(price, 2) if side_raw == "buy" else None,
        "exit": round(price, 2) if side_raw == "sell" else None,
        "price": round(price, 2),
        "pnl": None,
        "pnlPct": None,
        "duration": None,
        "date": date_str,
        "orderId": order_id,
        "transactionTime": tx_time,
    }


@router.get("")
async def get_portfolio():
    """
    Return current positions and trade history from Alpaca.
    Positions: live from GET /v2/positions.
    History: recent FILL activities from GET /v2/account/activities.

    WebSocket note: when a trade executes or position changes, call:
        await broadcast_ws("trades", {"type": "trade_executed", ...})
        await broadcast_ws("trades", {"type": "position_updated", ...})
    """
    positions_raw = await alpaca_service.get_positions()
    activities_raw = await alpaca_service.get_activities(
        activity_types="FILL", limit=50
    )

    if positions_raw is None and activities_raw is None:
        return {
            "positions": [],
            "history": [],
            "error": "Alpaca API unavailable or not configured",
        }

    positions = []
    if positions_raw:
        positions = [
            _format_position(p, i) for i, p in enumerate(positions_raw)
        ]

    history = []
    if activities_raw:
        history = [
            _format_fill(f, i) for i, f in enumerate(activities_raw)
        ]

    return {"positions": positions, "history": history}
