"""Stock screener API endpoints. Tracked symbols from Market Data Agent via symbol_universe.

Data sources (in priority order):
1. Finviz Elite API (requires FINVIZ_API_KEY)
2. Alpaca Market Data API (uses trading keys, works 24/7 including weekends)

If Finviz is unavailable (no API key), endpoints return Alpaca-sourced data
instead of crashing with a 500 error.
"""
import logging
import time

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
from typing import Optional, List, Dict
from app.core.config import settings

router = APIRouter()

# Whether Finviz is available (has API key)
_finviz_available = bool(settings.FINVIZ_API_KEY)

# Default symbols when symbol_universe is empty AND Finviz is unavailable.
# These are the most liquid US equities + ETFs — ensures the frontend always
# has something to display even before the Market Data Agent runs.
_DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "SPY", "QQQ", "IWM",
    "GLD", "BITI", "DIA", "AMD", "NFLX",
]


async def _alpaca_stock_list() -> List[Dict]:
    """BUG FIX 9: Fallback stock list from Alpaca snapshots when Finviz is unavailable.

    Fetches snapshot data for default symbols and returns a minimal stock list
    with current price info so the frontend Stock Screener page isn't empty.
    """
    try:
        from app.services.alpaca_service import alpaca_service
        if not alpaca_service._is_configured():
            return []

        snapshots = await alpaca_service.get_snapshots(_DEFAULT_SYMBOLS)
        if not snapshots:
            return []

        result = []
        for symbol in _DEFAULT_SYMBOLS:
            snap = snapshots.get(symbol)
            if not snap:
                continue
            daily = snap.get("dailyBar") or {}
            prev = snap.get("prevDailyBar") or {}
            latest = snap.get("latestTrade") or {}
            close = float(latest.get("p") or daily.get("c") or 0)
            prev_close = float(prev.get("c") or 0)
            change_pct = (
                round(((close - prev_close) / prev_close) * 100, 2)
                if prev_close and close else 0
            )
            volume = int(daily.get("v") or 0)
            result.append({
                "No.": len(result) + 1,
                "Ticker": symbol,
                "Company": symbol,
                "Sector": "",
                "Industry": "",
                "Country": "USA",
                "Market Cap": "",
                "Price": f"{close:.2f}" if close else "",
                "Change": f"{change_pct:.2f}%",
                "Volume": str(volume),
                "exchange": "nyse",
                "market_cap_category": None,
                "market_cap_display": None,
                "source": "alpaca",
            })
        return result
    except Exception as e:
        logger.warning("Alpaca stock list fallback failed: %s", e)
        return []


@router.get("/")
async def get_stocks_root():
    """Root endpoint — returns tracked symbols summary for frontend useApi('stocks').

    BUG FIX 10: When symbol_universe is empty (Finviz never ran), falls back to
    a default list of liquid symbols so the frontend always has data.
    """
    from app.modules.symbol_universe import get_tracked_symbols, get_symbol_metadata

    symbols = get_tracked_symbols()

    # If no symbols tracked yet (Finviz never ran), seed with defaults
    if not symbols:
        symbols = list(_DEFAULT_SYMBOLS)
        logger.info(
            "symbol_universe empty — returning %d default symbols",
            len(symbols),
        )

    metadata = {}
    for s in symbols:
        meta = get_symbol_metadata(s)
        if meta:
            metadata[s] = meta

    return {
        "symbols": symbols,
        "metadata": metadata,
        "count": len(symbols),
    }


@router.get("/tracked")
async def get_tracked():
    """
    Return symbols tracked by the Market Data Agent (symbol_universe).
    Updated when Market Data Agent runs (Finviz scan). Use this as the client list.

    Falls back to default symbols when symbol_universe is empty.
    """
    from app.modules.symbol_universe import get_tracked_symbols, get_symbol_metadata

    symbols = get_tracked_symbols()
    source = None

    try:
        store = (
            __import__(
                "app.services.database", fromlist=["db_service"]
            ).db_service.get_config("symbol_universe")
            or {}
        )
        source = store.get("source")
    except Exception:
        pass

    # If no symbols tracked yet, return defaults
    if not symbols:
        symbols = list(_DEFAULT_SYMBOLS)
        source = "default"

    metadata = {}
    for s in symbols:
        meta = get_symbol_metadata(s)
        if meta:
            metadata[s] = meta

    return {
        "symbols": symbols,
        "source": source,
        "metadata": metadata,
        "count": len(symbols),
    }


_stock_list_cache: Dict = {"data": None, "timestamp": 0}

@router.get("/list", response_model=List[Dict])
async def get_stock_list(
    filters: Optional[str] = Query(
        None,
        description="Comma-separated filter parameters (e.g., 'cap_midover,sh_avgvol_o500,sh_price_o10')",
    ),
    version: Optional[str] = Query(
        None, description="Screener version (default: from config)"
    ),
    filter_type: Optional[str] = Query(
        None, description="Filter type (default: from config)"
    ),
    columns: Optional[str] = Query(
        None, description="Optional comma-separated column names to export"
    ),
):
    """
    Get stock list from Finviz screener.
    Returns a list of stocks matching the specified filters.

    BUG FIX 9: When FINVIZ_API_KEY is not configured, falls back to Alpaca
    snapshot data for default symbols instead of crashing with a 500 error.

    Cached for 1 hour (3600s) — stock list rarely changes.
    """
    # Return cached result if fresh (1 hour TTL)
    if _stock_list_cache["data"] and time.time() - _stock_list_cache["timestamp"] < 3600:
        return _stock_list_cache["data"]

    # Try Finviz first (if API key is configured)
    if _finviz_available:
        try:
            from app.services.finviz_service import FinvizService
            finviz_service = FinvizService()
            stocks = await finviz_service.get_stock_list(
                filters=filters, version=version, filter_type=filter_type, columns=columns
            )
            _stock_list_cache["data"] = stocks
            _stock_list_cache["timestamp"] = time.time()
            return stocks
        except Exception as e:
            logger.warning("Finviz stock list failed, trying Alpaca fallback: %s", e)

    # Alpaca fallback (works 24/7 including weekends)
    alpaca_stocks = await _alpaca_stock_list()
    if alpaca_stocks:
        _stock_list_cache["data"] = alpaca_stocks
        _stock_list_cache["timestamp"] = time.time()
        return alpaca_stocks

    # Return empty list as last resort (never crash)
    return []
