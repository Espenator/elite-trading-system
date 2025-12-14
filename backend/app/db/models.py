# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    """Stock data from finviz screener"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(150), nullable=True)
    country = Column(String(50), nullable=True)
    market_cap = Column(String(20), nullable=True)
    pe_ratio = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    change = Column(Float, nullable=True)  # Percentage change
    volume = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_stocks_ticker_updated", "ticker", "updated_at"),
    )

    def __repr__(self):
        return f"<Stock(ticker={self.ticker}, company={self.company}, price={self.price})>"
