"""Off-Hours Data Monitor — pre-market gaps, data freshness, session-aware quality.

Monitors data quality during extended hours (pre-market 4-9:30 AM ET,
after-hours 4-8 PM ET) and detects overnight gaps for risk awareness.

Publishes:
  - signal.overnight_gap: When a stock gaps >2% from prior close
  - data.staleness_alert: When snapshot data hasn't updated in >3 minutes

Subscribes to:
  - market_data.bar: Monitors incoming bar data for freshness and gaps
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# Thresholds
GAP_ALERT_THRESHOLD = 0.02        # 2% gap triggers alert
LARGE_GAP_THRESHOLD = 0.05        # 5% gap = large (higher risk)
STALENESS_THRESHOLD_SEC = 180     # 3 minutes without update = stale
DATA_QUALITY_LOG_INTERVAL = 300   # Log data quality summary every 5 min


class OffHoursMonitor:
    """Monitors data quality during extended trading hours.

    Detects overnight gaps, tracks data freshness per symbol,
    and publishes alerts for risk management.
    """

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False

        # Per-symbol tracking
        self._last_update: Dict[str, float] = {}       # symbol -> timestamp
        self._prev_close: Dict[str, float] = {}        # symbol -> prev day close
        self._gaps_detected: Dict[str, Dict] = {}      # symbol -> gap info
        self._stale_symbols: set = set()

        # Session state
        self._session = "unknown"
        self._last_quality_log = 0.0

        # Stats
        self._bars_monitored = 0
        self._gaps_published = 0
        self._staleness_alerts = 0

    async def start(self):
        """Subscribe to market_data.bar and begin monitoring."""
        if self._bus:
            await self._bus.subscribe("market_data.bar", self._on_bar)
        self._running = True
        asyncio.create_task(self._staleness_check_loop())
        logger.info("OffHoursMonitor started")

    async def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._bus:
            await self._bus.unsubscribe("market_data.bar", self._on_bar)
        logger.info(
            "OffHoursMonitor stopped: monitored=%d bars, gaps=%d, staleness_alerts=%d",
            self._bars_monitored, self._gaps_published, self._staleness_alerts,
        )

    async def _on_bar(self, bar_data: Dict[str, Any]) -> None:
        """Process incoming bar data for gap detection and freshness tracking."""
        self._bars_monitored += 1
        symbol = bar_data.get("symbol", "")
        if not symbol:
            return

        now = time.time()
        self._last_update[symbol] = now
        self._stale_symbols.discard(symbol)

        # Detect session
        self._session = self._detect_session()

        # Gap detection: compare current price to previous close
        price = bar_data.get("close", 0) or bar_data.get("latest_trade_price", 0)
        prev_close = bar_data.get("prev_close", 0)

        if prev_close and prev_close > 0 and price and price > 0:
            self._prev_close[symbol] = prev_close
            gap_pct = (price - prev_close) / prev_close

            # Only flag gaps during pre-market or at market open
            if abs(gap_pct) >= GAP_ALERT_THRESHOLD and self._session in ("pre", "regular_open"):
                await self._publish_gap(symbol, price, prev_close, gap_pct)

    async def _publish_gap(self, symbol: str, price: float, prev_close: float, gap_pct: float):
        """Publish overnight gap event."""
        # Avoid duplicate gap alerts for same symbol same day
        today = datetime.now(ET).strftime("%Y-%m-%d")
        gap_key = f"{symbol}:{today}"
        if gap_key in self._gaps_detected:
            return

        gap_size = "large" if abs(gap_pct) >= LARGE_GAP_THRESHOLD else "normal"
        direction = "up" if gap_pct > 0 else "down"

        gap_info = {
            "symbol": symbol,
            "gap_pct": round(gap_pct * 100, 2),
            "gap_direction": direction,
            "gap_size": gap_size,
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "session": self._session,
            "timestamp": datetime.now(ET).isoformat(),
            "risk_flag": gap_size == "large",
        }
        self._gaps_detected[gap_key] = gap_info
        self._gaps_published += 1

        if self._bus:
            await self._bus.publish("signal.overnight_gap", gap_info)

        log_fn = logger.warning if gap_size == "large" else logger.info
        log_fn(
            "Overnight gap: %s %s %.1f%% (prev=$%.2f -> $%.2f) [%s]",
            symbol, direction, abs(gap_pct) * 100, prev_close, price, gap_size,
        )

    async def _staleness_check_loop(self):
        """Periodically check for stale data — intelligence runs 24/7."""
        while self._running:
            session = self._detect_session()
            # Weekend: check less frequently (every 10 min vs every 1 min)
            interval = 600 if session == "weekend" else 60
            await asyncio.sleep(interval)
            if session == "closed":
                continue  # Only skip overnight closed, not weekend

            now = time.time()
            newly_stale = []
            for symbol, last_ts in self._last_update.items():
                if now - last_ts > STALENESS_THRESHOLD_SEC:
                    if symbol not in self._stale_symbols:
                        self._stale_symbols.add(symbol)
                        newly_stale.append(symbol)

            if newly_stale and len(newly_stale) <= 20:
                # Only alert for reasonable number of stale symbols
                self._staleness_alerts += 1
                logger.warning(
                    "Data staleness: %d symbols stale (>%ds): %s",
                    len(newly_stale), STALENESS_THRESHOLD_SEC,
                    ", ".join(newly_stale[:10]),
                )
                if self._bus:
                    await self._bus.publish("data.staleness_alert", {
                        "stale_symbols": newly_stale[:50],
                        "threshold_sec": STALENESS_THRESHOLD_SEC,
                        "session": session,
                        "timestamp": datetime.now(ET).isoformat(),
                    })

            # Periodic quality summary
            if now - self._last_quality_log > DATA_QUALITY_LOG_INTERVAL:
                self._last_quality_log = now
                total = len(self._last_update)
                stale = len(self._stale_symbols)
                fresh = total - stale
                if total > 0:
                    logger.info(
                        "Data quality [%s]: %d/%d symbols fresh (%.0f%%), "
                        "%d stale, %d gaps today",
                        session, fresh, total, 100 * fresh / total,
                        stale, self._gaps_published,
                    )

    def _detect_session(self) -> str:
        """Detect current market session."""
        now_et = datetime.now(ET)
        hour = now_et.hour
        minute = now_et.minute
        weekday = now_et.weekday()

        if weekday >= 5:
            return "weekend"
        if hour < 4:
            return "closed"
        if hour < 9 or (hour == 9 and minute < 30):
            return "pre"
        if hour == 9 and minute < 45:
            return "regular_open"  # First 15 min after open (gap detection window)
        if hour < 16:
            return "regular"
        if hour < 20:
            return "post"
        return "closed"

    def get_status(self) -> Dict[str, Any]:
        """Return current monitoring status."""
        now = time.time()
        total = len(self._last_update)
        stale = len(self._stale_symbols)
        return {
            "running": self._running,
            "session": self._detect_session(),
            "symbols_tracked": total,
            "symbols_fresh": total - stale,
            "symbols_stale": stale,
            "bars_monitored": self._bars_monitored,
            "gaps_published": self._gaps_published,
            "staleness_alerts": self._staleness_alerts,
            "gaps_today": {k: v for k, v in self._gaps_detected.items()},
        }

    def get_gaps_today(self) -> list:
        """Return all overnight gaps detected today."""
        today = datetime.now(ET).strftime("%Y-%m-%d")
        return [
            v for k, v in self._gaps_detected.items()
            if k.endswith(f":{today}")
        ]

    def get_gap_risk_symbols(self) -> list:
        """Return symbols with large (>5%) gaps today."""
        return [
            v["symbol"] for v in self.get_gaps_today()
            if v.get("risk_flag")
        ]


# Module-level singleton
_monitor: Optional[OffHoursMonitor] = None


def get_off_hours_monitor(message_bus=None) -> OffHoursMonitor:
    """Get or create the OffHoursMonitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = OffHoursMonitor(message_bus=message_bus)
    return _monitor
