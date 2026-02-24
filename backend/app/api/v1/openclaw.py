"""
OpenClaw Bridge API — Phase 2 (DB-backed)
POST /signals    → ingest batch from OpenClaw PC1
GET  /signals/latest → latest scored signals (DB query)
GET  /health     → bridge health + DB stats
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.openclaw_db import openclaw_db

router = APIRouter(tags=["openclaw"])


# -- request / response schemas -----------------------------------------------

class RegimeIn(BaseModel):
    state: Literal["GREEN", "YELLOW", "RED"]
    confidence: Optional[float] = None
    source: Optional[str] = None


class OpenClawSignalIn(BaseModel):
    symbol: str = Field(..., min_length=1)
    direction: Literal["LONG", "SHORT"]
    score: float
    subscores: Optional[Dict[str, float]] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    timeframe: Optional[str] = None
    reasons: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None


class OpenClawIngestIn(BaseModel):
    run_id: str
    timestamp: datetime
    regime: Optional[RegimeIn] = None
    universe: Optional[Dict[str, Any]] = None
    signals: List[OpenClawSignalIn]


class IngestOut(BaseModel):
    run_id: str
    accepted: int
    ingest_id: int


class SignalOut(BaseModel):
    id: int
    symbol: str
    direction: str
    score: float
    subscores: Optional[Dict] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    timeframe: Optional[str] = None
    reasons: Optional[List[str]] = None
    regime_state: Optional[str] = None
    regime_confidence: Optional[float] = None
    received_at: str
    run_id: str


class HealthOut(BaseModel):
    status: str
    bridge_version: str = "2.0"
    total_ingests: int
    total_signals: int
    last_ingest: Optional[Dict] = None
    signals_last_24h: int


# -- auth helper --------------------------------------------------------------

def _check_token(token: Optional[str]):
    expected = settings.OPENCLAW_BRIDGE_TOKEN
    if expected and expected.strip():
        if not token or token != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing X-OpenClaw-Token")


# -- helpers ------------------------------------------------------------------

def _payload_hash(payload: OpenClawIngestIn) -> str:
    raw = json.dumps(payload.model_dump(), default=str, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _row_to_signal(row: Dict) -> Dict:
    """Normalise a DB row dict into the SignalOut shape."""
    out = dict(row)
    # deserialise JSON columns
    for col, key in [("subscores_json", "subscores"),
                     ("reasons_json", "reasons")]:
        val = out.pop(col, None)
        out[key] = json.loads(val) if val else None
    # drop internal columns the client doesn't need
    out.pop("raw_json", None)
    out.pop("ingest_id", None)
    return out


# -- endpoints ----------------------------------------------------------------

@router.post("/signals", response_model=IngestOut)
async def ingest_openclaw_signals(
    payload: OpenClawIngestIn,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """Receive a batch of scored signals from OpenClaw (PC1)."""
    _check_token(x_openclaw_token)

    regime_dict = payload.regime.model_dump() if payload.regime else None
    universe_dict = payload.universe
    ingest_id = openclaw_db.insert_ingest(
        run_id=payload.run_id,
        timestamp=payload.timestamp.isoformat(),
        regime=regime_dict,
        universe=universe_dict,
        signal_count=len(payload.signals),
        payload_hash=_payload_hash(payload),
    )

    signals_dicts = [s.model_dump() for s in payload.signals]
    accepted = openclaw_db.insert_signals(ingest_id, payload.run_id, signals_dicts)

    return IngestOut(run_id=payload.run_id, accepted=accepted, ingest_id=ingest_id)


@router.get("/signals/latest")
async def get_latest_signals(
    limit: int = 50,
    symbol: Optional[str] = None,
    x_openclaw_token: Optional[str] = Header(default=None),
):
    """Return the most recent OpenClaw signals from DB."""
    _check_token(x_openclaw_token)

    if symbol:
        rows = openclaw_db.get_signals_by_symbol(symbol, limit=limit)
    else:
        rows = openclaw_db.get_latest_signals(limit=limit)

    return [_row_to_signal(r) for r in rows]


@router.get("/health", response_model=HealthOut)
async def bridge_health():
    """Bridge health check — no auth required."""
    last = openclaw_db.get_latest_ingest()
    since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"

    history = openclaw_db.get_ingest_history(limit=1000)
    total_ingests = len(history)  # cheap for now
    total_signals = openclaw_db.count_signals()
    signals_24h = openclaw_db.count_signals(since=since_24h)

    status = "operational"
    if last:
        age_minutes = (
            datetime.utcnow()
            - datetime.fromisoformat(last["received_at"].replace("Z", ""))
        ).total_seconds() / 60
        if age_minutes > 60:
            status = "stale"

    return HealthOut(
        status=status,
        total_ingests=total_ingests,
        total_signals=total_signals,
        last_ingest=last,
        signals_last_24h=signals_24h,
    )
OpenClaw API routes - Bridge between OpenClaw scanner and Embodier Trader frontend.

Endpoints:
    GET /api/v1/openclaw/scan       - Full scan results (all scored candidates)
    GET /api/v1/openclaw/regime     - Current regime status (GREEN/YELLOW/RED)
    GET /api/v1/openclaw/top        - Top N candidates by composite score
    GET /api/v1/openclaw/health     - Bridge connection status and diagnostics
    GET /api/v1/openclaw/whale-flow - Whale flow alerts from latest scan
    GET /api/v1/openclaw/fom        - FOM expected move levels
    GET /api/v1/openclaw/llm        - LLM analysis summary + candidate analysis
        GET /api/v1/openclaw/sectors    - Sector rotation rankings
    GET /api/v1/openclaw/memory     - Memory IQ, agent rankings, expectancy
    GET /api/v1/openclaw/memory/recall - 3-stage recall pipeline for ticker
    POST /api/v1/openclaw/refresh   - Force cache refresh
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from app.services.openclaw_bridge_service import openclaw_bridge

logger = logging.getLogger(__name__)

router = APIRouter()


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
               candidate_count, cache_age_seconds, cache_ttl_seconds}
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


@router.post("/refresh")
async def force_refresh():
    """Force a cache refresh - fetches fresh data from Gist immediately."""
    logger.info("[OPENCLAW] Manual refresh triggered")
    health = await openclaw_bridge.force_refresh()
    return {"message": "Cache refreshed", "health": health}
    

# ------------------------------------------------------------------ #
# MEMORY INTELLIGENCE ENDPOINTS (NEW)
# ------------------------------------------------------------------ #

@router.get("/memory", summary="Get OpenClaw Memory Health & Quality Score")
async def get_memory_health():
    """Retrieves the persistent memory intelligence score (IQ), expectancy data,
    agent rankings, and general health from the OpenClaw swarm via the bridge."""
    try:
        memory_data = await openclaw_bridge.get_memory_status()
        if not memory_data:
            raise HTTPException(status_code=404, detail="Memory data not available from bridge.")
        return {"status": "success", "data": memory_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memory status: {str(e)}")


@router.get("/memory/recall", summary="Get Contextual Intelligence for Ticker")
async def get_memory_recall(
    ticker: str = Query(..., description="Ticker symbol to recall memory for"),
    score: float = Query(50.0, description="Signal score context"),
    regime: str = Query("UNKNOWN", description="Market regime context")
):
    """Executes the 3-stage recall pipeline (deterministic preload, semantic search,
    structured facts) for a specific ticker to feed the Agent Command Center UI."""
    try:
        recall_data = await openclaw_bridge.get_memory_recall(
            ticker=ticker.upper(),
            score=score,
            regime=regime.upper()
        )
        if not recall_data:
            raise HTTPException(status_code=404, detail=f"No recall data found for {ticker}.")
        return {"status": "success", "data": recall_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memory recall: {str(e)}")

        
# ------------------------------------------------------------------ #
# CLAWBOT PANEL ENDPOINTS (Phase 2.1)
# Macro Brain state, Swarm status, Bias override
# Spec: CLAWBOT_PANEL_DESIGN.md in openclaw repo
# ------------------------------------------------------------------ #


@router.get("/macro", summary="Get Macro Brain State")
async def get_macro_state():
    """
    Macro Brain state for the wave gauge + regime banner.
    Returns oscillator, wave_state, bias, regime, vix, hy_spread, fear_greed_index.
    Falls back to bridge regime data if direct PC1 proxy is unavailable.
    """
    try:
        # Try the bridge service first (reads from Gist/cached data)
        regime_data = await openclaw_bridge.get_regime()
        scan_data = await openclaw_bridge.get_scan_results()

        macro_context = scan_data.get("macro_context", {}) if scan_data else {}

        return {
            "oscillator": macro_context.get("oscillator", 0.0),
            "wave_state": macro_context.get("wave_state", regime_data.get("state", "NEUTRAL")),
            "bias": macro_context.get("bias_multiplier", 1.0),
            "regime": regime_data.get("state", "YELLOW"),
            "vix": regime_data.get("vix"),
            "hy_spread": macro_context.get("hy_spread"),
            "fear_greed_index": macro_context.get("fear_greed_index"),
        }
    except Exception as e:
        # Fallback to DB-backed ingest regime if bridge is down
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
        return {
            "oscillator": 0.0,
            "wave_state": "NEUTRAL",
            "bias": 1.0,
            "regime": "YELLOW",
            "vix": None,
            "hy_spread": None,
            "fear_greed_index": None,
        }


@router.get("/swarm-status", summary="Get Clawbot Swarm Status")
async def get_swarm_status():
    """
    Active clawbot team count and states.
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

    # Fallback: empty swarm status so frontend still renders
    return {
        "active": 0,
        "total": 0,
        "teams": [],
    }


@router.post("/macro/override", summary="Override Macro Brain Bias")
async def macro_override(
    bias_multiplier: float = Query(..., ge=0.0, le=5.0, description="Bias multiplier (0.0-5.0)")
):
    """
    Operator bias slider adjustment.
    Temporarily overrides Macro Brain bias in composite scoring.
    Multiplies long/short signal weights.
    """
    try:
        # Forward override to OpenClaw bridge
        result = await openclaw_bridge.set_bias_override(bias_multiplier)
        if result:
            return {
                "success": True,
                "bias_multiplier": bias_multiplier,
                "message": f"Bias override set to {bias_multiplier}",
            }
    except Exception as e:
        logger.warning(f"[OPENCLAW] Bias override failed: {e}")

    raise HTTPException(
        status_code=503,
        detail=(
            "OpenClaw PC1 is unreachable - cannot apply bias override. "
            "Ensure OPENCLAW_API_URL is configured and PC1 is running."
        ),
    )

