"""
Market indices snapshot — real data from Finviz quote API with Alpaca fallback.

GET /api/v1/market/indices returns current level and % change for
indices and major tickers.  Used by Dashboard top bar.
Cached to avoid Finviz rate limits (429).

BUG FIX 4: Added Alpaca Market Data API as fallback when Finviz is unavailable.
Alpaca snapshots work 24/7 and return real prices at all times.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from app.services.finviz_service import FinvizService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
finviz = FinvizService()

# Whether Finviz is available (has API key)
_finviz_available = bool(settings.FINVIZ_API_KEY)

# In-memory cache to reduce Finviz API calls (Dashboard polls every 5s)
_INDICES_CACHE: Dict[str, Any] = {}
_INDICES_CACHE_TTL_SEC = 30  # Serve cached result for 30s before refetch (paid Finviz Elite)

# Map display id -> ticker for quote fetch (matches Dashboard TickerStrip indexMap)
INDEX_SYMBOLS = [
    {"id": "SPX",   "ticker": "SPY"},
    {"id": "NDAQ",  "ticker": "QQQ"},
    {"id": "DOW",   "ticker": "DIA"},
    {"id": "SPY",   "ticker": "SPY"},
    {"id": "QQQ",   "ticker": "QQQ"},
    {"id": "DIA",   "ticker": "DIA"},
    {"id": "AAPL",  "ticker": "AAPL"},
    {"id": "MSFT",  "ticker": "MSFT"},
    {"id": "TSLA",  "ticker": "TSLA"},
    {"id": "AMZN",  "ticker": "AMZN"},
    {"id": "NVDA",  "ticker": "NVDA"},
    {"id": "META",  "ticker": "META"},
    {"id": "GOOGL", "ticker": "GOOGL"},
    {"id": "BTC",   "ticker": "BTC"},
    {"id": "ETH",   "ticker": "ETH"},
    {"id": "VIX",   "ticker": "VIX"},
]

# Concurrency limit for Finviz requests (avoid 429 while still being fast)
_FINVIZ_SEMAPHORE = asyncio.Semaphore(4)
_DELAY_BETWEEN_REQUESTS_SEC = 0.5  # Rate limit padding between sequential requests


def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _make_index_entry(
    id_: str,
    close: float | None,
    change: float | None,
    source: str = "finviz",
) -> Dict[str, Any]:
    """Build a single index entry with all fields the frontend expects.

    Frontend TickerStrip reads: price, value, change, changePct, last.
    """
    return {
        "id": id_,
        "value": f"{close:.2f}" if close else None,
        "price": round(close, 2) if close else None,
        "last": round(close, 2) if close else None,
        "change": round(change, 2) if change is not None else None,
        "changePct": round(change, 2) if change is not None else None,
        "source": source,
    }


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


async def _alpaca_snapshot_indices() -> List[Dict[str, Any]]:
    """BUG FIX 4: Fetch index/ticker data from Alpaca snapshots as fallback.

    Uses Alpaca Market Data API which works 24/7, even outside market hours.
    Returns the same format as the Finviz-based indices.
    """
    try:
        from app.services.alpaca_service import alpaca_service
        if not alpaca_service._is_configured():
            return []

        # Only fetch equity tickers (Alpaca doesn't have BTC/ETH/VIX as stock snapshots)
        equity_tickers = [item["ticker"] for item in INDEX_SYMBOLS
                          if item["ticker"] not in ("BTC", "ETH", "VIX")]
        unique_tickers = list(set(equity_tickers))

        snapshots = await alpaca_service.get_snapshots(unique_tickers)
        if not snapshots:
            return []

        result: List[Dict[str, Any]] = []
        for item in INDEX_SYMBOLS:
            ticker = item["ticker"]
            snap = snapshots.get(ticker)
            if snap:
                daily = snap.get("dailyBar") or {}
                prev = snap.get("prevDailyBar") or {}
                latest = snap.get("latestTrade") or {}
                close = _parse_float(latest.get("p") or daily.get("c"))
                prev_close = _parse_float(prev.get("c"))
                change = (
                    ((close - prev_close) / prev_close) * 100
                    if prev_close and close else None
                )
                result.append(_make_index_entry(item["id"], close, change, "alpaca"))
            else:
                result.append(_make_index_entry(item["id"], None, None, "alpaca"))
        return result
    except Exception as e:
        logger.warning("Alpaca snapshot fallback failed: %s", e)
        return []


@router.get("", summary="Market snapshot (indices + stub for Signal Intelligence)")
@router.get("/", summary="Market snapshot with trailing slash")
async def get_market_root() -> Dict[str, Any]:
    """
    Return market snapshot. Signal Intelligence and Market Regime pages call GET /api/v1/market.
    Reuses the same indices cache as /market/indices for consistency.

    BUG FIX 4: Falls back to Alpaca snapshots when Finviz is unavailable.
    """
    cached = _get_cached_indices()
    if cached is not None:
        return {"indices": cached, "marketIndices": cached}

    result: List[Dict[str, Any]] = []

    # Try Finviz first (if API key is configured)
    if _finviz_available:
        for item in INDEX_SYMBOLS[:4]:  # SPY, QQQ, DIA, SPY only for root to keep fast
            try:
                quotes = await finviz.get_quote_data(ticker=item["ticker"], timeframe="d", duration="d5")
                if not quotes or not isinstance(quotes, list):
                    result.append(_make_index_entry(item["id"], None, None))
                else:
                    row = quotes[-1] if quotes else {}
                    prev = quotes[-2] if len(quotes) >= 2 else {}
                    close_key = next((k for k in ("Close", "close", "C", "Adj Close") if k in row), None)
                    if not close_key and row:
                        close_key = list(row.keys())[-2] if len(row) > 1 else None
                    close = _parse_float(row.get(close_key))
                    prev_close = _parse_float(prev.get(close_key)) if prev else close
                    change = ((close - prev_close) / prev_close) * 100 if prev_close and close else None
                    result.append(_make_index_entry(item["id"], close, change))
            except Exception as e:
                logger.debug("Market root fetch %s: %s", item["ticker"], e)
                result.append(_make_index_entry(item["id"], None, None))
            await asyncio.sleep(_DELAY_BETWEEN_REQUESTS_SEC)

    # If Finviz produced no data, use Alpaca fallback
    if not result or all(r.get("value") is None for r in result):
        alpaca_result = await _alpaca_snapshot_indices()
        if alpaca_result:
            result = alpaca_result

    _set_cached_indices(result)
    return {"indices": result, "marketIndices": result}
async def _fetch_one_ticker(ticker: str) -> Dict[str, Any]:
    """Fetch quote data for a single ticker with semaphore throttling."""
    async with _FINVIZ_SEMAPHORE:
        quotes = await finviz.get_quote_data(
            ticker=ticker, timeframe="d", duration="d5",
        )
        return {"ticker": ticker, "quotes": quotes}


@router.get("/indices")
async def get_indices() -> Dict[str, Any]:
    """
    Return current index levels and % change (from previous close).
    Cached for 120s to avoid Finviz rate limits.
    Uses parallel fetching with deduplication for speed.

    BUG FIX 4: Falls back to Alpaca snapshots when Finviz is unavailable.
    """
    cached = _get_cached_indices()
    if cached is not None:
        return {"indices": cached}

    result: List[Dict[str, Any]] = []

    # Try Finviz first (if API key is configured)
    if _finviz_available:
        # Deduplicate tickers so SPY/QQQ/DIA are only fetched once
        unique_tickers = list({item["ticker"] for item in INDEX_SYMBOLS})

        # Fetch all unique tickers in parallel (semaphore limits concurrency)
        tasks = [_fetch_one_ticker(t) for t in unique_tickers]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

        # Build ticker -> quotes lookup
        ticker_data: Dict[str, Any] = {}
        for res in fetched:
            if isinstance(res, Exception):
                logger.warning("Indices fetch error: %s", res)
                continue
            ticker_data[res["ticker"]] = res["quotes"]

        # Map results back to display items
        for item in INDEX_SYMBOLS:
            quotes = ticker_data.get(item["ticker"])
            try:
                if not quotes or not isinstance(quotes, list):
                    result.append(_make_index_entry(item["id"], None, None))
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
                    result.append(_make_index_entry(item["id"], close, change))
            except Exception as e:
                logger.warning("Indices parse %s: %s", item["ticker"], e)
                result.append(_make_index_entry(item["id"], None, None))

    # If Finviz produced no data (or no API key), use Alpaca fallback
    if not result or all(r.get("value") is None for r in result):
        alpaca_result = await _alpaca_snapshot_indices()
        if alpaca_result:
            result = alpaca_result

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
