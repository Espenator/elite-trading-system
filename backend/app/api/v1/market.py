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
_INDICES_CACHE_TTL_SEC = 120  # Serve cached result for 120s before refetch

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
                result.append({
                    "id": item["id"],
                    "value": f"{close:.2f}" if close else None,
                    "change": round(change, 2) if change is not None else None,
                    "source": "alpaca",
                })
            else:
                result.append({"id": item["id"], "value": None, "change": None})
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
                    result.append({"id": item["id"], "value": None, "change": None})
                else:
                    row = quotes[-1] if quotes else {}
                    prev = quotes[-2] if len(quotes) >= 2 else {}
                    close_key = next((k for k in ("Close", "close", "C", "Adj Close") if k in row), None)
                    if not close_key and row:
                        close_key = list(row.keys())[-2] if len(row) > 1 else None
                    close = _parse_float(row.get(close_key))
                    prev_close = _parse_float(prev.get(close_key)) if prev else close
                    change = ((close - prev_close) / prev_close) * 100 if prev_close and close else None
                    result.append({
                        "id": item["id"],
                        "value": f"{close:.2f}" if close else None,
                        "change": round(change, 2) if change is not None else None,
                    })
            except Exception as e:
                logger.debug("Market root fetch %s: %s", item["ticker"], e)
                result.append({"id": item["id"], "value": None, "change": None})
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
                logger.warning("Indices parse %s: %s", item["ticker"], e)
                result.append({"id": item["id"], "value": None, "change": None})

    # If Finviz produced no data (or no API key), use Alpaca fallback
    if not result or all(r.get("value") is None for r in result):
        alpaca_result = await _alpaca_snapshot_indices()
        if alpaca_result:
            result = alpaca_result

    _set_cached_indices(result)
    return {"indices": result}


@router.get("/order-book")
async def get_order_book(symbol: str = "SPY"):
    """Return L2-style order book derived from Alpaca NBBO snapshot.

    Uses the latest bid/ask from Alpaca's SIP feed to construct a
    representative five-level order book.  Without an exchange-level L2
    subscription, levels are extrapolated from the NBBO spread.
    """
    try:
        from app.services.alpaca_service import alpaca_service
        if not alpaca_service._is_configured():
            return {"symbol": symbol, "bids": [], "asks": [], "status": "no_alpaca_key"}

        snaps = await alpaca_service.get_snapshots([symbol.upper()])
        if not snaps:
            return {"symbol": symbol, "bids": [], "asks": [], "status": "no_data"}

        snap = snaps.get(symbol.upper(), {})
        q = snap.get("latestQuote") or {}
        bid_price = _parse_float(q.get("bp"))
        ask_price = _parse_float(q.get("ap"))
        bid_size = int(q.get("bs") or 0)
        ask_size = int(q.get("as") or 0)

        if not bid_price or not ask_price:
            return {"symbol": symbol, "bids": [], "asks": [], "status": "no_quote"}

        spread = ask_price - bid_price
        tick = max(0.01, round(spread / 4, 2))

        bids = [
            {"price": round(bid_price - tick * i, 2), "size": max(1, bid_size // (i + 1))}
            for i in range(5)
        ]
        asks = [
            {"price": round(ask_price + tick * i, 2), "size": max(1, ask_size // (i + 1))}
            for i in range(5)
        ]

        return {
            "symbol": symbol.upper(),
            "bids": bids,
            "asks": asks,
            "mid": round((bid_price + ask_price) / 2, 4),
            "spread": round(spread, 4),
            "status": "live",
            "source": "alpaca_nbbo",
        }
    except Exception as exc:
        logger.warning("Order book fetch error for %s: %s", symbol, exc)
        return {"symbol": symbol, "bids": [], "asks": [], "status": "error"}


@router.get("/price-ladder")
async def get_price_ladder(symbol: str = "SPY"):
    """Return price ladder from Alpaca snapshot data.

    Constructs a visual price ladder around the current price using the
    daily trading range and NBBO spread as tick-size reference.
    """
    try:
        from app.services.alpaca_service import alpaca_service
        if not alpaca_service._is_configured():
            return {"symbol": symbol, "levels": [], "status": "no_alpaca_key"}

        snaps = await alpaca_service.get_snapshots([symbol.upper()])
        if not snaps:
            return {"symbol": symbol, "levels": [], "status": "no_data"}

        snap = snaps.get(symbol.upper(), {})
        latest_trade = snap.get("latestTrade") or {}
        latest_quote = snap.get("latestQuote") or {}
        daily_bar = snap.get("dailyBar") or {}
        prev_bar = snap.get("prevDailyBar") or {}

        current_price = _parse_float(latest_trade.get("p") or daily_bar.get("c"))
        bid = _parse_float(latest_quote.get("bp"))
        ask = _parse_float(latest_quote.get("ap"))
        day_high = _parse_float(daily_bar.get("h"))
        day_low = _parse_float(daily_bar.get("l"))
        prev_close = _parse_float(prev_bar.get("c"))

        if not current_price:
            return {"symbol": symbol, "levels": [], "status": "no_data"}

        spread = ask - bid if ask > bid else 0.0
        # Tick size: derive from spread; cap between $0.01 and $2.00 to keep the
        # ladder visually useful across penny stocks and high-priced symbols alike.
        if spread:
            tick = min(2.0, max(0.01, round(spread / 3, 2)))
        else:
            tick = min(2.0, max(0.01, round(current_price * 0.0005, 2)))

        tol = tick * 0.5  # tolerance for key-level proximity markers

        levels = []
        for i in range(-5, 6):
            price = round(current_price + tick * i, 2)
            level_type = "current" if i == 0 else ("above" if i > 0 else "below")
            levels.append({
                "price": price,
                "type": level_type,
                "is_bid": bid > 0 and abs(price - bid) <= tol,
                "is_ask": ask > 0 and abs(price - ask) <= tol,
                "is_day_high": day_high > 0 and abs(price - day_high) <= tol,
                "is_day_low": day_low > 0 and abs(price - day_low) <= tol,
                "is_prev_close": prev_close > 0 and abs(price - prev_close) <= tol,
            })

        return {
            "symbol": symbol.upper(),
            "levels": levels,
            "current_price": current_price,
            "bid": bid,
            "ask": ask,
            "day_high": day_high,
            "day_low": day_low,
            "prev_close": prev_close,
            "status": "live",
            "source": "alpaca_snapshot",
        }
    except Exception as exc:
        logger.warning("Price ladder fetch error for %s: %s", symbol, exc)
        return {"symbol": symbol, "levels": [], "status": "error"}


@router.get("/regime")
async def get_market_regime():
    """Return current market regime at a stable, non-openclaw URL.

    Delegates to the OpenClaw bridge for the actual regime data.
    This endpoint satisfies the frontend migration away from
    /api/v1/openclaw/regime (see openclaw/__init__.py TODO).

    Response: {state: GREEN|YELLOW|RED, vix, hmm_confidence, hurst, macro_context}
    """
    try:
        from app.services.openclaw_bridge_service import openclaw_bridge
        return await openclaw_bridge.get_regime()
    except Exception as exc:
        logger.warning("Market regime fetch error: %s", exc)
        return {"state": "UNKNOWN", "details": None, "readme": None}
