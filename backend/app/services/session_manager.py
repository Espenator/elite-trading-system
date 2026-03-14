"""Session Manager — session-aware state machine for 24/7 always-on operation.

Every service checks the current session state to decide what to run.
Replaces binary "market open / market closed" logic.

Sessions (ET, America/New_York):
  PREMARKET    (4:00 AM – 9:30 AM ET)  → News/sentiment scan, gap analysis, model prep
  MARKET_OPEN  (9:30 AM – 4:00 PM ET)  → Full 15-minute cycle, execution enabled
  AFTERHOURS   (4:00 PM – 8:00 PM ET)  → Daily aggregation, outcome logging, position review
  OVERNIGHT    (8:00 PM – 4:00 AM ET)  → Deep analysis, backtesting, ML retraining
  WEEKEND      (Sat/Sun all day)        → Walk-forward validation, backtest runs, news monitoring

Publishes session.changed on MessageBus when state transitions.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# Session names matching task spec
PREMARKET = "PREMARKET"
MARKET_OPEN = "MARKET_OPEN"
AFTERHOURS = "AFTERHOURS"
OVERNIGHT = "OVERNIGHT"
WEEKEND = "WEEKEND"

# US market holidays (simplified — add more as needed)
# Format: (month, day) — no year for recurring
_US_HOLIDAYS = frozenset({
    (1, 1),   # New Year
    (1, 20),  # MLK (3rd Mon — approximate)
    (2, 17),  # Presidents (3rd Mon — approximate)
    (4, 18),  # Good Friday (varies)
    (5, 26),  # Memorial (last Mon — approximate)
    (7, 4),   # Independence
    (9, 1),   # Labor (1st Mon — approximate)
    (11, 27), # Thanksgiving (4th Thu — approximate)
    (12, 25), # Christmas
})


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5  # Sat=5, Sun=6


def _is_holiday(dt: datetime) -> bool:
    return (dt.month, dt.day) in _US_HOLIDAYS


def get_current_session(dt: Optional[datetime] = None) -> str:
    """Return current market session.

    Uses Eastern Time. Handles weekends. Holiday handling is approximate
    (full calendar would use pandas_market_calendars or similar).

    Args:
        dt: Optional datetime to check; defaults to now(ET).

    Returns:
        One of: PREMARKET, MARKET_OPEN, AFTERHOURS, OVERNIGHT, WEEKEND
    """
    now = dt or datetime.now(ET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET)
    else:
        now = now.astimezone(ET)

    hour = now.hour
    minute = now.minute
    mins = hour * 60 + minute

    if _is_weekend(now) or _is_holiday(now):
        return WEEKEND

    # Overnight: 8:00 PM (1200 min) – 4:00 AM (240 min)
    if hour >= 20 or hour < 4:
        return OVERNIGHT

    # Pre-market: 4:00 AM (240) – 9:30 AM (570)
    if mins < 570:
        return PREMARKET

    # Market open: 9:30 AM (570) – 4:00 PM (960)
    if mins < 960:
        return MARKET_OPEN

    # After-hours: 4:00 PM (960) – 8:00 PM (1200)
    if mins < 1200:
        return AFTERHOURS

    return OVERNIGHT


def is_market_open() -> bool:
    """Return True when regular market hours (9:30 AM – 4:00 PM ET, Mon–Fri)."""
    return get_current_session() == MARKET_OPEN


def is_execution_enabled() -> bool:
    """Return True when execution is allowed (market open only)."""
    return get_current_session() == MARKET_OPEN


class SessionManager:
    """Session state machine with MessageBus publishing on transitions."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_session: str = ""
        self._check_interval = 60.0  # Check every 60s for transitions

    async def start(self) -> None:
        """Start the session monitor loop; publishes session.changed on transitions."""
        if self._running:
            return
        self._running = True
        self._last_session = get_current_session()
        self._task = asyncio.create_task(self._loop(), name="session_manager")
        logger.info("SessionManager started (session=%s)", self._last_session)

    async def stop(self) -> None:
        """Stop the session monitor."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SessionManager stopped")

    async def _loop(self) -> None:
        """Check session every interval; publish on change."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                current = get_current_session()
                if current != self._last_session:
                    previous = self._last_session
                    self._last_session = current
                    await self._publish_change(current, previous)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("SessionManager check error: %s", e)

    async def _publish_change(self, session: str, previous: str) -> None:
        """Publish session.changed to MessageBus."""
        if not self._bus:
            return
        payload: Dict[str, Any] = {
            "session": session,
            "previous": previous,
            "timestamp": datetime.now(ET).isoformat(),
            "market_open": session == MARKET_OPEN,
            "execution_enabled": session == MARKET_OPEN,
        }
        await self._bus.publish("session.changed", payload)
        logger.info("SessionManager: session changed → %s", session)

    def get_current_session(self) -> str:
        """Return current session (sync)."""
        return get_current_session()

    def get_status(self) -> Dict[str, Any]:
        """Return manager status for monitoring."""
        return {
            "running": self._running,
            "session": get_current_session(),
            "last_session": self._last_session,
            "market_open": is_market_open(),
            "execution_enabled": is_execution_enabled(),
        }


# Singleton
_manager: Optional[SessionManager] = None


def get_session_manager(message_bus=None) -> SessionManager:
    """Get or create the SessionManager singleton."""
    global _manager
    if _manager is None:
        _manager = SessionManager(message_bus=message_bus)
    elif message_bus and not _manager._bus:
        _manager._bus = message_bus
    return _manager
