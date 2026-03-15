"""Alpaca WebSocket streaming service with 24/5 market data coverage.

Connects to Alpaca's StockDataStream for real-time bars and publishes
each bar to the MessageBus topic 'market_data.bar'. Supports:
- Regular hours (9:30-16:00 ET): live 1-min bars via WebSocket
- Pre-market (4:00-9:30 ET): snapshot polling every 30s
- After-hours (16:00-20:00 ET): snapshot polling every 30s
- Overnight (20:00-4:00 ET): snapshot polling every 60s (24/5 active)
- Weekend: snapshot seeding on startup, then idle

On startup, always fetches snapshots so the system has current prices
regardless of market session. During all active sessions (Sun 8 PM - Fri 8 PM),
polls snapshots so the trading pipeline has fresh price data.

When WebSocket fails (connection limit, library issues), falls back to
snapshot polling that works regardless of market open/closed state.

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


def _get_et_hour() -> int:
    """Get current hour in US/Eastern, handling DST correctly."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/New_York")).hour


class AlpacaStreamService:
    """Alpaca WebSocket client with snapshot fallback for 24/7 coverage."""

    MAX_RECONNECT_DELAY = 60  # seconds
    INITIAL_RECONNECT_DELAY = 2  # seconds
    SNAPSHOT_POLL_INTERVAL = 30  # seconds between snapshot polls (pre/post market)
    OVERNIGHT_POLL_INTERVAL = 60  # seconds between snapshot polls (overnight 24/5)
    WEEKEND_POLL_INTERVAL = 300   # seconds between snapshot polls (weekend — data is stale)
    SNAPSHOT_BATCH_SIZE = 50  # symbols per snapshot API call
    # When Alpaca returns "connection limit exceeded", fall back after this many failures
    CONNECTION_LIMIT_FALLBACK_AFTER = int(
        os.getenv("ALPACA_STREAM_FALLBACK_AFTER_LIMIT", "1")
    )
    # E4: Circuit breaker — permanent REST fallback after N consecutive WS failures
    WS_CIRCUIT_BREAKER_THRESHOLD = int(
        os.getenv("ALPACA_WS_CIRCUIT_BREAKER_THRESHOLD", "10")
    )

    def __init__(self, message_bus, symbols: Optional[List[str]] = None, api_key: str = None, secret_key: str = None):
        self.message_bus = message_bus
        self._api_key = api_key
        self._secret_key = secret_key
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
        self._session = "unknown"  # "pre", "regular", "post", "overnight", "weekend"
        self._snapshot_task: Optional[asyncio.Task] = None
        self._connection_limit_failures = 0
        self._ws_fallback_to_snapshots = False  # True when WS fails and we poll instead
        # E4: Consecutive WS reconnection failure counter
        self._consecutive_ws_failures = 0
        self._ws_circuit_open = False  # True = permanently on REST until manual reset

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
            api_key = self._api_key or getattr(_settings, "ALPACA_API_KEY", "") or os.getenv("ALPACA_API_KEY", "")
            secret_key = self._secret_key or getattr(_settings, "ALPACA_SECRET_KEY", "") or os.getenv("ALPACA_SECRET_KEY", "")
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

        # Seed snapshots in background so the HTTP server stays responsive.
        # The snapshot seed publishes 1000+ bar events which cascade into
        # signal processing and would otherwise starve the event loop.
        asyncio.create_task(self._fetch_and_publish_snapshots())

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

                if self._market_is_open and not self._ws_fallback_to_snapshots:
                    # Market open: use WebSocket for real-time bars
                    logger.info("Market OPEN — switching to WebSocket streaming")
                    await self._connect_and_stream(api_key, secret_key)
                else:
                    # Market closed OR WebSocket failed: poll snapshots
                    reason = "WS fallback" if self._ws_fallback_to_snapshots else f"session={self._session}"
                    logger.info(
                        "Polling snapshots every %ds (%s)",
                        self.SNAPSHOT_POLL_INTERVAL, reason,
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
                    self._ws_fallback_to_snapshots = True
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
                            "Falling back to snapshot polling (real data, every %ds).",
                            self._connection_limit_failures,
                            self.SNAPSHOT_POLL_INTERVAL,
                        )
                        self._ws_fallback_to_snapshots = True
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
                self._consecutive_ws_failures += 1
                logger.exception(
                    "AlpacaStreamService error (failure %d/%d) — reconnecting in %ds",
                    self._consecutive_ws_failures,
                    self.WS_CIRCUIT_BREAKER_THRESHOLD,
                    self._reconnect_delay,
                )

                # E4: Circuit breaker — after N consecutive failures, stop trying
                if self._consecutive_ws_failures >= self.WS_CIRCUIT_BREAKER_THRESHOLD:
                    self._ws_circuit_open = True
                    self._ws_fallback_to_snapshots = True
                    msg = (
                        f"WebSocket circuit breaker OPEN after "
                        f"{self._consecutive_ws_failures} consecutive failures. "
                        f"Falling back to REST polling permanently. "
                        f"Manual reset required via reset_ws_circuit_breaker()."
                    )
                    logger.critical(msg)
                    await self._slack_alert(msg, level="critical")
                    # E4: Publish circuit breaker event to MessageBus
                    if self.message_bus:
                        try:
                            await self.message_bus.publish("alert.websocket_circuit_open", {
                                "consecutive_failures": self._consecutive_ws_failures,
                                "threshold": self.WS_CIRCUIT_BREAKER_THRESHOLD,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        except Exception:
                            pass  # Don't let alert publishing prevent fallback
                    continue

                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY
                )

    async def _check_clock(self) -> None:
        """Query Alpaca /v2/clock and update session state.

        Uses SessionClock for 24/5 session awareness. Overnight is now
        an active polling session (not idle) for 24/5 trading support.
        """
        try:
            from app.services.alpaca_service import alpaca_service
            from app.services.data_swarm.session_clock import get_session_clock, TradingSession

            clock = await alpaca_service.get_clock()
            session_clock = get_session_clock()
            current_session = session_clock.get_current_session()

            if clock:
                self._market_is_open = clock.get("is_open", False)
            else:
                self._market_is_open = False

            # Map TradingSession to legacy session string for status/logging
            _session_map = {
                TradingSession.REGULAR: "regular",
                TradingSession.PRE_MARKET: "pre",
                TradingSession.AFTER_HOURS: "post",
                TradingSession.OVERNIGHT: "overnight",
                TradingSession.WEEKEND: "weekend",
            }
            self._session = _session_map.get(current_session, "unknown")

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
            import asyncio
            from app.services.alpaca_service import alpaca_service

            # Session-aware symbol reduction: weekend=6 crypto/metals,
            # overnight=15 liquid names, market hours=full universe
            try:
                from app.core.market_clock import get_active_symbols
                active_symbols = get_active_symbols(self.symbols)
            except Exception:
                active_symbols = self.symbols

            # Build all snapshot batches, then fetch in parallel.
            # With Algo Trader Plus (10K req/min, 50 concurrent), we can safely
            # fire all batches simultaneously instead of sequentially.
            batches = [
                active_symbols[i:i + self.SNAPSHOT_BATCH_SIZE]
                for i in range(0, len(active_symbols), self.SNAPSHOT_BATCH_SIZE)
            ]

            # Fetch all batches concurrently
            snapshot_results = await asyncio.gather(
                *[alpaca_service.get_snapshots(batch) for batch in batches],
                return_exceptions=True,
            )

            for snapshots in snapshot_results:
                if isinstance(snapshots, Exception) or not snapshots:
                    continue
                for symbol, snap in snapshots.items():
                    bar_data = self._snapshot_to_bar(symbol, snap)
                    if bar_data:
                        bar_data["_source"] = "snapshot"
                        await self.message_bus.publish("market_data.bar", bar_data)
                        self._bars_received += 1
                        self._snapshots_fetched += 1
                        self._last_bar_time = time.time()

                # Real delay between batches so event loop can serve HTTP
                await asyncio.sleep(0.2)

            if self._snapshots_fetched > 0:
                logger.info(
                    "Snapshot seed: %d symbols priced of %d active (session=%s)",
                    self._snapshots_fetched, len(active_symbols), self._session,
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

    def _get_poll_interval(self) -> int:
        """Return session-appropriate snapshot polling interval.

        Market hours: 30s (real-time tracking)
        Overnight: 60s (conserve rate limits, still fresh)
        Weekend: 300s (5 min — data is stale, just monitor for news-driven moves)
        """
        if self._session == "weekend":
            return self.WEEKEND_POLL_INTERVAL
        if self._session == "overnight":
            return self.OVERNIGHT_POLL_INTERVAL
        return self.SNAPSHOT_POLL_INTERVAL

    async def _run_snapshot_poll_loop(self) -> None:
        """Poll snapshots on interval. Works in ALL market states.

        24/5 aware: overnight is now an active polling session (60s interval)
        instead of idle. Weekend is the only truly inactive state.

        When in WS fallback mode: polls continuously regardless of market state.
        When market is closed: polls until market opens, then exits so main loop
        can switch to WebSocket.
        """
        while self._running:
            # Fetch snapshots FIRST, then sleep (ensures immediate data on entry)
            await self._fetch_and_publish_snapshots()
            poll_interval = self._get_poll_interval()
            await asyncio.sleep(poll_interval)

            # Check if we should exit this loop
            await self._check_clock()
            if self._market_is_open and not self._ws_fallback_to_snapshots:
                # Market opened and WS is available — exit to switch to WebSocket
                logger.info("Market opened — exiting snapshot poll loop for WebSocket")
                return
            if self._session == "weekend" and not self._ws_fallback_to_snapshots:
                # Weekend: no trading, no need to poll aggressively
                logger.info("Weekend — reducing poll frequency")
            # Otherwise keep polling (WS fallback or active 24/5 session)

    async def _connect_and_stream(self, api_key: str, secret_key: str) -> None:
        """Connect to Alpaca StockDataStream and subscribe to bars."""
        try:
            from alpaca.data.live import StockDataStream
        except ImportError:
            logger.error(
                "alpaca-py not installed — run: pip install alpaca-py>=0.30.0. "
                "Falling back to snapshot polling."
            )
            self._ws_fallback_to_snapshots = True
            return

        feed_str = os.getenv("ALPACA_FEED", "sip")
        # StockDataStream expects the DataFeed enum, not a plain string
        try:
            from alpaca.data.enums import DataFeed
            feed = DataFeed(feed_str)
        except Exception:
            from alpaca.data.enums import DataFeed
            feed = DataFeed.SIP
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

            # GPU Channel 5: Feed bars to GPU bar aggregator for streaming indicators
            try:
                from app.modules.ml_engine.gpu_bar_aggregator import get_bar_aggregator
                get_bar_aggregator().ingest(bar_data)
            except Exception:
                pass  # Never break bar processing

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
        # E4: Reset failure counter on successful connection
        self._consecutive_ws_failures = 0

        # Guard against the Alpaca library's internal tight-reconnect loop:
        # When "connection limit exceeded" occurs, the library catches the error
        # internally and retries immediately without backoff, starving the event
        # loop. We run _run_forever in a task and cancel it if we detect rapid
        # failures (many reconnect attempts in a short window).
        _original_auth = self._stream._auth

        async def _guarded_auth():
            try:
                return await _original_auth()
            except ValueError as e:
                if "connection limit" in str(e).lower():
                    # Re-raise immediately to break out of _run_forever.
                    # The outer start() loop handles fallback to snapshots.
                    raise
                raise

        self._stream._auth = _guarded_auth
        try:
            await self._stream._run_forever()
        finally:
            self._stream._auth = _original_auth

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

    def reset_ws_circuit_breaker(self) -> Dict[str, Any]:
        """Manually reset the WebSocket circuit breaker.

        E4: After the circuit breaker trips (10 consecutive WS failures),
        the service permanently falls back to REST polling. Call this to
        allow WebSocket reconnection attempts again.
        """
        was_open = self._ws_circuit_open
        self._ws_circuit_open = False
        self._ws_fallback_to_snapshots = False
        self._consecutive_ws_failures = 0
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._connection_limit_failures = 0
        logger.info(
            "WebSocket circuit breaker RESET (was %s)",
            "OPEN" if was_open else "CLOSED",
        )
        return {
            "previous_state": "open" if was_open else "closed",
            "current_state": "closed",
            "message": "Circuit breaker reset — WebSocket will attempt reconnection on next cycle",
        }

    async def _slack_alert(self, message: str, level: str = "info") -> None:
        """Send alert via Slack (best-effort, never blocks)."""
        try:
            from app.services.slack_notification_service import send_slack_message
            prefix = {"critical": "🚨", "warning": "⚠️"}.get(level, "ℹ️")
            await send_slack_message(f"{prefix} AlpacaStream: {message}")
        except Exception:
            logger.debug("Slack alert failed (non-fatal)")

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
            "ws_fallback": self._ws_fallback_to_snapshots,
            "ws_circuit_breaker_open": self._ws_circuit_open,
            "consecutive_ws_failures": self._consecutive_ws_failures,
            "ws_circuit_breaker_threshold": self.WS_CIRCUIT_BREAKER_THRESHOLD,
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
