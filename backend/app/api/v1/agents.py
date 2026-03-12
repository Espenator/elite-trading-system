"""
Agent Command Center API — status and control of the 5 data-collection tick agents.

⚠️  ARCHITECTURE NOTE (March 2026 audit):
These 5 "System 1" template agents are LEGACY polling shims from the pre-event-driven
architecture. The real trading intelligence runs through:
  - 35-agent council DAG (see /api/v1/council/status)
  - Event-driven pipeline: AlpacaStream → MessageBus → SignalEngine → CouncilGate
  - <1s latency for 800+ symbols via WebSocket

These polling agents remain because:
  1. Market Data Agent (id=1) still handles non-WebSocket sources (Finviz, FRED, EDGAR)
  2. Frontend AgentCommandCenter polls GET /agents every 15s for status display
  3. The tick functions call real services (market_data_agent, signal_engine, ml_engine)

The GET endpoints and status display are actively used by the frontend.
The POST start/stop/tick endpoints are rarely called manually.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from app.core.security import require_auth

from app.websocket_manager import broadcast_ws
from app.services.database import db_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_process_metrics():
    try:
        import psutil

        p = psutil.Process(os.getpid())
        cpu = p.cpu_percent(interval=0.1)
        mem_mb = round(p.memory_info().rss / (1024 * 1024))
        now_ts = datetime.now(timezone.utc).timestamp()
        uptime_sec = max(0, int(now_ts - p.create_time()))
        d, r = divmod(uptime_sec, 86400)
        h, r = divmod(r, 3600)
        m, _ = divmod(r, 60)
        parts = [f"{d}d"] if d else []
        if h or parts:
            parts.append(f"{h}h")
        parts.append(f"{m}m")
        return {
            "cpuPercent": round(cpu, 1),
            "memoryMb": mem_mb,
            "uptime": " ".join(parts),
        }
    except Exception:
        return None


def _get_last_tick_at(agent_id: int):
    return db_service.get_config(f"agent_{agent_id}_last_tick_at")


def _set_last_tick_at(agent_id: int):
    db_service.set_config(
        f"agent_{agent_id}_last_tick_at", datetime.now(timezone.utc).isoformat()
    )


def _get_current_task(agent_id: int):
    return db_service.get_config(f"agent_{agent_id}_current_task")


def _set_current_task(agent_id: int, task: str):
    if task:
        db_service.set_config(f"agent_{agent_id}_current_task", (task or "")[:200])


# Persisted agent status (keyed by agent id); GET merges this over template
def _get_agent_status():
    return db_service.get_config("agent_status") or {}


def _set_agent_status(agent_id: int, status: str):
    s = _get_agent_status()
    s[str(agent_id)] = status
    db_service.set_config("agent_status", s)


def _append_log(agent_name: str, message: str, level: str = "info"):
    logs = db_service.get_config("agent_activity_log") or []
    now = datetime.now(timezone.utc)
    logs.insert(
        0,
        {
            "time": now.strftime("%H:%M:%S"),
            "agent": agent_name,
            "message": message,
            "level": level,
        },
    )
    db_service.set_config("agent_activity_log", logs[:100])


_AGENTS_TEMPLATE = [
    {
        "id": 1,
        "name": "Market Data Agent",
        "status": "running",
        "cpuPercent": 0,
        "memoryMb": 0,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Awaiting first tick",
        "currentTask": "Idle — waiting for first scan cycle",
        "description": "Scans Finviz Elite, Alpaca, Unusual Whales; pulls FRED economic data, SEC EDGAR filings. Runs every 60s during market hours.",
        "config": {
            "runIntervalSec": 60,
            "marketHoursOnly": True,
            "sources": ["finviz", "alpaca", "unusual_whales", "fred", "sec_edgar"],
        },
    },
    {
        "id": 2,
        "name": "Signal Generation Agent",
        "status": "running",
        "cpuPercent": 0,
        "memoryMb": 0,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Awaiting first tick",
        "currentTask": "Idle — waiting for signal generation cycle",
        "description": "Takes raw data from Market Data Agent; applies technical analysis, chart patterns, momentum algos; generates composite signal scores (0-100).",
        "config": {
            "minCompositeScore": 70,
            "timeframes": ["1m", "5m", "1H", "1D"],
            "autoAlert": True,
        },
    },
    {
        "id": 3,
        "name": "ML Learning Agent",
        "status": "running",
        "cpuPercent": 0,
        "memoryMb": 0,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Awaiting first inference",
        "currentTask": "Idle — waiting for next retrain cycle",
        "description": "XGBoost/LightGBM on GPU via CUDA. Trains on historical outcomes. Sunday full retrain (schedulable). Flywheel: outcome resolver feeds accuracy back.",
        "config": {"retrainDay": "sunday", "minAccuracy": 0.65, "gpuEnabled": True},
    },
    {
        "id": 4,
        "name": "Sentiment Agent",
        "status": "running",
        "cpuPercent": 0,
        "memoryMb": 0,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Awaiting first poll",
        "currentTask": "Idle — waiting for sentiment poll cycle",
        "description": "Aggregates from Stockgeist, News API, Discord, X (Twitter). NLP sentiment scoring per ticker; unusual sentiment spike detection.",
        "config": {
            "sources": ["stockgeist", "news_api", "discord", "twitter"],
            "spikeThreshold": 1.5,
        },
    },
    {
        "id": 5,
        "name": "YouTube Knowledge Agent",
        "status": "running",
        "cpuPercent": 0,
        "memoryMb": 0,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Awaiting first ingestion",
        "currentTask": "Idle — waiting for transcript processing",
        "description": "Ingests transcripts from financial YouTube videos; extracts trading ideas, technical analysis concepts; feeds into ML feature engineering. 24/7 self-learning flywheel.",
        "config": {"channels": 8, "autoProcess": True, "extractAlgos": True},
    },
]

_DEFAULT_LOGS: list = []  # No mock logs — real activity populates via _append_log()


def _get_all_agents():
    """Return the full agent template list. Used by swarm/team/alert/resource endpoints."""
    return _AGENTS_TEMPLATE


def _effective_status(agent_id: int) -> str:
    """Get persisted status for a single agent, falling back to template default."""
    a = next((x for x in _AGENTS_TEMPLATE if x["id"] == agent_id), None)
    default = a["status"] if a else "stopped"
    return _get_agent_status().get(str(agent_id), default)


@router.get("")
async def get_agents():
    """Return all 5 agents with status, last_actions per agent, and global logs."""
    status_overrides = _get_agent_status()
    stored_logs = db_service.get_config("agent_activity_log")
    logs = (
        stored_logs if isinstance(stored_logs, list) and stored_logs else []
    ) or _DEFAULT_LOGS.copy()

    real_metrics = _get_process_metrics()
    agents = []
    for a in _AGENTS_TEMPLATE:
        status = status_overrides.get(str(a["id"]), a["status"])
        last_actions = [
            {
                "time": log["time"],
                "message": log["message"],
                "level": log.get("level", "info"),
            }
            for log in logs
            if log.get("agent") == a["name"]
        ][:100]
        payload = {**a, "status": status, "last_actions": last_actions}
        if real_metrics:
            payload["cpuPercent"] = real_metrics["cpuPercent"]
            payload["memoryMb"] = real_metrics["memoryMb"]
            payload["uptime"] = real_metrics["uptime"]
        payload["cpu"] = payload.get("cpuPercent", 0)
        payload["mem"] = payload.get("memoryMb", 0)
        payload["statusDisplay"] = (status or "stopped").capitalize()
        payload["last_tick_at"] = _get_last_tick_at(a["id"])
        stored_task = _get_current_task(a["id"])
        if stored_task:
            payload["currentTask"] = stored_task
        agents.append(payload)
    return {"agents": agents, "logs": logs}


def _agent_by_id(agent_id: int):
    a = next((x for x in _AGENTS_TEMPLATE if x["id"] == agent_id), None)
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


async def _run_market_data_tick():
    """Run one Market Data Agent tick (Finviz, Alpaca, FRED/EDGAR/UW) and append logs."""
    from app.services.market_data_agent import run_tick, AGENT_NAME

    entries = await run_tick()
    for msg, level in entries:
        _append_log(AGENT_NAME, msg, level)
    _set_last_tick_at(1)
    _set_current_task(
        1, entries[0][0][:200] if entries else "Scanning Finviz Elite + Alpaca bars"
    )


async def run_market_data_tick_if_running():
    if _effective_status(1) != "running":
        return
    await _run_market_data_tick()
    await broadcast_ws(
        "agents",
        {"type": "tick_completed", "agent_id": 1, "last_tick_at": _get_last_tick_at(1)},
    )


async def _run_signal_generation_tick():
    """Run one Signal Generation Agent tick: symbol_universe + momentum/pattern → composite scores 0-100."""
    from app.services.signal_engine import run_tick

    agent_name = _agent_by_id(2)["name"]
    try:
        entries = await run_tick()
        for msg, level in entries:
            _append_log(agent_name, msg, level)
        _set_last_tick_at(2)
        _set_current_task(
            2, entries[0][0][:200] if entries else "Applying momentum algo to watchlist"
        )
    except Exception as e:
        logger.exception("Signal generation tick failed")
        _append_log(agent_name, f"Tick failed: {str(e)[:80]}", "warning")
        _set_current_task(2, f"Error: {str(e)[:80]}")


async def _run_ml_learning_tick():
    """Run one ML Learning Agent tick: Sunday retrain (XGBoost/LightGBM GPU) or idle + flywheel stats."""
    from app.modules.ml_engine import run_tick as ml_run_tick

    agent_name = _agent_by_id(3)["name"]
    try:
        entries = await ml_run_tick()
        for msg, level in entries:
            _append_log(agent_name, msg, level)
        _set_last_tick_at(3)
        _set_current_task(
            3, entries[0][0][:200] if entries else "Idle until next Sunday retrain"
        )
    except Exception as e:
        logger.exception("ML Learning tick failed")
        _append_log(agent_name, f"Tick failed: {str(e)[:80]}", "warning")
        _set_current_task(3, f"Error: {str(e)[:80]}")


async def _run_sentiment_tick():
    """Run one Sentiment Agent tick: aggregate Stockgeist/News/Discord/X, NLP score per ticker, spike detection."""
    from app.modules.social_news_engine import run_tick as sentiment_run_tick

    agent_name = _agent_by_id(4)["name"]
    try:
        entries = sentiment_run_tick()
        for msg, level in entries:
            _append_log(agent_name, msg, level)
        _set_last_tick_at(4)
        _set_current_task(
            4,
            entries[0][0][:200] if entries else "Polling Stockgeist, News, Discord, X",
        )
    except Exception as e:
        logger.exception("Sentiment tick failed")
        _append_log(agent_name, f"Tick failed: {str(e)[:80]}", "warning")
        _set_current_task(4, f"Error: {str(e)[:80]}")


async def _run_youtube_knowledge_tick():
    """Run one YouTube Knowledge Agent tick: fetch transcripts, extract ideas/concepts, feed ML."""
    from app.modules.youtube_agent import run_tick as youtube_run_tick

    agent_name = _agent_by_id(5)["name"]
    try:
        entries = youtube_run_tick()
        for msg, level in entries:
            _append_log(agent_name, msg, level)
        _set_last_tick_at(5)
        _set_current_task(
            5, entries[0][0][:200] if entries else "Processing YouTube transcripts"
        )
    except Exception as e:
        logger.exception("YouTube Knowledge tick failed")
        _append_log(agent_name, f"Tick failed: {str(e)[:80]}", "warning")
        _set_current_task(5, f"Error: {str(e)[:80]}")


@router.post("/{agent_id}/start", dependencies=[Depends(require_auth)])
async def start_agent(agent_id: int):
    """Start an agent; persist status and append to activity log.
    Market Data Agent (id=1): runs one tick (Finviz Elite, Alpaca, FRED/EDGAR/UW).
    Call POST /agents/1/tick every 60s (cron/scheduler) when running for periodic scan.
    """
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "running")
    _append_log(agent["name"], "Agent started", "success")
    if agent_id == 1:
        await _run_market_data_tick()
    elif agent_id == 2:
        await _run_signal_generation_tick()
    elif agent_id == 3:
        await _run_ml_learning_tick()
    elif agent_id == 4:
        await _run_sentiment_tick()
    elif agent_id == 5:
        await _run_youtube_knowledge_tick()
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "running"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "running"}


@router.post("/{agent_id}/tick", dependencies=[Depends(require_auth)])
async def run_agent_tick(agent_id: int):
    """Run one data-collection tick for an agent. For Market Data Agent (id=1): runs
    Finviz, Alpaca, FRED/EDGAR/UW. Call every 60s (configurable) when agent is running.
    Only runs if agent status is 'running' (no-op otherwise).
    """
    agent = _agent_by_id(agent_id)
    status = _effective_status(agent_id)
    if status != "running":
        return {"ok": True, "skipped": True, "reason": "agent_not_running"}
    if agent_id == 1:
        await _run_market_data_tick()
        await broadcast_ws(
            "agents",
            {
                "type": "tick_completed",
                "agent_id": agent_id,
                "last_tick_at": _get_last_tick_at(1),
            },
        )
    elif agent_id == 2:
        await _run_signal_generation_tick()
        await broadcast_ws(
            "agents",
            {
                "type": "tick_completed",
                "agent_id": agent_id,
                "last_tick_at": _get_last_tick_at(2),
            },
        )
    elif agent_id == 3:
        await _run_ml_learning_tick()
        await broadcast_ws(
            "agents",
            {
                "type": "tick_completed",
                "agent_id": agent_id,
                "last_tick_at": _get_last_tick_at(3),
            },
        )
    elif agent_id == 4:
        await _run_sentiment_tick()
        await broadcast_ws(
            "agents",
            {
                "type": "tick_completed",
                "agent_id": agent_id,
                "last_tick_at": _get_last_tick_at(4),
            },
        )
    elif agent_id == 5:
        await _run_youtube_knowledge_tick()
        await broadcast_ws(
            "agents",
            {
                "type": "tick_completed",
                "agent_id": agent_id,
                "last_tick_at": _get_last_tick_at(5),
            },
        )
    return {"ok": True, "agent_id": agent_id}


@router.post("/{agent_id}/stop", dependencies=[Depends(require_auth)])
async def stop_agent(agent_id: int):
    """Stop an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "stopped")
    _append_log(agent["name"], "Agent stopped", "info")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "stopped"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "stopped"}


@router.post("/{agent_id}/pause", dependencies=[Depends(require_auth)])
async def pause_agent(agent_id: int):
    """Pause an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "paused")
    _append_log(agent["name"], "Agent paused", "warning")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "paused"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "paused"}


@router.post("/{agent_id}/restart", dependencies=[Depends(require_auth)])
async def restart_agent(agent_id: int):
    """Restart an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "running")
    _append_log(agent["name"], "Agent restarted", "success")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "running"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "running"}


# --- Swarm Topology & ELO Leaderboard ---
@router.get("/swarm-topology")
async def get_swarm_topology():
    """Return agent network topology and ELO leaderboard for Swarm Topology panel."""
    agents = _get_all_agents()
    topology_nodes = []
    edges = []
    leaderboard = []

    for agent in agents:
        status = _effective_status(agent["id"])
        node = {
            "id": agent["id"],
            "name": agent["name"],
            "type": agent.get("type", "general"),
            "status": status,
            "elo": agent.get("elo", 1500),
            "win_pct": agent.get("win_pct", 50),
        }
        topology_nodes.append(node)
        leaderboard.append({
            "rank": 0,
            "agent": agent["name"],
            "elo": agent.get("elo", 1500),
            "win_pct": agent.get("win_pct", 50),
        })

    # Sort leaderboard by ELO descending
    leaderboard.sort(key=lambda x: x["elo"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    # Generate edges based on agent communication patterns
    agent_ids = [a["id"] for a in agents]
    for i, aid in enumerate(agent_ids):
        for j in range(i + 1, len(agent_ids)):
            edges.append({"source": aid, "target": agent_ids[j], "weight": 1})

    return {
        "nodes": topology_nodes,
        "edges": edges[:20],
        "leaderboard": leaderboard[:10],
    }


@router.get("/swarm-topology/{symbol}")
async def get_swarm_topology_for_symbol(symbol: str):
    """Same as GET /swarm-topology; symbol is optional (Dashboard per-symbol panel)."""
    return await get_swarm_topology()


# --- Conference Pipeline ---
@router.get("/conference")
async def get_conference_status():
    """Return current conference pipeline status and last conference result."""
    conference_data = db_service.get_config("last_conference")
    pipeline_stages = ["Researcher", "RiskOfficer", "Adversary", "Arbitrator"]

    # Build votes as array for frontend (LastConference expects [{agent, vote}])
    votes_obj = conference_data.get("votes", {}) if conference_data else {}
    votes_array = [
        {"agent": agent, "vote": v if isinstance(v, (int, float)) else 50}
        for agent, v in votes_obj.items()
    ] if isinstance(votes_obj, dict) else []

    last_conf = {
        "ticker": conference_data.get("ticker", "N/A") if conference_data else "N/A",
        "symbol": conference_data.get("ticker", "N/A") if conference_data else "N/A",
        "verdict": conference_data.get("verdict", "N/A") if conference_data else "N/A",
        "confidence": conference_data.get("confidence", 0) if conference_data else 0,
        "duration": conference_data.get("duration", 0) if conference_data else 0,
        "votes": votes_array,
    }

    return {
        "pipeline": pipeline_stages,
        "current_stage": db_service.get_config("conference_current_stage") or "idle",
        "last_conference": last_conf,
        "current": last_conf,
        "conference": last_conf,
        "total_conferences": int(db_service.get_config("conference_count") or 0),
    }


@router.get("/consensus")
async def get_consensus():
    """Agent consensus for Dashboard. Returns votes as array + top-level verdict/agreement."""
    conf = await get_conference_status()
    last = conf.get("last_conference") or {}
    # Convert votes object {agent: vote_str} to array [{name, vote, confidence}]
    votes_obj = last.get("votes") or {}
    votes_array = [
        {"name": agent, "vote": v if isinstance(v, str) else (v.get("vote", "HOLD") if isinstance(v, dict) else "HOLD"),
         "confidence": (v.get("confidence", 50) if isinstance(v, dict) else 50)}
        for agent, v in votes_obj.items()
    ] if isinstance(votes_obj, dict) else []
    verdict = last.get("verdict", "N/A")
    confidence = last.get("confidence", 0)
    return {
        "votes": votes_array,
        "agents": votes_array,
        "verdict": verdict,
        "consensus": verdict,
        "agreement_percent": confidence,
        "agreement": confidence,
        "ticker": last.get("ticker", "N/A"),
        "pipeline": conf.get("pipeline", []),
        "current_stage": conf.get("current_stage", "idle"),
        "total_conferences": conf.get("total_conferences", 0),
    }


# --- Team Status ---
@router.get("/teams")
async def get_team_status():
    """Return agent team groupings and health metrics."""
    agents = _get_all_agents()
    teams = {}

    for agent in agents:
        team = agent.get("team", "default")
        if team not in teams:
            teams[team] = {"name": team, "agents": 0, "active": 0, "health": 0}
        teams[team]["agents"] += 1
        status = _effective_status(agent["id"])
        if status == "running":
            teams[team]["active"] += 1

    result = []
    for team_name, team_data in teams.items():
        health = round(team_data["active"] / max(team_data["agents"], 1) * 100)
        team_data["health"] = health
        team_data["status"] = "ACTIVE" if health >= 80 else "DEGRADED" if health >= 50 else "DOWN"
        result.append(team_data)

    return {"teams": result}


# --- Drift Monitor ---
@router.get("/drift")
async def get_drift_metrics():
    """Return model drift metrics for the Drift Monitor panel."""
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        if hasattr(monitor, 'get_metrics'):
            return monitor.get_metrics()
    except Exception:
        pass

    # No drift data available — return honest empty state
    return {
        "metrics": [],
        "mean_psi": 0.0,
        "drift_detected": False,
        "status": "no_data",
        "message": "Drift monitor not available — no metrics collected yet",
    }


# --- System Alerts ---
@router.get("/alerts")
async def get_system_alerts():
    """Return active system alerts for the Agent Command Center."""
    alerts = []
    agents = _get_all_agents()

    # Check for unresponsive agents
    for agent in agents:
        last_tick = _get_last_tick_at(agent["id"])
        if last_tick:
            try:
                last_dt = datetime.fromisoformat(last_tick)
                elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if elapsed > 720:  # 12 minutes
                    alerts.append({
                        "level": "RED",
                        "message": f"{agent['name']} unresponsive — no heartbeat for {int(elapsed/60)}m",
                        "agent_id": agent["id"],
                    })
                elif elapsed > 300:  # 5 minutes
                    alerts.append({
                        "level": "AMBER",
                        "message": f"{agent['name']} slow heartbeat — {int(elapsed/60)}m since last tick",
                        "agent_id": agent["id"],
                    })
            except Exception:
                pass

    # Check process metrics
    metrics = _get_process_metrics()
    if metrics:
        if metrics.get("memoryMb", 0) > 3500:
            alerts.append({"level": "AMBER", "message": f"GPU memory at {metrics['memoryMb']}MB — approaching threshold"})

    # Add system status info
    if not alerts:
        alerts.append({"level": "INFO", "message": "All agents operating normally"})

    return {"alerts": alerts}


# --- Agent Resource Monitor ---
@router.get("/resources")
async def get_agent_resources():
    """Return per-agent resource usage for the Agent Resource Monitor panel."""
    agents = _get_all_agents()
    resources = []

    real_metrics = _get_process_metrics()
    for agent in agents:
        status = _effective_status(agent["id"])
        resources.append({
            "agent": agent["name"],
            "cpu_pct": real_metrics["cpuPercent"] if real_metrics else 0,
            "mem_mb": real_metrics["memoryMb"] if real_metrics else 0,
            "tokens_hr": 0,
            "status": status,
        })

    return {"resources": resources}


# --- HITL Ring Buffer ---
_hitl_buffer = []  # In-memory HITL queue
_hitl_stats = {"approved": 0, "rejected": 0, "deferred": 0, "total": 0}

@router.get("/hitl/buffer")
async def get_hitl_buffer():
    """Return current HITL ring buffer contents."""
    return {
        "items": _hitl_buffer[-50:],
        "stats": _hitl_stats,
        "buffer_size": len(_hitl_buffer),
        "max_size": 50,
        "fill_pct": round(len(_hitl_buffer) / 50 * 100, 1),
        "overflow_policy": "BLOCK",
        "avg_approve_threshold": 0.75,
    }

@router.post("/hitl/{item_id}/approve", dependencies=[Depends(require_auth)])
async def approve_hitl(item_id: str):
    """Approve an HITL item."""
    for item in _hitl_buffer:
        if str(item.get("id")) == item_id:
            item["status"] = "APPROVED"
            item["resolved_at"] = datetime.now(timezone.utc).isoformat()
            _hitl_stats["approved"] += 1
            _append_log("HITL", f"Approved item {item_id}", "success")
            await broadcast_ws("agents", {"type": "hitl_resolved", "item_id": item_id, "action": "approve"})
            return {"ok": True, "item_id": item_id, "action": "approved"}
    raise HTTPException(status_code=404, detail=f"HITL item {item_id} not found")

@router.post("/hitl/{item_id}/reject", dependencies=[Depends(require_auth)])
async def reject_hitl(item_id: str):
    """Reject an HITL item."""
    for item in _hitl_buffer:
        if str(item.get("id")) == item_id:
            item["status"] = "REJECTED"
            item["resolved_at"] = datetime.now(timezone.utc).isoformat()
            _hitl_stats["rejected"] += 1
            _append_log("HITL", f"Rejected item {item_id}", "warning")
            await broadcast_ws("agents", {"type": "hitl_resolved", "item_id": item_id, "action": "reject"})
            return {"ok": True, "item_id": item_id, "action": "rejected"}
    raise HTTPException(status_code=404, detail=f"HITL item {item_id} not found")

@router.post("/hitl/{item_id}/defer", dependencies=[Depends(require_auth)])
async def defer_hitl(item_id: str):
    """Defer an HITL item."""
    for item in _hitl_buffer:
        if str(item.get("id")) == item_id:
            item["status"] = "DEFERRED"
            _hitl_stats["deferred"] += 1
            _append_log("HITL", f"Deferred item {item_id}", "info")
            return {"ok": True, "item_id": item_id, "action": "deferred"}
    raise HTTPException(status_code=404, detail=f"HITL item {item_id} not found")

@router.get("/hitl/stats")
async def get_hitl_stats():
    """Return HITL analytics."""
    total = _hitl_stats["approved"] + _hitl_stats["rejected"] + _hitl_stats["deferred"]
    return {
        **_hitl_stats,
        "total": total,
        "approval_rate": round(_hitl_stats["approved"] / max(total, 1), 3),
        "avg_review_time_sec": 0,
        "buffer_fill_pct": round(len(_hitl_buffer) / 50 * 100, 1),
    }


# --- Agent Extended Config ---
_agent_configs = {}  # agent_id -> {weight, confidence_threshold, temperature, context_window, priority}

@router.get("/all-config")
async def get_all_agent_config():
    """Return all agents with their full configuration for Node Control table."""
    agents = _get_all_agents()
    status_overrides = _get_agent_status()
    result = []
    for agent in agents:
        aid = agent["id"]
        config = _agent_configs.get(str(aid), {})
        result.append({
            **agent,
            "status": status_overrides.get(str(aid), agent["status"]),
            "weight": config.get("weight", 1.0),
            "confidence_threshold": config.get("confidence_threshold", 0.65),
            "temperature": config.get("temperature", 0.7),
            "context_window": config.get("context_window", 4096),
            "priority": config.get("priority", "medium"),
            "load_pct": config.get("load_pct", 0),
            "accuracy_pct": config.get("accuracy_pct", 0),
            "reach_trades": config.get("reach_trades", 0),
        })
    # Include all council agents from canonical registry
    try:
        from app.council.registry import get_agents as get_council_agents
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
        council_agent_names = get_council_agents()
        for i, name in enumerate(council_agent_names):
            aid = 100 + i
            config = _agent_configs.get(str(aid), {})
            result.append({
                "id": aid,
                "name": name.replace("_", " ").title(),
                "type": "council",
                "status": "running",
                "weight": weights.get(name, config.get("weight", 1.0)),
                "confidence_threshold": config.get("confidence_threshold", 0.65),
                "temperature": config.get("temperature", 0.7),
                "context_window": config.get("context_window", 4096),
                "priority": config.get("priority", "medium"),
                "load_pct": config.get("load_pct", 0),
                "accuracy_pct": config.get("accuracy_pct", 0),
                "reach_trades": config.get("reach_trades", 0),
            })
    except Exception:
        pass
    return {"agents": result}

@router.put("/{agent_id}/config", dependencies=[Depends(require_auth)])
async def update_agent_config(agent_id: int, payload: dict):
    """Update agent config: weight, confidence_threshold, temperature, context_window, priority."""
    allowed_keys = {"weight", "confidence_threshold", "temperature", "context_window", "priority", "load_pct"}
    config = _agent_configs.get(str(agent_id), {})
    for k, v in payload.items():
        if k in allowed_keys:
            config[k] = v
    _agent_configs[str(agent_id)] = config
    agent_name = f"Agent-{agent_id}"
    for a in _AGENTS_TEMPLATE:
        if a["id"] == agent_id:
            agent_name = a["name"]
            break
    _append_log(agent_name, f"Config updated: {list(payload.keys())}", "info")
    await broadcast_ws("agents", {"type": "config_updated", "agent_id": agent_id, "config": config})
    return {"ok": True, "agent_id": agent_id, "config": config}


# --- Batch Agent Operations ---
@router.post("/batch/start", dependencies=[Depends(require_auth)])
async def batch_start_agents():
    """Start all agents."""
    results = []
    for agent in _AGENTS_TEMPLATE:
        _set_agent_status(agent["id"], "running")
        _append_log(agent["name"], "Agent started (batch)", "success")
        results.append({"agent_id": agent["id"], "status": "running"})
    await broadcast_ws("agents", {"type": "batch_status_changed", "status": "running"})
    return {"ok": True, "results": results}

@router.post("/batch/stop", dependencies=[Depends(require_auth)])
async def batch_stop_agents():
    """Stop all agents."""
    results = []
    for agent in _AGENTS_TEMPLATE:
        _set_agent_status(agent["id"], "stopped")
        _append_log(agent["name"], "Agent stopped (batch)", "info")
        results.append({"agent_id": agent["id"], "status": "stopped"})
    await broadcast_ws("agents", {"type": "batch_status_changed", "status": "stopped"})
    return {"ok": True, "results": results}

@router.post("/batch/restart", dependencies=[Depends(require_auth)])
async def batch_restart_agents():
    """Restart all agents."""
    results = []
    for agent in _AGENTS_TEMPLATE:
        _set_agent_status(agent["id"], "running")
        _append_log(agent["name"], "Agent restarted (batch)", "success")
        results.append({"agent_id": agent["id"], "status": "running"})
    await broadcast_ws("agents", {"type": "batch_status_changed", "status": "running"})
    return {"ok": True, "results": results}


# --- Agent Attribution & ELO ---
@router.get("/attribution")
async def get_agent_attribution():
    """Per-agent PnL contribution, accuracy, signal count for leaderboard."""
    agents = _get_all_agents()
    attribution = []
    for agent in agents:
        status = _effective_status(agent["id"])
        attribution.append({
            "agent_id": agent["id"],
            "name": agent["name"],
            "status": status,
            "elo": agent.get("elo", 1500),
            "pnl_contribution": 0,
            "accuracy_pct": 0,
            "signal_count": 0,
            "win_rate": agent.get("win_pct", 50),
        })
    # Try to get council agent attribution
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
        for name, weight in weights.items():
            attribution.append({
                "agent_id": name,
                "name": name.replace("_", " ").title(),
                "status": "running",
                "elo": int(1500 * weight),
                "weight": weight,
                "pnl_contribution": 0,
                "accuracy_pct": 0,
                "signal_count": 0,
            })
    except Exception:
        pass
    return {"attribution": attribution}

@router.get("/elo-leaderboard")
async def get_elo_leaderboard():
    """ELO leaderboard with history — sources weights from Bayesian WeightLearner."""
    leaderboard = []
    # Pull real council agent weights as ELO proxy
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
        for name, weight in weights.items():
            leaderboard.append({
                "rank": 0,
                "agent_id": name,
                "name": name.replace("_", " ").title(),
                "elo": int(1500 * weight),
                "weight": round(weight, 3),
                "win_rate": 0,
                "games": 0,
                "streak": 0,
            })
    except Exception:
        pass
    # Also include the 5 tick agents
    agents = _get_all_agents()
    for agent in agents:
        leaderboard.append({
            "rank": 0,
            "agent_id": agent["id"],
            "name": agent["name"],
            "elo": 1500,
            "win_rate": 0,
            "games": 0,
            "streak": 0,
        })
    leaderboard.sort(key=lambda x: x["elo"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    return leaderboard


@router.get("/ws-channels")
async def get_ws_channel_status():
    """Return WebSocket channel info for the Blackboard Channel Monitor."""
    from app.websocket_manager import get_channel_info
    info = get_channel_info()
    channels = []
    default_channels = ["agents", "signals", "risk", "council", "kelly", "sentiment", "trades", "logs", "homeostasis", "circuit_breaker", "llm_health"]
    for ch in default_channels:
        subs = info.get("channels", {}).get(ch, 0)
        channels.append({
            "channel": ch,
            "status": "active" if subs > 0 else "idle",
            "subscribers": subs,
            "msg_per_sec": 0,
            "last_msg": "",
        })
    return {
        "total_connections": info.get("total_connections", 0),
        "channels": channels,
    }


@router.get("/flow-anomalies")
async def get_flow_anomalies():
    """Detected anomalies in data flow between agents."""
    return {
        "anomalies": [],
        "total_flows_monitored": 0,
        "anomaly_count": 0,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }


# --- Weight & Toggle Endpoints (SignalIntelligenceV3 page) ---
@router.put("/{agent_id}/weight", dependencies=[Depends(require_auth)])
async def update_agent_weight(agent_id: int, payload: dict):
    """Update the weight/priority of an agent, scanner, or intel module."""
    weight = payload.get("weight", 1.0)
    config = _agent_configs.get(str(agent_id), {})
    config["weight"] = float(weight)
    _agent_configs[str(agent_id)] = config
    db_service.set_config(f"agent_{agent_id}_weight", weight)
    agent_name = next((a["name"] for a in _AGENTS_TEMPLATE if a["id"] == agent_id), f"Agent-{agent_id}")
    _append_log(agent_name, f"Weight updated to {weight}", "info")
    await broadcast_ws("agents", {"type": "weight_updated", "agent_id": agent_id, "weight": weight})
    return {"ok": True, "agent_id": agent_id, "weight": weight}


@router.post("/{agent_id}/toggle", dependencies=[Depends(require_auth)])
async def toggle_agent(agent_id: int, payload: dict = {}):
    """Toggle an agent, scanner, or intel module active/inactive."""
    active = payload.get("active", True)
    new_status = "running" if active else "stopped"
    _set_agent_status(agent_id, new_status)
    agent_name = next((a["name"] for a in _AGENTS_TEMPLATE if a["id"] == agent_id), f"Agent-{agent_id}")
    _append_log(agent_name, f"Toggled to {new_status}", "info")
    await broadcast_ws("agents", {"type": "status_changed", "agent_id": agent_id, "status": new_status})
    return {"ok": True, "agent_id": agent_id, "status": new_status, "active": active}
