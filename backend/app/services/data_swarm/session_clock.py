"""Session clock — determines current trading session and source availability.

Uses America/New_York (ET) for session boundaries. Tells the swarm orchestrator
which collectors (Alpaca, Unusual Whales, FinViz) are live in each session so
we only spawn collectors that can actually get data.

Sessions (ET):
  - OVERNIGHT:    8:00 PM - 4:00 AM ET (24/5 Alpaca/UW; no options, no FinViz)
  - PRE_MARKET:   4:00 AM - 9:30 AM ET (FinViz live from 4 AM; options not yet)
  - REGULAR:      9:30 AM - 4:00 PM ET (all sources active)
  - AFTER_HOURS:  4:00 PM - 8:00 PM ET (options closed; FinViz until 8 PM)
  - WEEKEND:      Saturday 8:00 PM - Sunday 8:00 PM ET (UW REST historical only)
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Dict

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class TradingSession(str, Enum):
    """Current trading session in ET (America/New_York)."""

    OVERNIGHT = "overnight"       # 8:00 PM - 4:00 AM ET
    PRE_MARKET = "pre_market"     # 4:00 AM - 9:30 AM ET
    REGULAR = "regular"           # 9:30 AM - 4:00 PM ET
    AFTER_HOURS = "after_hours"   # 4:00 PM - 8:00 PM ET
    WEEKEND = "weekend"           # Saturday 8 PM - Sunday 8 PM ET


class SourceAvailability:
    """Which data sources are live in each session.

    Used by the swarm orchestrator to spawn only collectors that can
    return data in the current session.
    """

    SESSION_SOURCES: Dict[TradingSession, Dict[str, bool]] = {
        TradingSession.OVERNIGHT: {
            "alpaca_stream": True,    # 24/5 WebSocket
            "alpaca_rest": True,       # 24/5 REST
            "alpaca_futures": True,    # via stream
            "uw_websocket": True,      # price + news channels
            "uw_rest": True,           # stock-state, OHLC
            "uw_flow": False,          # options markets closed
            "finviz_screener": False,  # offline until 4 AM
            "finviz_futures": False,   # offline
        },
        TradingSession.PRE_MARKET: {
            "alpaca_stream": True,
            "alpaca_rest": True,
            "alpaca_futures": True,
            "uw_websocket": True,
            "uw_rest": True,
            "uw_flow": False,          # options not trading yet
            "finviz_screener": True,   # live from 4 AM
            "finviz_futures": True,     # delayed but available
        },
        TradingSession.REGULAR: {
            "alpaca_stream": True,
            "alpaca_rest": True,
            "alpaca_futures": True,
            "uw_websocket": True,
            "uw_rest": True,
            "uw_flow": True,           # dark pool, lit flow, options tape
            "finviz_screener": True,
            "finviz_futures": True,
        },
        TradingSession.AFTER_HOURS: {
            "alpaca_stream": True,
            "alpaca_rest": True,
            "alpaca_futures": True,
            "uw_websocket": True,
            "uw_rest": True,
            "uw_flow": False,           # options closed
            "finviz_screener": True,   # live until 8 PM
            "finviz_futures": True,
        },
        TradingSession.WEEKEND: {
            "alpaca_stream": False,
            "alpaca_rest": False,
            "alpaca_futures": False,
            "uw_websocket": False,
            "uw_rest": True,            # historical data still available
            "uw_flow": False,
            "finviz_screener": False,
            "finviz_futures": False,
        },
    }

    def get_current_session(self) -> TradingSession:
        """Return current session based on ET clock.

        Returns:
            One of TradingSession.OVERNIGHT, PRE_MARKET, REGULAR,
            AFTER_HOURS, WEEKEND.
        """
        now_et = datetime.now(ET)
        hour = now_et.hour
        minute = now_et.minute
        weekday = now_et.weekday()  # 0=Mon, 5=Sat, 6=Sun

        # Weekend: Saturday 8:00 PM through Sunday 8:00 PM (exclusive of Sun 8 PM)
        if weekday == 5 and hour >= 20:
            return TradingSession.WEEKEND
        if weekday == 6 and hour < 20:
            return TradingSession.WEEKEND

        # Overnight: 8:00 PM - 4:00 AM ET
        if hour >= 20 or hour < 4:
            return TradingSession.OVERNIGHT

        # Pre-market: 4:00 AM - 9:30 AM ET
        if hour < 9 or (hour == 9 and minute < 30):
            return TradingSession.PRE_MARKET

        # After-hours: 4:00 PM - 8:00 PM ET
        if hour >= 16 and hour < 20:
            return TradingSession.AFTER_HOURS

        # Regular: 9:30 AM - 4:00 PM ET
        return TradingSession.REGULAR

    def get_active_sources(self) -> Dict[str, bool]:
        """Return which collectors should be running right now.

        Returns:
            Dict mapping collector name to True if it should be active,
            False otherwise. Keys: alpaca_stream, alpaca_rest, alpaca_futures,
            uw_websocket, uw_rest, uw_flow, finviz_screener, finviz_futures.
        """
        session = self.get_current_session()
        return dict(SourceAvailability.SESSION_SOURCES.get(session, {}))


# Singleton for app-wide use
_session_clock: SourceAvailability | None = None


def get_session_clock() -> SourceAvailability:
    """Return the shared session clock instance."""
    global _session_clock
    if _session_clock is None:
        _session_clock = SourceAvailability()
    return _session_clock
