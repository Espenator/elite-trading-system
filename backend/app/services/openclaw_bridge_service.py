"""
OpenClaw Bridge Service v2.1 — Real-time Signal Ingestion + Memory Intelligence

Architecture (2026.2.24):
  PC1 (OpenClaw scanner)
    └─ bridge_sender.py  ──POST──►  PC2 (Embodier Trader)
                                      └─ this file: openclaw_bridge_service.py
                                           ├─ Ring buffer (sub-second hot path)
                                           ├─ WebSocket broadcast → Agent Command Center
                                           ├─ SQLite persistence → openclaw_db
                                           ├─ Phase 1: Semantic RAG auto-embed
                                           ├─ Phase 2: Core Memory injection
                                           └─ Phase 3: GraphRAG auto-graph

Real-time path (primary):
  bridge_sender.py POST → ingest_signals() → dedup → ring buffer → WS broadcast
                                            → openclaw_db.insert_signals() (SQLite + vectors + graph)

Gist path (fallback / batch snapshots):
  api_data_bridge.py → GitHub Gist → _fetch_gist() → cache

Memory Intelligence hooks (v2.1):
  Every ingested signal is also:
    1) Embedded into ChromaDB vector store  (Phase 1 — Semantic RAG)
    2) Written as graph nodes + edges        (Phase 3 — GraphRAG)
  Recall / search responses inject:
    3) Core Memory context block             (Phase 2 — Letta-style)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ===========================================================================
# Configuration
# ===========================================================================
_CACHE_TTL_SECONDS = 15 * 60          # 15 min for Gist fallback
_REALTIME_BUFFER_SIZE = 500            # Ring buffer for last 500 signals
_SIGNAL_DEDUP_WINDOW = 60             # Dedup window in seconds
_BRIDGE_TOKEN = getattr(settings, "OPENCLAW_BRIDGE_TOKEN", "") or ""
_BRIDGE_SECRET = getattr(settings, "OPENCLAW_BRIDGE_SECRET", "") or ""

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
    # Memory Intelligence counters (Phase 1 + 3)
    "semantic_embeds": 0,
    "semantic_embed_failures": 0,
    "graph_writes": 0,
    "graph_write_failures": 0,
}

# WebSocket subscribers for real-time broadcast
_ws_subscribers: List[Callable] = []


# ===========================================================================
# Security: HMAC Signature Verification
# ===========================================================================
def verify_bridge_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from bridge_sender."""
    if not _BRIDGE_SECRET:
        logger.warning("OPENCLAW_BRIDGE_SECRET not set — rejecting all bridge requests")
        return False
    expected = hmac.new(
        _BRIDGE_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def validate_bridge_token(token: str) -> bool:
    """Validate bearer token from bridge_sender."""
    if not _BRIDGE_TOKEN:
        logger.warning("OPENCLAW_BRIDGE_TOKEN not set — rejecting all bridge requests")
        return False
    return secrets.compare_digest(token, _BRIDGE_TOKEN)


# ===========================================================================
# Main Service
# ===========================================================================
class OpenClawBridgeService:
    """Hybrid bridge: real-time signal ingestion + Gist scan fallback.

    Real-time path (primary):
        bridge_sender.py POST → ingest_signals() → ring buffer → WS broadcast
    Gist path (fallback):
        api_data_bridge.py → GitHub Gist → _fetch_gist() → cache

    Memory Intelligence (v2.1):
        Every ingested signal is also:
          Phase 1 → embedded into ChromaDB vector store via openclaw_db
          Phase 3 → written as graph nodes/edges via openclaw_db
        Recall / search responses inject:
          Phase 2 → Core Memory context block from openclaw_db
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self):
        # Gist config (legacy fallback)
        self.gist_id: str = getattr(settings, "OPENCLAW_GIST_ID", "") or ""
        self.gist_token: str = getattr(settings, "OPENCLAW_GIST_TOKEN", "") or ""
        self.gist_filename: str = "openclaw_scan_latest.json"
        self._http = httpx.AsyncClient(timeout=20.0)

        # Real-time state
        self._running = False
        self._bridge_id = str(uuid.uuid4())[:8]

        # Lazy DB handle (set on first use to avoid circular import)
        self._db = None

        logger.info(
            "[OPENCLAW] BridgeService v2.1 initialized (bridge_id=%s, "
            "gist=%s, token_auth=%s, hmac_auth=%s)",
            self._bridge_id,
            "configured" if self.gist_id else "none",
            "enabled" if _BRIDGE_TOKEN else "open",
            "enabled" if _BRIDGE_SECRET else "open",
        )

    # ------------------------------------------------------------------
    # Lazy DB accessor (avoids circular import at module load time)
    # ------------------------------------------------------------------
    @property
    def db(self):
        """Return the openclaw_db singleton, importing on first access."""
        if self._db is None:
            from app.services.openclaw_db import openclaw_db
            self._db = openclaw_db
        return self._db

    # ==================================================================
    # REAL-TIME SIGNAL INGESTION (hot path)
    # Enhanced: Phase 1 (Semantic) + Phase 3 (Graph) hooks
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

        Hot path — must stay sub-second for the ring-buffer / WS broadcast.
        Memory Intelligence writes are fire-and-forget (non-blocking).

        Returns dict with accepted/rejected/deduplicated/embedded/graphed counts.
        """
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        accepted = 0
        rejected = 0
        deduplicated = 0
        embedded = 0
        graphed = 0
        db_persisted = 0

        # ----- Persist ingest header to SQLite via openclaw_db -----
        ingest_id: Optional[int] = None
        try:
            ingest_id = self.db.insert_ingest(
                run_id=run_id or f"bridge_{self._bridge_id}_{int(now)}",
                timestamp=now_iso,
                regime=regime,
                universe=universe,
                signal_count=len(signals),
                payload_hash=hashlib.md5(
                    json.dumps(signals, sort_keys=True, default=str).encode()
                ).hexdigest(),
            )
        except Exception as exc:
            # Duplicate run_id → already ingested (dedup at ingest level)
            if "UNIQUE constraint" in str(exc):
                logger.debug("[OPENCLAW] Duplicate ingest run_id=%s — skipping", run_id)
                return {
                    "run_id": run_id,
                    "accepted": 0,
                    "rejected": 0,
                    "deduplicated": len(signals),
                    "embedded": 0,
                    "graphed": 0,
                    "note": "duplicate_run_id",
                }
            logger.warning("[OPENCLAW] Ingest header write failed: %s", exc)

        # ----- Per-signal processing -----
        accepted_signals: List[Dict[str, Any]] = []

        for sig in signals:
            _realtime_stats["signals_received"] += 1

            # -- Deterministic dedup key --
            sig_key = (
                f"{sig.get('symbol', '')}:{sig.get('direction', '')}:"
                f"{sig.get('score', '')}:{run_id or ''}"
            )
            sig_id = hashlib.md5(sig_key.encode()).hexdigest()[:12]

            # -- Dedup check --
            if sig_id in _signal_ids_seen:
                deduplicated += 1
                _realtime_stats["signals_deduplicated"] += 1
                continue

            # -- Validate minimum fields --
            if not sig.get("symbol") or not sig.get("direction"):
                rejected += 1
                _realtime_stats["signals_rejected"] += 1
                logger.warning("[OPENCLAW] Rejected signal: missing symbol/direction")
                continue

            # -- Enrich with provenance --
            sent_at = sig.get("_sent_at")
            latency_ms = (
                round((now - sent_at) * 1000, 2) if sent_at else None
            )
            enriched: Dict[str, Any] = {
                **sig,
                "_signal_id": sig_id,
                "_run_id": run_id,
                "_ingested_at": now_iso,
                "_latency_ms": latency_ms,
                "_regime": regime,
                "_source": "openclaw_bridge",
            }

            # -- Track latency --
            if latency_ms is not None:
                samples = _realtime_stats["latency_samples"]
                samples.append(latency_ms)
                if len(samples) > 100:
                    samples.pop(0)
                _realtime_stats["avg_latency_ms"] = round(
                    sum(samples) / len(samples), 2
                )

            # -- Add to ring buffer --
            _realtime_signals.appendleft(enriched)
            _signal_ids_seen.add(sig_id)
            accepted += 1
            _realtime_stats["signals_accepted"] += 1
            accepted_signals.append(enriched)

        # ----- Bulk persist accepted signals to SQLite + auto-embed + auto-graph -----
        # openclaw_db.insert_signals() already calls:
        #   Phase 1: semantic_upsert_signal() for each row
        #   Phase 3: graph_upsert_signal() for each row
        if accepted_signals and ingest_id is not None:
            try:
                db_persisted = self.db.insert_signals(
                    ingest_id, run_id or "", accepted_signals
                )
                # Count embeds / graph writes (insert_signals does both internally)
                embedded = db_persisted
                graphed = db_persisted
                _realtime_stats["semantic_embeds"] += embedded
                _realtime_stats["graph_writes"] += graphed
            except Exception as exc:
                logger.warning("[OPENCLAW] Bulk signal persist failed: %s", exc)
                # Fall back to individual embed + graph if bulk failed
                embedded, graphed = self._fallback_embed_and_graph(
                    accepted_signals, regime
                )

        # ----- Prune old dedup IDs -----
        if len(_signal_ids_seen) > _REALTIME_BUFFER_SIZE * 2:
            _signal_ids_seen.clear()
            for s in _realtime_signals:
                _signal_ids_seen.add(s.get("_signal_id", ""))

        _realtime_stats["last_signal_at"] = now_iso
        if not _realtime_stats["bridge_connected_since"]:
            _realtime_stats["bridge_connected_since"] = now_iso

        # ----- WebSocket broadcast -----
        if accepted > 0:
            await self._broadcast_signals(
                list(_realtime_signals)[:accepted]
            )

        result = {
            "run_id": run_id,
            "accepted": accepted,
            "rejected": rejected,
            "deduplicated": deduplicated,
            "db_persisted": db_persisted,
            "embedded": embedded,
            "graphed": graphed,
            "buffer_size": len(_realtime_signals),
            "ingested_at": now_iso,
        }
        logger.info(
            "[OPENCLAW] Ingested %d signals (rejected=%d, dedup=%d, "
            "persisted=%d, embedded=%d, graphed=%d, run=%s)",
            accepted, rejected, deduplicated, db_persisted,
            embedded, graphed, run_id,
        )
        return result

    def _fallback_embed_and_graph(
        self, signals: List[Dict], regime: Optional[Dict]
    ) -> Tuple[int, int]:
        """Fallback: individually embed + graph signals if bulk persist failed."""
        embedded = 0
        graphed = 0
        for sig in signals:
            sig_id = sig.get("_signal_id", "")
            synthetic_db_id = int(
                hashlib.md5(sig_id.encode()).hexdigest()[:8], 16
            )
            try:
                if self.db.semantic_upsert_signal(synthetic_db_id, sig, regime):
                    embedded += 1
                    _realtime_stats["semantic_embeds"] += 1
            except Exception:
                _realtime_stats["semantic_embed_failures"] += 1

            try:
                if self.db.graph_upsert_signal(synthetic_db_id, sig, regime):
                    graphed += 1
                    _realtime_stats["graph_writes"] += 1
            except Exception:
                _realtime_stats["graph_write_failures"] += 1
        return embedded, graphed

    # ------------------------------------------------------------------
    # WebSocket broadcast
    # ------------------------------------------------------------------
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
        dead: List[int] = []
        for i, callback in enumerate(_ws_subscribers):
            try:
                await callback(payload)
            except Exception as exc:
                logger.warning("[OPENCLAW] WS subscriber %d failed: %s", i, exc)
                dead.append(i)
        for i in reversed(dead):
            _ws_subscribers.pop(i)

    def subscribe_ws(self, callback: Callable) -> None:
        _ws_subscribers.append(callback)
        logger.info("[OPENCLAW] WS subscriber added (total=%d)", len(_ws_subscribers))

    def unsubscribe_ws(self, callback: Callable) -> None:
        try:
            _ws_subscribers.remove(callback)
        except ValueError:
            pass

    # ==================================================================
    # REAL-TIME QUERY METHODS
    # ==================================================================

    def get_realtime_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the N most recent signals from the ring buffer."""
        return list(_realtime_signals)[:limit]

    def get_realtime_stats(self) -> Dict[str, Any]:
        """Return bridge statistics including memory intelligence counters."""
        return {
            **_realtime_stats,
            "buffer_size": len(_realtime_signals),
            "buffer_capacity": _REALTIME_BUFFER_SIZE,
            "ws_subscribers": len(_ws_subscribers),
            "bridge_id": self._bridge_id,
            "latency_samples": None,  # exclude raw samples from public API
        }

    def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific signal in the ring buffer by its dedup ID."""
        for sig in _realtime_signals:
            if sig.get("_signal_id") == signal_id:
                return sig
        return None

    # ==================================================================
    # PHASE 1: SEMANTIC RAG — proxy methods through openclaw_db
    # ==================================================================

    def semantic_search(
        self,
        query: str,
        k: int = 10,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict]:
        """Semantic similarity search across all embedded documents.
        Proxies to openclaw_db.semantic_search()."""
        return self.db.semantic_search(
            query=query, k=k,
            symbol=symbol.upper() if symbol else None,
            regime=regime.upper() if regime else None,
            doc_type=doc_type,
        )

    def semantic_build_context(
        self,
        query: str,
        k: int = 5,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
    ) -> str:
        """Build a compact context string from top-k semantic hits for LLM prompts.
        Proxies to openclaw_db.semantic_build_context()."""
        return self.db.semantic_build_context(
            query=query, k=k,
            symbol=symbol.upper() if symbol else None,
            regime=regime.upper() if regime else None,
        )

    def semantic_embed_text(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Embed arbitrary text (news, discord, notes) into the vector store.
        Proxies to openclaw_db.semantic_upsert_text()."""
        return self.db.semantic_upsert_text(doc_id, text, metadata)

    def semantic_backfill(self, limit: int = 1000) -> int:
        """Backfill the vector store from existing SQLite signal history.
        Proxies to openclaw_db.semantic_backfill()."""
        return self.db.semantic_backfill(limit=limit)

    # ==================================================================
    # PHASE 2: CORE MEMORY — proxy methods through openclaw_db
    # ==================================================================

    def core_memory_inject(self, top_n: int = 10) -> str:
        """Return the 'always-on' core memory block for LLM prompt injection.
        Proxies to openclaw_db.core_memory_inject()."""
        return self.db.core_memory_inject(top_n=top_n)

    def core_memory_list(
        self, category: Optional[str] = None, top_n: int = 50
    ) -> List[Dict]:
        """List core memory entries.
        Proxies to openclaw_db.core_memory_list()."""
        return self.db.core_memory_list(category=category, top_n=top_n)

    def core_memory_upsert(
        self,
        key: str,
        content: str,
        category: str = "general",
        priority: int = 50,
        source: str = "system",
        ttl_days: Optional[int] = None,
    ) -> bool:
        """Upsert a core memory entry.
        Proxies to openclaw_db.core_memory_upsert()."""
        return self.db.core_memory_upsert(
            key=key, content=content, category=category,
            priority=priority, source=source, ttl_days=ttl_days,
        )

    def core_memory_consolidate(self, lessons: List[Dict]) -> int:
        """Batch-write lessons learned (post-market review).
        Proxies to openclaw_db.core_memory_consolidate()."""
        return self.db.core_memory_consolidate(lessons)

    # ==================================================================
    # PHASE 3: GRAPHRAG — proxy methods through openclaw_db
    # ==================================================================

    def graph_neighborhood(
        self, ticker: str, depth: int = 2, limit: int = 50
    ) -> Dict:
        """Get the graph neighborhood around a ticker.
        Proxies to openclaw_db.graph_neighborhood()."""
        return self.db.graph_neighborhood(
            ticker=ticker.upper(), depth=depth, limit=limit,
        )

    def graph_add_correlation(
        self,
        ticker_a: str,
        ticker_b: str,
        correlation: float,
        edge_type: str = "CORRELATED_WITH",
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Add a correlation edge between two tickers.
        Proxies to openclaw_db.graph_add_correlation()."""
        return self.db.graph_add_correlation(
            ticker_a=ticker_a, ticker_b=ticker_b,
            correlation=correlation, edge_type=edge_type, metadata=metadata,
        )

    def graph_add_catalyst(
        self, ticker: str, headline: str, catalyst_type: str = "news"
    ) -> bool:
        """Add a catalyst event linked to a ticker.
        Proxies to openclaw_db.graph_add_catalyst()."""
        return self.db.graph_add_catalyst(
            ticker=ticker, headline=headline, catalyst_type=catalyst_type,
        )

    def graph_query_natural(
        self, question: str, ticker: Optional[str] = None
    ) -> Dict:
        """Answer a natural-language question with graph + semantic context.
        Proxies to openclaw_db.graph_query_natural()."""
        return self.db.graph_query_natural(question=question, ticker=ticker)

    # ==================================================================
    # GIST-BASED SCAN DATA (fallback / batch scans)
    # ==================================================================

    def _is_cache_valid(self) -> bool:
        if _cache["data"] is None:
            return False
        return (time.time() - _cache["fetched_at"]) < _CACHE_TTL_SECONDS

    async def _fetch_gist(self) -> Optional[Dict]:
        """Fetch the Gist JSON from GitHub API."""
        if not self.gist_id:
            logger.warning("[OPENCLAW] OPENCLAW_GIST_ID not configured")
            return None
        url = f"https://api.github.com/gists/{self.gist_id}"
        accept = "application/vnd.github.v3+json"

        async def do_get(auth_headers: dict):
            resp = await self._http.get(
                url, headers={**auth_headers, "Accept": accept}
            )
            resp.raise_for_status()
            return resp.json()

        headers = {}
        if self.gist_token and self.gist_token.strip():
            headers["Authorization"] = f"token {self.gist_token.strip()}"

        try:
            gist_json = await do_get(headers)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning(
                    "[OPENCLAW] Gist 401 Unauthorized. Retrying without token…"
                )
                try:
                    gist_json = await do_get({})
                    logger.info("[OPENCLAW] Fetched using public Gist (no token)")
                except httpx.HTTPStatusError as retry_exc:
                    logger.error(
                        "[OPENCLAW] Gist HTTP %s.", retry_exc.response.status_code
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
                    "[OPENCLAW] Gist file '%s' not found", self.gist_filename
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
        if self._is_cache_valid():
            return _cache["data"]
        data = await self._fetch_gist()
        if data is not None:
            _cache["data"] = data
            _cache["fetched_at"] = time.time()
        return _cache["data"]

    # ==================================================================
    # PUBLIC API — Gist-based accessors (backward-compatible)
    # ==================================================================

    async def get_scan_results(self) -> Optional[Dict]:
        return await self._get_data()

    async def get_regime(self) -> Dict:
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
        data = await self._get_data()
        if not data:
            return []
        return data.get("whale_flow_alerts", [])

    async def get_fom_expected_moves(self) -> Dict:
        data = await self._get_data()
        if not data:
            return {}
        return data.get("fom_expected_moves", {})

    async def get_llm_summary(self) -> Optional[str]:
        data = await self._get_data()
        if not data:
            return None
        return data.get("llm_summary")

    async def get_llm_candidate_analysis(self) -> Optional[Dict]:
        data = await self._get_data()
        if not data:
            return None
        return data.get("llm_candidate_analysis")

    async def get_sector_rankings(self) -> List[Dict]:
        data = await self._get_data()
        if not data:
            return []
        return data.get("sector_rankings", [])

    async def force_refresh(self) -> Dict:
        _cache["fetched_at"] = 0.0
        await self._get_data()
        return await self.get_health()

    # ==================================================================
    # HEALTH — Combined bridge + memory intelligence
    # ==================================================================

    async def get_health(self) -> Dict:
        """Full health check: Gist + real-time + memory intelligence layers."""
        data = await self._get_data()
        is_connected = data is not None
        candidate_count = (
            len(data.get("top_candidates", [])) if data else 0
        )
        last_scan_ts = data.get("timestamp") if data else None
        cache_age_s = (
            round(time.time() - _cache["fetched_at"], 1)
            if _cache["fetched_at"]
            else None
        )
        rt = self.get_realtime_stats()

        # Memory Intelligence health (Phase 1 + 2 + 3)
        try:
            intel_health = self.db.get_intelligence_health()
        except Exception:
            intel_health = {}

        return {
            "connected": is_connected,
            "gist_id_configured": bool(self.gist_id),
            "last_scan_timestamp": last_scan_ts,
            "candidate_count": candidate_count,
            "cache_age_seconds": cache_age_s,
            "cache_ttl_seconds": _CACHE_TTL_SECONDS,
            "realtime": {
                "bridge_id": rt["bridge_id"],
                "signals_received": rt["signals_received"],
                "signals_accepted": rt["signals_accepted"],
                "signals_rejected": rt["signals_rejected"],
                "signals_deduplicated": rt["signals_deduplicated"],
                "buffer_size": rt["buffer_size"],
                "buffer_capacity": rt["buffer_capacity"],
                "avg_latency_ms": rt["avg_latency_ms"],
                "last_signal_at": rt["last_signal_at"],
                "bridge_connected_since": rt["bridge_connected_since"],
                "ws_subscribers": rt["ws_subscribers"],
                "semantic_embeds": rt.get("semantic_embeds", 0),
                "semantic_embed_failures": rt.get("semantic_embed_failures", 0),
                "graph_writes": rt.get("graph_writes", 0),
                "graph_write_failures": rt.get("graph_write_failures", 0),
            },
            "memory_intelligence": intel_health,
        }

    # ==================================================================
    # MEMORY INTELLIGENCE PARSERS — Enhanced with all 3 phases
    # ==================================================================

    async def get_memory_status(self) -> Dict:
        """Memory health: Gist bridge memory data + local intelligence layers."""
        try:
            gist_data = await self._get_data()
            base: Dict[str, Any] = {}

            # Pull memory stats from Gist (PC1-published)
            if gist_data:
                memory_section = gist_data.get("memory", {})
                if memory_section:
                    base = {
                        "memory_iq": memory_section.get("quality_score", {}).get(
                            "memory_iq", 0
                        ),
                        "quality_metrics": memory_section.get("quality_score", {}),
                        "expectancy_overview": memory_section.get(
                            "expectancy_summary", {}
                        ),
                        "top_agents": memory_section.get("agent_rankings", [])[:5],
                        "health": memory_section.get("health", {}),
                    }

            # Enrich with local intelligence health (all 3 phases)
            try:
                base["local_intelligence"] = self.db.get_intelligence_health()
            except Exception:
                pass

            if not base:
                return {
                    "memory_iq": 0,
                    "status": "waiting_for_data",
                    "message": "Memory stats not yet published to bridge.",
                }
            return base
        except Exception as e:
            logger.error("[BridgeService] Error fetching memory status: %s", e)
            return {}

    async def get_memory_recall(
        self,
        ticker: str,
        score: float = 50.0,
        regime: str = "UNKNOWN",
    ) -> Dict:
        """Enhanced 4-stage recall pipeline:
          Stage 1: Gist-published recall data (PC1 memory)
          Stage 2: Semantic RAG vector search (Phase 1)
          Stage 3: Core Memory injection (Phase 2)
          Stage 4: GraphRAG neighborhood (Phase 3)
          + Structured SQL facts as baseline
        """
        ticker = ticker.upper()
        regime = regime.upper()

        try:
            # ── Stage 1: Gist-published recall ──
            gist_recall: Dict = {}
            gist_data = await self._get_data()
            if gist_data:
                recalls_section = gist_data.get("recalls", {})
                gist_recall = recalls_section.get(ticker, {})

            # ── Stage 2: Semantic RAG (Phase 1) ──
            query_text = f"{ticker} score={score} regime={regime}"
            semantic_hits = self.db.semantic_search(
                query=query_text, k=5, symbol=ticker, regime=regime,
            )
            semantic_context = self.db.semantic_build_context(
                query=query_text, k=5, symbol=ticker, regime=regime,
            )

            # ── Stage 3: Core Memory (Phase 2) ──
            core_inject = self.db.core_memory_inject(top_n=10)
            core_entries = self.db.core_memory_list(top_n=10)

            # Also pull regime-specific core memory
            regime_memories = self.db.core_memory_list(
                category="regime", top_n=5
            )

            # ── Stage 4: GraphRAG (Phase 3) ──
            graph_data = self.db.graph_neighborhood(ticker, depth=2)

            # ── Baseline: Structured SQL facts ──
            sql_signals = self.db.get_signals_by_symbol(ticker, limit=10)
            signal_count = self.db.count_signals()

            return {
                "ticker": ticker,
                "query_context": {
                    "score": score,
                    "regime": regime,
                },
                # Stage 1 — PC1 memory
                "gist_recall": gist_recall,
                # Stage 2 — Semantic RAG
                "semantic_memory": {
                    "hits": semantic_hits,
                    "hit_count": len(semantic_hits),
                    "context_block": semantic_context,
                },
                # Stage 3 — Core Memory
                "core_memory": {
                    "inject_block": core_inject,
                    "entries": [
                        {
                            "key": e["key"],
                            "category": e["category"],
                            "content": e["content"],
                            "priority": e["priority"],
                        }
                        for e in core_entries
                    ],
                    "regime_specific": [
                        {
                            "key": e["key"],
                            "content": e["content"],
                            "priority": e["priority"],
                        }
                        for e in regime_memories
                    ],
                },
                # Stage 4 — GraphRAG
                "graph_neighborhood": {
                    "nodes": graph_data.get("nodes", []),
                    "edges": graph_data.get("edges", []),
                    "node_count": len(graph_data.get("nodes", [])),
                    "edge_count": len(graph_data.get("edges", [])),
                },
                # Baseline SQL facts
                "structured_facts": {
                    "recent_signals": sql_signals[:5],
                    "signal_count_for_ticker": len(sql_signals),
                    "total_signals_in_db": signal_count,
                },
            }
        except Exception as e:
            logger.error(
                "[BridgeService] Error in enhanced memory recall for %s: %s",
                ticker, e,
            )
            return {
                "ticker": ticker,
                "gist_recall": {},
                "semantic_memory": {"hits": [], "hit_count": 0, "context_block": ""},
                "core_memory": {"inject_block": "", "entries": [], "regime_specific": []},
                "graph_neighborhood": {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0},
                "structured_facts": {"recent_signals": [], "signal_count_for_ticker": 0, "total_signals_in_db": 0},
                "error": str(e),
            }

    async def build_agent_prompt_context(
        self,
        ticker: str,
        score: float = 50.0,
        regime: str = "UNKNOWN",
        include_core: bool = True,
        include_semantic: bool = True,
        include_graph: bool = True,
        semantic_k: int = 5,
        core_n: int = 10,
    ) -> str:
        """Build a complete LLM prompt context block combining all 3 memory layers.

        This is the method other services/agents should call when they need
        memory-grounded context for an LLM prompt.

        Returns a single string ready for prompt injection.
        """
        ticker = ticker.upper()
        regime = regime.upper()
        sections: List[str] = []

        # Phase 2: Core Memory (always-on context)
        if include_core:
            core = self.db.core_memory_inject(top_n=core_n)
            if core:
                sections.append(core)

        # Phase 1: Semantic RAG (similarity-based context)
        if include_semantic:
            query = f"{ticker} score={score} regime={regime}"
            sem_ctx = self.db.semantic_build_context(
                query=query, k=semantic_k, symbol=ticker, regime=regime,
            )
            if sem_ctx:
                sections.append(f"=== SIMILAR PAST TRADES ({ticker}) ===")
                sections.append(sem_ctx)
                sections.append("=== END SIMILAR TRADES ===")

        # Phase 3: GraphRAG (relational context)
        if include_graph:
            graph = self.db.graph_neighborhood(ticker, depth=2, limit=20)
            edges = graph.get("edges", [])
            if edges:
                sections.append(f"=== GRAPH CONTEXT ({ticker}) ===")
                for edge in edges[:15]:
                    sections.append(
                        f"  {edge.get('from', '?')} "
                        f"--[{edge.get('type', '?')}]--> "
                        f"{edge.get('to', '?')}"
                    )
                sections.append("=== END GRAPH CONTEXT ===")

        return "\n".join(sections)


# ===========================================================================
# Global service instance
# ===========================================================================
openclaw_bridge = OpenClawBridgeService()
