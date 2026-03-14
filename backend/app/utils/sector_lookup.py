"""Sector lookup utility for risk management.

Provides GICS sector classification for common US equities.
Used by Risk Governor and OrderExecutor to enforce sector concentration
and correlation limits even when Alpaca doesn't provide sector data.

Includes a DuckDB fallback for tickers not in the static map, using
finviz screener data if available.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# GICS Sector mappings for S&P 500 and commonly-traded stocks
# Source: S&P Global GICS classification
_SECTOR_MAP = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Technology", "GOOG": "Technology", "META": "Technology",
    "AVGO": "Technology", "ORCL": "Technology", "CRM": "Technology",
    "AMD": "Technology", "ADBE": "Technology", "CSCO": "Technology",
    "ACN": "Technology", "INTC": "Technology", "TXN": "Technology",
    "QCOM": "Technology", "INTU": "Technology", "AMAT": "Technology",
    "PANW": "Technology", "MU": "Technology", "LRCX": "Technology",
    "KLAC": "Technology", "SNPS": "Technology", "CDNS": "Technology",
    "MRVL": "Technology", "FTNT": "Technology", "CRWD": "Technology",
    "NXPI": "Technology", "ON": "Technology", "MCHP": "Technology",
    "SMCI": "Technology", "PLTR": "Technology", "DELL": "Technology",
    "HPE": "Technology", "HPQ": "Technology", "SNOW": "Technology",
    "NET": "Technology", "DDOG": "Technology", "ZS": "Technology",
    "TEAM": "Technology", "WDAY": "Technology", "NOW": "Technology",
    "SHOP": "Technology", "SQ": "Technology", "UBER": "Technology",
    "COIN": "Technology", "ARM": "Technology", "TSM": "Technology",
    "ASML": "Technology",

    # Communication Services
    "NFLX": "Communication Services", "DIS": "Communication Services",
    "CMCSA": "Communication Services", "T": "Communication Services",
    "VZ": "Communication Services", "TMUS": "Communication Services",
    "CHTR": "Communication Services", "EA": "Communication Services",
    "TTWO": "Communication Services", "WBD": "Communication Services",
    "PARA": "Communication Services", "RBLX": "Communication Services",
    "SPOT": "Communication Services", "SNAP": "Communication Services",
    "PINS": "Communication Services", "ROKU": "Communication Services",

    # Consumer Discretionary
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "HD": "Consumer Discretionary", "MCD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary", "LOW": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary", "TJX": "Consumer Discretionary",
    "BKNG": "Consumer Discretionary", "CMG": "Consumer Discretionary",
    "MAR": "Consumer Discretionary", "ORLY": "Consumer Discretionary",
    "AZO": "Consumer Discretionary", "ROST": "Consumer Discretionary",
    "DHI": "Consumer Discretionary", "LEN": "Consumer Discretionary",
    "GM": "Consumer Discretionary", "F": "Consumer Discretionary",
    "RIVN": "Consumer Discretionary", "LCID": "Consumer Discretionary",
    "NIO": "Consumer Discretionary", "LI": "Consumer Discretionary",

    # Consumer Staples
    "WMT": "Consumer Staples", "PG": "Consumer Staples",
    "COST": "Consumer Staples", "KO": "Consumer Staples",
    "PEP": "Consumer Staples", "PM": "Consumer Staples",
    "MO": "Consumer Staples", "MDLZ": "Consumer Staples",
    "CL": "Consumer Staples", "GIS": "Consumer Staples",
    "SYY": "Consumer Staples", "KMB": "Consumer Staples",
    "HSY": "Consumer Staples", "KR": "Consumer Staples",

    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "LLY": "Healthcare",
    "ABBV": "Healthcare", "MRK": "Healthcare", "PFE": "Healthcare",
    "TMO": "Healthcare", "ABT": "Healthcare", "DHR": "Healthcare",
    "BMY": "Healthcare", "AMGN": "Healthcare", "GILD": "Healthcare",
    "ISRG": "Healthcare", "VRTX": "Healthcare", "MDT": "Healthcare",
    "SYK": "Healthcare", "BSX": "Healthcare", "ELV": "Healthcare",
    "CI": "Healthcare", "HCA": "Healthcare", "CVS": "Healthcare",
    "ZTS": "Healthcare", "REGN": "Healthcare", "MRNA": "Healthcare",
    "DXCM": "Healthcare", "BIIB": "Healthcare", "ILMN": "Healthcare",

    # Financials
    "BRK.B": "Financials", "JPM": "Financials", "V": "Financials",
    "MA": "Financials", "BAC": "Financials", "WFC": "Financials",
    "GS": "Financials", "MS": "Financials", "C": "Financials",
    "AXP": "Financials", "BLK": "Financials", "SCHW": "Financials",
    "CB": "Financials", "PGR": "Financials", "MMC": "Financials",
    "AON": "Financials", "ICE": "Financials", "CME": "Financials",
    "MCO": "Financials", "TFC": "Financials", "USB": "Financials",
    "PNC": "Financials", "AIG": "Financials", "MET": "Financials",
    "PYPL": "Financials", "SOFI": "Financials", "HOOD": "Financials",

    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "SLB": "Energy", "EOG": "Energy", "MPC": "Energy",
    "PSX": "Energy", "VLO": "Energy", "PXD": "Energy",
    "OXY": "Energy", "WMB": "Energy", "HAL": "Energy",
    "DVN": "Energy", "FANG": "Energy", "HES": "Energy",

    # Industrials
    "GE": "Industrials", "CAT": "Industrials", "RTX": "Industrials",
    "HON": "Industrials", "UNP": "Industrials", "BA": "Industrials",
    "DE": "Industrials", "UPS": "Industrials", "LMT": "Industrials",
    "ADP": "Industrials", "GD": "Industrials", "NOC": "Industrials",
    "MMM": "Industrials", "CSX": "Industrials", "WM": "Industrials",
    "EMR": "Industrials", "ITW": "Industrials", "ETN": "Industrials",
    "FDX": "Industrials",

    # Materials
    "LIN": "Materials", "APD": "Materials", "SHW": "Materials",
    "ECL": "Materials", "FCX": "Materials", "NEM": "Materials",
    "DOW": "Materials", "NUE": "Materials", "DD": "Materials",

    # Real Estate
    "PLD": "Real Estate", "AMT": "Real Estate", "EQIX": "Real Estate",
    "CCI": "Real Estate", "SPG": "Real Estate", "O": "Real Estate",
    "PSA": "Real Estate", "DLR": "Real Estate", "WELL": "Real Estate",

    # Utilities
    "NEE": "Utilities", "SO": "Utilities", "DUK": "Utilities",
    "D": "Utilities", "AEP": "Utilities", "SRE": "Utilities",
    "EXC": "Utilities", "XEL": "Utilities", "ED": "Utilities",
    "WEC": "Utilities",

    # ETFs (mapped to closest sector or "ETF")
    "SPY": "ETF", "QQQ": "ETF", "IWM": "ETF", "DIA": "ETF",
    "VOO": "ETF", "VTI": "ETF", "ARKK": "ETF", "XLF": "ETF",
    "XLE": "ETF", "XLK": "ETF", "XLV": "ETF", "XLI": "ETF",
    "XLP": "ETF", "XLY": "ETF", "XLB": "ETF", "XLU": "ETF",
    "XLRE": "ETF", "XLC": "ETF", "SOXL": "ETF", "TQQQ": "ETF",
    "SQQQ": "ETF", "UVXY": "ETF", "VXX": "ETF",
}

# All GICS sectors
GICS_SECTORS = [
    "Technology", "Communication Services", "Consumer Discretionary",
    "Consumer Staples", "Healthcare", "Financials", "Energy",
    "Industrials", "Materials", "Real Estate", "Utilities",
]


@lru_cache(maxsize=4096)
def enrich_sector_from_duckdb(symbol: str) -> str:
    """Try to look up sector from DuckDB (finviz screener or similar data).

    SYNCHRONOUS — safe to call from sync scan methods.
    Uses LRU cache so repeated lookups are fast.
    Returns sector string or "" on any error / miss.
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        cursor = duckdb_store.get_thread_cursor()
        # Try finviz_screener table first (has sector column from FinViz data)
        for table in ("finviz_screener", "stock_fundamentals", "company_info"):
            try:
                row = cursor.execute(
                    f"SELECT sector FROM {table} WHERE ticker = ? OR symbol = ? LIMIT 1",
                    [symbol.upper(), symbol.upper()],
                ).fetchone()
                if row and row[0]:
                    sector = str(row[0]).strip()
                    if sector and sector.lower() not in ("", "none", "n/a"):
                        # Cache in the static map too for future fast lookups
                        _SECTOR_MAP[symbol.upper()] = sector
                        return sector
            except Exception:
                continue  # Table doesn't exist, try next
    except Exception as e:
        logger.debug("DuckDB sector lookup failed for %s: %s", symbol, e)
    return ""


def get_sector(symbol: str) -> str:
    """Look up GICS sector for a symbol.

    Returns the sector name or "Unknown" if not found.
    Tries static map first, then DuckDB fallback.
    """
    result = _SECTOR_MAP.get(symbol.upper(), "")
    if result:
        return result
    result = enrich_sector_from_duckdb(symbol)
    return result if result else "Unknown"


def get_sector_or_none(symbol: str) -> str:
    """Look up GICS sector, return empty string if not found.

    Tries static map first, then DuckDB fallback.
    """
    result = _SECTOR_MAP.get(symbol.upper(), "")
    if result:
        return result
    return enrich_sector_from_duckdb(symbol)


def is_known_symbol(symbol: str) -> bool:
    """Check if we have sector data for this symbol."""
    return symbol.upper() in _SECTOR_MAP


def get_symbols_in_sector(sector: str) -> list:
    """Get all known symbols in a given sector."""
    return [sym for sym, sec in _SECTOR_MAP.items() if sec == sector]
