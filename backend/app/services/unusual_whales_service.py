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
                # Also publish to canonical unusual_whales.flow topic (0c)
                await bus.publish("unusual_whales.flow", {
                    "type": "options_flow",
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
                await bus.publish("unusual_whales.congress", {
                    "type": "congress_trades",
                    "trades": data,
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
                await bus.publish("unusual_whales.insider", {
                    "type": "insider_trades",
                    "trades": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass

        return data

    async def get_top_flow_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch top flow alerts by premium, limited to `limit` results.
        Returns list of alert dicts with ticker, premium, put_call fields.
        Used by FlowHunterScout.
        """
        try:
            data = await self.get_flow_alerts()
            if isinstance(data, dict):
                items = data.get("data") or data.get("items") or data.get("alerts") or []
            elif isinstance(data, list):
                items = data
            else:
                return []
            # Normalize and sort by premium descending
            results = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                results.append(item)
            results.sort(
                key=lambda x: float(x.get("premium", 0) or x.get("total_premium", 0) or 0),
                reverse=True,
            )
            return results[:limit]
        except Exception as e:
            logger.debug("get_top_flow_alerts error: %s", e)
            return []

    async def get_congressional_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch congressional trades, limited to `limit` results.
        Wraps get_congress_trades() with normalization for CongressScout.
        """
        try:
            data = await self.get_congress_trades()
            if isinstance(data, dict):
                items = data.get("data") or data.get("trades") or data.get("items") or []
            elif isinstance(data, list):
                items = data
            else:
                return []
            return [item for item in items if isinstance(item, dict)][:limit]
        except Exception as e:
            logger.debug("get_congressional_trades error: %s", e)
            return []

    async def get_gex_levels(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Fetch GEX (Gamma Exposure) levels for top symbols.
        Used by GammaScout for gamma squeeze detection.
        """
        try:
            self._validate_api_key()
            url = f"{self.base_url}/stock/gamma-exposure"
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers=self._headers())
            r.raise_for_status()
            data = r.json() if r.content else []
            if isinstance(data, dict):
                items = data.get("data") or data.get("items") or data.get("levels") or []
            elif isinstance(data, list):
                items = data
            else:
                return []

            try:
                bus = get_message_bus()
                if bus._running:
                    await bus.publish("perception.gex", {
                        "type": "gex_levels",
                        "levels": items[:limit],
                        "source": "unusual_whales_service",
                        "timestamp": time.time(),
                    })
            except Exception:
                pass

            return [item for item in items if isinstance(item, dict)][:limit]
        except Exception as e:
            logger.debug("get_gex_levels error: %s", e)
            return []

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
                await bus.publish("unusual_whales.darkpool", {
                    "type": "darkpool_flow",
                    "transactions": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass

        return data


# ---------------------------------------------------------------------------
# Singleton getter — used by scouts and other services
# ---------------------------------------------------------------------------
_unusual_whales_service: Optional[UnusualWhalesService] = None


def get_unusual_whales_service() -> UnusualWhalesService:
    """Return singleton UnusualWhalesService instance."""
    global _unusual_whales_service
    if _unusual_whales_service is None:
        _unusual_whales_service = UnusualWhalesService()
    return _unusual_whales_service
