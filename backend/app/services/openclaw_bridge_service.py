"""OpenClaw Bridge Service v2 - Real-time Signal Ingestion + Gist Fallback.

v2.0 (2026.2.22 Architecture):
    - Real-time POST /openclaw/signals ingestion from bridge_sender.py (PC1 -> PC2)
    - Sub-second signal delivery via in-memory ring buffer
    - WebSocket broadcast to Agent Command Center UI
    - Gist polling retained as fallback for scan snapshots
    - Token-authenticated bridge with HMAC signature verification
    - Signal deduplication and provenance tracking
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Set

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ===========================================================================
# Configuration
# ===========================================================================
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes for Gist fallback
_REALTIME_BUFFER_SIZE = 500   # Ring buffer for last 500 signals
_SIGNAL_DEDUP_WINDOW = 60     # Dedup window in seconds
_BRIDGE_TOKEN = getattr(settings, 'OPENCLAW_BRIDGE_TOKEN', '') or ''
_BRIDGE_SECRET = getattr(settings, 'OPENCLAW_BRIDGE_SECRET', '') or ''

# Gist polling cache (legacy fallback)
_cache: Dict[str, Any] = {
    "data": None,
    "fetched_at": 0.0,
}

# Real-time signal ring buffer
_realtime_signals: Deque[Dict[str, Any]] = deque(maxlen=_REALTIME_BUFFER_SIZE)
_signal_ids_seen: Set[str] = set()
_realtime_stats: Dict[str, Any] = {
    "signals_received": 0,
    "signals_accepted": 0,
    "signals_rejected": 0,
    "signals_deduplicated": 0,
    "last_signal_at": None,
    "bridge_connected_since": None,
    "avg_latency_ms": 0.0,
    "latency_samples": [],
}

# WebSocket subscribers for real-time broadcast
_ws_subscribers: List[Callable] = []


# ===========================================================================
# Security: HMAC Signature Verification
# ===========================================================================
def verify_bridge_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from bridge_sender."""
    if not _BRIDGE_SECRET:
        return True  # No secret configured = open mode
    expected = hmac.new(
        _BRIDGE_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def validate_bridge_token(token: str) -> bool:
    """Validate bearer token from bridge_sender."""
    if not _BRIDGE_TOKEN:
        return True  # No token configured = open mode
    return token == _BRIDGE_TOKEN


class OpenClawBridgeService:
    """Hybrid bridge: real-time signal ingestion + Gist scan fallback.

    Real-time path (primary):
        bridge_sender.py POST -> ingest_signals() -> ring buffer -> WS broadcast

    Gist path (fallback):
        api_data_bridge.py -> GitHub Gist -> _fetch_gist() -> cache
    """

    def __init__(self):
        # Gist config (legacy fallback)
        self.gist_id: str = getattr(settings, 'OPENCLAW_GIST_ID', '') or ''
        self.gist_token: str = getattr(settings, 'OPENCLAW_GIST_TOKEN', '') or ''
        self.gist_filename: str = "openclaw_scan_latest.json"
        self._http = httpx.AsyncClient(timeout=20.0)

        # Real-time state
        self._running = False
        self._bridge_id = str(uuid.uuid4())[:8]

        logger.info(
            "[OPENCLAW] BridgeService v2 initialized (bridge_id=%s, "
            "gist=%s, token_auth=%s, hmac_auth=%s)",
            self._bridge_id,
            'configured' if self.gist_id else 'none',
            'enabled' if _BRIDGE_TOKEN else 'open',
            'enabled' if _BRIDGE_SECRET else 'open',
        )

    # ==================================================================
    # REAL-TIME SIGNAL INGESTION (PC1 -> PC2 bridge)
    # ==================================================================
    async def ingest_signals(
        self,
        signals: List[Dict[str, Any]],
        run_id: Optional[str] = None,
        regime: Optional[Dict[str, Any]] = None,
        universe: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest real-time signals from bridge_sender.py POST.

        This is the hot path - must be sub-second.
        """
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        accepted = 0
        rejected = 0
        deduplicated = 0

        for sig in signals:
            _realtime_stats["signals_received"] += 1

            # Generate deterministic signal ID for dedup
            sig_key = f"{sig.get('symbol', '')}:{sig.get('direction', '')}:{sig.get('score', '')}:{run_id or ''}"
            sig_id = hashlib.md5(sig_key.encode()).hexdigest()[:12]

            # Dedup check
            if sig_id in _signal_ids_seen:
                deduplicated += 1
                _realtime_stats["signals_deduplicated"] += 1
                continue

            # Validate minimum fields
            if not sig.get("symbol") or not sig.get("direction"):
                rejected += 1
                _realtime_stats["signals_rejected"] += 1
                logger.warning("[OPENCLAW] Rejected signal: missing symbol/direction")
                continue

            # Enrich signal with provenance
            enriched = {
                **sig,
                "_signal_id": sig_id,
                "_run_id": run_id,
                "_ingested_at": now_iso,
                "_latency_ms": round((now - sig.get("_sent_at", now)) * 1000, 2) if sig.get("_sent_at") else None,
                "_regime": regime,
                "_source": "openclaw_bridge",
            }

            # Track latency
            if enriched["_latency_ms"] is not None:
                samples = _realtime_stats["latency_samples"]
                samples.append(enriched["_latency_ms"])
                if len(samples) > 100:
                    samples.pop(0)
                _realtime_stats["avg_latency_ms"] = round(
                    sum(samples) / len(samples), 2
                )

            # Add to ring buffer
            _realtime_signals.appendleft(enriched)
            _signal_ids_seen.add(sig_id)
            accepted += 1
            _realtime_stats["signals_accepted"] += 1

        # Prune old dedup IDs (keep last N)
        if len(_signal_ids_seen) > _REALTIME_BUFFER_SIZE * 2:
            _signal_ids_seen.clear()
            for s in _realtime_signals:
                _signal_ids_seen.add(s.get("_signal_id", ""))

        _realtime_stats["last_signal_at"] = now_iso
        if not _realtime_stats["bridge_connected_since"]:
            _realtime_stats["bridge_connected_since"] = now_iso

        # Broadcast to WebSocket subscribers
        if accepted > 0:
            await self._broadcast_signals(
                [s for s in list(_realtime_signals)[:accepted]]
            )

        result = {
            "run_id": run_id,
            "accepted": accepted,
            "rejected": rejected,
            "deduplicated": deduplicated,
            "buffer_size": len(_realtime_signals),
            "ingested_at": now_iso,
        }
        logger.info(
            "[OPENCLAW] Ingested %d signals (rejected=%d, dedup=%d, run=%s)",
            accepted, rejected, deduplicated, run_id,
        )
        return result

    async def _broadcast_signals(self, signals: List[Dict]) -> None:
        """Broadcast new signals to all WebSocket subscribers."""
        if not _ws_subscribers:
            return
        payload = {
            "type": "openclaw_signals",
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        dead = []
        for i, callback in enumerate(_ws_subscribers):
            try:
                await callback(payload)
            except Exception as exc:
                logger.warning("[OPENCLAW] WS subscriber %d failed: %s", i, exc)
                dead.append(i)
        for i in reversed(dead):
            _ws_subscribers.pop(i)

    def subscribe_ws(self, callback: Callable) -> None:
        """Register a WebSocket callback for real-time signal events."""
        _ws_subscribers.append(callback)
        logger.info("[OPENCLAW] WS subscriber added (total=%d)", len(_ws_subscribers))

    def unsubscribe_ws(self, callback: Callable) -> None:
        """Remove a WebSocket callback."""
        try:
            _ws_subscribers.remove(callback)
        except ValueError:
            pass

    # ==================================================================
    # REAL-TIME QUERY METHODS
    # ==================================================================
    def get_realtime_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get most recent real-time signals from ring buffer."""
        return list(_realtime_signals)[:limit]

    def get_realtime_stats(self) -> Dict[str, Any]:
        """Get real-time bridge statistics."""
        return {
            **_realtime_stats,
            "buffer_size": len(_realtime_signals),
            "buffer_capacity": _REALTIME_BUFFER_SIZE,
            "ws_subscribers": len(_ws_subscribers),
            "bridge_id": self._bridge_id,
            "latency_samples": None,  # Don't expose raw samples
        }

    def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Look up a signal by its dedup ID."""
        for sig in _realtime_signals:
            if sig.get("_signal_id") == signal_id:
                return sig
        return None

    # ==================================================================
    # GIST-BASED SCAN DATA (fallback / batch scans)
    # ==================================================================
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

    # ==================================================================
    # PUBLIC API (backward-compatible + enhanced)
    # ==================================================================
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
        """Return bridge health / status information (enhanced with real-time stats)."""
        data = await self._get_data()
        is_connected = data is not None
        candidate_count = len(data.get("top_candidates", [])) if data else 0
        last_scan_ts = data.get("timestamp") if data else None
        cache_age_s = (
            round(time.time() - _cache["fetched_at"], 1)
            if _cache["fetched_at"]
            else None
        )
        rt_stats = self.get_realtime_stats()

        return {
            "connected": is_connected,
            "gist_id_configured": bool(self.gist_id),
            "last_scan_timestamp": last_scan_ts,
            "candidate_count": candidate_count,
            "cache_age_seconds": cache_age_s,
            "cache_ttl_seconds": _CACHE_TTL_SECONDS,
            # Real-time bridge stats
            "realtime": {
                "bridge_id": rt_stats["bridge_id"],
                "signals_received": rt_stats["signals_received"],
                "signals_accepted": rt_stats["signals_accepted"],
                "buffer_size": rt_stats["buffer_size"],
                "avg_latency_ms": rt_stats["avg_latency_ms"],
                "last_signal_at": rt_stats["last_signal_at"],
                "bridge_connected_since": rt_stats["bridge_connected_since"],
                "ws_subscribers": rt_stats["ws_subscribers"],
            },
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

    # ================================================================== #
    # MEMORY INTELLIGENCE PARSERS
    # ================================================================== #
    async def get_memory_status(self) -> dict:
        """Parses memory health, quality score (IQ), and agent rankings from the Gist bridge data.
        Feeds the Agent Command Center UI with the swarm's current learning state."""
        try:
            gist_data = await self._get_data()
            if not gist_data:
                return {}

            memory_section = gist_data.get("memory", {})
            if not memory_section:
                return {
                    "memory_iq": 0,
                    "status": "waiting_for_data",
                    "message": "Memory stats not yet published to bridge."
                }

            return {
                "memory_iq": memory_section.get("quality_score", {}).get("memory_iq", 0),
                "quality_metrics": memory_section.get("quality_score", {}),
                "expectancy_overview": memory_section.get("expectancy_summary", {}),
                "top_agents": memory_section.get("agent_rankings", [])[:5],
                "health": memory_section.get("health", {})
            }
        except Exception as e:
            logger.error(f"[BridgeService] Error fetching memory status: {e}")
            return {}

    async def get_memory_recall(self, ticker: str, score: float = 50.0, regime: str = "UNKNOWN") -> dict:
        """Parses the 3-stage recall pipeline data for a specific ticker from the Gist bridge."""
        try:
            gist_data = await self._get_data()
            if not gist_data:
                return {}

            recalls_section = gist_data.get("recalls", {})
            ticker_data = recalls_section.get(ticker.upper())
            if ticker_data:
                return ticker_data

            return {
                "ticker": ticker.upper(),
                "recent_context": [],
                "semantic_memory": [],
                "structured_facts": {
                    "signals": 0,
                    "outcomes": 0,
                    "total_pnl_pct": 0.0,
                    "avg_score": 0.0
                },
                "learned_rules": [],
                "note": "Awaiting direct recall sync from OpenClaw."
            }
        except Exception as e:
            logger.error(f"[BridgeService] Error fetching memory recall for {ticker}: {e}")
            return {}


# ===========================================================================
# Global service instance
# ===========================================================================
openclaw_bridge = OpenClawBridgeService()
