"""Alpaca WebSocket streaming service.

Connects to Alpaca's StockDataStream for real-time 1-min bars and publishes
each bar to the MessageBus topic 'market_data.bar'. Supports auto-reconnect
and graceful shutdown.

Requires env vars: ALPACA_API_KEY, ALPACA_SECRET_KEY
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlpacaStreamService:
    """Alpaca WebSocket client that publishes bars to MessageBus."""

    MAX_RECONNECT_DELAY = 60  # seconds
    INITIAL_RECONNECT_DELAY = 2  # seconds
    # When Alpaca returns "connection limit exceeded", fall back to mock after this many failures (0 = never)
    CONNECTION_LIMIT_FALLBACK_AFTER = int(
        os.getenv("ALPACA_STREAM_FALLBACK_AFTER_LIMIT", "1")
    )

    def __init__(self, message_bus, symbols: Optional[List[str]] = None):
        self.message_bus = message_bus
        self.symbols = symbols or [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "TSLA",
            "META",
            "SPY",
            "QQQ",
            "IWM",
        ]
        self._stream = None
        self._running = False
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._bars_received = 0
        self._last_bar_time: Optional[float] = None
        self._start_time: Optional[float] = None
        self._use_mock = False
        self._connection_limit_failures = 0

    async def start(self) -> None:
        """Start streaming with auto-reconnect loop."""
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")

        if not api_key or not secret_key:
            logger.warning(
                "ALPACA_API_KEY / ALPACA_SECRET_KEY not set — "
                "starting in MOCK mode (simulated bars every 60s)"
            )
            self._use_mock = True
            await self._run_mock_stream()
            return

        self._running = True
        self._start_time = time.time()
        logger.info(
            "AlpacaStreamService starting for %d symbols: %s",
            len(self.symbols),
            ", ".join(self.symbols[:5]) + ("..." if len(self.symbols) > 5 else ""),
        )

        while self._running:
            try:
                await self._connect_and_stream(api_key, secret_key)
            except asyncio.CancelledError:
                logger.info("AlpacaStreamService cancelled")
                break
            except TypeError as e:
                if "extra_headers" in str(e) or "create_connection" in str(e):
                    logger.warning(
                        "Alpaca websocket failed (incompatible websockets library). "
                        'Install: pip install "websockets>=10.4,<14" then restart. Using MOCK stream.'
                    )
                    self._use_mock = True
                    await self._run_mock_stream()
                    return
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
                            "Only one WebSocket per account is allowed. Falling back to MOCK stream. "
                            "To free the slot: close other apps/tabs using the same Alpaca API key, or set "
                            "DISABLE_ALPACA_DATA_STREAM=1 if you use OpenClaw --stream separately.",
                            self._connection_limit_failures,
                        )
                        self._use_mock = True
                        await self._run_mock_stream()
                        return
                    logger.warning(
                        "Alpaca data stream: %s. Only one websocket per account is allowed. "
                        "Close other apps/tabs using the same API key, then retry. Backing off %ds.",
                        e,
                        self.MAX_RECONNECT_DELAY,
                    )
                    self._reconnect_delay = self.MAX_RECONNECT_DELAY
                    await asyncio.sleep(self._reconnect_delay)
                    continue
                raise
            except Exception:
                logger.exception(
                    "Alpaca stream disconnected — reconnecting in %ds",
                    self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY
                )

    async def _connect_and_stream(self, api_key: str, secret_key: str) -> None:
        """Connect to Alpaca StockDataStream and subscribe to bars."""
        try:
            from alpaca.data.live import StockDataStream
        except ImportError:
            logger.error(
                "alpaca-py not installed — run: pip install alpaca-py>=0.30.0. "
                "Falling back to mock stream."
            )
            self._use_mock = True
            await self._run_mock_stream()
            return

        self._stream = StockDataStream(
            api_key=api_key,
            secret_key=secret_key,
            raw_data=False,
        )

        async def _handle_bar(bar) -> None:
            """Process incoming bar and publish to MessageBus."""
            self._bars_received += 1
            self._last_bar_time = time.time()
            self._reconnect_delay = self.INITIAL_RECONNECT_DELAY  # reset on success

            bar_data = {
                "symbol": bar.symbol,
                "timestamp": (
                    bar.timestamp.isoformat()
                    if hasattr(bar.timestamp, "isoformat")
                    else str(bar.timestamp)
                ),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if hasattr(bar, "vwap") and bar.vwap else None,
                "trade_count": (
                    int(bar.trade_count)
                    if hasattr(bar, "trade_count") and bar.trade_count
                    else None
                ),
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
        logger.info(
            "Alpaca WebSocket connected — subscribed to %d symbols", len(self.symbols)
        )
        await self._stream._run_forever()

    async def _run_mock_stream(self) -> None:
        """Simulated bar stream for development without Alpaca keys."""
        import random

        logger.info("Mock stream started for %d symbols", len(self.symbols))
        self._running = True
        self._start_time = time.time()

        mock_prices = {s: round(random.uniform(50, 500), 2) for s in self.symbols}

        while self._running:
            for symbol in self.symbols:
                price = mock_prices[symbol]
                change = round(random.uniform(-0.5, 0.5), 2)
                new_price = round(max(1.0, price + change), 2)
                mock_prices[symbol] = new_price

                bar_data = {
                    "symbol": symbol,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "open": price,
                    "high": round(max(price, new_price) + abs(change) * 0.5, 2),
                    "low": round(min(price, new_price) - abs(change) * 0.5, 2),
                    "close": new_price,
                    "volume": random.randint(10000, 500000),
                    "vwap": round((price + new_price) / 2, 2),
                    "trade_count": random.randint(50, 2000),
                    "source": "mock",
                }
                await self.message_bus.publish("market_data.bar", bar_data)
                self._bars_received += 1
                self._last_bar_time = time.time()

            await asyncio.sleep(60)  # Mock bars every 60s

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._stream:
            try:
                await self._stream.close()
            except Exception:
                pass
        logger.info(
            "AlpacaStreamService stopped — %d total bars received",
            self._bars_received,
        )

    def update_symbols(self, symbols: List[str]) -> None:
        """Update the symbol watchlist (takes effect on next reconnect)."""
        self.symbols = symbols
        logger.info("Symbol watchlist updated: %d symbols", len(symbols))

    def get_status(self) -> Dict[str, Any]:
        """Return service status for monitoring."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "mock_mode": self._use_mock,
            "symbols_count": len(self.symbols),
            "bars_received": self._bars_received,
            "uptime_seconds": round(uptime, 1),
            "last_bar_age_seconds": (
                round(time.time() - self._last_bar_time, 1)
                if self._last_bar_time
                else None
            ),
            "reconnect_delay": self._reconnect_delay,
        }
