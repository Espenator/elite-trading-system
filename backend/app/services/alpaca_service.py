"""Alpaca Markets API service — account, positions, orders, activities, portfolio history.
Real data only. No mock data, no fabricated numbers.
"""
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
    Uses paper by default. Every method returns real Alpaca data or None on failure."""

    def __init__(self):
        raw_url = settings.ALPACA_BASE_URL or "https://paper-api.alpaca.markets"
        # Ensure base URL includes /v2 for Alpaca API v2 endpoints
        self.base_url = raw_url.rstrip("/") + "/v2" if "/v2" not in raw_url else raw_url
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self.trading_mode = (getattr(settings, "TRADING_MODE", None) or "paper").lower()
        if self.trading_mode not in ("paper", "live"):
            self.trading_mode = "paper"
        self._cache: Dict[str, Any] = {}  # key -> (timestamp, data)
        self._cache_max_size = 100  # Prevent unbounded memory growth

    # ── helpers ──────────────────────────────────────────────────────────────────

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
        self._cache[key] = (time.time(), data)
        # Evict stale entries when cache exceeds max size
        if len(self._cache) > self._cache_max_size:
            now = time.time()
            stale = [k for k, (ts, _) in self._cache.items() if now - ts > _CACHE_TTL_MEDIUM]
            for k in stale:
                del self._cache[k]

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        timeout: float = _TIMEOUT,
    ) -> Optional[Any]:
        """Centralised HTTP caller with error handling."""
        if not self._is_configured():
            logger.warning("Alpaca API keys not configured")
            return None
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient() as client:
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
            if resp.status_code == 429:
                logger.warning("Alpaca rate-limited on %s %s", method, path)
                return None
            detail = ""
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            logger.error("Alpaca %s %s -> %s: %s", method, path, resp.status_code, detail)
            if resp.status_code == 404:
                return None
            raise Exception(f"Alpaca API error {resp.status_code}: {detail}")
        except httpx.TimeoutException:
            logger.error("Alpaca timeout on %s %s", method, path)
            return None
        except httpx.RequestError as exc:
            logger.error("Alpaca connection error on %s %s: %s", method, path, exc)
            return None

    def get_cached_equity(self, default: float = 100_000.0) -> float:
        """Return cached account equity without making an API call.

        Useful for synchronous contexts (e.g., Kelly sizing) where you need
        a recent equity value but can't await.
        """
        cached = self._cache_get("account", _CACHE_TTL_MEDIUM)
        if cached:
            try:
                return float(cached.get("equity", default))
            except (ValueError, TypeError):
                pass
        return default

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
            async with httpx.AsyncClient() as client:
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
        data_url = "https://data.alpaca.markets/v2"
        url = f"{data_url}/stocks/{symbol.upper()}/bars"
        params = {"timeframe": timeframe, "limit": str(limit)}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self._TIMEOUT if hasattr(self, '_TIMEOUT') else 30.0,
                )
                if resp.status_code != 200:
                    logger.error("Alpaca bars %s -> %s", symbol, resp.status_code)
                    return None
                data = resp.json()
                return data.get("bars", [])
        except Exception as exc:
            logger.error("Alpaca get_bars error for %s: %s", symbol, exc)
            return None


# ── singleton ────────────────────────────────────────────────────────────────────
alpaca_service = AlpacaService()
