"""Portfolio API - positions and history stub. GET /api/v1/portfolio."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_portfolio():
    return {
        "positions": [
            {
                "id": 1,
                "ticker": "AAPL",
                "side": "Long",
                "qty": 50,
                "entry": 189.5,
                "current": 192.3,
                "pnl": 140,
                "pnlPct": 1.48,
                "stop": 185.0,
                "target": 198.0,
                "signal": "AI Signal #1",
                "time": "2h ago",
            },
            {
                "id": 2,
                "ticker": "TSLA",
                "side": "Long",
                "qty": 30,
                "entry": 245.3,
                "current": 248.1,
                "pnl": 84,
                "pnlPct": 1.14,
                "stop": 240.0,
                "target": 260.0,
                "signal": "AI Signal #2",
                "time": "4h ago",
            },
            {
                "id": 3,
                "ticker": "NVDA",
                "side": "Long",
                "qty": 10,
                "entry": 875.0,
                "current": 868.2,
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
