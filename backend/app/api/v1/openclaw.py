"""
OpenClaw API routes v2 - Bridge between OpenClaw scanner and Embodier Trader frontend.

Endpoints:
    GET  /api/v1/openclaw/scan          - Full scan results (all scored candidates)
    GET  /api/v1/openclaw/regime        - Current regime status (GREEN/YELLOW/RED)
    GET  /api/v1/openclaw/top           - Top N candidates by composite score
    GET  /api/v1/openclaw/health        - Bridge connection status and diagnostics
    GET  /api/v1/openclaw/whale-flow    - Whale flow alerts from latest scan
    GET  /api/v1/openclaw/fom           - FOM expected move levels
    GET  /api/v1/openclaw/llm           - LLM analysis summary + candidate analysis
    GET  /api/v1/openclaw/sectors       - Sector rotation rankings
    GET  /api/v1/openclaw/memory        - Memory IQ, agent rankings, expectancy
    GET  /api/v1/openclaw/memory/recall - 3-stage recall pipeline for ticker
    POST /api/v1/openclaw/refresh       - Force cache refresh
        GET  /api/v1/openclaw/regime/transitions - Last 30 regime state changes

    Real-time Bridge (v2 - 2026.2.22):
    POST /api/v1/openclaw/signals       - Ingest real-time signals from bridge_sender.py
    GET  /api/v1/openclaw/signals/realtime - Get recent real-time signals from ring buffer
    GET  /api/v1/openclaw/signals/stats - Real-time bridge statistics

    Agent Command Center endpoints (Phase 2.1):
    GET  /api/v1/openclaw/macro         - Macro brain state (regime, oscillator, bias)
    GET  /api/v1/openclaw/swarm-status  - Active agent teams and health
    GET  /api/v1/openclaw/candidates    - Ranked candidates with scores
    POST /api/v1/openclaw/spawn-team    - Spawn or kill agent teams
    POST /api/v1/openclaw/macro/override - Override bias multiplier
    GET  /api/v1/openclaw/llm-flow      - LLM alert stream (polling)
"""

import logging
import os
import json
import httpx
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, Query, HTTPException, Request
from app.core.security import require_auth
from app.services.openclaw_bridge_service import (
    openclaw_bridge,
    validate_bridge_token,
    verify_bridge_signature,
)
from app.services.openclaw_db import openclaw_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Direct OpenClaw API URL (PC1 Flask server)
OPENCLAW_API_URL = os.getenv("OPENCLAW_API_URL", "http://localhost:5000")


# ===========================================================================
# ROOT ENDPOINT - Dashboard summary (GET /api/v1/openclaw and /api/v1/openclaw/)
# ===========================================================================
async def _openclaw_summary():
    """Shared logic for root summary (used by both '' and '/' routes)."""
    try:
        regime = await openclaw_bridge.get_regime()
        health = await openclaw_bridge.get_health()
        candidates = await openclaw_bridge.get_top_candidates(n=5)
        stats = openclaw_bridge.get_realtime_stats()
        regime_state = (regime.get("state") or "YELLOW") if isinstance(regime, dict) else (str(regime) if regime else "YELLOW")
        composite_score = (candidates[0].get("composite_score") if candidates else None)
        # Dashboard expects a number; use 50 when bridge has no candidates
        score_val = int(composite_score) if composite_score is not None else 50
        return {
            "regime": regime_state,
            "compositeScore": score_val,
            "regime_full": regime,
            "health": health,
            "top_candidates": candidates,
            "realtime_stats": stats,
            "candidate_count": len(candidates),
        }
    except Exception as e:
        logger.warning(f"[OPENCLAW] Summary error: {e}")
        return {
            "regime": "YELLOW",
            "compositeScore": 50,
            "regime_full": {"state": "YELLOW", "confidence": 0},
            "health": {"connected": False},
            "top_candidates": [],
            "realtime_stats": {},
            "candidate_count": 0,
        }


@router.get("", summary="OpenClaw Bridge Summary (no trailing slash)")
async def get_openclaw_summary_root():
    """Root path for Dashboard: GET /api/v1/openclaw."""
    return await _openclaw_summary()


@router.get("/", summary="OpenClaw Bridge Summary (with trailing slash)")
async def get_openclaw_summary():
    """Root path with trailing slash: GET /api/v1/openclaw/."""
    return await _openclaw_summary()


@router.get("/consensus")
async def get_openclaw_consensus():
    """Consensus list for openclawService.getConsensus(). Returns { consensus: [] } when no bridge data."""
    try:
        candidates = await openclaw_bridge.get_top_candidates(n=20)
        consensus = [
            {"symbol": c.get("symbol", ""), "score": c.get("composite_score"), "direction": c.get("direction", "LONG")}
            for c in (candidates or [])
        ]
        return {"consensus": consensus}
    except Exception:
        return {"consensus": []}


# ===========================================================================
# REAL-TIME SIGNAL INGESTION (v2 - 2026.2.22)
# POST /api/v1/openclaw/signals - Hot path from bridge_sender.py
# ===========================================================================
@router.post("/signals", summary="Ingest Real-time Signals from OpenClaw Bridge", dependencies=[Depends(require_auth)])
async def ingest_signals(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_bridge_signature: Optional[str] = Header(None, alias="X-Bridge-Signature"),
):
    """
    Accepts scored signals POSTed by bridge_sender.py on PC1.
    This is the real-time hot path (sub-second latency target).

    Expected JSON body:
    {
        "signals": [{"symbol": "AAPL", "direction": "LONG", "score": 85.0, ...}],
        "run_id": "openclaw_20260224_170000",
        "regime": {"state": "GREEN", "confidence": 0.9},
        "universe": {"name": "sp500", "count": 500},
        "meta": {"openclaw_version": "2026.2.22"}
    }
    """
    # Token authentication - REQUIRED in live mode
    if not authorization:
        if os.getenv("TRADING_MODE", "live") == "live":
            raise HTTPException(status_code=401, detail="Authorization header required in live mode")
        logger.warning("[OPENCLAW] Signal ingestion without auth token (non-live mode)")
    else:
        token = authorization.replace("Bearer ", "").strip()
        if not validate_bridge_token(token):
            raise HTTPException(status_code=401, detail="Invalid bridge token")

    # Read body
    try:
        body_bytes = await request.body()
        payload = json.loads(body_bytes)
    except Exception as e:
        logger.warning("Invalid JSON in OpenClaw request: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # HMAC signature verification
    if x_bridge_signature:
        if not verify_bridge_signature(body_bytes, x_bridge_signature):
            raise HTTPException(status_code=401, detail="Invalid bridge signature")

    signals = payload.get("signals", [])
    if not signals:
        return {"run_id": None, "accepted": 0, "error": "No signals provided"}

    # Ingest into bridge service
    result = await openclaw_bridge.ingest_signals(
        signals=signals,
        run_id=payload.get("run_id"),
        regime=payload.get("regime"),
        universe=payload.get("universe"),
        meta=payload.get("meta"),
    )

    logger.info(
        "[OPENCLAW] POST /signals ingested %d signals (run=%s)",
        result.get("accepted", 0),
        result.get("run_id"),
    )
    return result


@router.get("/signals/realtime", summary="Get Recent Real-time Signals")
async def get_realtime_signals(limit: int = Query(default=50, ge=1, le=500)):
    """Return the most recent real-time signals from the ring buffer."""
    signals = openclaw_bridge.get_realtime_signals(limit=limit)
    return {
        "count": len(signals),
        "signals": signals,
        "stats": openclaw_bridge.get_realtime_stats(),
    }


@router.get("/signals/stats", summary="Real-time Bridge Statistics")
async def get_signal_stats():
    """Return real-time bridge statistics (latency, throughput, buffer status)."""
    return openclaw_bridge.get_realtime_stats()


# ===========================================================================
# EXISTING SCAN / GIST ENDPOINTS (preserved from v1)
# ===========================================================================
@router.get("/scan")
async def get_scan_results():
    """Return full OpenClaw scan payload (all candidates + metadata)."""
    data = await openclaw_bridge.get_scan_results()
    if data is None:
        return {
            "error": "No scan data available",
            "hint": "Check OPENCLAW_GIST_ID and OPENCLAW_GIST_TOKEN in .env",
        }
    return data


@router.post("/scan", dependencies=[Depends(require_auth)])
async def trigger_scan(body: dict = {}):
    """
    Trigger a manual scan refresh.
    Frontend sends: { scannerId: "turbo_scanner" }
    """
    scanner_id = body.get("scannerId", "default")
    logger.info("Manual scan triggered: scanner=%s", scanner_id)

    # Re-fetch scan data from bridge
    data = await openclaw_bridge.get_scan_results()
    candidates = len(data.get("candidates", [])) if data else 0
    return {"ok": True, "scanner": scanner_id, "candidates": candidates}


@router.get("/regime")
async def get_regime():
    """
    Return current market regime status.
    Response: {state: GREEN|YELLOW|RED, vix, hmm_confidence, hurst, macro_context}
    """
    return await openclaw_bridge.get_regime()


@router.get("/top")
async def get_top_candidates(n: int = Query(default=10, ge=1, le=50)):
    """
    Return top N candidates sorted by composite score.
    Each candidate includes: symbol, composite_score, tier, pillar scores,
    whale data, suggested entry/stop, position sizing.
    """
    candidates = await openclaw_bridge.get_top_candidates(n=n)
    regime = await openclaw_bridge.get_regime()
    return {
        "regime": regime.get("state", "UNKNOWN"),
        "regime_readme": regime.get("readme"),
        "count": len(candidates),
        "candidates": candidates,
    }


@router.get("/health")
async def get_health():
    """
    Return bridge health and diagnostics.
    Response: {connected, gist_id_configured, last_scan_timestamp,
    candidate_count, cache_age_seconds, cache_ttl_seconds, realtime: {...}}
    """
    return await openclaw_bridge.get_health()


@router.get("/whale-flow")
async def get_whale_flow():
    """Return whale flow (unusual options activity) alerts from latest scan."""
    alerts = await openclaw_bridge.get_whale_flow()
    return {"count": len(alerts), "alerts": alerts}


@router.get("/fom")
async def get_fom_expected_moves():
    """Return FOM expected move levels for watchlist symbols."""
    return await openclaw_bridge.get_fom_expected_moves()


@router.get("/llm")
async def get_llm_analysis():
    """
    Return LLM-generated analysis (scan summary + candidate analysis).
    Only populated if OpenClaw ran with Ollama/Perplexity enabled.
    """
    summary = await openclaw_bridge.get_llm_summary()
    analysis = await openclaw_bridge.get_llm_candidate_analysis()
    return {
        "summary_available": summary is not None,
        "summary": summary,
        "candidate_analysis_available": analysis is not None,
        "candidate_analysis": analysis,
    }


@router.get("/sectors")
async def get_sector_rankings():
    """Return sector rotation rankings from latest scan."""
    sectors = await openclaw_bridge.get_sector_rankings()
    return {"count": len(sectors), "sectors": sectors}


@router.post("/refresh", dependencies=[Depends(require_auth)])
async def force_refresh():
    """Force a cache refresh - fetches fresh data from Gist immediately."""
    logger.info("[OPENCLAW] Manual refresh triggered")
    health = await openclaw_bridge.force_refresh()
    return {"message": "Cache refreshed", "health": health}


# ------------------------------------------------------------------ #
# MEMORY INTELLIGENCE ENDPOINTS
# ------------------------------------------------------------------ #
@router.get("/memory", summary="Get OpenClaw Memory Health & Quality Score")
async def get_memory_health():
    """Retrieves the persistent memory intelligence score (IQ), expectancy data,
    agent rankings, and general health from the OpenClaw swarm via the bridge."""
    try:
        memory_data = await openclaw_bridge.get_memory_status()
        if not memory_data:
            raise HTTPException(
                status_code=404, detail="Memory data not available from bridge."
            )
        return {"status": "success", "data": memory_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to fetch memory status"
        )


@router.get("/memory/recall", summary="Get Contextual Intelligence for Ticker")
async def get_memory_recall(
    ticker: str = Query(..., description="Ticker symbol to recall memory for"),
    score: float = Query(50.0, description="Signal score context"),
    regime: str = Query("UNKNOWN", description="Market regime context"),
):
    """Executes the 3-stage recall pipeline (deterministic preload, semantic search,
    structured facts) for a specific ticker to feed the Agent Command Center UI."""
    try:
        recall_data = await openclaw_bridge.get_memory_recall(
            ticker=ticker.upper(), score=score, regime=regime.upper()
        )
        if not recall_data:
            raise HTTPException(
                status_code=404, detail=f"No recall data found for {ticker}."
            )
        return {"status": "success", "data": recall_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to fetch memory recall"
        )


# ------------------------------------------------------------------ #
# AGENT COMMAND CENTER ENDPOINTS (Phase 2.1)
# Macro Brain state, Swarm status, Bias override
# ------------------------------------------------------------------ #
@router.get("/macro", summary="Get Macro Brain State")
async def get_macro_state():
    """
    Macro Brain state for the wave gauge + regime banner.
    Returns oscillator, wave_state, bias, regime, vix, hy_spread, fear_greed_index.
    Falls back to bridge regime data if direct PC1 proxy is unavailable.
    """
    try:
        regime_data = await openclaw_bridge.get_regime()
        scan_data = await openclaw_bridge.get_scan_results()
        macro_context = scan_data.get("macro_context", {}) if scan_data else {}

        return {
            "oscillator": macro_context.get("oscillator", 0.0),
            "wave_state": macro_context.get(
                "wave_state", regime_data.get("state", "NEUTRAL")
            ),
            "bias": macro_context.get("bias_multiplier", 1.0),
            "regime": regime_data.get("state", "YELLOW"),
            "vix": regime_data.get("vix"),
            "hy_spread": macro_context.get("hy_spread"),
            "fear_greed_index": macro_context.get("fear_greed_index"),
            "yield_curve": macro_context.get("yield_curve"),
        }
    except Exception as e:
        logger.warning(f"[OPENCLAW] Macro state error: {e}")
        # Fallback to DB-backed ingest regime if bridge is down
        try:
            last = openclaw_db.get_latest_ingest()
            if last:
                regime_json = last.get("regime_json")
                regime = json.loads(regime_json) if regime_json else {}
                return {
                    "oscillator": regime.get("confidence", 0.0),
                    "wave_state": regime.get("source", "NEUTRAL"),
                    "bias": 1.0,
                    "regime": regime.get("state", "YELLOW"),
                    "vix": None,
                    "hy_spread": None,
                    "fear_greed_index": None,
                }
        except Exception:
            pass
        return {
            "oscillator": 0.0,
            "wave_state": "NEUTRAL",
            "bias": 1.0,
            "regime": "YELLOW",
            "vix": None,
            "hy_spread": None,
            "fear_greed_index": None,
        }


@router.get("/swarm-status", summary="Get Agent Swarm Status")
async def get_swarm_status():
    """
    Active agent team count and states.
    Returns active team count, total teams, and per-team details.
    """
    try:
        memory_data = await openclaw_bridge.get_memory_status()
        if memory_data and "teams" in memory_data:
            teams = memory_data["teams"]
            active = sum(1 for t in teams if t.get("status") == "active")
            return {
                "active": active,
                "total": len(teams),
                "teams": teams,
            }
    except Exception:
        pass
    return {
        "active": 0,
        "total": 0,
        "teams": [],
    }


@router.get("/agents", summary="Get Agent List for Backtesting/Command Center")
async def get_agents():
    """
    Return list of agent subsystems with status.
    Used by Backtesting page swarm panel and Agent Command Center.
    """
    try:
        health = await openclaw_bridge.get_health()
        connected = health.get("connected", False)
        base_status = "active" if connected else "idle"
        agents = [
            {"id": "scanner", "name": "Market Scanner", "status": base_status, "type": "scanner"},
            {"id": "memory", "name": "Memory Agent", "status": base_status, "type": "memory"},
            {"id": "signals", "name": "Signal Processor", "status": base_status, "type": "signals"},
            {"id": "regime", "name": "Regime Detector", "status": base_status, "type": "regime"},
            {"id": "risk", "name": "Risk Monitor", "status": base_status, "type": "risk"},
            {"id": "execution", "name": "Execution Agent", "status": base_status, "type": "execution"},
        ]
        return {"agents": agents, "total": len(agents), "active": sum(1 for a in agents if a["status"] == "active")}
    except Exception as e:
        logger.debug(f"[OPENCLAW] Agents list error: {e}")
        return {"agents": [], "total": 0, "active": 0}


@router.post("/macro/override", summary="Override Macro Brain Bias", dependencies=[Depends(require_auth)])
async def macro_override(
    bias_multiplier: float = Body(
        ..., ge=0.0, le=5.0, description="Bias multiplier (0.0-5.0)"
    )
):
    """
    Operator bias slider adjustment.
    Temporarily overrides Macro Brain bias in composite scoring.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{OPENCLAW_API_URL}/api/v1/openclaw/macro/override",
                params={"bias_multiplier": bias_multiplier},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"[OPENCLAW] Bias override failed: {e}")
    raise HTTPException(
        status_code=503,
        detail=(
            "OpenClaw PC1 is unreachable - cannot apply bias override. "
            "Ensure OPENCLAW_API_URL is configured and PC1 is running."
        ),
    )


# ------------------------------------------------------------------ #
# AGENT COMMAND CENTER - ADDITIONAL ENDPOINTS
# Candidates, Spawn/Kill Teams, LLM Flow Stream
# ------------------------------------------------------------------ #
@router.get("/candidates", summary="Get Ranked Candidates for Agent Command Center")
async def get_candidates(n: int = Query(default=20, ge=1, le=50)):
    """
    Ranked candidates with symbol, score, team_tag, entry/stop/target.
    Proxies to OpenClaw Flask API, falls back to bridge scan data.
    """
    # Try direct OpenClaw API first
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{OPENCLAW_API_URL}/api/v1/openclaw/candidates", params={"top": n}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.debug(f"[OPENCLAW] Direct candidates proxy failed: {e}")

    # Fallback to bridge top candidates
    try:
        candidates = await openclaw_bridge.get_top_candidates(n=n)
        formatted = []
        for c in candidates:
            formatted.append(
                {
                    "symbol": c.get("symbol", "?"),
                    "score": c.get("composite_score", 0),
                    "team_tag": c.get("source", "scanner"),
                    "entry": c.get("suggested_entry") or c.get("entry"),
                    "stop": c.get("suggested_stop") or c.get("stop"),
                    "target": c.get("target"),
                    "setup": c.get("setup", "unknown"),
                }
            )
        return {
            "candidates": formatted,
            "count": len(formatted),
            "_source": "bridge_fallback",
        }
    except Exception:
        pass
    return {"candidates": [], "count": 0, "_fallback": True}


@router.post("/spawn-team", summary="Spawn or Kill Agent Team", dependencies=[Depends(require_auth)])
async def spawn_team(
    team_type: str = Query(default="momentum", description="Team type to spawn"),
    action: str = Query(default="spawn", description="'spawn' or 'kill'"),
    team_name: Optional[str] = Query(default=None, description="Team name (for kill)"),
):
    """
    Spawn or kill an agent team.
    Proxies to OpenClaw Flask API on PC1.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"team_type": team_type, "action": action}
            if team_name:
                payload["team_name"] = team_name
            resp = await client.post(
                f"{OPENCLAW_API_URL}/api/v1/openclaw/spawn-team",
                json=payload,
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.json().get("error", "Spawn team failed"),
                )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="OpenClaw PC1 is unreachable. Cannot spawn/kill teams.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OpenClaw team management error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/llm-flow", summary="Get LLM Alert Stream for Agent Command Center")
async def get_llm_flow(limit: int = Query(default=5, ge=1, le=50)):
    """
    LLM alert stream (last N alerts) for the Agent Command Center.
    Proxies to OpenClaw Flask API, returns empty on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{OPENCLAW_API_URL}/api/v1/openclaw/llm-flow",
                params={"limit": limit},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.debug(f"[OPENCLAW] LLM flow proxy failed: {e}")

    # Graceful fallback
    return {"alerts": [], "total": 0, "_fallback": True}


# ------------------------------------------------------------------ #
# ADDITIONAL ENDPOINTS (called by openclawService.js)
# nlp-spawn, health-matrix
# ------------------------------------------------------------------ #
@router.get("/consensus-summary", summary="Get Agent Swarm Consensus")
async def get_consensus():
    """
    Return the current agent consensus view — aggregated opinions
    from all active swarm agents on top candidates.
    """
    try:
        candidates = await openclaw_bridge.get_top_candidates(n=10)
        consensus = []
        for c in candidates:
            consensus.append({
                "symbol": c.get("symbol"),
                "score": c.get("composite_score", 0),
                "direction": "LONG" if c.get("composite_score", 0) > 60 else "NEUTRAL",
                "agent_count": c.get("agent_count", 1),
                "agreement_pct": c.get("agreement_pct", 100),
            })
        return {"consensus": consensus, "count": len(consensus)}
    except Exception as e:
        logger.debug(f"[OPENCLAW] Consensus error: {e}")
        return {"consensus": [], "count": 0}



@router.post("/nlp-spawn", summary="Spawn Agent Team via NLP Prompt", dependencies=[Depends(require_auth)])
async def nlp_spawn(request: Request):
    """
    Natural language prompt to spawn an agent team.
    Proxies to OpenClaw Flask API on PC1.
    """
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{OPENCLAW_API_URL}/api/v1/openclaw/nlp-spawn",
                json={"prompt": prompt},
            )
            if resp.status_code == 200:
                return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[OPENCLAW] NLP spawn proxy failed: {e}")
    raise HTTPException(
        status_code=503,
        detail="OpenClaw PC1 is unreachable. Cannot process NLP spawn.",
    )


@router.get("/health-matrix", summary="Get Agent Health Matrix")
async def get_health_matrix():
    """
    Return health matrix for all agent subsystems.
    Aggregates bridge health, memory, swarm, and regime status.
    """
    try:
        health = await openclaw_bridge.get_health()
        regime = await openclaw_bridge.get_regime()
        stats = openclaw_bridge.get_realtime_stats()
        return {
            "bridge": health,
            "regime": {"state": regime.get("state", "YELLOW")},
            "realtime": stats,
            "subsystems": {
                "scanner": {"status": "ok" if health.get("connected") else "degraded"},
                "memory": {"status": "ok"},
                "signals": {"status": "ok" if stats.get("total_ingested", 0) > 0 else "idle"},
            },
        }
    except Exception as e:
        logger.debug(f"[OPENCLAW] Health matrix error: {e}")
        return {
            "bridge": {"connected": False},
            "regime": {"state": "YELLOW"},
            "realtime": {},
            "subsystems": {},
        }


# ------------------------------------------------------------------
# MARKET REGIME PAGE ENDPOINTS (Page 10/15)
# Regime transitions history + enhanced macro data for VIX chart
# ------------------------------------------------------------------

@router.get("/regime/transitions", summary="Get Regime Transition History")
async def get_regime_transitions(limit: int = Query(default=30, ge=1, le=100)):
    """
    Return last N regime transitions with timestamp, from/to state,
    trigger reason, confidence, duration, and P&L impact.
    Sources data from OpenClaw bridge scan history.
    """
    try:
        scan_data = await openclaw_bridge.get_scan_results()
        regime_data = await openclaw_bridge.get_regime()
        memory_data = await openclaw_bridge.get_memory_status()

        transitions = []

        # Extract transitions from scan history if available
        if scan_data and "regime_history" in scan_data:
            for t in scan_data["regime_history"][-limit:]:
                transitions.append({
                    "timestamp": t.get("timestamp"),
                    "from": t.get("from_state"),
                    "to": t.get("to_state"),
                    "trigger": t.get("trigger", "HMM state change"),
                    "confidence": t.get("confidence"),
                    "duration": t.get("duration"),
                    "pnl_impact": t.get("pnl_impact"),
                })

        # If no history from scan, try memory data
        if not transitions and memory_data:
            mem_data = memory_data if isinstance(memory_data, dict) else {}
            if "data" in mem_data:
                mem_data = mem_data["data"]
            regime_transitions = mem_data.get("regime_transitions", [])
            for t in regime_transitions[-limit:]:
                transitions.append({
                    "timestamp": t.get("timestamp"),
                    "from": t.get("from_state"),
                    "to": t.get("to_state"),
                    "trigger": t.get("trigger", "HMM state change"),
                    "confidence": t.get("confidence"),
                    "duration": t.get("duration"),
                    "pnl_impact": t.get("pnl_impact"),
                })

        # If still no transitions, try DB ingest history
        if not transitions:
            try:
                ingests = openclaw_db.get_recent_ingests(limit=limit)
                prev_regime = None
                for ingest in ingests:
                    regime_json = ingest.get("regime_json")
                    regime = json.loads(regime_json) if regime_json else {}
                    current = regime.get("state")
                    if prev_regime and current and current != prev_regime:
                        transitions.append({
                            "timestamp": ingest.get("timestamp"),
                            "from": prev_regime,
                            "to": current,
                            "trigger": "HMM state change",
                            "confidence": regime.get("confidence"),
                            "duration": None,
                            "pnl_impact": None,
                        })
                    prev_regime = current
            except Exception:
                pass

        return {
            "count": len(transitions),
            "transitions": transitions[-limit:],
            "current_state": regime_data.get("state", "YELLOW"),
            "time_in_state": regime_data.get("time_in_state"),
        }
    except Exception as e:
        logger.error(f"[OPENCLAW] Regime transitions error: {e}")
        return {"count": 0, "transitions": [], "current_state": "YELLOW"}
