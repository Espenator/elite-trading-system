"""Portfolio API - positions and history stub. GET /api/v1/portfolio."""

from fastapi import APIRouter
from app.websocket_manager import broadcast_ws

router = APIRouter()


@router.get("")
async def get_portfolio():
    """
    Return current positions and trade history.
    Note: When a trade executes or position changes, call:
        await broadcast_ws("trades", {"type": "trade_executed", "symbol": "AAPL", "side": "BUY", "quantity": 100})
        await broadcast_ws("trades", {"type": "position_updated", "positions": [...]})
    """
    # Positions: include both Dashboard shape (symbol, entryPrice, currentPrice, quantity, unrealizedPnL) and Trades shape (ticker, entry, current, qty, pnl)
    return {
        "positions": [
            {
                "id": 1,
                "symbol": "AAPL",
                "ticker": "AAPL",
                "side": "Long",
                "quantity": 50,
                "qty": 50,
                "entryPrice": 189.5,
                "entry": 189.5,
                "currentPrice": 192.3,
                "current": 192.3,
                "unrealizedPnL": 140,
                "pnl": 140,
                "pnlPct": 1.48,
                "stop": 185.0,
                "target": 198.0,
                "signal": "AI Signal #1",
                "time": "2h ago",
            },
            {
                "id": 2,
                "symbol": "TSLA",
                "ticker": "TSLA",
                "side": "Long",
                "quantity": 30,
                "qty": 30,
                "entryPrice": 245.3,
                "entry": 245.3,
                "currentPrice": 248.1,
                "current": 248.1,
                "unrealizedPnL": 84,
                "pnl": 84,
                "pnlPct": 1.14,
                "stop": 240.0,
                "target": 260.0,
                "signal": "AI Signal #2",
                "time": "4h ago",
            },
            {
                "id": 3,
                "symbol": "NVDA",
                "ticker": "NVDA",
                "side": "Long",
                "quantity": 10,
                "qty": 10,
                "entryPrice": 875.0,
                "entry": 875.0,
                "currentPrice": 868.2,
                "current": 868.2,
                "unrealizedPnL": -68,
                "pnl": -68,
                "pnlPct": -0.78,
                "stop": 850.0,
                "target": 920.0,
                "signal": "AI Signal #3",
                "time": "1d ago",
            },
        ],
        "history": [
            {
                "id": 101,
                "ticker": "MSFT",
                "side": "Long",
                "qty": 40,
                "entry": 408.2,
                "exit": 418.5,
                "pnl": 412,
                "pnlPct": 2.52,
                "duration": "2d 4h",
                "date": "Feb 14",
            },
            {
                "id": 102,
                "ticker": "AMD",
                "side": "Long",
                "qty": 60,
                "entry": 165.0,
                "exit": 172.3,
                "pnl": 438,
                "pnlPct": 4.42,
                "duration": "1d 8h",
                "date": "Feb 13",
            },
        ],
    }
