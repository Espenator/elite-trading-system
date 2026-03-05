"""Alpaca Data API client for daily OHLCV bars (research doc: daily timeframe)."""
from datetime import datetime, date
from typing import List

import pandas as pd

from app.core.config import settings


def get_daily_bars(symbols: List[str], start: date, end: date) -> pd.DataFrame:
    """
    Fetch daily bars from Alpaca Data API for the given symbols and date range.
    Returns DataFrame with columns: symbol, date, open, high, low, close, volume.
    """
    if not symbols:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume"])

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume"])

    if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume"])

    client = StockHistoricalDataClient(
        api_key=settings.ALPACA_API_KEY,
        secret_key=settings.ALPACA_SECRET_KEY,
    )
    req = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=datetime.combine(start, datetime.min.time()),
        end=datetime.combine(end, datetime.min.time()),
        adjustment="raw",
    )
    bars = client.get_stock_bars(req)
    if bars is None or bars.data is None:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume"])

    df = bars.df
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume"])

    df = df.reset_index()
    if "timestamp" in df.columns:
        df["date"] = df["timestamp"].dt.date
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
    out = df[["symbol", "date", "open", "high", "low", "close", "volume"]].copy()
    return out
