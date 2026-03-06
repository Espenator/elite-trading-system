"""Council API — evaluate symbols through the 13-agent council.

Existing:
  POST /api/v1/council/evaluate        -> full DecisionPacket
  GET  /api/v1/council/status          -> council configuration (13 agents, 7 stages)
  GET  /api/v1/council/latest          -> most recent DecisionPacket
  GET  /api/v1/council/weights         -> current agent weights (Bayesian-updated)
  POST /api/v1/council/weights/reset   -> reset weights to defaults

Glass Box cockpit additions:
  GET  /api/v1/council/latest-decision -> Decision Header (symbol, direction, confidence, votes summary)
  GET  /api/v1/council/agent-health    -> Agent Consensus Matrix (per-agent health + weights + streaks)
  GET  /api/v1/council/decision/{id}   -> Decision Replay (full vote reconstruction)
  GET  /api/v1/council/decisions       -> Recent decisions list (for replay browser)
  POST /api/v1/council/agent-config    -> Per-agent enable/disable toggles
  GET  /api/v1/council/gate-status     -> CouncilGate metrics (signals received, pass rate, etc.)
"""
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for the latest council decision (shown on dashboard)
_latest_decision: Optional[Dict[str, Any]] = None

# Decision history ring buffer for replay (kept in memory, also persisted to DuckDB)
_decision_history: deque = deque(maxlen=200)

# Per-agent enabled state (overrides; all enabled by default)
_agent_overrides: Dict[str, bool] = {}

# Rate limiting: max evaluations per minute to prevent DoS
_eval_timestamps: list = []
_RATE_LIMIT_MAX = 10  # Max 10 council evaluations per minute
_RATE_LIMIT_WINDOW = 60  # seconds


class CouncilEvalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    features: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class AgentConfigRequest(BaseModel):
    agent_name: str
    enabled: bool


def _check_rate_limit():
    """Enforce rate limiting on council evaluations."""
    now = time.time()
    _eval_timestamps[:] = [t for t in _eval_timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_eval_timestamps) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_RATE_LIMIT_MAX} evaluations per minute",
        )
    _eval_timestamps.append(now)


def _store_decision(result: Dict[str, Any]):
    """Store decision in ring buffer and attempt DuckDB persistence."""
    _decision_history.append(result)
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS council_decisions (
                decision_id VARCHAR PRIMARY KEY,
                symbol VARCHAR,
                timestamp VARCHAR,
                final_direction VARCHAR,
                final_confidence DOUBLE,
                vetoed BOOLEAN,
                execution_ready BOOLEAN,
                payload JSON
            )
        """)
        import json
        conn.execute(
            "INSERT OR REPLACE INTO council_decisions VALUES (?,?,?,?,?,?,?,?)",
            [
                result.get("council_decision_id", ""),
                result.get("symbol", ""),
                result.get("timestamp", ""),
                result.get("final_direction", ""),
                result.get("final_confidence", 0),
                result.get("vetoed", False),
                result.get("execution_ready", False),
                json.dumps(result),
            ],
        )
    except Exception as e:
        logger.debug("DuckDB decision persist skipped: %s", e)


@router.post("/evaluate", dependencies=[Depends(require_auth)])
async def evaluate_symbol(req: CouncilEvalRequest):
    """Run the 13-agent council on a symbol and return DecisionPacket."""
    global _latest_decision
    _check_rate_limit()
    try:
        from app.council.runner import run_council

        decision = await run_council(
            symbol=req.symbol,
            timeframe=req.timeframe,
            features=req.features,
            context=req.context or {},
        )

        result = decision.to_dict()
        _latest_decision = result
        _store_decision(result)
        return result
    except Exception as e:
        logger.error("Council evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail="Council evaluation failed")


@router.get("/latest")
async def council_latest():
    """Return the most recent council DecisionPacket (if any)."""
    if _latest_decision is None:
        return {"status": "no_evaluation_yet", "votes": None}
    return _latest_decision


# ---------------------------------------------------------------------------
# Glass Box: Decision Header for dashboard strip
# ---------------------------------------------------------------------------
@router.get("/latest-decision")
async def council_latest_decision():
    """Summarised latest decision for the Dashboard Decision Header strip.

    Returns a lightweight object: symbol, direction, confidence, vote breakdown,
    cognitive mode, and timestamp — suitable for a top-bar widget.
    """
    if _latest_decision is None:
        return {"status": "no_decision", "decision": None}

    votes = _latest_decision.get("votes") or []
    buy_count = sum(1 for v in votes if v.get("direction") == "buy")
    sell_count = sum(1 for v in votes if v.get("direction") == "sell")
    hold_count = sum(1 for v in votes if v.get("direction") == "hold")

    cognitive = _latest_decision.get("cognitive") or {}

    return {
        "status": "ok",
        "decision": {
            "council_decision_id": _latest_decision.get("council_decision_id"),
            "symbol": _latest_decision.get("symbol"),
            "final_direction": _latest_decision.get("final_direction"),
            "final_confidence": _latest_decision.get("final_confidence"),
            "vetoed": _latest_decision.get("vetoed", False),
            "execution_ready": _latest_decision.get("execution_ready", False),
            "timestamp": _latest_decision.get("timestamp"),
            "vote_summary": {
                "buy": buy_count,
                "sell": sell_count,
                "hold": hold_count,
                "total": len(votes),
            },
            "cognitive_mode": cognitive.get("mode", "exploit"),
            "total_latency_ms": cognitive.get("total_latency_ms", 0),
            "council_reasoning": _latest_decision.get("council_reasoning", ""),
        },
    }


# ---------------------------------------------------------------------------
# Glass Box: Agent Consensus Matrix (health + weights + streaks per agent)
# ---------------------------------------------------------------------------
@router.get("/agent-health")
async def council_agent_health():
    """Per-agent health matrix combining self_awareness + weight_learner data.

    Used by the Agent Consensus Matrix panel in the Glass Box cockpit.
    """
    agents_data = []

    # Gather weights
    weights = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
    except Exception:
        pass

    # Gather self-awareness data (Bayesian weights, streaks, health)
    sa_status = {}
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        sa_status = sa.get_status()
    except Exception:
        pass

    # Gather feedback loop accuracy
    agent_perf = {}
    try:
        from app.council.feedback_loop import get_agent_performance
        agent_perf = get_agent_performance()
    except Exception:
        pass

    # Latest votes (if any)
    latest_votes = {}
    if _latest_decision and _latest_decision.get("votes"):
        for v in _latest_decision["votes"]:
            latest_votes[v.get("agent_name", "")] = v

    agent_names = [
        "market_perception", "flow_perception", "regime", "intermarket",
        "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
        "hypothesis", "strategy", "risk", "execution", "critic",
        "bull_debater", "bear_debater", "red_team",
    ]

    for name in agent_names:
        health_info = sa_status.get("health", {}).get(name, {})
        streak_info = sa_status.get("streaks", {}).get(name, {})
        bayesian_info = sa_status.get("bayesian", {}).get(name, {})
        perf = agent_perf.get(name, {})
        vote = latest_votes.get(name)

        agents_data.append({
            "agent_name": name,
            "weight": weights.get(name, 1.0),
            "bayesian_mean": bayesian_info.get("mean", 0.5),
            "streak_status": streak_info.get("status", "ACTIVE"),
            "streak_count": streak_info.get("current_streak", 0),
            "healthy": health_info.get("healthy", True),
            "error_rate": health_info.get("error_rate", 0.0),
            "avg_latency_ms": health_info.get("avg_latency_ms", 0.0),
            "accuracy": perf.get("accuracy", None),
            "total_decisions": perf.get("total", 0),
            "enabled": _agent_overrides.get(name, True),
            "latest_vote": {
                "direction": vote.get("direction"),
                "confidence": vote.get("confidence"),
                "reasoning": vote.get("reasoning", "")[:200],
            } if vote else None,
        })

    return {"agents": agents_data, "total": len(agents_data)}


# ---------------------------------------------------------------------------
# Glass Box: Decision Replay (full vote reconstruction for a past decision)
# ---------------------------------------------------------------------------
@router.get("/decision/{decision_id}")
async def council_decision_replay(decision_id: str):
    """Reconstruct a past council decision for the Decision Replay panel.

    Tries in-memory ring buffer first, then falls back to DuckDB.
    """
    # Check in-memory ring buffer
    for d in _decision_history:
        if d.get("council_decision_id") == decision_id:
            return {"status": "ok", "decision": d}

    # Fallback to DuckDB
    try:
        import json
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        row = conn.execute(
            "SELECT payload FROM council_decisions WHERE decision_id = ?",
            [decision_id],
        ).fetchone()
        if row:
            return {"status": "ok", "decision": json.loads(row[0])}
    except Exception as e:
        logger.debug("DuckDB decision lookup failed: %s", e)

    raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")


@router.get("/decisions")
async def council_decisions(limit: int = 50):
    """List recent council decisions (lightweight summaries for replay browser)."""
    # Try DuckDB first for persistence
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        rows = conn.execute(
            """SELECT decision_id, symbol, timestamp, final_direction,
                      final_confidence, vetoed, execution_ready
               FROM council_decisions
               ORDER BY timestamp DESC
               LIMIT ?""",
            [limit],
        ).fetchall()
        if rows:
            return {
                "decisions": [
                    {
                        "council_decision_id": r[0],
                        "symbol": r[1],
                        "timestamp": r[2],
                        "final_direction": r[3],
                        "final_confidence": r[4],
                        "vetoed": r[5],
                        "execution_ready": r[6],
                    }
                    for r in rows
                ],
                "total": len(rows),
            }
    except Exception:
        pass

    # Fallback to in-memory ring buffer
    decisions = []
    for d in reversed(_decision_history):
        decisions.append({
            "council_decision_id": d.get("council_decision_id"),
            "symbol": d.get("symbol"),
            "timestamp": d.get("timestamp"),
            "final_direction": d.get("final_direction"),
            "final_confidence": d.get("final_confidence"),
            "vetoed": d.get("vetoed", False),
            "execution_ready": d.get("execution_ready", False),
        })
        if len(decisions) >= limit:
            break
    return {"decisions": decisions, "total": len(decisions)}


# ---------------------------------------------------------------------------
# Glass Box: Per-agent enable/disable config
# ---------------------------------------------------------------------------
@router.post("/agent-config", dependencies=[Depends(require_auth)])
async def set_agent_config(req: AgentConfigRequest):
    """Enable or disable a specific council agent.

    Disabled agents will be skipped in future council evaluations.
    """
    valid_agents = {
        "market_perception", "flow_perception", "regime", "intermarket",
        "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
        "hypothesis", "strategy", "risk", "execution", "critic",
        "bull_debater", "bear_debater", "red_team",
    }
    if req.agent_name not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent_name}")

    _agent_overrides[req.agent_name] = req.enabled
    logger.info("Agent %s %s by operator", req.agent_name, "enabled" if req.enabled else "disabled")

    return {
        "status": "ok",
        "agent_name": req.agent_name,
        "enabled": req.enabled,
        "all_overrides": dict(_agent_overrides),
    }


@router.get("/agent-config")
async def get_agent_config():
    """Return current per-agent enable/disable overrides."""
    return {"overrides": dict(_agent_overrides)}


# ---------------------------------------------------------------------------
# Glass Box: CouncilGate status (signal flow metrics)
# ---------------------------------------------------------------------------
@router.get("/gate-status")
async def council_gate_status():
    """Return CouncilGate metrics: signals received, councils invoked, pass rate."""
    try:
        from app.council.council_gate import CouncilGate
        # The gate instance is created in main.py; access via module globals
        import app.main as main_mod
        gate = getattr(main_mod, "_council_gate", None)
        if gate:
            return {"status": "ok", "gate": gate.get_status()}
        return {"status": "gate_not_running", "gate": None}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/status")
async def council_status():
    """Return council configuration and agent list (13 agents, 7 stages)."""
    import os

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
        "agent_count": 13,
        "agents": [
            "market_perception",
            "flow_perception",
            "regime",
            "intermarket",
            "rsi",
            "bbv",
            "ema_trend",
            "relative_strength",
            "cycle_timing",
            "hypothesis",
            "strategy",
            "risk",
            "execution",
            "critic",
        ],
        "dag_stages": [
            ["market_perception", "flow_perception", "regime", "intermarket"],
            ["rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing"],
            ["hypothesis"],
            ["strategy"],
            ["risk", "execution"],
            ["critic"],
            ["arbiter"],
        ],
        "agent_weights": agent_weights,
        "agent_overrides": dict(_agent_overrides),
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
        return {"status": "weight_learner_unavailable", "error": str(e)}


@router.post("/weights/reset", dependencies=[Depends(require_auth)])
async def reset_weights():
    """Reset agent weights to defaults."""
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        learner.reset()
        return {"status": "ok", "weights": learner.get_weights()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
