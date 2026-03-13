"""Alpaca Markets API service — account, positions, orders, activities, portfolio history.
Real data only. No mock data, no fabricated numbers.

Supports both Trading API (paper-api.alpaca.markets/v2) and
Market Data API (data.alpaca.markets/v2) for 24/7 price coverage.
"""
import asyncio
import httpx
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_CACHE_TTL_SHORT = 5      # seconds — positions / account (live but prevents hammering)
_CACHE_TTL_MEDIUM = 60    # seconds — portfolio history, activities

# Map human-readable order types to Alpaca API values
_ORDER_TYPE_MAP = {
    "Market": "market",
    "market": "market",
    "Limit": "limit",
    "limit": "limit",
    "Stop": "stop",
    "stop": "stop",
    "Stop Limit": "stop_limit",
    "stop_limit": "stop_limit",
    "Trailing Stop": "trailing_stop",
    "trailing_stop": "trailing_stop",
}


class AlpacaService:
    """Service for interacting with Alpaca Markets API.
    Production mode by default. Every method returns real Alpaca data or None on failure."""

    def __init__(self):
        self.trading_mode = (getattr(settings, "TRADING_MODE", None) or "live").lower()
        if self.trading_mode not in ("paper", "live"):
            self.trading_mode = "live"

        # Determine correct API URL based on trading mode
        raw_url = settings.ALPACA_BASE_URL or "https://api.alpaca.markets"
        is_paper_url = "paper-api" in raw_url or "paper" in raw_url

        # Safety: ensure URL matches trading mode
        if self.trading_mode == "live" and is_paper_url:
            logger.warning("SAFETY: TRADING_MODE=live but URL contains 'paper': %s — forcing live URL", raw_url)
            raw_url = "https://api.alpaca.markets"
        elif self.trading_mode == "paper" and not is_paper_url and "localhost" not in raw_url:
            logger.warning("SAFETY: TRADING_MODE=paper but URL does not contain 'paper': %s — forcing paper URL", raw_url)
            raw_url = "https://paper-api.alpaca.markets"

        # Ensure base URL includes /v2 for Alpaca API v2 endpoints
        self.base_url = raw_url.rstrip("/") + "/v2" if "/v2" not in raw_url else raw_url

        # BUG FIX 1+7: Try direct settings first, then fall back to key pool's trading key.
        # If user only configured ALPACA_KEY_1/ALPACA_SECRET_1 (pool keys) but not the
        # legacy ALPACA_API_KEY/ALPACA_SECRET_KEY, the service would have empty credentials
        # and ALL Alpaca calls would return None.
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY

        if not self.api_key or not self.secret_key:
            # Fall back to key pool's trading key
            try:
                from app.services.alpaca_key_pool import get_alpaca_key_pool
                pool = get_alpaca_key_pool()
                trading_key = pool.get_key("trading")
                if trading_key and trading_key.api_key and trading_key.secret_key:
                    self.api_key = trading_key.api_key
                    self.secret_key = trading_key.secret_key
                    logger.info("AlpacaService: using key pool trading key (redacted)")
            except Exception as e:
                logger.warning("AlpacaService: key pool fallback failed: %s", e)

        if not self.api_key or not self.secret_key:
            logger.warning(
                "Alpaca API keys not configured via environment variables or key pool. "
                "Set ALPACA_API_KEY/ALPACA_SECRET_KEY or ALPACA_KEY_1/ALPACA_SECRET_1 in .env"
            )
            
        self._cache: Dict[str, Any] = {}  # key -> (timestamp, data)

        # Persistent connection pool — reuses TCP/SSL connections across calls.
        # Previous: created fresh httpx.AsyncClient per call (SSL handshake overhead).
        # Now: single pooled client with keep-alive, 50 max connections.
        self._http_client: Optional[httpx.AsyncClient] = None
        self._http_client_loop_id: Optional[int] = None

        logger.info("AlpacaService initialized: mode=%s, url=%s, configured=%s",
                    self.trading_mode, self.base_url, self._is_configured())

    # ── helpers ──────────────────────────────────────────────────────────────────

    async def validate_account_safety(self) -> Dict[str, Any]:
        """Validate that account type matches TRADING_MODE (US8 fix).

        On startup, fetches the actual Alpaca account and verifies:
        - Paper mode uses paper account URL
        - Live mode uses live account URL
        - Returns validation result dict

        If mismatch detected, logs CRITICAL warning. Caller should decide
        whether to block trading.
        """
        result = {"valid": True, "mode": self.trading_mode, "warnings": []}
        if not self._is_configured():
            result["valid"] = False
            result["warnings"].append("Alpaca API keys not configured")
            return result

        try:
            account = await self.get_account()
            if not account:
                result["valid"] = False
                result["warnings"].append("Cannot fetch Alpaca account — refusing to trade")
                return result

            # Check if base URL matches expected mode
            is_paper_url = "paper-api" in self.base_url or "paper" in self.base_url
            if self.trading_mode == "paper" and not is_paper_url:
                result["valid"] = False
                result["warnings"].append(
                    f"CRITICAL: TRADING_MODE=paper but base_url={self.base_url} is NOT paper API. "
                    "This could result in REAL MONEY trades!"
                )
                logger.critical("PAPER/LIVE MISMATCH: mode=%s url=%s", self.trading_mode, self.base_url)
            elif self.trading_mode == "live" and is_paper_url:
                result["warnings"].append(
                    f"TRADING_MODE=live but using paper API URL: {self.base_url}"
                )

            logger.info(
                "Account safety check: mode=%s, url=%s, equity=$%.2f, valid=%s",
                self.trading_mode, self.base_url,
                float(account.get("equity", 0)), result["valid"],
            )
        except Exception as e:
            result["valid"] = False
            result["warnings"].append(f"Account validation failed: {e}")
            logger.error("Account safety validation error: %s", e)

        return result

    def _is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def _cache_get(self, key: str, ttl: float) -> Any:
        entry = self._cache.get(key)
        if entry and (time.time() - entry[0]) < ttl:
            return entry[1]
        return None

    def _cache_set(self, key: str, data: Any) -> None:
        # Prevent unbounded cache growth
        if len(self._cache) > 500:
            now = time.time()
            self._cache = {k: v for k, v in self._cache.items() if (now - v[0]) < 300}
        self._cache[key] = (time.time(), data)

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create persistent connection-pooled HTTP client.

        Reuses TCP/SSL connections across calls. This avoids the overhead of
        creating a new SSL handshake on every API call (~50-100ms per call saved).
        The pool maintains up to 50 connections with keep-alive.
        """
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            current_loop_id = None

        # AsyncClient transports are loop-bound; recreate on loop changes.
        if (
            self._http_client is not None
            and not self._http_client.is_closed
            and self._http_client_loop_id is not None
            and current_loop_id is not None
            and self._http_client_loop_id != current_loop_id
        ):
            self._http_client = None
            self._http_client_loop_id = None

        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=_TIMEOUT,
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                    keepalive_expiry=30,
                ),
                headers=self._get_headers(),
            )
            self._http_client_loop_id = current_loop_id
        return self._http_client

    async def close(self) -> None:
        """Close the persistent HTTP client (call on shutdown)."""
        if self._http_client and not self._http_client.is_closed:
            try:
                await self._http_client.aclose()
            except RuntimeError:
                # Can happen during shutdown when originating loop is already closed.
                pass
            self._http_client = None
            self._http_client_loop_id = None

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        timeout: float = _TIMEOUT,
        _retries: int = 3,
    ) -> Optional[Any]:
        """Centralised HTTP caller with persistent connection pool and retry for 429/503."""
        if not self._is_configured():
            logger.warning("Alpaca API keys not configured")
            return None
        url = f"{self.base_url}{path}"

        client = self._get_http_client()

        for attempt in range(_retries + 1):
            try:
                resp = await client.request(
                    method,
                    url,
                    headers=self._get_headers(),
                    params=params,
                    json=json_body,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 204:
                    return True
                if resp.status_code in (429, 503) and attempt < _retries:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        "Alpaca %s on %s %s — retrying in %ds (attempt %d/%d)",
                        resp.status_code, method, path, wait, attempt + 1, _retries,
                    )
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code in (429, 503):
                    logger.error("Alpaca %s on %s %s — retries exhausted", resp.status_code, method, path)
                    return None
                detail = ""
                try:
                    detail = resp.json().get("message", resp.text)
                except Exception:
                    detail = resp.text
                logger.error("Alpaca %s %s -> %s: %s", method, path, resp.status_code, detail)
                if resp.status_code == 404:
                    return None
                return None  # Non-retriable HTTP error — callers handle None gracefully
            except httpx.TimeoutException:
                if attempt < _retries:
                    logger.warning("Alpaca timeout on %s %s — retrying (attempt %d/%d)", method, path, attempt + 1, _retries)
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error("Alpaca timeout on %s %s — retries exhausted", method, path)
                return None
            except httpx.RequestError as exc:
                if attempt < _retries:
                    logger.warning("Alpaca connection error on %s %s: %s — retrying", method, path, exc)
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error("Alpaca connection error on %s %s: %s — retries exhausted", method, path, exc)
                return None
        return None

    # ── account ──────────────────────────────────────────────────────────────────

    async def get_account(self) -> Optional[Dict]:
        """GET /v2/account — real account equity, buying power, margins."""
        cached = self._cache_get("account", _CACHE_TTL_SHORT)
        if cached is not None:
            return cached
        data = await self._request("GET", "/account")
        if data:
            self._cache_set("account", data)
        return data

    # ── positions ────────────────────────────────────────────────────────────────

    async def get_positions(self) -> Optional[List[Dict]]:
        """GET /v2/positions — all open positions with cost basis, P&L, current price."""
        cached = self._cache_get("positions", _CACHE_TTL_SHORT)
        if cached is not None:
            return cached
        data = await self._request("GET", "/positions")
        if data is not None:
            self._cache_set("positions", data)
        return data

    async def get_position(self, symbol: str) -> Optional[Dict]:
        """GET /v2/positions/{symbol} — single position detail."""
        return await self._request("GET", f"/positions/{symbol.upper()}")

    # ── orders ───────────────────────────────────────────────────────────────────

    async def get_orders(
        self,
        status: str = "all",
        limit: int = 50,
        direction: str = "desc",
        nested: bool = True,
    ) -> Optional[List[Dict]]:
        """GET /v2/orders — list orders with status, direction, and nested leg support.

        Unified method (previously split into two with different signatures).
        """
        return await self._request(
            "GET",
            "/orders",
            params={
                "status": status,
                "limit": str(limit),
                "direction": direction,
                "nested": str(nested).lower(),
            },
        )

    async def create_order(
        self,
        symbol: str,
        qty: Optional[str] = None,
        notional: Optional[str] = None,
        side: str = "buy",
        type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None,
        trail_price: Optional[str] = None,
        trail_percent: Optional[str] = None,
        extended_hours: bool = False,
        client_order_id: Optional[str] = None,
        order_class: Optional[str] = None,
        take_profit: Optional[Dict] = None,
        stop_loss: Optional[Dict] = None,
        # Legacy simple interface (database.py / older callers)
        order_type: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ) -> Optional[Dict]:
        """POST /v2/orders — submit any order type.

        Unified method supporting both:
        - Simple: create_order('AAPL', order_type='Market', side='buy', quantity=10)
        - Advanced: create_order('AAPL', qty='10', type='limit', limit_price='150.00',
                                 order_class='bracket', take_profit={...}, stop_loss={...})
        """
        # Legacy compatibility: map order_type -> type, quantity -> qty
        if order_type is not None:
            type = _ORDER_TYPE_MAP.get(order_type, order_type.lower())
        if quantity is not None and qty is None:
            qty = str(quantity)
        if price is not None:
            if type in ("limit", "stop_limit") and limit_price is None:
                limit_price = str(price)
            elif type in ("stop", "stop_limit") and stop_price is None:
                stop_price = str(price)

        body: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.lower(),
            "type": type,
            "time_in_force": time_in_force,
        }
        if qty is not None:
            body["qty"] = str(qty)
        if notional is not None:
            body["notional"] = str(notional)
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if stop_price is not None:
            body["stop_price"] = str(stop_price)
        if trail_price is not None:
            body["trail_price"] = str(trail_price)
        if trail_percent is not None:
            body["trail_percent"] = str(trail_percent)
        if extended_hours:
            body["extended_hours"] = True
        if client_order_id:
            body["client_order_id"] = client_order_id
        if order_class and order_class != "simple":
            body["order_class"] = order_class
        if take_profit:
            body["take_profit"] = take_profit
        if stop_loss:
            body["stop_loss"] = stop_loss

        result = await self._request("POST", "/orders", json_body=body)
        if result is None:
            raise Exception("Failed to create order — Alpaca returned no data")
        return result

    async def get_order(self, order_id: str) -> Optional[Dict]:
        """GET /v2/orders/{order_id}."""
        return await self._request("GET", f"/orders/{order_id}")

    async def replace_order(
        self,
        order_id: str,
        qty: Optional[str] = None,
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None,
        trail: Optional[str] = None,
        time_in_force: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """PATCH /v2/orders/{order_id} — replace/amend an open order."""
        body: Dict[str, Any] = {}
        if qty is not None:
            body["qty"] = str(qty)
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if stop_price is not None:
            body["stop_price"] = str(stop_price)
        if trail is not None:
            body["trail"] = str(trail)
        if time_in_force is not None:
            body["time_in_force"] = time_in_force
        if client_order_id:
            body["client_order_id"] = client_order_id
        if not body:
            return None
        return await self._request("PATCH", f"/orders/{order_id}", json_body=body)

    async def cancel_order(self, order_id: str) -> Optional[Any]:
        """DELETE /v2/orders/{order_id} — cancel a single order.

        Returns True (204 No Content) on success, None on failure.
        Callers that need bool can check: `result is not None`.
        """
        return await self._request("DELETE", f"/orders/{order_id}")

    async def cancel_all_orders(self) -> Optional[List]:
        """DELETE /v2/orders — cancel all open orders."""
        return await self._request("DELETE", "/orders")

    # ── positions management ───────────────────────────────────────────────────

    async def close_position(
        self, symbol: str, qty: Optional[str] = None, percentage: Optional[str] = None
    ) -> Optional[Dict]:
        """DELETE /v2/positions/{symbol} — close or reduce a position."""
        params: Dict[str, str] = {}
        if qty is not None:
            params["qty"] = str(qty)
        if percentage is not None:
            params["percentage"] = str(percentage)
        return await self._request("DELETE", f"/positions/{symbol.upper()}", params=params or None)

    async def close_all_positions(self, cancel_orders: bool = True) -> Optional[List]:
        """DELETE /v2/positions — liquidate all positions."""
        params = {"cancel_orders": str(cancel_orders).lower()}
        return await self._request("DELETE", "/positions", params=params)

    # ── activities (trade history) ─────────────────────────────────────────────

    async def get_activities(
        self,
        activity_types: str = "FILL",
        limit: int = 50,
        after: Optional[str] = None,
        until: Optional[str] = None,
        direction: str = "desc",
    ) -> Optional[List[Dict]]:
        """GET /v2/account/activities — real trade fills for history."""
        cache_key = f"activities:{activity_types}:{limit}"
        cached = self._cache_get(cache_key, _CACHE_TTL_MEDIUM)
        if cached is not None:
            return cached
        params: Dict[str, Any] = {
            "activity_types": activity_types,
            "page_size": limit,
            "direction": direction,
        }
        if after:
            params["after"] = after
        if until:
            params["until"] = until
        data = await self._request("GET", "/account/activities", params=params)
        if data is not None:
            self._cache_set(cache_key, data)
        return data

    # ── portfolio history ──────────────────────────────────────────────────────

    async def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: str = "1D",
        extended_hours: bool = False,
    ) -> Optional[Dict]:
        """GET /v2/account/portfolio/history — equity timeseries."""
        cache_key = f"portfolio_history:{period}:{timeframe}"
        cached = self._cache_get(cache_key, _CACHE_TTL_MEDIUM)
        if cached is not None:
            return cached
        data = await self._request(
            "GET",
            "/account/portfolio/history",
            params={
                "period": period,
                "timeframe": timeframe,
                "extended_hours": str(extended_hours).lower(),
            },
        )
        if data is not None:
            self._cache_set(cache_key, data)
        return data

    # ── asset lookup ───────────────────────────────────────────────────────────

    async def get_asset_exchange_map(self) -> Dict[str, str]:
        """Fetch all US equity assets from Alpaca → symbol:exchange map."""
        out: Dict[str, str] = {}
        if not self._is_configured():
            return out
        try:
            client = self._get_http_client()
            resp = await client.get(
                f"{self.base_url}/assets",
                params={"status": "active", "asset_class": "us_equity"},
                headers=self._get_headers(),
                timeout=60.0,
            )
            if resp.status_code != 200:
                return out
            for asset in resp.json() or []:
                sym = (asset.get("symbol") or "").strip().upper()
                ex = (asset.get("exchange") or "").strip().upper()
                if not sym:
                    continue
                if "NASDAQ" in ex:
                    out[sym] = "nasdaq"
                elif "AMEX" in ex:
                    out[sym] = "amex"
                elif "NYSE" in ex or "ARCA" in ex or "BATS" in ex:
                    out[sym] = "nyse"
                else:
                    out[sym] = "nyse"
        except Exception as exc:
            logger.warning("Alpaca get_asset_exchange_map failed: %s", exc)
        return out

    # ── Market Data API (data.alpaca.markets) ────────────────────────────────
    # BUG FIX 6: Use settings.ALPACA_DATA_URL instead of hardcoded URL.
    # This respects the user's .env configuration.
    _data_url = getattr(settings, "ALPACA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
    DATA_BASE_URL = _data_url if _data_url.endswith("/v2") else _data_url + "/v2"

    async def _data_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        timeout: float = _TIMEOUT,
    ) -> Optional[Any]:
        """HTTP caller for Alpaca Market Data API (data.alpaca.markets).

        Separate from _request() which targets the Trading API.
        Market Data API works 24/7 and returns real prices at all times.
        """
        if not self._is_configured():
            logger.warning("Alpaca API keys not configured")
            return None
        url = f"{self.DATA_BASE_URL}{path}"
        try:
            client = self._get_http_client()
            resp = await client.request(
                method,
                url,
                headers=self._get_headers(),
                params=params,
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error("Alpaca Data API %s %s -> %s", method, path, resp.status_code)
            return None
        except Exception as exc:
            logger.error("Alpaca Data API error %s %s: %s", method, path, exc)
            return None

    async def get_clock(self) -> Optional[Dict]:
        """GET /v2/clock — market open/close status and times.

        Returns: {is_open, timestamp, next_open, next_close}
        Works 24/7. Used by AlpacaStreamService for session detection.
        """
        return await self._request("GET", "/clock")

    async def get_snapshots(self, symbols: List[str]) -> Optional[Dict]:
        """GET /v2/stocks/snapshots — latest trade, quote, minute bar, daily bar.

        Works 24/7. Returns real prices for all sessions:
        pre-market, regular, after-hours, and overnight (last close).

        Returns dict keyed by symbol with:
        - latestTrade (price, size, timestamp)
        - latestQuote (bid/ask)
        - minuteBar (last completed 1-min bar)
        - dailyBar (current/last trading day OHLCV)
        - prevDailyBar (previous trading day OHLCV)
        """
        if not symbols:
            return None
        return await self._data_request(
            "GET",
            "/stocks/snapshots",
            params={"symbols": ",".join(symbols), "feed": "sip"},
        )

    async def get_latest_bars(
        self, symbols: List[str], feed: str = "sip"
    ) -> Optional[Dict]:
        """GET /v2/stocks/bars/latest — most recent bar per symbol."""
        if not symbols:
            return None
        return await self._data_request(
            "GET",
            "/stocks/bars/latest",
            params={"symbols": ",".join(symbols), "feed": feed},
        )

    async def get_latest_trades(
        self, symbols: List[str], feed: str = "sip"
    ) -> Optional[Dict]:
        """GET /v2/stocks/trades/latest — most recent trade per symbol.

        Works 24/7. Shows last traded price from any session.
        """
        if not symbols:
            return None
        return await self._data_request(
            "GET",
            "/stocks/trades/latest",
            params={"symbols": ",".join(symbols), "feed": feed},
        )

    async def get_latest_quote(self, symbol: str, feed: str = "sip") -> Optional[Dict]:
        """GET /v2/stocks/quotes/latest for a single symbol.

        Returns the quote dict (bid_price, ask_price, etc.) or None.
        Used by order_executor._get_fresh_price and outcome_tracker.
        """
        result = await self.get_latest_quotes([symbol.upper()], feed=feed)
        if not result or not isinstance(result, dict):
            return None
        # Alpaca returns {"SYMBOL": { "bp", "ap", ... } } or {"quotes": {...}}
        if symbol.upper() in result:
            return result[symbol.upper()]
        quotes = result.get("quotes", result)
        return quotes.get(symbol.upper()) if isinstance(quotes, dict) else None

    async def get_latest_quotes(
        self, symbols: List[str], feed: str = "sip"
    ) -> Optional[Dict]:
        """GET /v2/stocks/quotes/latest — most recent NBBO quote per symbol.

        Works 24/7. Shows current bid/ask spread.
        """
        if not symbols:
            return None
        return await self._data_request(
            "GET",
            "/stocks/quotes/latest",
            params={"symbols": ",".join(symbols), "feed": feed},
        )

    # ── bars (OHLCV) ──────────────────────────────────────────────────────────
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 14,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """GET /v2/bars — historical OHLCV bars from Alpaca Data API.
        Uses data.alpaca.markets (not the trading API).
        """
        if not self._is_configured():
            return None
        _du = getattr(settings, "ALPACA_DATA_URL", "https://data.alpaca.markets").rstrip("/")
        data_url = _du if _du.endswith("/v2") else _du + "/v2"
        url = f"{data_url}/stocks/{symbol.upper()}/bars"
        params = {"timeframe": timeframe, "limit": str(limit)}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            client = self._get_http_client()
            resp = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error("Alpaca bars %s -> %s", symbol, resp.status_code)
                return None
            data = resp.json()
            return data.get("bars", [])
        except Exception as exc:
            logger.error("Alpaca get_bars error for %s: %s", symbol, exc)
            return None

    # ── Batch Multi-Symbol Bars (Algo Trader Plus optimization) ───────────────

    async def get_multi_bars(
        self,
        symbols: List[str],
        timeframe: str = "1Day",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 60,
        feed: str = "sip",
    ) -> Optional[Dict[str, list]]:
        """GET /v2/stocks/bars — multi-symbol bars in a single request.

        Alpaca's multi-bars endpoint accepts up to ~200 symbols per call,
        returning OHLCV data for all of them. This is 50-200x more efficient
        than calling get_bars() per symbol.

        With Algo Trader Plus (10K req/min), we can fetch 200 symbols x 60 bars
        in one request instead of 200 separate calls.

        Returns dict keyed by symbol: {"AAPL": [{bar}, ...], "MSFT": [...]}
        """
        if not symbols:
            return {}
        params: Dict[str, Any] = {
            "symbols": ",".join(s.upper() for s in symbols),
            "timeframe": timeframe,
            "limit": limit,
            "feed": feed,
            "adjustment": "split",
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        result = await self._data_request("GET", "/stocks/bars", params=params)
        if result and "bars" in result:
            return result["bars"]
        return result

    async def get_multi_snapshots(
        self,
        symbols: List[str],
        feed: str = "sip",
    ) -> Optional[Dict]:
        """GET /v2/stocks/snapshots — batch snapshots for many symbols.

        Wrapper around get_snapshots that handles splitting into batches
        of 100 symbols and fetching concurrently. Returns merged dict.
        """
        import asyncio

        if not symbols:
            return {}

        batch_size = 100  # Alpaca allows ~200 but URL length limits apply
        batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

        results = await asyncio.gather(
            *[self.get_snapshots(batch) for batch in batches],
            return_exceptions=True,
        )

        merged = {}
        for r in results:
            if isinstance(r, dict):
                merged.update(r)
        return merged

    async def get_latest_multi_trades(
        self,
        symbols: List[str],
        feed: str = "sip",
    ) -> Optional[Dict]:
        """GET /v2/stocks/trades/latest — latest trade for multiple symbols.

        Returns dict keyed by symbol with latest trade info.
        """
        if not symbols:
            return {}
        params = {
            "symbols": ",".join(s.upper() for s in symbols),
            "feed": feed,
        }
        return await self._data_request("GET", "/stocks/trades/latest", params=params)

    async def get_most_actives(
        self,
        by: str = "volume",
        top: int = 20,
    ) -> Optional[list]:
        """GET /v1beta1/screener/stocks/most-actives — Alpaca screener.

        Returns the most active stocks by volume or trade count.
        Useful for discovery scanning without using a full universe scan.
        Available on Algo Trader Plus plan.
        """
        params = {"by": by, "top": top}
        # Screener uses v1beta1, not v2
        data_url = self.DATA_BASE_URL.replace("/v2", "")
        url = f"{data_url}/v1beta1/screener/stocks/most-actives"
        try:
            client = self._get_http_client()
            resp = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("most_actives", [])
            logger.debug("Alpaca screener most-actives -> %s", resp.status_code)
            return None
        except Exception as exc:
            logger.debug("Alpaca screener error: %s", exc)
            return None

    async def get_market_movers(
        self,
        market_type: str = "stocks",
        top: int = 20,
    ) -> Optional[Dict]:
        """GET /v1beta1/screener/{market_type}/movers — top gainers/losers.

        Returns dict with 'gainers' and 'losers' lists.
        Available on Algo Trader Plus plan.
        """
        data_url = self.DATA_BASE_URL.replace("/v2", "")
        url = f"{data_url}/v1beta1/screener/{market_type}/movers"
        try:
            client = self._get_http_client()
            resp = await client.get(
                url,
                headers=self._get_headers(),
                params={"top": top},
                timeout=_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.debug("Alpaca movers -> %s", resp.status_code)
            return None
        except Exception as exc:
            logger.debug("Alpaca movers error: %s", exc)
            return None


# ── singleton ────────────────────────────────────────────────────────────────────
alpaca_service = AlpacaService()
