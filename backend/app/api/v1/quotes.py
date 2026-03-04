"""Quote/chart data API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query, Path

logger = logging.getLogger(__name__)
from typing import Optional, List, Dict, Any
from app.services.finviz_service import FinvizService

router = APIRouter()
finviz_service = FinvizService()


def _date_to_yyyy_mm_dd(t: Any) -> Optional[str]:
    """Normalize date string to yyyy-mm-dd (lightweight-charts / frontend expect this)."""
    if t is None:
        return None
    s = str(t).strip()
    if not s:
        return None
    # Already yyyy-mm-dd
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    # mm/dd/yyyy
    parts = s.split("/")
    if len(parts) == 3:
        m, d, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
        if len(y) == 4:
            return f"{y}-{m}-{d}"
    # mm-dd-yyyy
    parts = s.split("-")
    if len(parts) == 3 and len(parts[2]) == 4:
        m, d, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
        return f"{y}-{m}-{d}"
    return s[:10]


def _normalize_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert Finviz CSV row to chart format: time, open, high, low, close, volume."""
    close_key = next(
        (k for k in ("Close", "close", "C", "Adj Close") if k in row),
        list(row.keys())[-2] if len(row) > 1 else None,
    )
    date_key = next(
        (k for k in ("Date", "date", "time", "Time") if k in row),
        list(row.keys())[0] if row else None,
    )
    open_key = next((k for k in ("Open", "open", "O") if k in row), None)
    high_key = next((k for k in ("High", "high", "H") if k in row), None)
    low_key = next((k for k in ("Low", "low", "L") if k in row), None)
    vol_key = next((k for k in ("Volume", "volume", "V") if k in row), None)
    if not close_key or not date_key:
        return None
    try:
        t = row.get(date_key)
        if t is None:
            return None
        time_val = _date_to_yyyy_mm_dd(t)
        o = float(row[open_key]) if open_key and row.get(open_key) else None
        h = float(row[high_key]) if high_key and row.get(high_key) else None
        l = float(row[low_key]) if low_key and row.get(low_key) else None
        c = float(row[close_key])
        v = int(float(row[vol_key])) if vol_key and row.get(vol_key) else 0
        if c is None:
            return None
        return {
            "time": time_val,
            "open": o if o is not None else c,
            "high": h if h is not None else c,
            "low": l if l is not None else c,
            "close": c,
            "volume": v,
        }
    except (TypeError, ValueError):
        return None


@router.get("/{ticker}/candles")
async def get_candles(
    ticker: str = Path(..., description="Stock ticker symbol"),
    timeframe: Optional[str] = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1D, 1W"),
):
    """
    Get OHLCV candles for the Dashboard Price Action chart.
    Returns { candles: [ { time, open, high, low, close, volume }, ... ] }.
    """
    p_map = {"1m": "i1", "5m": "i5", "15m": "i15", "1h": "h", "4h": "h", "1D": "d", "1W": "w"}
    r_map = {"1m": "d1", "5m": "d1", "15m": "d5", "1h": "d5", "4h": "m1", "1D": "m3", "1W": "y1"}
    p = p_map.get(timeframe, "h")
    r = r_map.get(timeframe, "d5")
    try:
        quotes = await finviz_service.get_quote_data(ticker=ticker, timeframe=p, duration=r)
        if not quotes or not isinstance(quotes, list):
            return {"candles": [], "bars": []}
        normalized = []
        for row in quotes:
            n = _normalize_row(row)
            if n:
                normalized.append(n)
        return {"candles": normalized, "bars": normalized}
    except Exception as e:
        logger.error("Candle fetch failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail="Failed to fetch candle data")


@router.get("/{ticker}/book")
async def get_order_book(
    ticker: str = Path(..., description="Stock ticker symbol"),
) -> Dict[str, Any]:
    """
    Order book stub for Dashboard. Returns empty bids/asks when no live book is available.
    """
    return {
        "symbol": ticker,
        "bids": [],
        "asks": [],
        "timestamp": None,
    }


@router.get("/{ticker}", response_model=List[Dict])
async def get_quote_data(
    ticker: str = Path(..., description="Stock ticker symbol (e.g., MSFT)"),
    p: Optional[str] = Query(
        None,
        description="Timeframe/unit: i1, i3, i5, i15, i30, h, d, w, m (default: from config)"
    ),
    r: Optional[str] = Query(
        None,
        description="Duration/range: d1, d5, m1, m3, m6, ytd, y1, y2, y5, max (optional)"
    )
):
    """
    Get quote/chart data for a specific ticker.
    
    Returns historical price data for the specified ticker.
    
    **Timeframe options (p parameter):**
    - `i1`, `i3`, `i5`, `i15`, `i30` - Intraday intervals (1min, 3min, 5min, 15min, 30min)
    - `h` - Hourly
    - `d` - Daily
    - `w` - Weekly
    - `m` - Monthly
    
    **Duration options (r parameter):**
    - `d1` - 1 day
    - `d5` - 5 days
    - `m1` - 1 month
    - `m3` - 3 months
    - `m6` - 6 months
    - `ytd` - Year to date
    - `y1` - 1 year
    - `y2` - 2 years
    - `y5` - 5 years
    - `max` - Maximum available data
    """
    try:
        quotes = await finviz_service.get_quote_data(
            ticker=ticker,
            timeframe=p,
            duration=r
        )
        return quotes
    except Exception as e:
        logger.error("Quote data fetch failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail="Failed to fetch quote data")

