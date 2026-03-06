"""Alpaca WebSocket streaming service with 24/7 market data coverage.

Connects to Alpaca's StockDataStream for real-time bars and publishes
each bar to the MessageBus topic 'market_data.bar'. Supports:
- Regular hours (9:30-16:00 ET): live 1-min bars via WebSocket
- Pre-market (4:00-9:30 ET): snapshot polling every 30s
- After-hours (16:00-20:00 ET): snapshot polling every 30s
- Overnight (20:00-4:00 ET): snapshot seeding on startup, then idle

On startup, always fetches snapshots so the system has current prices
regardless of market session. During off-hours, polls snapshots on a
configurable interval so the UI always shows real (not mock) data.

Requires env vars: ALPACA_API_KEY, ALPACA_SECRET_KEY
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Market session windows (ET)
_PRE_MARKET_OPEN = 4    # 4:00 AM ET
_REGULAR_OPEN = 9       # 9:30 AM ET (we use 9 for simplicity; real check via /clock)
_REGULAR_CLOSE = 16     # 4:00 PM ET
_POST_MARKET_CLOSE = 20 # 8:00 PM ET


class AlpacaStreamService:
    """Alpaca WebSocket client with snapshot fallback for 24/7 coverage."""

    MAX_RECONNECT_DELAY = 60  # seconds
    INITIAL_RECONNECT_DELAY = 2  # seconds
    SNAPSHOT_POLL_INTERVAL = 30  # seconds between snapshot polls off-hours
    SNAPSHOT_BATCH_SIZE = 50  # symbols per snapshot API call
    # When Alpaca returns "connection limit exceeded", fall back to mock after this many failures
    CONNECTION_LIMIT_FALLBACK_AFTER = int(
        os.getenv("ALPACA_STREAM_FALLBACK_AFTER_LIMIT", "1")
    )

    def __init__(self, message_bus, symbols: Optional[List[str]] = None):
        self.message_bus = message_bus
        self.symbols = symbols or [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "TSLA", "META", "SPY", "QQQ", "IWM",
        ]
        self._stream = None
        self._running = False
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._bars_received = 0
        self._snapshots_fetched = 0
        self._last_bar_time: Optional[float] = None
        self._start_time: Optional[float] = None
        self._use_mock = False
        self._market_is_open = False
        self._session = "unknown"  # "pre", "regular", "post", "closed"
        self._snapshot_task: Optional[asyncio.Task] = None
        self._connection_limit_failures = 0

    async def start(self) -> None:
        """Start streaming with clock-aware mode selection.

        1. Check market clock
        2. Fetch snapshots immediately (seed current prices)
        3. If market is open: connect WebSocket for live bars
        4. If market is closed: poll snapshots on interval
        5. Monitor clock and switch modes when session changes
        """
        # Try settings first (pydantic), fall back to os.environ
        try:
            from app.core.config import settings as _settings
            api_key = getattr(_settings, "ALPACA_API_KEY", "") or os.getenv("ALPACA_API_KEY", "")
            secret_key = getattr(_settings, "ALPACA_SECRET_KEY", "") or os.getenv("ALPACA_SECRET_KEY", "")
        except Exception:
            api_key = os.getenv("ALPACA_API_KEY", "")
            secret_key = os.getenv("ALPACA_SECRET_KEY", "")

        if not api_key or not secret_key:
            logger.warning(
                "ALPACA_API_KEY / ALPACA_SECRET_KEY not set — "
                "starting in OFFLINE mode (no market data)"
            )
            self._use_mock = True
            await self._run_mock_stream()
            return

        self._running = True
        self._start_time = time.time()

        # Always seed snapshots on startup
        await self._fetch_and_publish_snapshots()

        # Check market clock and enter appropriate mode
        await self._check_clock()

        logger.info(
            "AlpacaStreamService starting for %d symbols — session: %s",
            len(self.symbols), self._session,
        )

        # Main loop: switch between WebSocket and snapshot polling
        while self._running:
            try:
                await self._check_clock()

                if self._market_is_open:
                    # Market open: use WebSocket for real-time bars
                    logger.info("Market OPEN — switching to WebSocket streaming")
                    await self._connect_and_stream(api_key, secret_key)
                else:
                    # Market closed: poll snapshots
                    logger.info(
                        "Market CLOSED (session=%s) — polling snapshots every %ds",
                        self._session, self.SNAPSHOT_POLL_INTERVAL,
                    )
                    await self._run_snapshot_poll_loop()

            except asyncio.CancelledError:
                logger.info("AlpacaStreamService cancelled")
                break
            except TypeError as e:
                if "extra_headers" in str(e) or "create_connection" in str(e):
                    logger.warning(
                        "Alpaca websocket failed (incompatible websockets library). "
                        'Install: pip install "websockets>=10.4,<14" then restart. '
                        "Falling back to snapshot polling."
                    )
                    await self._run_snapshot_poll_loop()
                    continue
                raise
            except ValueError as e:
                err_msg = str(e).lower()
                if "connection limit exceeded" in err_msg or "auth failed" in err_msg:
                    self._connection_limit_failures += 1
                    fallback_after = self.CONNECTION_LIMIT_FALLBACK_AFTER
                    if (
                        fallback_after > 0
                        and self._connection_limit_failures >= fallback_after
                    ):
                        logger.warning(
                            "Alpaca data stream: connection limit exceeded (%d time(s)). "
                            "Only one WebSocket per account is allowed. "
                            "Falling back to snapshot polling instead of mock data.",
                            self._connection_limit_failures,
                        )
                        # Fall back to snapshot polling (real data), not mock
                        await self._run_snapshot_poll_loop()
                        continue
                    logger.warning(
                        "Alpaca data stream: %s. Backing off %ds.",
                        e, self.MAX_RECONNECT_DELAY,
                    )
                    self._reconnect_delay = self.MAX_RECONNECT_DELAY
                    await asyncio.sleep(self._reconnect_delay)
                    continue
                raise
            except Exception:
                logger.exception(
                    "AlpacaStreamService error — reconnecting in %ds",
                    self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY
                )

    async def _check_clock(self) -> None:
        """Query Alpaca /v2/clock and update session state."""
        try:
            from app.services.alpaca_service import alpaca_service
            clock = await alpaca_service.get_clock()
            if clock:
                self._market_is_open = clock.get("is_open", False)
                # Determine session from timestamps
                now = datetime.now(timezone.utc)
                hour_et = (now.hour - 5) % 24  # rough ET offset

                if self._market_is_open:
                    self._session = "regular"
                elif _PRE_MARKET_OPEN <= hour_et < _REGULAR_OPEN:
                    self._session = "pre"
                elif _REGULAR_CLOSE <= hour_et < _POST_MARKET_CLOSE:
                    self._session = "post"
                else:
                    self._session = "closed"
            else:
                self._market_is_open = False
                self._session = "unknown"
        except Exception as exc:
            logger.warning("Clock check failed: %s", exc)
            self._market_is_open = False
            self._session = "unknown"

    async def _fetch_and_publish_snapshots(self) -> None:
        """Fetch snapshots from Alpaca Market Data API and publish as bars.

        Uses GET /v2/stocks/snapshots which returns:
        - latestTrade (price, size, timestamp)
        - latestQuote (bid/ask)
        - minuteBar (last completed 1-min bar)
        - dailyBar (current/last trading day OHLCV)
        - prevDailyBar (previous trading day OHLCV)

        This works 24/7 and returns real prices at all times.
        """
        try:
            from app.services.alpaca_service import alpaca_service

            # Batch symbols to avoid URL length limits
            for i in range(0, len(self.symbols), self.SNAPSHOT_BATCH_SIZE):
                batch = self.symbols[i:i + self.SNAPSHOT_BATCH_SIZE]
                snapshots = await alpaca_service.get_snapshots(batch)

                if not snapshots:
                    continue

                for symbol, snap in snapshots.items():
                    bar_data = self._snapshot_to_bar(symbol, snap)
                    if bar_data:
                        await self.message_bus.publish("market_data.bar", bar_data)
                        self._bars_received += 1
                        self._snapshots_fetched += 1
                        self._last_bar_time = time.time()

            if self._snapshots_fetched > 0:
                logger.info(
                    "Snapshot seed: %d symbols priced (session=%s)",
                    self._snapshots_fetched, self._session,
                )

        except Exception:
            logger.exception("Snapshot fetch failed")

    def _snapshot_to_bar(self, symbol: str, snap: Dict) -> Optional[Dict]:
        """Convert an Alpaca snapshot response into a bar_data dict.

        Prioritizes: minuteBar > dailyBar > latestTrade for price data.
        Always includes latest trade price for most current value.
        """
        # Try minuteBar first (most granular recent data)
        minute_bar = snap.get("minuteBar") or {}
        daily_bar = snap.get("dailyBar") or {}
        prev_daily = snap.get("prevDailyBar") or {}
        latest_trade = snap.get("latestTrade") or {}
        latest_quote = snap.get("latestQuote") or {}

        # Use minuteBar if available, else dailyBar
        source_bar = minute_bar if minute_bar.get("c") else daily_bar

        close = (
            latest_trade.get("p")
            or source_bar.get("c")
            or 0
        )
        if not close:
            return None

        return {
            "symbol": symbol,
            "timestamp": (
                latest_trade.get("t")
                or source_bar.get("t")
                or datetime.now(timezone.utc).isoformat()
            ),
            "open": float(source_bar.get("o") or close),
            "high": float(source_bar.get("h") or close),
            "low": float(source_bar.get("l") or close),
            "close": float(close),
            "volume": int(source_bar.get("v") or 0),
            "vwap": float(source_bar.get("vw") or close),
            "trade_count": int(source_bar.get("n") or 0),
            "source": f"alpaca_snapshot_{self._session}",
            # Extra fields from snapshot
            "latest_trade_price": float(latest_trade.get("p") or 0),
            "latest_trade_size": int(latest_trade.get("s") or 0),
            "bid": float(latest_quote.get("bp") or 0),
            "ask": float(latest_quote.get("ap") or 0),
            "bid_size": int(latest_quote.get("bs") or 0),
            "ask_size": int(latest_quote.get("as") or 0),
            "prev_close": float(prev_daily.get("c") or 0),
            "daily_open": float(daily_bar.get("o") or 0),
            "daily_high": float(daily_bar.get("h") or 0),
            "daily_low": float(daily_bar.get("l") or 0),
            "daily_close": float(daily_bar.get("c") or 0),
            "daily_volume": int(daily_bar.get("v") or 0),
        }

    async def _run_snapshot_poll_loop(self) -> None:
        """Poll snapshots on interval while market is closed.

        Exits when market opens (checked every poll cycle).
        """
        while self._running:
            await asyncio.sleep(self.SNAPSHOT_POLL_INTERVAL)

            # Check if market has opened — if so, exit to switch to WebSocket
            await self._check_clock()
            if self._market_is_open:
                logger.info("Market opened — exiting snapshot poll loop")
                return

            await self._fetch_and_publish_snapshots()

    async def _connect_and_stream(self, api_key: str, secret_key: str) -> None:
        """Connect to Alpaca StockDataStream and subscribe to bars."""
        try:
            from alpaca.data.live import StockDataStream
        except ImportError:
            logger.error(
                "alpaca-py not installed — run: pip install alpaca-py>=0.30.0. "
                "Falling back to snapshot polling."
            )
            await self._run_snapshot_poll_loop()
            return

        feed = os.getenv("ALPACA_FEED", "sip")
        self._stream = StockDataStream(
            api_key=api_key,
            secret_key=secret_key,
            raw_data=False,
            feed=feed,
        )

        async def _handle_bar(bar) -> None:
            """Process incoming bar and publish to MessageBus."""
            self._bars_received += 1
            self._last_bar_time = time.time()
            self._reconnect_delay = self.INITIAL_RECONNECT_DELAY

            bar_data = {
                "symbol": bar.symbol,
                "timestamp": bar.timestamp.isoformat() if hasattr(bar.timestamp, "isoformat") else str(bar.timestamp),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if hasattr(bar, "vwap") and bar.vwap else None,
                "trade_count": int(bar.trade_count) if hasattr(bar, "trade_count") and bar.trade_count else None,
                "source": "alpaca_websocket",
            }

            await self.message_bus.publish("market_data.bar", bar_data)

            if self._bars_received % 100 == 0:
                logger.info(
                    "AlpacaStream: %d bars received (latest: %s @ $%.2f)",
                    self._bars_received,
                    bar.symbol,
                    float(bar.close),
                )

        self._stream.subscribe_bars(_handle_bar, *self.symbols)
        logger.info("Alpaca WebSocket connected — subscribed to %d symbols", len(self.symbols))
        await self._stream._run_forever()

    async def _run_mock_stream(self) -> None:
        """Idle loop when Alpaca keys are unavailable — publishes no data.

        No fake market data is generated. The system simply waits for
        Alpaca API credentials to be configured.
        """
        logger.warning(
            "AlpacaStreamService running in OFFLINE mode — "
            "no market data will be published until Alpaca API keys are configured. "
            "Symbols queued: %d",
            len(self.symbols),
        )
        self._running = True
        self._start_time = time.time()

        while self._running:
            await asyncio.sleep(60)

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._stream:
            try:
                await self._stream.close()
            except Exception:
                logger.debug("Exception closing Alpaca stream during shutdown", exc_info=True)
        logger.info(
            "AlpacaStreamService stopped — %d total bars (%d from snapshots)",
            self._bars_received, self._snapshots_fetched,
        )

    def update_symbols(self, symbols: List[str]) -> None:
        """Update the symbol watchlist (takes effect on next reconnect/poll)."""
        self.symbols = symbols
        logger.info("Symbol watchlist updated: %d symbols", len(symbols))

    def get_status(self) -> Dict[str, Any]:
        """Return service status for monitoring."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "mock_mode": self._use_mock,
            "session": self._session,
            "market_is_open": self._market_is_open,
            "symbols_count": len(self.symbols),
            "bars_received": self._bars_received,
            "snapshots_fetched": self._snapshots_fetched,
            "uptime_seconds": round(uptime, 1),
            "last_bar_age_seconds": (
                round(time.time() - self._last_bar_time, 1)
                if self._last_bar_time
                else None
            ),
            "reconnect_delay": self._reconnect_delay,
            "snapshot_poll_interval": self.SNAPSHOT_POLL_INTERVAL,
        }
