# app/services/stock_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from app.db.models import Stock
from app.schemas.stock import StockCreate, ScrapeResponse
from app.services.finviz_scraper import FinvizScraper


def get_stocks(
    db: Session,
    page: int = 1,
    per_page: int = 50,
    ticker: str | None = None,
    sector: str | None = None,
    country: str | None = None,
) -> tuple[list[Stock], int]:
    """Get stocks from database with filtering and pagination"""
    query = db.query(Stock)
    
    if ticker:
        query = query.filter(Stock.ticker.ilike(f"%{ticker}%"))
    if sector:
        query = query.filter(Stock.sector.ilike(f"%{sector}%"))
    if country:
        query = query.filter(Stock.country.ilike(f"%{country}%"))
    
    total = query.count()
    
    stocks = (
        query
        .order_by(desc(Stock.updated_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    
    return stocks, total


def get_stock_by_ticker(db: Session, ticker: str) -> Stock | None:
    """Get a single stock by ticker"""
    return db.query(Stock).filter(Stock.ticker == ticker.upper()).first()


def create_or_update_stock(db: Session, stock_data: StockCreate) -> tuple[Stock, bool]:
    """Create or update a stock record. Returns (stock, is_new)"""
    existing = db.query(Stock).filter(Stock.ticker == stock_data.ticker.upper()).first()
    
    if existing:
        # Update existing record
        for field, value in stock_data.model_dump().items():
            setattr(existing, field, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False
    else:
        # Create new record
        new_stock = Stock(**stock_data.model_dump())
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)
        return new_stock, True


def scrape_and_save(
    db: Session,
    filters: str = "cap_midover,sh_avgvol_o500,sh_price_o10",
    max_pages: int | None = None,
) -> ScrapeResponse:
    """Scrape finviz and save to database"""
    added = 0
    updated = 0
    
    try:
        with FinvizScraper() as scraper:
            stocks = scraper.scrape_all(filters, max_pages)
            
            for stock_data in stocks:
                _, is_new = create_or_update_stock(db, stock_data)
                if is_new:
                    added += 1
                else:
                    updated += 1
        
        return ScrapeResponse(
            success=True,
            message=f"Successfully scraped {len(stocks)} stocks",
            total_stocks=len(stocks),
            stocks_added=added,
            stocks_updated=updated,
        )
    except Exception as e:
        return ScrapeResponse(
            success=False,
            message=f"Error during scrape: {str(e)}",
            total_stocks=0,
            stocks_added=added,
            stocks_updated=updated,
        )


def delete_all_stocks(db: Session) -> int:
    """Delete all stocks from database. Returns count of deleted records."""
    count = db.query(Stock).count()
    db.query(Stock).delete()
    db.commit()
    return count


def get_unique_sectors(db: Session) -> list[str]:
    """Get list of unique sectors"""
    results = db.query(Stock.sector).distinct().filter(Stock.sector.isnot(None)).all()
    return [r[0] for r in results if r[0]]


def get_unique_countries(db: Session) -> list[str]:
    """Get list of unique countries"""
    results = db.query(Stock.country).distinct().filter(Stock.country.isnot(None)).all()
    return [r[0] for r in results if r[0]]


