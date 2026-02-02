"""
Symbol Universe — stock/symbol database and watchlists.

Single source of symbols the system tracks. Feeds screeners, ML, and execution.
Inputs: Screener results (e.g. Finviz), manual watchlists.
Outputs: Symbol lists and metadata to other modules.
"""

# Placeholder: real implementation will use DB and Finviz/screener integration
def get_tracked_symbols() -> list[str]:
    """Return list of symbols currently tracked. Stub for now."""
    return []


def get_symbol_metadata(symbol: str) -> dict | None:
    """Return metadata for a symbol (sector, cap, liquidity, etc.). Stub for now."""
    return None
