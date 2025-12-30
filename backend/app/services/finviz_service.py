"""Finviz API service for fetching stock screener and quote data."""
import httpx
import csv
import io
import logging

from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class FinvizService:
    """Service for interacting with Finviz Elite API."""
    
    def __init__(self):
        self.base_url = settings.FINVIZ_BASE_URL
        self.api_key = settings.FINVIZ_API_KEY
        
        if not self.api_key:
            raise ValueError("FINVIZ_API_KEY is not set in environment variables")
    
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
        
        # Log request parameters
        logger.info("Fetching stock list from Finviz screener")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Parse CSV response
                csv_content = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                # Convert to list of dictionaries
                stocks = [row for row in csv_reader]
                
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

        # Log request parameters
        logger.info(f"Fetching quote data for {ticker}")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {params}")
        
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

