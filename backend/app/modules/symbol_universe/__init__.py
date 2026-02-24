"""
Symbol Universe — stock/symbol database and watchlists.

Single source of symbols the system tracks. Feeds screeners, ML, and execution.
Inputs: Market Data Agent (Finviz, Alpaca), manual watchlists.
Outputs: Symbol lists and metadata to other modules (client).
"""

from typing import Optional


# Persist via app DB config (key: symbol_universe)
def _get_store():
    from app.services.database import db_service

    return db_service.get_config("symbol_universe") or {
        "symbols": [],
        "metadata": {},
        "source": None,
    }


def _set_store(symbols: list, metadata: dict, source: Optional[str] = None):
    from app.services.database import db_service

    db_service.set_config(
        "symbol_universe",
        {
            "symbols": symbols,
            "metadata": metadata,
            "source": source or "manual",
        },
    )


def get_tracked_symbols() -> list[str]:
    """Return list of symbols currently tracked. Updated by Market Data Agent (Finviz scan)."""
    store = _get_store()
    return list(store.get("symbols") or [])


def get_symbol_metadata(symbol: str) -> dict | None:
    """Return metadata for a symbol (sector, cap, liquidity, etc.)."""
    store = _get_store()
    meta = store.get("metadata") or {}
    return meta.get(symbol.upper())


def set_tracked_symbols_from_finviz(stocks: list[dict]) -> int:
    """
    Update tracked symbols and metadata from a Finviz screener result (list of row dicts).
    Expects rows with 'Ticker' or 'Symbol' key; optional 'Sector', 'Market Cap', etc.
    Called by Market Data Agent after a successful Finviz scan.
    Returns count of symbols stored.
    """
    symbols: list[str] = []
    metadata: dict = {}
    for row in stocks or []:
        if not isinstance(row, dict):
            continue
        ticker = (
            (
                row.get("Ticker")
                or row.get("Symbol")
                or row.get("ticker")
                or row.get("symbol")
                or ""
            )
            .strip()
            .upper()
        )
        if not ticker:
            continue
        if ticker not in metadata:
            symbols.append(ticker)
        metadata[ticker] = {
            "sector": row.get("Sector") or row.get("sector"),
            "market_cap": row.get("Market Cap") or row.get("market_cap"),
            "company": row.get("Company") or row.get("company"),
        }
    _set_store(symbols, metadata, source="finviz")
    return len(symbols)


def set_tracked_symbols(symbols: list[str], source: str = "manual") -> None:
    """Set tracked symbols from a simple list (e.g. watchlist). Use set_tracked_symbols_from_finviz for Finviz data."""
    symbols = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
    store = _get_store()
    metadata = {s: store.get("metadata", {}).get(s) or {} for s in symbols}
    _set_store(symbols, metadata, source=source)


def get_summary() -> dict:
    """Return symbols, source, and metadata for API clients."""
    store = _get_store()
    symbols = list(store.get("symbols") or [])
    meta = store.get("metadata") or {}
    return {
        "symbols": symbols,
        "source": store.get("source"),
        "metadata": {s: meta.get(s) or {} for s in symbols},
        "count": len(symbols),
    }
