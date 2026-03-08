"""Unusual Whales API service for options flow alerts."""

import logging
import time
from typing import Any, Dict, List

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
                await bus.publish("unusual_whales.flow", {
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
        data = r.json() if r.content else []
        try:
            bus = get_message_bus()
            if bus._running:
                await bus.publish("unusual_whales.flow", {
                    "type": "congress_trades",
                    "alerts": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass
        return data

    async def get_insider_trades(self) -> Any:
        """Fetch insider trading activity (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/insider/trading"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        data = r.json() if r.content else []
        try:
            bus = get_message_bus()
            if bus._running:
                await bus.publish("unusual_whales.flow", {
                    "type": "insider_trades",
                    "alerts": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass
        return data

    async def get_darkpool_flow(self) -> Any:
        """Fetch dark pool transaction data (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/darkpool/recent"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        data = r.json() if r.content else []
        try:
            bus = get_message_bus()
            if bus._running:
                await bus.publish("unusual_whales.flow", {
                    "type": "darkpool_flow",
                    "alerts": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass
        return data
