"""Stock screener API endpoints. Tracked symbols from Market Data Agent via symbol_universe."""
import logging

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
from typing import Optional, List, Dict
from app.services.finviz_service import FinvizService
from app.modules.symbol_universe import get_tracked_symbols, get_symbol_metadata

router = APIRouter()
finviz_service = FinvizService()


@router.get("/tracked")
async def get_tracked():
    """
    Return symbols tracked by the Market Data Agent (symbol_universe).
    Updated when Market Data Agent runs (Finviz scan). Use this as the client list.
    """
    symbols = get_tracked_symbols()
    metadata = {s: get_symbol_metadata(s) for s in symbols}
    store = (
        __import__(
            "app.services.database", fromlist=["db_service"]
        ).db_service.get_config("symbol_universe")
        or {}
    )
    return {
        "symbols": symbols,
        "source": store.get("source"),
        "metadata": metadata,
        "count": len(symbols),
    }


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
    """
    try:
        stocks = await finviz_service.get_stock_list(
            filters=filters, version=version, filter_type=filter_type, columns=columns
        )
        return stocks
    except Exception as e:
        logger.error("Stock list fetch failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch stock list")
