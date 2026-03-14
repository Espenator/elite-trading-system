"""PDT (Pattern Day Trader) Tracker — Issue #76.

Tracks day trades in a rolling 5-business-day window and blocks new day trades
when the count reaches 3/3 (FINRA limit for accounts under $25K).

A "day trade" is opening and closing the same position on the same day.
We track this by monitoring Alpaca trade activities (FILL events).

Usage:
    from app.services.pdt_tracker import get_pdt_tracker
    tracker = get_pdt_tracker()
    count = await tracker.get_day_trade_count()
    can_trade = await tracker.can_open_day_trade()
"""
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_PDT_MAX_DAY_TRADES = 3  # FINRA limit for accounts under $25K
_PDT_ROLLING_DAYS = 5    # Rolling window
_CACHE_TTL = 60.0        # Cache day trade count for 60 seconds


class PDTTracker:
    """Pattern Day Trader rule tracker.

    Counts day trades (round-trip same-day trades) in a rolling 5-day window
    using Alpaca account activities. Caches the result to avoid excessive API calls.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {"count": 0, "trades": [], "timestamp": 0.0}
        self._max_day_trades = _PDT_MAX_DAY_TRADES

    async def get_day_trade_count(self) -> int:
        """Return the number of day trades in the rolling 5-day window.

        Uses Alpaca account activities (FILL type) to identify same-day
        round-trip trades. Results are cached for 60 seconds.
        """
        now = time.time()
        if now - self._cache["timestamp"] < _CACHE_TTL:
            return self._cache["count"]

        try:
            from app.services.alpaca_service import alpaca_service

            # Get fills from the last 5 business days
            five_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
                "%Y-%m-%dT00:00:00Z"
            )
            activities = await alpaca_service.get_activities(
                activity_types="FILL",
                limit=200,
                after=five_days_ago,
            )

            if not activities:
                self._cache = {"count": 0, "trades": [], "timestamp": now}
                return 0

            # Group fills by symbol and date to identify day trades
            # A day trade = buy and sell of the same symbol on the same calendar date
            day_fills: Dict[str, Dict[str, List[str]]] = {}  # date -> symbol -> [sides]
            for activity in activities:
                symbol = activity.get("symbol", "")
                side = activity.get("side", "")
                # Parse transaction_time or timestamp
                tx_time = activity.get("transaction_time") or activity.get("timestamp", "")
                if not tx_time or not symbol or not side:
                    continue
                try:
                    # Extract just the date part
                    trade_date = tx_time[:10]  # YYYY-MM-DD
                except (IndexError, TypeError):
                    continue

                if trade_date not in day_fills:
                    day_fills[trade_date] = {}
                if symbol not in day_fills[trade_date]:
                    day_fills[trade_date][symbol] = []
                day_fills[trade_date][symbol].append(side.lower())

            # Count day trades: a symbol with both 'buy' and 'sell' on same date
            day_trade_count = 0
            day_trade_details = []
            # Only look at the last 5 business days
            cutoff = (datetime.now(timezone.utc) - timedelta(days=_PDT_ROLLING_DAYS)).strftime(
                "%Y-%m-%d"
            )
            for date_str, symbols in day_fills.items():
                if date_str < cutoff:
                    continue
                for symbol, sides in symbols.items():
                    has_buy = any(s in ("buy", "buy_to_cover") for s in sides)
                    has_sell = any(s in ("sell", "sell_short") for s in sides)
                    if has_buy and has_sell:
                        day_trade_count += 1
                        day_trade_details.append({"date": date_str, "symbol": symbol})

            self._cache = {
                "count": day_trade_count,
                "trades": day_trade_details[-10:],  # keep last 10 for display
                "timestamp": now,
            }
            return day_trade_count

        except Exception as e:
            logger.warning("PDT day trade count failed: %s", e)
            return self._cache.get("count", 0)

    async def can_open_day_trade(self) -> bool:
        """Check if a new day trade is allowed under PDT rules.

        Returns True if the day trade count is below the limit.
        For accounts over $25K, PDT rules don't apply — but we still
        track for awareness. This method is conservative (blocks at limit).
        """
        try:
            from app.services.alpaca_service import alpaca_service
            account = await alpaca_service.get_account()
            if account:
                equity = float(account.get("equity", 0))
                # PDT rules don't apply to accounts with $25K+ equity
                if equity >= 25_000:
                    return True
        except Exception:
            pass

        count = await self.get_day_trade_count()
        return count < self._max_day_trades

    async def get_pdt_status(self) -> Dict[str, Any]:
        """Return PDT status dict for system status endpoint and frontend display."""
        count = await self.get_day_trade_count()
        can_trade = count < self._max_day_trades

        # Check if account is above $25K (exempt from PDT)
        exempt = False
        equity = 0.0
        try:
            from app.services.alpaca_service import alpaca_service
            account = await alpaca_service.get_account()
            if account:
                equity = float(account.get("equity", 0))
                exempt = equity >= 25_000
        except Exception:
            pass

        return {
            "day_trades_used": count,
            "day_trades_max": self._max_day_trades,
            "day_trades_remaining": max(0, self._max_day_trades - count),
            "can_day_trade": can_trade or exempt,
            "pdt_exempt": exempt,
            "rolling_window_days": _PDT_ROLLING_DAYS,
            "recent_day_trades": self._cache.get("trades", []),
        }


# Singleton
_pdt_tracker: Optional[PDTTracker] = None


def get_pdt_tracker() -> PDTTracker:
    """Get or create the singleton PDT tracker."""
    global _pdt_tracker
    if _pdt_tracker is None:
        _pdt_tracker = PDTTracker()
    return _pdt_tracker
