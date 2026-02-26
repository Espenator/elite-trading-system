"""
Market indices snapshot — real data from Finviz quote API.
GET /api/v1/market/indices returns current level and % change for SPY, QQQ, DIA.
Used by Dashboard top bar. No mock data.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.finviz_service import FinvizService

logger = logging.getLogger(__name__)
router = APIRouter()
finviz = FinvizService()

# Map display id -> ticker for quote fetch
INDEX_SYMBOLS = [
    {"id": "SPX", "ticker": "SPY"},
    {"id": "NDAQ", "ticker": "QQQ"},
    {"id": "DOW", "ticker": "DIA"},
]


def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@router.get("/indices")
async def get_indices() -> Dict[str, Any]:
    """
    Return current index levels and % change (from previous close).
    Uses Finviz quote data for SPY, QQQ, DIA. Returns empty list on failure.
    """
    result: List[Dict[str, Any]] = []
    for item in INDEX_SYMBOLS:
        try:
            quotes = await finviz.get_quote_data(
                ticker=item["ticker"],
                timeframe="d",
                duration="d5",
            )
            if not quotes or not isinstance(quotes, list):
                result.append({"id": item["id"], "value": None, "change": None})
                continue
            # CSV columns may be Date, Open, High, Low, Close, Volume (or similar)
            row = quotes[-1] if quotes else {}
            prev = quotes[-2] if len(quotes) >= 2 else {}
            close_key = next(
                (k for k in ("Close", "close", "C", "Adj Close") if k in row),
                None,
            )
            if not close_key:
                close_key = list(row.keys())[-2] if len(row) > 1 else None
            close = _parse_float(row.get(close_key))
            prev_close = _parse_float(prev.get(close_key)) if prev else close
            if prev_close and close:
                change = ((close - prev_close) / prev_close) * 100
            else:
                change = None
            result.append({
                "id": item["id"],
                "value": f"{close:.2f}" if close else None,
                "change": round(change, 2) if change is not None else None,
            })
        except Exception as e:
            logger.warning("Indices fetch %s: %s", item["ticker"], e)
            result.append({"id": item["id"], "value": None, "change": None})

    return {"indices": result}
