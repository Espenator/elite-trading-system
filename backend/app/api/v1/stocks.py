"""Stock screener API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from app.services.finviz_service import FinvizService

router = APIRouter()
finviz_service = FinvizService()


@router.get("/list", response_model=List[Dict])
async def get_stock_list(
    filters: Optional[str] = Query(
        None,
        description="Comma-separated filter parameters (e.g., 'cap_midover,sh_avgvol_o500,sh_price_o10')"
    ),
    version: Optional[str] = Query(
        None,
        description="Screener version (default: from config)"
    ),
    filter_type: Optional[str] = Query(
        None,
        description="Filter type (default: from config)"
    ),
    columns: Optional[str] = Query(
        None,
        description="Optional comma-separated column names to export"
    )
):
    """
    Get stock list from Finviz screener.
    
    Returns a list of stocks matching the specified filters.
    """
    try:
        stocks = await finviz_service.get_stock_list(
            filters=filters,
            version=version,
            filter_type=filter_type,
            columns=columns
        )
        return stocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

