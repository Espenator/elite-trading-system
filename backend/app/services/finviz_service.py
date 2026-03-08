"""Finviz API service for fetching stock screener and quote data."""
import asyncio
import httpx
import csv
import io
import logging
import re
import time

from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)


def _parse_market_cap_num(value: Any) -> Optional[float]:
    """Parse Market Cap string to numeric (dollars). Handles '47224.21' (millions), '35.73B', '1.2M'."""
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s or s in ("-", "—", "N/A"):
        return None
    # Strip non-numeric prefix/suffix but keep B/M/K
    num_str = re.sub(r"[^0-9.-]", "", s)
    try:
        num = float(num_str)
    except ValueError:
        return None
    if num <= 0:
        return None
    if "B" in s or s.endswith("B"):
        return num * 1e9
    if "M" in s or s.endswith("M"):
        return num * 1e6
    if "K" in s or s.endswith("K"):
        return num * 1e3
    # Raw number: assume millions (e.g. Finviz export "47224.21" = 47.2B)
    return num * 1e6


def _market_cap_category(cap_num: Optional[float]) -> Optional[str]:
    """small < 2B, mid 2B–10B, large > 10B."""
    if cap_num is None or cap_num <= 0:
        return None
    if cap_num < 2e9:
        return "small"
    if cap_num <= 10e9:
        return "mid"
    return "large"


def _market_cap_display(cap_num: Optional[float]) -> Optional[str]:
    """Format for display, e.g. 47.22B, 1.20M."""
    if cap_num is None or cap_num <= 0:
        return None
    if cap_num >= 1e9:
        return f"{cap_num / 1e9:.2f}B"
    if cap_num >= 1e6:
        return f"{cap_num / 1e6:.2f}M"
    if cap_num >= 1e3:
        return f"{cap_num / 1e3:.2f}K"
    return f"{cap_num:.0f}"


def _normalize_exchange(value: Any) -> Optional[str]:
    """Map exchange string to frontend filter key: nasdaq, nyse, amex."""
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if "NASDAQ" in s:
        return "nasdaq"
    if "NYSE" in s:
        return "nyse"
    if "AMEX" in s or "AMERICAN" in s:
        return "amex"
    return None


def _enrich_stock_row(
    row: Dict[str, str],
    exchange_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Add market_cap_category, market_cap_display, and exchange for frontend filters."""
    out = dict(row)
    raw_cap = row.get("Market Cap") or row.get("market_cap") or row.get("Market Cap.")
    cap_num = _parse_market_cap_num(raw_cap)
    out["market_cap_category"] = _market_cap_category(cap_num)
    out["market_cap_display"] = _market_cap_display(cap_num)
    raw_exchange = row.get("Exchange") or row.get("exchange")
    exchange = _normalize_exchange(raw_exchange)
    if exchange is None and exchange_map is not None:
        ticker = (row.get("Ticker") or row.get("ticker") or "").strip().upper()
        exchange = exchange_map.get(ticker) if ticker else None
    out["exchange"] = exchange
    return out


MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds

FINVIZ_PRESETS = {
    "breakout": "ta_highlow52w_nh,sh_avgvol_o500,ta_sma20_pa,ta_sma200_pa",
    "momentum": "ta_sma20_pa,ta_sma200_pa,sh_relvol_o1.5",
    "swing_pullback": "ta_pattern_channelup,ta_sma20_cross20above,ta_sma200_pa",
    "pas_gate": "ta_pattern_channelup,ta_sma20_pa,ta_sma200_pa",
}


async def _fetch_with_retry(url: str, params: dict, timeout: float = 30.0) -> httpx.Response:
    """Fetch with exponential backoff retry."""
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                return r
        except (httpx.HTTPStatusError, httpx.ConnectError) as e:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Finviz retry %d/%d after %.1fs: %s", attempt + 1, MAX_RETRIES, delay, e)
            await asyncio.sleep(delay)


class FinvizService:
    """Service for interacting with Finviz Elite API."""
    
    def __init__(self):
        self.base_url = settings.FINVIZ_BASE_URL
        self.api_key = settings.FINVIZ_API_KEY
    
    def _validate_api_key(self):
        """Validate that API key is set before making API calls."""
        if not self.api_key:
            raise ValueError("FINVIZ_API_KEY is not set in environment variables. Please set it in your .env file.")
    
    async def get_stock_list(
        self,
        filters: Optional[str] = None,
        version: Optional[str] = None,
        filter_type: Optional[str] = None,
        columns: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch stock list from Finviz screener.
        
        Args:
            filters: Comma-separated filter parameters (e.g., "cap_midover,sh_avgvol_o500")
            version: Screener version (default: from config)
            filter_type: Filter type (default: from config)
            columns: Optional comma-separated column names to export
        
        Returns:
            List of dictionaries containing stock data
        """
        # Validate API key before making request
        self._validate_api_key()
        
        # Use provided filters or fall back to config
        filters = filters or settings.FINVIZ_SCREENER_FILTERS
        version = version or settings.FINVIZ_SCREENER_VERSION
        filter_type = filter_type or settings.FINVIZ_SCREENER_FILTER_TYPE
        
        # Build URL
        url = f"{self.base_url}/export.ashx"
        params = {
            "v": version,
            "f": filters,
            "ft": filter_type,
            "auth": self.api_key
        }
        
        # Add columns if specified
        if columns:
            params["c"] = columns
        
        # Log request parameters (redact API key)
        logger.info("Fetching stock list from Finviz screener")
        logger.info("URL: %s", url)
        logger.info("Params: v=%s, f=%s, ft=%s, auth=***REDACTED***", version, filters, filter_type)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Parse CSV response — validate it's actually CSV, not an HTML error page
                csv_content = response.text
                if csv_content.strip().startswith("<!") or csv_content.strip().startswith("<html"):
                    logger.error("Finviz returned HTML instead of CSV (likely auth or parameter error). First 200 chars: %s", csv_content[:200])
                    raise Exception("Finviz returned HTML error page instead of CSV data. Check FINVIZ_API_KEY and screener parameters.")
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                rows = [dict(row) for row in csv_reader]
                logger.info("Finviz screener returned %d rows", len(rows))
                # Exchange: Finviz CSV often has no Exchange column; resolve from Alpaca when available
                exchange_map: Dict[str, str] = {}
                try:
                    from app.services.alpaca_service import alpaca_service
                    exchange_map = await alpaca_service.get_asset_exchange_map()
                except Exception as e:
                    logger.debug("Exchange lookup via Alpaca skipped: %s", e)
                # Enrich each row (market cap category + exchange)
                stocks = [_enrich_stock_row(r, exchange_map) for r in rows]

                # Publish screener results to MessageBus for downstream consumers
                try:
                    bus = get_message_bus()
                    if bus._running:
                        await bus.publish("perception.finviz.screener", {
                            "type": "finviz_screener_results",
                            "results": stocks,
                            "source": "finviz_service",
                            "timestamp": time.time(),
                        })
                except Exception:
                    pass

                return stocks
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Finviz API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Error fetching stock list: {str(e)}")
    
    async def get_quote_data(
        self,
        ticker: str,
        timeframe: Optional[str] = None,
        duration: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch quote/chart data for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., "MSFT")
            timeframe: Timeframe - i1, i3, i5, i15, i30, h, d, w, m (default: from config)
            duration: Duration/range - d1, d5, m1, m3, m6, ytd, y1, y2, y5, max (optional)
        
        Returns:
            List of dictionaries containing quote/chart data
        """
        # Validate API key before making request
        self._validate_api_key()
        
        timeframe = timeframe or settings.FINVIZ_QUOTE_TIMEFRAME
        
        # Build URL
        url = f"{self.base_url}/quote_export.ashx"
        params = {
            "t": ticker.upper(),
            "p": timeframe,
            "auth": self.api_key
        }
        
        # Add duration/range if specified
        if duration:
            params["r"] = duration

        # Log request parameters (redact API key)
        logger.info("Fetching quote data for %s", ticker)
        logger.info("URL: %s", url)
        logger.info("Params: t=%s, p=%s, auth=***REDACTED***", ticker.upper(), timeframe)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Parse CSV response
                csv_content = response.text                
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                # Convert to list of dictionaries
                quotes = [row for row in csv_reader]
                
                return quotes
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Finviz API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Error fetching quote data: {str(e)}")

    async def get_intraday_screen(self, timeframe: str = "i5", filters: str = None) -> List[Dict]:
        """Run Finviz Elite intraday screener.

        Args:
            timeframe: i1, i3, i5, i15, i30, h (Elite plan required for intraday)
            filters: Comma-separated Finviz filter string
        """
        self._validate_api_key()
        filters = filters or settings.FINVIZ_SCREENER_FILTERS
        url = f"{self.base_url}/export.ashx"
        params = {
            "v": settings.FINVIZ_SCREENER_VERSION,
            "f": filters,
            "ft": settings.FINVIZ_SCREENER_FILTER_TYPE,
            "p": timeframe,
            "auth": self.api_key,
        }
        r = await _fetch_with_retry(url, params)
        csv_content = r.text
        if csv_content.strip().startswith("<!") or csv_content.strip().startswith("<html"):
            raise Exception("Finviz returned HTML error page instead of CSV data.")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        return [dict(row) for row in csv_reader]

    async def get_screener(self, filters: str = None) -> List[Dict]:
        """Alias for get_stock_list with retry support."""
        return await self.get_stock_list(filters=filters)

    async def run_all_presets(self) -> Dict[str, List[Dict]]:
        """Run all 4 filter presets in parallel. Returns {preset_name: [results]}."""
        tasks = {
            name: self.get_stock_list(filters=filters)
            for name, filters in FINVIZ_PRESETS.items()
        }
        results = {}
        for name, coro in tasks.items():
            try:
                results[name] = await coro
            except Exception as e:
                logger.warning("Finviz preset %s failed: %s", name, e)
                results[name] = []
        return results

