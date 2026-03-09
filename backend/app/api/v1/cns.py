"""CNS (Central Nervous System) API — exposes homeostasis, circuit breaker,
self-awareness, blackboard, postmortems, and directive endpoints.

GET /api/v1/cns/homeostasis/vitals     → system vitals + mode
GET /api/v1/cns/circuit-breaker/status → thresholds + last trigger
GET /api/v1/cns/agents/health          → all agent health + weights
GET /api/v1/cns/agents/{name}/history  → agent weight/streak history
GET /api/v1/cns/blackboard/current     → current blackboard snapshot
GET /api/v1/cns/postmortems            → recent postmortems
GET /api/v1/cns/postmortems/attribution → agent attribution stats
GET /api/v1/cns/directives             → list directive files
PUT /api/v1/cns/directives/{filename}  → update a directive file
GET /api/v1/cns/council/last-verdict   → latest council verdict
POST /api/v1/cns/agents/{name}/override-status → override agent streak status
POST /api/v1/cns/agents/{name}/override-weight → override agent Bayesian weight
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Homeostasis ───

@router.get("/homeostasis/vitals")
async def homeostasis_vitals():
    """Get system vitals and current homeostasis mode."""
    try:
        from app.council.homeostasis import get_homeostasis
        h = get_homeostasis()
        vitals = await h.check_vitals()
        return {
            "mode": h.get_mode(),
            "position_scale": h.get_position_scale(),
            "directive_regime": h.get_directive_regime(),
            "vitals": vitals,
            "last_check": h._last_check,
        }
    except Exception as e:
        logger.error("Homeostasis vitals failed: %s", e)
        return {
            "mode": "NORMAL",
            "position_scale": 1.0,
            "directive_regime": "unknown",
            "vitals": {},
            "last_check": 0,
        }


# ─── Circuit Breaker ───

@router.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Get circuit breaker thresholds and current status."""
    try:
        from app.council.reflexes.circuit_breaker import circuit_breaker, _get_thresholds
        thresholds = _get_thresholds()
        metrics = circuit_breaker.get_metrics()
        return {
            "armed": True,
            "thresholds": thresholds,
            "metrics": metrics,
            "checks": [
                {"name": "flash_crash_detector", "description": "Rapid price drop detection"},
                {"name": "vix_spike_detector", "description": "VIX above panic threshold"},
                {"name": "daily_drawdown_limit", "description": "Daily drawdown limit check"},
                {"name": "position_limit_check", "description": "Max position count check"},
                {"name": "market_hours_check", "description": "Market hours validation"},
            ],
        }
    except Exception as e:
        logger.error("Circuit breaker status failed: %s", e)
        return {"armed": False, "thresholds": {}, "metrics": {}, "checks": []}


# ─── Agent Health & Self-Awareness ───

@router.get("/agents/health")
async def agents_health():
    """Get all agent health, Bayesian weights, and streak status."""
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        return {
            "agents": sa.get_status(),
            "summary": {
                "total_agents": len(sa.get_status()),
                "hibernated": sum(1 for a in sa.get_status().values() if a.get("skip")),
                "on_probation": sum(
                    1 for a in sa.get_status().values()
                    if a.get("streak", {}).get("status") == "PROBATION"
                ),
            },
        }
    except Exception as e:
        logger.error("Agent health failed: %s", e)
        return {"agents": {}, "summary": {"total_agents": 0, "hibernated": 0, "on_probation": 0}}


@router.get("/agents/{name}/history")
async def agent_history(name: str):
    """Get detailed history for a specific agent."""
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        return {
            "agent_name": name,
            "bayesian_weight": sa.weights.get_weight(name),
            "distribution": sa.weights.get_distribution(name),
            "streak": sa.streaks.get_streak_info(name),
            "health": sa.health.get_health(name),
            "effective_weight": sa.get_effective_weight(name),
            "should_skip": sa.should_skip_agent(name),
        }
    except Exception as e:
        logger.error("Agent history failed for %s: %s", name, e)
        raise HTTPException(status_code=500, detail=f"Agent history failed: {e}")


class OverrideStatusRequest(BaseModel):
    action: str  # "reset" | "probation" | "hibernate"


@router.post("/agents/{name}/override-status", dependencies=[Depends(require_auth)])
async def override_agent_status(name: str, req: OverrideStatusRequest):
    """Override agent streak status (reset from hibernation, etc.)."""
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        if req.action == "reset":
            sa.streaks.reset(name)
        elif req.action == "probation":
            sa.streaks._streaks.setdefault(name, {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0})
            sa.streaks._streaks[name]["loss_streak"] = sa.streaks.PROBATION_THRESHOLD
            sa.streaks._save()
        elif req.action == "hibernate":
            sa.streaks._streaks.setdefault(name, {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0})
            sa.streaks._streaks[name]["loss_streak"] = sa.streaks.HIBERNATION_THRESHOLD
            sa.streaks._save()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        return {"status": "ok", "agent": name, "new_status": sa.streaks.get_status(name)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OverrideWeightRequest(BaseModel):
    alpha: float
    beta: float


@router.post("/agents/{name}/override-weight", dependencies=[Depends(require_auth)])
async def override_agent_weight(name: str, req: OverrideWeightRequest):
    """Override agent Bayesian weight distribution."""
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        sa.weights._weights[name] = (req.alpha, req.beta)
        sa.weights._save()
        return {
            "status": "ok",
            "agent": name,
            "new_weight": sa.weights.get_weight(name),
            "distribution": sa.weights.get_distribution(name),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Blackboard ───

@router.get("/blackboard/current")
async def blackboard_current():
    """Get the most recent blackboard snapshot (from last council run)."""
    try:
        from app.api.v1.council import _latest_decision
        if _latest_decision:
            return {
                "available": True,
                "council_decision_id": _latest_decision.get("council_decision_id", ""),
                "symbol": _latest_decision.get("symbol", ""),
                "direction": _latest_decision.get("final_direction", ""),
                "confidence": _latest_decision.get("final_confidence", 0),
                "votes": _latest_decision.get("votes", []),
                "vetoed": _latest_decision.get("vetoed", False),
                "timestamp": _latest_decision.get("timestamp", ""),
            }
        return {"available": False}
    except Exception:
        return {"available": False}


# ─── Postmortems ───

@router.get("/postmortems")
async def list_postmortems(limit: int = 20):
    """Get recent postmortems from DuckDB."""
    try:
        from app.data.duckdb_storage import duckdb_store
        postmortems = duckdb_store.get_postmortems(limit=limit)
        return {"postmortems": postmortems, "count": len(postmortems)}
    except Exception as e:
        logger.error("Postmortems fetch failed: %s", e)
        return {"postmortems": [], "count": 0}


@router.get("/postmortems/attribution")
async def postmortem_attribution():
    """Get agent attribution stats from postmortems."""
    try:
        from app.data.duckdb_storage import duckdb_store
        postmortems = duckdb_store.get_postmortems(limit=100)

        # Aggregate attribution by agent
        agent_stats: Dict[str, Dict[str, Any]] = {}
        for pm in postmortems:
            votes = pm.get("agent_votes", [])
            if isinstance(votes, str):
                import json
                try:
                    votes = json.loads(votes)
                except Exception:
                    votes = []
            for vote in votes:
                agent = vote.get("agent_name", "unknown")
                if agent not in agent_stats:
                    agent_stats[agent] = {"total_votes": 0, "directions": {}, "avg_confidence": 0, "confidences": []}
                agent_stats[agent]["total_votes"] += 1
                direction = vote.get("direction", "hold")
                agent_stats[agent]["directions"][direction] = agent_stats[agent]["directions"].get(direction, 0) + 1
                conf = vote.get("confidence", 0)
                agent_stats[agent]["confidences"].append(conf)

        # Compute averages
        for agent, stats in agent_stats.items():
            confs = stats.pop("confidences", [])
            stats["avg_confidence"] = sum(confs) / len(confs) if confs else 0

        return {"attribution": agent_stats, "total_postmortems": len(postmortems)}
    except Exception as e:
        logger.error("Attribution fetch failed: %s", e)
        return {"attribution": {}, "total_postmortems": 0}


# ─── Directives ───

@router.get("/directives")
async def list_directives():
    """List all directive files and their content."""
    try:
        from app.council.directives.loader import directive_loader
        directives_dir = directive_loader._dir
        files = []
        if directives_dir.exists():
            for f in sorted(directives_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                files.append({
                    "filename": f.name,
                    "content": content,
                    "size_bytes": len(content.encode("utf-8")),
                })
        return {"directives": files, "directory": str(directives_dir)}
    except Exception as e:
        logger.error("Directives listing failed: %s", e)
        return {"directives": [], "directory": ""}


class DirectiveUpdateRequest(BaseModel):
    content: str


@router.put("/directives/{filename}", dependencies=[Depends(require_auth)])
async def update_directive(filename: str, req: DirectiveUpdateRequest):
    """Update a directive markdown file."""
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Filename must end with .md")
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    try:
        from app.council.directives.loader import directive_loader
        directives_dir = directive_loader._dir
        path = directives_dir / filename
        if not path.parent.resolve() == directives_dir.resolve():
            raise HTTPException(status_code=400, detail="Invalid path")
        path.write_text(req.content, encoding="utf-8")
        directive_loader.clear_cache()
        return {"status": "ok", "filename": filename, "size_bytes": len(req.content.encode("utf-8"))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Council Last Verdict ───

@router.get("/profit-brain")
async def profit_brain_status():
    """Complete Profit Brain CNS status — the 40,000ft view.

    Aggregates all subsystems into a single response showing:
    - Sensory cortex: data ingestion health (scanner, sweep, news, stream)
    - Cerebral cortex: scoring engine (unified brain weights + accuracy)
    - Prefrontal cortex: council deliberation (agent health, verdicts)
    - Motor cortex: execution (order stats, position management)
    - Cerebellum: feedback loop (outcome tracking, Kelly calibration)
    - Risk shield: circuit breaker, drawdown, regime
    """
    brain = {
        "version": "3.2.0",
        "mode": "UNKNOWN",
    }

    # Sensory Cortex — data flowing in?
    sensory = {}
    try:
        from app.services.turbo_scanner import get_turbo_scanner
        ts = get_turbo_scanner()
        sensory["turbo_scanner"] = {"running": ts._running, "signals": ts._stats.get("total_signals", 0)}
    except Exception:
        sensory["turbo_scanner"] = {"running": False}
    try:
        from app.services.news_aggregator import get_news_aggregator
        sensory["news"] = get_news_aggregator().get_status()
    except Exception:
        sensory["news"] = {"running": False}
    try:
        from app.services.market_wide_sweep import get_market_sweep
        ms = get_market_sweep()
        sensory["sweep"] = {"running": ms._running, "universe": len(ms._universe)}
    except Exception:
        sensory["sweep"] = {"running": False}
    try:
        from app.services.hyper_swarm import get_hyper_swarm
        hs = get_hyper_swarm()
        sensory["hyper_swarm"] = {"running": hs._running, "triaged": hs._stats.get("total_triaged", 0)}
    except Exception:
        sensory["hyper_swarm"] = {"running": False}
    brain["sensory_cortex"] = sensory

    # Cerebral Cortex — scoring + ML
    cortex = {}
    try:
        from app.services.unified_profit_engine import get_unified_engine
        ue = get_unified_engine()
        cortex["unified_engine"] = ue.get_status()
    except Exception:
        cortex["unified_engine"] = {"running": False}
    try:
        from app.services.ml_scorer import get_ml_scorer
        cortex["ml_scorer"] = get_ml_scorer().get_status()
    except Exception:
        cortex["ml_scorer"] = {"model_loaded": False}
    brain["cerebral_cortex"] = cortex

    # Prefrontal Cortex — council
    prefrontal = {}
    try:
        from app.council.feedback_loop import get_agent_performance
        prefrontal["agent_performance"] = get_agent_performance()
    except Exception:
        prefrontal["agent_performance"] = {}
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        status = sa.get_status()
        prefrontal["agent_count"] = len(status)
        prefrontal["hibernated"] = sum(1 for a in status.values() if a.get("skip"))
    except Exception:
        prefrontal["agent_count"] = 17
        prefrontal["hibernated"] = 0
    brain["prefrontal_cortex"] = prefrontal

    # Motor Cortex — execution
    motor = {}
    try:
        from app.services.order_executor import OrderExecutor
        # Get from the global instance in main.py
        from app.main import _order_executor
        if _order_executor:
            motor["executor"] = _order_executor.get_status()
    except Exception:
        motor["executor"] = {}
    try:
        from app.services.position_manager import get_position_manager
        motor["position_manager"] = get_position_manager().get_status()
    except Exception:
        motor["position_manager"] = {"running": False}
    brain["motor_cortex"] = motor

    # Cerebellum — feedback loop
    cerebellum = {}
    try:
        from app.services.outcome_tracker import get_outcome_tracker
        ot = get_outcome_tracker()
        cerebellum["outcome_tracker"] = ot.get_status()
        cerebellum["kelly_params"] = ot.get_kelly_params()
    except Exception:
        cerebellum["outcome_tracker"] = {"running": False}
        cerebellum["kelly_params"] = {}
    brain["cerebellum"] = cerebellum

    # Risk Shield
    risk_shield = {}
    try:
        from app.council.homeostasis import get_homeostasis
        h = get_homeostasis()
        risk_shield["mode"] = h.get_mode()
        risk_shield["position_scale"] = h.get_position_scale()
        brain["mode"] = h.get_mode()
    except Exception:
        risk_shield["mode"] = "NORMAL"
    try:
        from app.council.reflexes.circuit_breaker import _get_thresholds
        risk_shield["circuit_breaker"] = _get_thresholds()
    except Exception:
        pass
    brain["risk_shield"] = risk_shield

    # Health summary
    running_count = sum(1 for s in sensory.values() if isinstance(s, dict) and s.get("running"))
    brain["health"] = {
        "sensory_systems_active": running_count,
        "ml_model_loaded": cortex.get("ml_scorer", {}).get("model_loaded", False),
        "feedback_loop_calibrated": cerebellum.get("outcome_tracker", {}).get("kelly_calibrated", False),
        "win_rate": cerebellum.get("outcome_tracker", {}).get("win_rate", 0),
        "total_pnl": cerebellum.get("outcome_tracker", {}).get("total_pnl", 0),
    }

    return brain


@router.get("/council/last-verdict")
async def council_last_verdict():
    """Get the latest council verdict (alias for council/latest with extra metadata)."""
    try:
        from app.api.v1.council import _latest_decision
        from app.council.homeostasis import get_homeostasis
        h = get_homeostasis()

        result = {
            "verdict": _latest_decision,
            "homeostasis_mode": h.get_mode(),
            "position_scale": h.get_position_scale(),
        }
        return result
    except Exception as e:
        logger.error("Last verdict failed: %s", e)
        return {"verdict": None, "homeostasis_mode": "NORMAL", "position_scale": 1.0}
