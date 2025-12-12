# app/api/v1/stocks.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.stock import (
    StockRead,
    ScrapeRequest,
    ScrapeResponse,
    StockListResponse,
)
from app.services import stock_service

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
def scrape_stocks(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
    max_pages: int | None = Query(None, description="Limit number of pages to scrape"),
):
    """
    Scrape stock data from finviz.com with specified filters.
    
    Default filters: cap_midover,sh_avgvol_o500,sh_price_o10
    - cap_midover: Market Cap Mid and over ($2bln+)
    - sh_avgvol_o500: Average Volume over 500K
    - sh_price_o10: Price over $10
    """
    filters = request.filters or "cap_midover,sh_avgvol_o500,sh_price_o10"
    return stock_service.scrape_and_save(db, filters, max_pages)


@router.get("/", response_model=StockListResponse)
def list_stocks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    ticker: str | None = Query(None, description="Filter by ticker (partial match)"),
    sector: str | None = Query(None, description="Filter by sector"),
    country: str | None = Query(None, description="Filter by country"),
    db: Session = Depends(get_db),
):
    """Get paginated list of stocks from database"""
    stocks, total = stock_service.get_stocks(
        db, page, per_page, ticker, sector, country
    )
    return StockListResponse(
        total=total,
        page=page,
        per_page=per_page,
        stocks=stocks,
    )


@router.get("/ticker/{ticker}", response_model=StockRead)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    """Get a single stock by ticker symbol"""
    stock = stock_service.get_stock_by_ticker(db, ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return stock


@router.get("/sectors", response_model=list[str])
def get_sectors(db: Session = Depends(get_db)):
    """Get list of unique sectors"""
    return stock_service.get_unique_sectors(db)


@router.get("/countries", response_model=list[str])
def get_countries(db: Session = Depends(get_db)):
    """Get list of unique countries"""
    return stock_service.get_unique_countries(db)


@router.delete("/", response_model=dict)
def delete_all_stocks(db: Session = Depends(get_db)):
    """Delete all stocks from database"""
    count = stock_service.delete_all_stocks(db)
    return {"message": f"Deleted {count} stocks", "count": count}


