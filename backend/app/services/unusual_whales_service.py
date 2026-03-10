"""Unusual Whales API service for options flow alerts."""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)


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


# Global service instance for module-level function access
_service_instance = None


def _get_service() -> UnusualWhalesService:
    """Get or create the global UnusualWhalesService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UnusualWhalesService()
    return _service_instance


# Module-level wrapper functions for council agents
# These provide per-symbol data access with symbol filtering


async def get_insider_trades(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch insider trades filtered by symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of insider trade dicts for the specified symbol
    """
    service = _get_service()
    try:
        all_trades = await service.get_insider_trades()
        if not all_trades:
            return []

        # Filter by symbol (case-insensitive)
        symbol_upper = symbol.upper()
        if isinstance(all_trades, list):
            return [
                trade for trade in all_trades
                if str(trade.get("ticker", "") or trade.get("symbol", "")).upper() == symbol_upper
            ]
        elif isinstance(all_trades, dict) and "data" in all_trades:
            # Handle paginated response format
            data = all_trades.get("data", [])
            return [
                trade for trade in data
                if str(trade.get("ticker", "") or trade.get("symbol", "")).upper() == symbol_upper
            ]
        return []
    except Exception as e:
        logger.warning("Failed to fetch insider trades for %s: %s", symbol, e)
        return []


async def get_dark_pool_flow(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch dark pool flow data filtered by symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        Dict with dark pool flow data for the symbol, or None if not found
    """
    service = _get_service()
    try:
        all_flow = await service.get_darkpool_flow()
        if not all_flow:
            return None

        # Filter by symbol (case-insensitive)
        symbol_upper = symbol.upper()
        if isinstance(all_flow, list):
            # Find the first matching entry
            for entry in all_flow:
                if str(entry.get("ticker", "") or entry.get("symbol", "")).upper() == symbol_upper:
                    return entry
        elif isinstance(all_flow, dict) and "data" in all_flow:
            # Handle paginated response format
            data = all_flow.get("data", [])
            for entry in data:
                if str(entry.get("ticker", "") or entry.get("symbol", "")).upper() == symbol_upper:
                    return entry
        return None
    except Exception as e:
        logger.warning("Failed to fetch dark pool flow for %s: %s", symbol, e)
        return None


async def get_options_chain(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch options chain data for a symbol from flow alerts.

    Note: Unusual Whales flow alerts contain options data, not a full options chain.
    This function filters flow alerts by the specified symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of options flow alerts for the specified symbol
    """
    service = _get_service()
    try:
        all_alerts = await service.get_flow_alerts()
        if not all_alerts:
            return []

        # Filter by symbol (case-insensitive)
        symbol_upper = symbol.upper()
        if isinstance(all_alerts, list):
            return [
                alert for alert in all_alerts
                if str(alert.get("ticker", "") or alert.get("symbol", "")).upper() == symbol_upper
            ]
        elif isinstance(all_alerts, dict) and "data" in all_alerts:
            # Handle paginated response format
            data = all_alerts.get("data", [])
            return [
                alert for alert in data
                if str(alert.get("ticker", "") or alert.get("symbol", "")).upper() == symbol_upper
            ]
        return []
    except Exception as e:
        logger.warning("Failed to fetch options chain for %s: %s", symbol, e)
        return []


async def get_institutional_flow(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch institutional flow/trading activity filtered by symbol.

    Note: This uses congress trades as a proxy for institutional activity.
    Actual institutional flow would require 13F filings or other data sources.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of institutional trades for the specified symbol
    """
    service = _get_service()
    try:
        all_trades = await service.get_congress_trades()
        if not all_trades:
            return []

        # Filter by symbol (case-insensitive)
        symbol_upper = symbol.upper()
        if isinstance(all_trades, list):
            return [
                trade for trade in all_trades
                if str(trade.get("ticker", "") or trade.get("symbol", "")).upper() == symbol_upper
            ]
        elif isinstance(all_trades, dict) and "data" in all_trades:
            # Handle paginated response format
            data = all_trades.get("data", [])
            return [
                trade for trade in data
                if str(trade.get("ticker", "") or trade.get("symbol", "")).upper() == symbol_upper
            ]
        return []
    except Exception as e:
        logger.warning("Failed to fetch institutional flow for %s: %s", symbol, e)
        return []
