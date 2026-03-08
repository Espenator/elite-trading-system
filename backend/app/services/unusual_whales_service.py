"""Unusual Whales API service for options flow alerts."""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)

# Global cache for latest unusual whales alerts (updated via MessageBus)
_latest_alerts_cache: Dict[str, Any] = {}
_cache_timestamp: float = 0.0


class UnusualWhalesService:
    """Service for Unusual Whales options flow API."""

    def __init__(self):
        self.base_url = (
            getattr(settings, "UNUSUAL_WHALES_BASE_URL", None)
            or "https://api.unusualwhales.com/api"
        ).rstrip("/")
        self.api_key = (getattr(settings, "UNUSUAL_WHALES_API_KEY", None) or "").strip()
        flow_path = (getattr(settings, "UNUSUAL_WHALES_FLOW_PATH", None) or "").strip()
        self.flow_path = flow_path or "/option-trades/flow-alerts"
        if not self.flow_path.startswith("/"):
            self.flow_path = "/" + self.flow_path

    def _validate_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "UNUSUAL_WHALES_API_KEY is not set. Set it in .env for options flow (see api.unusualwhales.com/docs)."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def get_flow_alerts(self) -> Any:
        """
        Fetch flow alerts from the configured flow path.
        Returns raw response JSON (list or dict with count/total/items).
        """
        self._validate_api_key()
        url = f"{self.base_url}{self.flow_path}"
        logger.debug("Unusual Whales get_flow_alerts: %s", url)
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        if not r.content:
            return []
        data = r.json()

        # Publish to MessageBus so downstream consumers (council, screeners) receive flow data
        try:
            bus = get_message_bus()
            if bus._running:
                await bus.publish("perception.unusualwhales", {
                    "type": "unusual_whales_alerts",
                    "alerts": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass

        return data

    async def get_flow_count(self) -> int:
        """
        Get number of flow entries from the last response (for logging).
        Returns 0 if response is not a list or has no count/total.
        """
        try:
            data = await self.get_flow_alerts()
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                return int(data.get("count") or data.get("total") or 0)
            return 0
        except Exception:
            return 0

    async def get_congress_trades(self) -> Any:
        """Fetch congress trading activity (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/congress/trading"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []

    async def get_insider_trades(self) -> Any:
        """Fetch insider trading activity (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/insider/trading"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []

    async def get_darkpool_flow(self) -> Any:
        """Fetch dark pool transaction data (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/darkpool/recent"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []


def update_alerts_cache(event_data: Dict[str, Any]) -> None:
    """Update global alerts cache from MessageBus event.

    Called by MessageBus subscriber in main.py to store latest UW alerts.
    """
    global _latest_alerts_cache, _cache_timestamp
    alerts = event_data.get("alerts", [])
    timestamp = event_data.get("timestamp", time.time())

    # Store alerts by symbol for easy lookup
    if isinstance(alerts, list):
        for alert in alerts:
            if isinstance(alert, dict) and "ticker" in alert:
                symbol = alert["ticker"]
                _latest_alerts_cache[symbol] = {
                    **alert,
                    "_cached_at": timestamp,
                }
        _cache_timestamp = timestamp
        logger.debug("Updated UnusualWhales cache: %d symbols", len(_latest_alerts_cache))
    elif isinstance(alerts, dict):
        # Handle dict response format
        items = alerts.get("items", []) or alerts.get("data", [])
        for alert in items:
            if isinstance(alert, dict) and "ticker" in alert:
                symbol = alert["ticker"]
                _latest_alerts_cache[symbol] = {
                    **alert,
                    "_cached_at": timestamp,
                }
        _cache_timestamp = timestamp
        logger.debug("Updated UnusualWhales cache: %d symbols", len(_latest_alerts_cache))


def get_alerts_for_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get cached unusual whales alerts for a specific symbol.

    Returns None if no alerts available or cache is stale (>5 min).
    """
    if not _latest_alerts_cache:
        return None

    # Check cache age
    cache_age = time.time() - _cache_timestamp
    if cache_age > 300:  # 5 minutes
        return None

    return _latest_alerts_cache.get(symbol)


def get_all_cached_alerts() -> Dict[str, Any]:
    """Get all cached alerts with metadata."""
    return {
        "alerts": dict(_latest_alerts_cache),
        "cache_timestamp": _cache_timestamp,
        "cache_age_seconds": time.time() - _cache_timestamp if _cache_timestamp > 0 else None,
        "symbol_count": len(_latest_alerts_cache),
    }
