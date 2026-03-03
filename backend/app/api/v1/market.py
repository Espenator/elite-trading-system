"""
Market indices snapshot — real data from Finviz quote API.
GET /api/v1/market/indices returns current level and % change for indices and major tickers.
Used by Dashboard top bar. Cached to avoid Finviz rate limits (429).
"""
import asyncio
import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.finviz_service import FinvizService

logger = logging.getLogger(__name__)
router = APIRouter()
finviz = FinvizService()

# In-memory cache to reduce Finviz API calls (Dashboard polls every 5s)
_INDICES_CACHE: Dict[str, Any] = {}
_INDICES_CACHE_TTL_SEC = 60  # Serve cached result for 60s before refetch
_DELAY_BETWEEN_REQUESTS_SEC = 0.4  # Space out requests to avoid 429

# Map display id -> ticker for quote fetch (matches Dashboard TickerStrip indexMap)
INDEX_SYMBOLS = [
    {"id": "SPX", "ticker": "SPY"},
    {"id": "NDAQ", "ticker": "QQQ"},
    {"id": "DOW", "ticker": "DIA"},
    {"id": "SPY", "ticker": "SPY"},
    {"id": "QQQ", "ticker": "QQQ"},
    {"id": "DIA", "ticker": "DIA"},
    {"id": "AAPL", "ticker": "AAPL"},
    {"id": "MSFT", "ticker": "MSFT"},
    {"id": "TSLA", "ticker": "TSLA"},
    {"id": "AMZN", "ticker": "AMZN"},
    {"id": "NVDA", "ticker": "NVDA"},
    {"id": "META", "ticker": "META"},
    {"id": "GOOGL", "ticker": "GOOGL"},
    {"id": "BTC", "ticker": "BTC"},
    {"id": "ETH", "ticker": "ETH"},
    {"id": "VIX", "ticker": "VIX"},
]


def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _get_cached_indices() -> List[Dict[str, Any]] | None:
    """Return cached indices list if still valid."""
    cached = _INDICES_CACHE.get("result")
    ts = _INDICES_CACHE.get("ts")
    if cached is not None and ts is not None and (time.monotonic() - ts) < _INDICES_CACHE_TTL_SEC:
        return cached
    return None


def _set_cached_indices(result: List[Dict[str, Any]]) -> None:
    _INDICES_CACHE["result"] = result
    _INDICES_CACHE["ts"] = time.monotonic()


@router.get("/indices")
async def get_indices() -> Dict[str, Any]:
    """
    Return current index levels and % change (from previous close).
    Cached for 60s to avoid Finviz rate limits. Requests are spaced when refilling cache.
    """
    cached = _get_cached_indices()
    if cached is not None:
        return {"indices": cached}

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
            else:
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
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                logger.warning("Finviz rate limited; returning partial cache and backing off")
                _set_cached_indices(result)  # cache partial or empty so we don't retry for TTL
                return {"indices": result}
            logger.warning("Indices fetch %s: %s", item["ticker"], e)
            result.append({"id": item["id"], "value": None, "change": None})

        await asyncio.sleep(_DELAY_BETWEEN_REQUESTS_SEC)

    _set_cached_indices(result)
    return {"indices": result}


@router.get("/order-book")
async def get_order_book(symbol: str = "SPY"):
    """TODO: Implement real order book from market data provider.
    Returns L2 order book for TradeExecution page."""
    return {"symbol": symbol, "bids": [], "asks": [], "status": "stub"}


@router.get("/price-ladder")
async def get_price_ladder(symbol: str = "SPY"):
    """TODO: Implement real price ladder from market data provider.
    Returns price ladder for TradeExecution page."""
    return {"symbol": symbol, "levels": [], "status": "stub"}
