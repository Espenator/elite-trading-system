"""FRED (Federal Reserve Economic Data) API service."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class FredService:
    """Service for interacting with FRED API (series/observations)."""

    def __init__(self):
        self.base_url = (
            getattr(settings, "FRED_BASE_URL", None)
            or "https://api.stlouisfed.org/fred"
        ).rstrip("/")
        self.api_key = getattr(settings, "FRED_API_KEY", None) or ""

    def _validate_api_key(self) -> None:
        if not (self.api_key or "").strip():
            raise ValueError(
                "FRED_API_KEY is not set. Set it in .env (free key at fred.stlouisfed.org/docs/api/api_key.html)."
            )

    async def get_observations(
        self,
        series_id: str,
        limit: int = 1,
        sort_order: str = "desc",
        file_type: str = "json",
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest observations for a FRED series.

        Args:
            series_id: FRED series ID (e.g. CPIAUCSL, UNRATE).
            limit: Max number of observations to return.
            sort_order: 'asc' or 'desc'.
            file_type: 'json' or 'xml'.

        Returns:
            List of observation dicts with keys such as date, value.
        """
        self._validate_api_key()
        url = f"{self.base_url}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key.strip(),
            "file_type": file_type,
            "sort_order": sort_order,
            "limit": limit,
        }
        logger.debug("FRED get_observations: series_id=%s limit=%s", series_id, limit)
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        observations = (data.get("observations") or [])[:limit]
        return observations

    async def get_latest_value(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the single latest observation for a series (value and date).
        Returns None if no valid observation.
        """
        obs = await self.get_observations(series_id, limit=1)
        if not obs or obs[0].get("value") == ".":
            return None
        return {"date": obs[0].get("date"), "value": obs[0].get("value")}

    async def get_latest_macro_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of key macro indicators: VIX, 10Y Treasury, 2Y Treasury.
        Used by MacroScout for regime detection and yield curve analysis.

        Returns dict with keys: vix, treasury_10y, treasury_2y.
        Values default to 0 if unavailable.
        """
        snapshot: Dict[str, Any] = {"vix": 0, "treasury_10y": 0, "treasury_2y": 0}

        # FRED series IDs for key macro indicators
        series_map = {
            "vix": "VIXCLS",           # CBOE Volatility Index
            "treasury_10y": "DGS10",   # 10-Year Treasury Constant Maturity Rate
            "treasury_2y": "DGS2",     # 2-Year Treasury Constant Maturity Rate
        }

        for key, series_id in series_map.items():
            try:
                obs = await self.get_latest_value(series_id)
                if obs and obs.get("value"):
                    snapshot[key] = float(obs["value"])
            except Exception as e:
                logger.debug("FRED macro snapshot %s (%s) error: %s", key, series_id, e)

        return snapshot


# ---------------------------------------------------------------------------
# Singleton getter — used by scouts and other services
# ---------------------------------------------------------------------------
_fred_service: Optional[FredService] = None


def get_fred_service() -> FredService:
    """Return singleton FredService instance."""
    global _fred_service
    if _fred_service is None:
        _fred_service = FredService()
    return _fred_service
