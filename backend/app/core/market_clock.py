"""Market Clock — session-aware scan intervals and symbol universe.

Central place for all services to query:
  - What market session are we in?
  - How often should scans run?
  - Which symbols should be active?

Uses the existing session_manager for session detection.
"""
import logging
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)


class MarketSession(str, Enum):
    MARKET_OPEN = "MARKET_OPEN"
    PRE_MARKET = "PREMARKET"
    POST_MARKET = "AFTERHOURS"
    OVERNIGHT = "OVERNIGHT"
    WEEKEND = "WEEKEND"


# ── Scan intervals per session ─────────────────────────────────────────────
SCAN_INTERVALS = {
    MarketSession.MARKET_OPEN: 30,    # 30s — full speed, live bars
    MarketSession.PRE_MARKET:  60,    # 60s — gap scan
    MarketSession.POST_MARKET: 120,   # 2min — earnings digestion
    MarketSession.OVERNIGHT:   300,   # 5min — crypto/macro/social only
    MarketSession.WEEKEND:     600,   # 10min — social scan only
}

# ── Symbol universes per session ───────────────────────────────────────────
WEEKEND_SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD", "GLD", "SLV", "UUP"]

OVERNIGHT_SYMBOLS = [
    "BTCUSD", "ETHUSD", "GLD", "TLT", "UUP",
    "SPY", "QQQ", "AAPL", "NVDA", "MSFT",
    "TSLA", "AMZN", "META", "GOOGL", "AMD",
]


def get_session() -> MarketSession:
    """Return the current MarketSession enum."""
    try:
        from app.services.session_manager import (
            get_current_session,
            WEEKEND, OVERNIGHT, PREMARKET, AFTERHOURS, MARKET_OPEN,
        )
        session = get_current_session()
        mapping = {
            MARKET_OPEN: MarketSession.MARKET_OPEN,
            PREMARKET: MarketSession.PRE_MARKET,
            AFTERHOURS: MarketSession.POST_MARKET,
            OVERNIGHT: MarketSession.OVERNIGHT,
            WEEKEND: MarketSession.WEEKEND,
        }
        return mapping.get(session, MarketSession.MARKET_OPEN)
    except Exception:
        return MarketSession.MARKET_OPEN


def get_scan_interval() -> int:
    """Return the scan interval in seconds for the current session."""
    return SCAN_INTERVALS[get_session()]


def get_active_symbols(full_universe: List[str]) -> List[str]:
    """Return the active symbol universe for the current session.

    Weekend: only crypto/metals (6 symbols)
    Overnight: top 15 liquid names
    All other sessions: full universe
    """
    session = get_session()
    if session == MarketSession.WEEKEND:
        return WEEKEND_SYMBOLS
    if session == MarketSession.OVERNIGHT:
        return OVERNIGHT_SYMBOLS
    return full_universe
