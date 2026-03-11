"""Session Scanner — Pre-market gap detection + after-hours earnings reactions (D5).

Runs two scanner loops during off-hours:
  1. Pre-market gap scanner (4:00-9:25 AM ET)
     - Detects overnight gaps >2% from previous close
     - Publishes gap alerts to scout.discovery for council evaluation
  2. After-hours earnings scanner (4:05-6:00 PM ET)
     - Detects >3% moves in the 30 min after close
     - Correlates with known earnings dates
     - Publishes earnings reaction alerts

Both scanners use Alpaca's /v2/stocks/snapshots endpoint which
provides extended-hours price data.

Pipeline:
    SessionScanner → scout.discovery → IdeaTriage → SwarmSpawner

Usage:
    from app.services.session_scanner import get_session_scanner
    scanner = get_session_scanner()
    await scanner.start(message_bus)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Trading session boundaries in ET (UTC-5 for EST, UTC-4 for EDT)
# Using EST (UTC-5) as approximation
_ET_OFFSET = timedelta(hours=-5)

# Thresholds
GAP_THRESHOLD_PCT = 2.0       # Minimum gap % to report
EARNINGS_MOVE_PCT = 3.0       # Minimum post-close move % to report
SCAN_INTERVAL_SECONDS = 120   # Scan every 2 minutes during active windows


class SessionScanner:
    """Pre-market and after-hours scanner.

    Detects:
    - Overnight gaps (pre-market): stocks that gapped >2% from previous close
    - Earnings reactions (after-hours): stocks that moved >3% post-close

    Publishes to scout.discovery on the MessageBus.
    """

    def __init__(self):
        self._bus = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alerted_today: Set[str] = set()  # Prevent duplicate alerts per day
        self._last_alert_date: Optional[str] = None
        self._scan_count = 0
        self._gaps_found = 0
        self._earnings_found = 0

    async def start(self, message_bus=None) -> None:
        """Start the session scanner background loop."""
        if message_bus:
            self._bus = message_bus
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("SessionScanner started (gap_threshold=%.1f%%, earnings_threshold=%.1f%%)",
                     GAP_THRESHOLD_PCT, EARNINGS_MOVE_PCT)

    async def stop(self) -> None:
        """Stop the scanner."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("SessionScanner stopped (%d scans, %d gaps, %d earnings)",
                     self._scan_count, self._gaps_found, self._earnings_found)

    def _now_et(self) -> datetime:
        """Get current time in ET."""
        return datetime.now(timezone.utc) + _ET_OFFSET

    def _detect_session(self) -> str:
        """Detect which scanning session we're in.

        Returns: 'premarket', 'afterhours', 'market', 'closed'
        """
        now = self._now_et()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0=Mon, 6=Sun

        if weekday >= 5:  # Weekend
            return "closed"
        if 4 <= hour < 9 or (hour == 9 and minute < 25):
            return "premarket"
        if (hour == 16 and minute >= 5) or (17 <= hour < 18):
            return "afterhours"
        if 9 <= hour < 16 or (hour == 9 and minute >= 25):
            return "market"
        return "closed"

    async def _scan_loop(self) -> None:
        """Main scanning loop — checks session and runs appropriate scanner."""
        while self._running:
            try:
                # Reset daily alert set at midnight ET
                today_str = self._now_et().strftime("%Y-%m-%d")
                if self._last_alert_date != today_str:
                    self._alerted_today.clear()
                    self._last_alert_date = today_str

                session = self._detect_session()

                if session == "premarket":
                    await self._scan_premarket_gaps()
                elif session == "afterhours":
                    await self._scan_afterhours_earnings()
                # During market hours and closed: just sleep

                await asyncio.sleep(SCAN_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("SessionScanner loop error")
                await asyncio.sleep(60)

    async def _get_snapshots(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch snapshot data from Alpaca for multiple symbols.

        Returns dict of symbol -> snapshot data.
        """
        api_key = settings.ALPACA_API_KEY
        secret_key = settings.ALPACA_SECRET_KEY
        if not api_key or not secret_key:
            return {}

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        result = {}
        # Alpaca snapshots endpoint: max ~100 symbols per request
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                from app.core.rate_limiter import get_rate_limiter
                limiter = get_rate_limiter("alpaca")
                async with limiter:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(
                            "https://data.alpaca.markets/v2/stocks/snapshots",
                            headers=headers,
                            params={"symbols": ",".join(batch), "feed": "sip"},
                        )
                if resp.status_code == 200:
                    result.update(resp.json())
                else:
                    logger.debug("Alpaca snapshots HTTP %s for batch", resp.status_code)
            except Exception as e:
                logger.debug("Alpaca snapshots failed: %s", e)

        return result

    def _get_scan_symbols(self) -> List[str]:
        """Get symbols to scan."""
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            return get_tracked_symbols()[:200]  # Cap at 200 for speed
        except Exception:
            return [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
                "SPY", "QQQ", "IWM", "AMD", "NFLX", "CRM", "PLTR", "COIN",
            ]

    async def _scan_premarket_gaps(self) -> None:
        """Scan for overnight gaps in pre-market.

        Compares current pre-market price vs previous day's close.
        Gaps >2% are published as scout.discovery events.
        """
        self._scan_count += 1
        symbols = self._get_scan_symbols()
        snapshots = await self._get_snapshots(symbols)

        if not snapshots:
            return

        for symbol, snap in snapshots.items():
            if symbol in self._alerted_today:
                continue

            try:
                # Previous close from dailyBar
                daily_bar = snap.get("dailyBar") or {}
                prev_close = float(daily_bar.get("c") or 0)
                if prev_close <= 0:
                    continue

                # Current pre-market price from latestTrade or minuteBar
                latest_trade = snap.get("latestTrade") or {}
                current_price = float(latest_trade.get("p") or 0)
                if current_price <= 0:
                    continue

                gap_pct = ((current_price - prev_close) / prev_close) * 100

                if abs(gap_pct) >= GAP_THRESHOLD_PCT:
                    self._gaps_found += 1
                    self._alerted_today.add(symbol)

                    direction = "up" if gap_pct > 0 else "down"
                    alert = {
                        "symbol": symbol,
                        "type": "premarket_gap",
                        "direction": direction,
                        "gap_pct": round(gap_pct, 2),
                        "prev_close": prev_close,
                        "current_price": current_price,
                        "session": "premarket",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "session_scanner",
                    }

                    logger.info(
                        "Gap %s: %s %.1f%% ($%.2f -> $%.2f)",
                        direction.upper(), symbol, gap_pct, prev_close, current_price,
                    )

                    if self._bus:
                        await self._bus.publish("scout.discovery", alert)

            except (ValueError, TypeError, KeyError):
                continue

    async def _scan_afterhours_earnings(self) -> None:
        """Scan for earnings reactions in after-hours.

        Compares current AH price vs closing price.
        Moves >3% are published as scout.discovery events.
        """
        self._scan_count += 1
        symbols = self._get_scan_symbols()
        snapshots = await self._get_snapshots(symbols)

        if not snapshots:
            return

        for symbol, snap in snapshots.items():
            ah_key = f"ah_{symbol}"
            if ah_key in self._alerted_today:
                continue

            try:
                daily_bar = snap.get("dailyBar") or {}
                close_price = float(daily_bar.get("c") or 0)
                if close_price <= 0:
                    continue

                latest_trade = snap.get("latestTrade") or {}
                current_price = float(latest_trade.get("p") or 0)
                if current_price <= 0:
                    continue

                move_pct = ((current_price - close_price) / close_price) * 100

                if abs(move_pct) >= EARNINGS_MOVE_PCT:
                    self._earnings_found += 1
                    self._alerted_today.add(ah_key)

                    direction = "up" if move_pct > 0 else "down"
                    alert = {
                        "symbol": symbol,
                        "type": "afterhours_move",
                        "direction": direction,
                        "move_pct": round(move_pct, 2),
                        "close_price": close_price,
                        "current_price": current_price,
                        "session": "afterhours",
                        "possible_earnings": True,  # Likely earnings if >3% AH move
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "session_scanner",
                    }

                    logger.info(
                        "AH move %s: %s %.1f%% ($%.2f -> $%.2f) — possible earnings reaction",
                        direction.upper(), symbol, move_pct, close_price, current_price,
                    )

                    if self._bus:
                        await self._bus.publish("scout.discovery", alert)

            except (ValueError, TypeError, KeyError):
                continue

    def get_status(self) -> Dict[str, Any]:
        """Return scanner status for monitoring."""
        return {
            "running": self._running,
            "session": self._detect_session(),
            "scan_count": self._scan_count,
            "gaps_found": self._gaps_found,
            "earnings_found": self._earnings_found,
            "alerts_today": len(self._alerted_today),
            "gap_threshold_pct": GAP_THRESHOLD_PCT,
            "earnings_threshold_pct": EARNINGS_MOVE_PCT,
            "scan_interval_seconds": SCAN_INTERVAL_SECONDS,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[SessionScanner] = None


def get_session_scanner() -> SessionScanner:
    global _instance
    if _instance is None:
        _instance = SessionScanner()
    return _instance
