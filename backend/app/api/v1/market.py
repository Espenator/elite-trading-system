"""
Market indices snapshot — real data from Finviz quote API with Alpaca fallback.

GET /api/v1/market/indices returns current level and % change for
indices and major tickers.  Used by Dashboard top bar.
Cached to avoid Finviz rate limits (429).

FIX (Mar 10 2026):
  - Added Alpaca Market Data API as fallback when Finviz is unavailable.
  - Alpaca snapshots work 24/7 and return real prices at all times.
  - Response always includes: id, price, value, last, change, changePct
    so frontend TickerStrip can read any of these field names.
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

_finviz_available = bool(settings.FINVIZ_API_KEY)

_INDICES_CACHE: Dict[str, Any] = {}
_INDICES_CACHE_TTL_SEC = 30

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

_FINVIZ_SEMAPHORE = asyncio.Semaphore(4)
_DELAY_BETWEEN_REQUESTS_SEC = 0.5


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
    """Build index entry with ALL field names frontend may read.

    Frontend TickerStrip and Layout.jsx read:
      price, value, last, change, changePct
    All are populated here so Layout.jsx needs no fallback chains.
    """
    price_val = round(close, 2) if close else None
    change_val = round(change, 2) if change is not None else None
    return {
        "id": id_,
        "value": f"{close:.2f}" if close else None,
        "price": price_val,
        "last": price_val,
        "last_price": price_val,
        "change": change_val,
        "changePct": change_val,
        "change_pct": change_val,
        "source": source,
    }


def _get_cached_indices() -> List[Dict[str, Any]] | None:
    cached = _INDICES_CACHE.get("result")
    ts = _INDICES_CACHE.get("ts")
    if cached is not None and ts is not None and (time.monotonic() - ts) < _INDICES_CACHE_TTL_SEC:
        return cached
    return None


def _set_cached_indices(result: List[Dict[str, Any]]) -> None:
    _INDICES_CACHE["result"] = result
    _INDICES_CACHE["ts"] = time.monotonic()


async def _alpaca_snapshot_indices() -> List[Dict[str, Any]]:
    """Fetch index/ticker data from Alpaca snapshots as fallback.
    Works 24/7 regardless of market hours.
    """
    try:
        from app.services.alpaca_service import alpaca_service
        if not alpaca_service._is_configured():
            return []

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


@router.get("", summary="Market snapshot")
@router.get("/", summary="Market snapshot (trailing slash)")
async def get_market_root() -> Dict[str, Any]:
    """Return market snapshot used by Signal Intelligence and Market Regime pages."""
    cached = _get_cached_indices()
    if cached is not None:
        return {"indices": cached, "marketIndices": cached}

    result: List[Dict[str, Any]] = []

    if _finviz_available:
        for item in INDEX_SYMBOLS[:4]:
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

    if not result or all(r.get("price") is None for r in result):
        alpaca_result = await _alpaca_snapshot_indices()
        if alpaca_result:
            result = alpaca_result

    _set_cached_indices(result)
    return {"indices": result, "marketIndices": result}


async def _fetch_one_ticker(ticker: str) -> Dict[str, Any]:
    async with _FINVIZ_SEMAPHORE:
        quotes = await finviz.get_quote_data(ticker=ticker, timeframe="d", duration="d5")
        return {"ticker": ticker, "quotes": quotes}


@router.get("/indices")
async def get_indices() -> Dict[str, Any]:
    """Return current index levels and % change. Cached 30s."""
    cached = _get_cached_indices()
    if cached is not None:
        return {"indices": cached}

    result: List[Dict[str, Any]] = []

    if _finviz_available:
        unique_tickers = list({item["ticker"] for item in INDEX_SYMBOLS})
        tasks = [_fetch_one_ticker(t) for t in unique_tickers]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

        ticker_data: Dict[str, Any] = {}
        for res in fetched:
            if isinstance(res, Exception):
                logger.warning("Indices fetch error: %s", res)
                continue
            ticker_data[res["ticker"]] = res["quotes"]

        for item in INDEX_SYMBOLS:
            quotes = ticker_data.get(item["ticker"])
            try:
                if not quotes or not isinstance(quotes, list):
                    result.append(_make_index_entry(item["id"], None, None))
                else:
                    row = quotes[-1] if quotes else {}
                    prev = quotes[-2] if len(quotes) >= 2 else {}
                    close_key = next(
                        (k for k in ("Close", "close", "C", "Adj Close") if k in row), None,
                    )
                    if not close_key:
                        close_key = list(row.keys())[-2] if len(row) > 1 else None
                    close = _parse_float(row.get(close_key))
                    prev_close = _parse_float(prev.get(close_key)) if prev else close
                    change = ((close - prev_close) / prev_close) * 100 if prev_close and close else None
                    result.append(_make_index_entry(item["id"], close, change))
            except Exception as e:
                logger.warning("Indices parse %s: %s", item["ticker"], e)
                result.append(_make_index_entry(item["id"], None, None))

    if not result or all(r.get("price") is None for r in result):
        alpaca_result = await _alpaca_snapshot_indices()
        if alpaca_result:
            result = alpaca_result

    _set_cached_indices(result)
    return {"indices": result}


@router.get("/order-book")
async def get_order_book(symbol: str = "SPY"):
    """L2 order book stub — implement with real market data provider."""
    return {"symbol": symbol, "bids": [], "asks": [], "status": "stub"}


@router.get("/price-ladder")
async def get_price_ladder(symbol: str = "SPY"):
    """Price ladder stub — implement with real market data provider."""
    return {"symbol": symbol, "levels": [], "status": "stub"}
