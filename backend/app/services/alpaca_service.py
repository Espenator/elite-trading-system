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


class AlpacaService:
    """Service for interacting with Alpaca Markets API.
    Uses paper by default. Every method returns real Alpaca data or None on failure."""

    def __init__(self):
        self.base_url = (
            settings.ALPACA_BASE_URL or "https://paper-api.alpaca.markets/v2"
        )
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self.trading_mode = (getattr(settings, "TRADING_MODE", None) or "paper").lower()
        if self.trading_mode not in ("paper", "live"):
            self.trading_mode = "paper"
        self._cache: Dict[str, Any] = {}  # key -> (timestamp, data)

    # ── helpers ──────────────────────────────────────────────────────────

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

    # ── account ──────────────────────────────────────────────────────────

    async def get_account(self) -> Optional[Dict]:
        """GET /v2/account — real account equity, buying power, margins."""
        cached = self._cache_get("account", _CACHE_TTL_SHORT)
        if cached is not None:
            return cached
        data = await self._request("GET", "/account")
        if data:
            self._cache_set("account", data)
        return data

    # ── positions ────────────────────────────────────────────────────────

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

    # ── orders ───────────────────────────────────────────────────────────

    async def get_orders(
        self,
        status: str = "all",
        limit: int = 50,
        direction: str = "desc",
    ) -> Optional[List[Dict]]:
        """GET /v2/orders — open / closed / all orders."""
        return await self._request(
            "GET",
            "/orders",
            params={"status": status, "limit": limit, "direction": direction},
        )

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
    ) -> Dict:
        """POST /v2/orders — create a real order."""
        mapping = {
            "Market": "market", "Limit": "limit", "Stop": "stop",
            "Stop Limit": "stop_limit", "Trailing Stop": "trailing_stop",
        }
        alpaca_type = mapping.get(order_type, "market")
        order_data: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "qty": str(quantity),
            "side": side.lower(),
            "type": alpaca_type,
            "time_in_force": time_in_force,
        }
        if alpaca_type in ("limit", "stop_limit") and price:
            order_data["limit_price"] = str(price)
        if alpaca_type in ("stop", "stop_limit") and stop_price:
            order_data["stop_price"] = str(stop_price)
        elif alpaca_type in ("stop", "stop_limit") and price:
            order_data["stop_price"] = str(price)

        result = await self._request("POST", "/orders", json_body=order_data)
        if result is None:
            raise Exception("Failed to create order — Alpaca returned no data")
        return result

    async def get_order(self, order_id: str) -> Optional[Dict]:
        """GET /v2/orders/{order_id}."""
        return await self._request("GET", f"/orders/{order_id}")

    async def cancel_order(self, order_id: str) -> bool:
        """DELETE /v2/orders/{order_id}."""
        result = await self._request("DELETE", f"/orders/{order_id}")
        return result is True

    # ── activities (trade history) ───────────────────────────────────────

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

    # ── portfolio history ────────────────────────────────────────────────

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

    # ── asset lookup ─────────────────────────────────────────────────────

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


# ── singleton ────────────────────────────────────────────────────────────
alpaca_service = AlpacaService()
