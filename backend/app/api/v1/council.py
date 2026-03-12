"""Council API — evaluate symbols through the 35-agent council DAG.

POST /api/v1/council/evaluate  -> full DecisionPacket
GET  /api/v1/council/status    -> council configuration (35 agents, 7 stages)
GET  /api/v1/council/latest    -> most recent DecisionPacket
GET  /api/v1/council/weights   -> current agent weights (Bayesian-updated)
POST /api/v1/council/weights/reset -> reset weights to defaults
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None

# Rate limiting: max evaluations per minute to prevent DoS
_eval_timestamps: list = []
_RATE_LIMIT_MAX = 10  # Max 10 council evaluations per minute
_RATE_LIMIT_WINDOW = 60  # seconds


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


def _check_rate_limit():
    """Enforce rate limiting on council evaluations."""
    now = time.time()
    # Prune old timestamps
    _eval_timestamps[:] = [t for t in _eval_timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_eval_timestamps) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_RATE_LIMIT_MAX} evaluations per minute",
        )
    _eval_timestamps.append(now)


async def _broadcast_verdict_safe(verdict_dict: dict, halt_reason: Optional[str] = None):
    """Broadcast compact verdict to WebSocket; never raise (WS failures must not break pipeline)."""
    try:
        from app.council.verdict_broadcast import (
            build_compact_verdict_payload,
            broadcast_council_verdict,
        )
        payload = build_compact_verdict_payload(verdict_dict, halt_reason=halt_reason)
        await broadcast_council_verdict(payload)
    except Exception as e:
        logger.debug("Council verdict broadcast failed (non-fatal): %s", e)


@router.post("/evaluate", dependencies=[Depends(require_auth)])
async def evaluate_symbol(req: CouncilEvalRequest):
    """Run the 35-agent council on a symbol and return DecisionPacket.
    On completion (or timeout/halt), broadcasts a compact verdict to WebSocket channel council_verdict.
    """
    global _latest_decision
    _check_rate_limit()
    symbol = (req.symbol or "").upper()
    try:
        from app.council.runner import run_council

        decision = await asyncio.wait_for(
            run_council(
                symbol=req.symbol,
                timeframe=req.timeframe,
                features=req.features,
                context=req.context or {},
            ),
            timeout=120.0,  # Hard 2-minute cap on full council evaluation
        )

        result = decision.to_dict()
        _latest_decision = result
        # Broadcast verdict to WebSocket (best-effort; do not block response)
        halt_reason = None
        if decision.vetoed:
            halt_reason = "vetoed"
        elif decision.final_direction == "hold" or not decision.execution_ready:
            halt_reason = "hold"
        asyncio.create_task(_broadcast_verdict_safe(result, halt_reason=halt_reason))
        return result
    except asyncio.TimeoutError:
        logger.error("Council evaluation timed out for %s (120s limit)", req.symbol)
        # Emit halted verdict so clients see consistent payload
        halt_payload = {
            "council_decision_id": "",
            "symbol": symbol,
            "final_direction": "hold",
            "final_confidence": 0.0,
            "votes": [],
            "execution_ready": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        asyncio.create_task(_broadcast_verdict_safe(halt_payload, halt_reason="timeout"))
        raise HTTPException(status_code=504, detail="Council evaluation timed out (120s)")
    except Exception as e:
        logger.error("Council evaluation failed: %s", e)
        halt_payload = {
            "council_decision_id": "",
            "symbol": symbol,
            "final_direction": "hold",
            "final_confidence": 0.0,
            "votes": [],
            "execution_ready": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        asyncio.create_task(_broadcast_verdict_safe(halt_payload, halt_reason="error"))
        raise HTTPException(status_code=500, detail="Council evaluation failed")


@router.get("/latest")
async def council_latest():
    """Return the most recent council DecisionPacket (if any)."""
    if _latest_decision is None:
        return {"status": "no_evaluation_yet", "votes": None}
    return _latest_decision


@router.get("/status")
async def council_status():
    """Return council configuration from canonical registry (agent_count matches DAG)."""
    import os

    from app.council.registry import get_agent_count, get_agents, get_dag_stages

    agent_weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        agent_weights = learner.get_weights()
    except Exception:
        pass

    return {
        "council_enabled": os.getenv("COUNCIL_ENABLED", "true").lower() == "true",
        "brain_enabled": os.getenv("BRAIN_ENABLED", "false").lower() == "true",
        "council_gate_enabled": os.getenv("COUNCIL_GATE_ENABLED", "true").lower() == "true",
        "agent_count": get_agent_count(),
        "agents": get_agents(),
        "dag_stages": get_dag_stages(),
        "agent_weights": agent_weights,
    }


@router.get("/weights")
async def council_weights():
    """Return current Bayesian-updated agent weights."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        return {
            "weights": learner.get_weights(),
            "update_count": learner.update_count,
            "last_update": learner.last_update,
        }
    except Exception as e:
        logger.warning("Weight learner unavailable: %s", e)
        return {"status": "weight_learner_unavailable", "error": "Service unavailable"}


@router.post("/weights/reset", dependencies=[Depends(require_auth)])
async def reset_weights():
    """Reset agent weights to defaults."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        learner.reset()
        return {"status": "ok", "weights": learner.get_weights()}
    except Exception as e:
        logger.warning("Weight reset failed: %s", e)
        return {"status": "error", "error": "Service unavailable"}


# ── Phase C Endpoints ──────────────────────────────────────────────────


@router.get("/history")
async def council_history(symbol: str = "", limit: int = 100):
    """Return council decision audit trail from DuckDB (C4)."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM council_decisions WHERE symbol = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                [symbol.upper(), min(limit, 500)],
            ).fetchdf().to_dict(orient="records")
        else:
            rows = conn.execute(
                "SELECT * FROM council_decisions ORDER BY timestamp DESC LIMIT ?",
                [min(limit, 500)],
            ).fetchdf().to_dict(orient="records")
        return {"decisions": rows, "count": len(rows)}
    except Exception as e:
        logger.debug("Council history unavailable: %s", e)
        return {"decisions": [], "count": 0, "status": "unavailable"}


@router.get("/decision/{decision_id}")
async def council_decision_detail(decision_id: str):
    """Return full detail of a single council decision (C4)."""
    try:
        import json
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        row = conn.execute(
            "SELECT * FROM council_decisions WHERE decision_id = ?",
            [decision_id],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Decision not found")
        cols = [d[0] for d in conn.description]
        result = dict(zip(cols, row))
        # Parse JSON columns
        for col in ("agent_votes", "execution_result"):
            if col in result and isinstance(result[col], str):
                try:
                    result[col] = json.loads(result[col])
                except Exception:
                    pass
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.debug("Decision detail unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Service unavailable")


@router.get("/debates")
async def council_debates(limit: int = 50):
    """Return debate history (C3)."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        rows = conn.execute(
            "SELECT * FROM debate_history ORDER BY timestamp DESC LIMIT ?",
            [min(limit, 200)],
        ).fetchdf().to_dict(orient="records")
        return {"debates": rows, "count": len(rows)}
    except Exception as e:
        logger.debug("Debate history unavailable: %s", e)
        return {"debates": [], "count": 0, "status": "unavailable"}


@router.get("/calibration")
async def agent_calibration():
    """Return Brier score calibration data per agent (C2)."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        rows = conn.execute(
            "SELECT * FROM agent_calibration ORDER BY brier_score ASC"
        ).fetchdf().to_dict(orient="records")
        return {"calibration": rows, "count": len(rows)}
    except Exception as e:
        logger.debug("Calibration data unavailable: %s", e)
        return {"calibration": [], "count": 0, "status": "unavailable"}


# ── Health observability (Prompt 3) ────────────────────────────────────────


@router.get("/health")
async def council_health():
    """Return council health: last evaluation + rolling 24h stats."""
    try:
        from app.council.council_health import get_health
        return get_health()
    except Exception as e:
        logger.debug("Council health unavailable: %s", e)
        return {
            "last_evaluation": None,
            "rolling_24h": {"evaluations": 0, "avg_healthy_agents": 0, "avg_latency_ms": 0, "p95_latency_ms": 0, "worst_degradation": None},
        }


@router.get("/agents/performance")
async def council_agents_performance():
    """Return per-agent performance (vote counts, failures, Brier, health)."""
    try:
        from app.council.council_health import get_agents_performance
        return get_agents_performance()
    except Exception as e:
        logger.debug("Agents performance unavailable: %s", e)
        return {"agents": [], "broken_agents": [], "always_hold_agents": []}
