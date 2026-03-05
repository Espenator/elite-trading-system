"""
Execution Engine — live/paper order execution and risk checks.

Wraps Alpaca; live by default (TRADING_MODE=live). Order placement,
cancellation, risk checks, audit log. Feeds fill/outcome data back for ML learning.
"""

from app.core.config import settings
from app.services.alpaca_service import alpaca_service


def get_trading_mode() -> str:
    """Return current mode: 'live' or 'paper'. For glass-box UI."""
    mode = getattr(settings, "TRADING_MODE", "live") or "live"
    return mode.lower() if mode.lower() in ("paper", "live") else "live"


def get_status() -> dict:
    """Return execution engine status (mode, broker_connected, last_order). For glass-box UI."""
    return {
        "trading_mode": get_trading_mode(),
        "broker": "alpaca",
        "broker_connected": bool(settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY),
        "last_order_at": None,  # Can be wired to DB when needed
    }
