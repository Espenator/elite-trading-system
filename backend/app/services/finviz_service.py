"""Finviz API service for fetching stock screener and quote data."""
import httpx
import csv
import io
import logging
import re

from typing import List, Dict, Optional, Any
from app.core.config import settings

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
                
                # Parse CSV response
                csv_content = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                rows = [dict(row) for row in csv_reader]
                # Exchange: Finviz CSV often has no Exchange column; resolve from Alpaca when available
                exchange_map: Dict[str, str] = {}
                try:
                    from app.services.alpaca_service import alpaca_service
                    exchange_map = await alpaca_service.get_asset_exchange_map()
                except Exception as e:
                    logger.debug("Exchange lookup via Alpaca skipped: %s", e)
                # Enrich each row (market cap category + exchange)
                stocks = [_enrich_stock_row(r, exchange_map) for r in rows]
                
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

