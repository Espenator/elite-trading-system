"""OpenClaw Bridge Service - Fetches scan data from OpenClaw GitHub Gist.

Reads the JSON payload produced by OpenClaw's api_data_bridge.py,
caches results for 15 minutes, and exposes typed accessors for
the Embodier Trader frontend.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes
_cache: Dict[str, Any] = {
    "data": None,
    "fetched_at": 0.0,
}


class OpenClawBridgeService:
    """Fetches and caches OpenClaw scan data from a GitHub Gist."""

    def __init__(self):
        self.gist_id: str = settings.OPENCLAW_GIST_ID
        self.gist_token: str = settings.OPENCLAW_GIST_TOKEN
        self.gist_filename: str = "openclaw_scan_latest.json"
        self._http = httpx.AsyncClient(timeout=20.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_cache_valid(self) -> bool:
        if _cache["data"] is None:
            return False
        return (time.time() - _cache["fetched_at"]) < _CACHE_TTL_SECONDS

    async def _fetch_gist(self) -> Optional[Dict]:
        """Fetch the Gist JSON from GitHub API. Uses token if set; on 401 retries without auth for public gists."""
        if not self.gist_id:
            logger.warning("[OPENCLAW] OPENCLAW_GIST_ID not configured")
            return None

        url = f"https://api.github.com/gists/{self.gist_id}"
        accept = "application/vnd.github.v3+json"

        async def do_get(auth_headers: dict):
            resp = await self._http.get(url, headers={**auth_headers, "Accept": accept})
            resp.raise_for_status()
            return resp.json()

        # First try with token if configured
        headers = {}
        if self.gist_token and self.gist_token.strip():
            headers["Authorization"] = f"token {self.gist_token.strip()}"

        try:
            gist_json = await do_get(headers)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning(
                    "[OPENCLAW] Gist 401 Unauthorized. "
                    "OPENCLAW_GIST_TOKEN may be invalid, expired, or the Gist is private. "
                    "Retrying without token for public Gist..."
                )
                try:
                    gist_json = await do_get({})
                    logger.info("[OPENCLAW] Fetched using public Gist (no token)")
                except httpx.HTTPStatusError as retry_exc:
                    logger.error(
                        "[OPENCLAW] Gist HTTP %s. For a private Gist, use a valid GitHub token with 'gist' scope.",
                        retry_exc.response.status_code,
                    )
                    return None
            else:
                logger.error("[OPENCLAW] Gist HTTP %s", exc.response.status_code)
                return None
        except Exception as exc:
            logger.error("[OPENCLAW] Gist fetch error: %s", exc)
            return None

        try:
            file_data = gist_json.get("files", {}).get(self.gist_filename)
            if not file_data:
                logger.error(
                    "[OPENCLAW] Gist file '%s' not found",
                    self.gist_filename,
                )
                return None
            content = json.loads(file_data["content"])
            logger.info(
                "[OPENCLAW] Fetched scan: %s candidates, regime=%s",
                len(content.get("top_candidates", [])),
                content.get("regime", {}).get("state", "?"),
            )
            return content
        except Exception as exc:
            logger.error("[OPENCLAW] Gist parse error: %s", exc)
            return None

    async def _get_data(self) -> Optional[Dict]:
        """Return cached data or fetch fresh from Gist."""
        if self._is_cache_valid():
            return _cache["data"]
        data = await self._fetch_gist()
        if data is not None:
            _cache["data"] = data
            _cache["fetched_at"] = time.time()
        return _cache["data"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_scan_results(self) -> Optional[Dict]:
        """Return the full scan payload."""
        return await self._get_data()

    async def get_regime(self) -> Dict:
        """Return current regime status and details."""
        data = await self._get_data()
        if not data:
            return {"state": "UNKNOWN", "details": None, "readme": None}
        regime = data.get("regime", {})
        macro = data.get("macro_context", {})
        readme = (
            regime.get("readme")
            or regime.get("summary")
            or regime.get("text")
            or data.get("regime_readme")
            or ""
        )
        if readme and not isinstance(readme, str):
            readme = str(readme)
        return {
            "state": regime.get("state", "UNKNOWN"),
            "vix": regime.get("vix"),
            "hmm_confidence": regime.get("hmm_confidence"),
            "hurst": regime.get("hurst"),
            "macro_context": macro,
            "readme": readme or None,
            "scan_date": data.get("scan_date"),
            "timestamp": data.get("timestamp"),
        }

    async def get_top_candidates(self, n: int = 10) -> List[Dict]:
        """Return top N candidates sorted by composite score."""
        data = await self._get_data()
        if not data:
            return []
        candidates = data.get("top_candidates", [])
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get("composite_score", 0),
            reverse=True,
        )
        return sorted_candidates[:n]

    async def get_whale_flow(self) -> List[Dict]:
        """Return whale flow alerts from last scan."""
        data = await self._get_data()
        if not data:
            return []
        return data.get("whale_flow_alerts", [])

    async def get_fom_expected_moves(self) -> Dict:
        """Return FOM expected move levels."""
        data = await self._get_data()
        if not data:
            return {}
        return data.get("fom_expected_moves", {})

    async def get_health(self) -> Dict:
        """Return bridge health / status information."""
        data = await self._get_data()
        is_connected = data is not None
        candidate_count = len(data.get("top_candidates", [])) if data else 0
        last_scan_ts = data.get("timestamp") if data else None
        cache_age_s = (
            round(time.time() - _cache["fetched_at"], 1)
            if _cache["fetched_at"]
            else None
        )
        return {
            "connected": is_connected,
            "gist_id_configured": bool(self.gist_id),
            "last_scan_timestamp": last_scan_ts,
            "candidate_count": candidate_count,
            "cache_age_seconds": cache_age_s,
            "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        }

    async def force_refresh(self) -> Dict:
        """Force a cache refresh and return health."""
        _cache["fetched_at"] = 0.0
        await self._get_data()
        return await self.get_health()

    async def get_llm_summary(self) -> Optional[str]:
        """Return LLM-generated scan summary if available."""
        data = await self._get_data()
        if not data:
            return None
        return data.get("llm_summary")

    async def get_llm_candidate_analysis(self) -> Optional[Dict]:
        """Return LLM candidate analysis if available."""
        data = await self._get_data()
        if not data:
            return None
        return data.get("llm_candidate_analysis")

    async def get_sector_rankings(self) -> List[Dict]:
        """Return sector rotation rankings."""
        data = await self._get_data()
        if not data:
            return []
        return data.get("sector_rankings", [])


# ---------------------------------------------------------------------------
# Global service instance
# ---------------------------------------------------------------------------
openclaw_bridge = OpenClawBridgeService()
