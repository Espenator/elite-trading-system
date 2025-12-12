# app/schemas/stock.py
from pydantic import BaseModel
from datetime import datetime


class StockBase(BaseModel):
    ticker: str
    company: str
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    market_cap: str | None = None
    pe_ratio: float | None = None
    price: float | None = None
    change: float | None = None
    volume: int | None = None


class StockCreate(StockBase):
    pass


class StockRead(StockBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    """Request to scrape finviz with custom filters"""
    filters: str | None = "cap_midover,sh_avgvol_o500,sh_price_o10"


class ScrapeResponse(BaseModel):
    """Response from scrape operation"""
    success: bool
    message: str
    total_stocks: int
    stocks_added: int
    stocks_updated: int


class StockListResponse(BaseModel):
    """Response for stock list"""
    total: int
    page: int
    per_page: int
    stocks: list[StockRead]


