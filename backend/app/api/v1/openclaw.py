"""
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
