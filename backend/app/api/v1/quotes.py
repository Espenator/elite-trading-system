"""Quote/chart data API endpoints."""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List, Dict
from app.services.finviz_service import FinvizService

router = APIRouter()
finviz_service = FinvizService()


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
        raise HTTPException(status_code=500, detail=str(e))

