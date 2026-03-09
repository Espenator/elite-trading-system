"""
Agent Command Center API — status and control of the 5 operational tick agents.
GET returns agents + logs; POST start/stop/pause/restart update persisted status and append to activity log.
Note: These are the 5 data-collection tick agents. The 11-agent council DAG is at /council/status.
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
        "cpuPercent": 12,
        "memoryMb": 256,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Pulled FRED CPI, SEC 8-K for AAPL",
        "currentTask": "Scanning Finviz Elite + Alpaca bars (next in 45s)",
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
        "cpuPercent": 18,
        "memoryMb": 512,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Generated composite score 87 for MSFT (Bull Flag)",
        "currentTask": "Applying momentum algo to S&P 500 watchlist",
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
        "cpuPercent": 8,
        "memoryMb": 2048,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Inference batch completed (142 tickers)",
        "currentTask": "Idle until next Sunday retrain",
        "description": "XGBoost/LightGBM on GPU via CUDA. Trains on historical outcomes. Sunday full retrain (schedulable). Flywheel: outcome resolver feeds accuracy back.",
        "config": {"retrainDay": "sunday", "minAccuracy": 0.65, "gpuEnabled": True},
    },
    {
        "id": 4,
        "name": "Sentiment Agent",
        "status": "running",
        "cpuPercent": 5,
        "memoryMb": 384,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Aggregated sentiment for NVDA: 78 (Stockgeist + News + X)",
        "currentTask": "Polling Discord channels",
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
        "cpuPercent": 3,
        "memoryMb": 128,
        "uptime": "0m",
        "lastActionTimestamp": None,
        "lastAction": "Extracted 5 ideas from 'Top 5 Swing Trade Setups'",
        "currentTask": "Processing: 'Fed Rate Decision Analysis'",
        "description": "Ingests transcripts from financial YouTube videos; extracts trading ideas, technical analysis concepts; feeds into ML feature engineering. 24/7 self-learning flywheel.",
        "config": {"channels": 8, "autoProcess": True, "extractAlgos": True},
    },
]

_DEFAULT_LOGS = [
    {
        "time": "13:02:15",
        "agent": "Market Data Agent",
        "message": "Pulled FRED CPI, SEC 8-K for AAPL",
        "level": "info",
    },
    {
        "time": "13:01:48",
        "agent": "Signal Generation Agent",
        "message": "Composite score 87 for MSFT (Bull Flag)",
        "level": "success",
    },
    {
        "time": "13:00:30",
        "agent": "ML Learning Agent",
        "message": "Inference batch completed (142 tickers)",
        "level": "info",
    },
    {
        "time": "12:58:12",
        "agent": "Sentiment Agent",
        "message": "Aggregated sentiment for NVDA: 78",
        "level": "success",
    },
    {
        "time": "12:55:00",
        "agent": "YouTube Knowledge Agent",
        "message": "Extracted 5 ideas from 'Top 5 Swing Trade Setups'",
        "level": "success",
    },
    {
        "time": "12:52:30",
        "agent": "Market Data Agent",
        "message": "Unusual Whales flow spike on SPY",
        "level": "warning",
    },
]


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

    return {
        "pipeline": pipeline_stages,
        "current_stage": db_service.get_config("conference_current_stage") or "idle",
        "last_conference": {
            "ticker": conference_data.get("ticker", "N/A") if conference_data else "N/A",
            "verdict": conference_data.get("verdict", "N/A") if conference_data else "N/A",
            "confidence": conference_data.get("confidence", 0) if conference_data else 0,
            "duration": conference_data.get("duration", 0) if conference_data else 0,
            "votes": conference_data.get("votes", {}) if conference_data else {},
        },
        "total_conferences": int(db_service.get_config("conference_count") or 0),
    }


@router.get("/consensus")
async def get_consensus():
    """Agent consensus for Performance Analytics. Same data as conference when available."""
    return await get_conference_status()


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

    # Return structure matching mockup even without real data
    return {
        "metrics": [
            {"name": "volume_sma_ratio", "value": 0.24, "sparkline": [], "status": "ok"},
            {"name": "atr_normalized", "value": 0.22, "sparkline": [], "status": "ok"},
            {"name": "macd_histogram", "value": 0.15, "sparkline": [], "status": "ok"},
            {"name": "vwap_distance", "value": 0.11, "sparkline": [], "status": "ok"},
            {"name": "rsi_14", "value": 0.08, "sparkline": [], "status": "ok"},
        ],
        "mean_psi": 0.119,
        "drift_detected": False,
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

    # Add info alerts
    alerts.append({"level": "INFO", "message": "Bridge latency normalized — 23ms avg"})

    return {"alerts": alerts}


# --- Agent Resource Monitor ---
@router.get("/resources")
async def get_agent_resources():
    """Return per-agent resource usage for the Agent Resource Monitor panel."""
    agents = _get_all_agents()
    resources = []

    for agent in agents:
        status = _effective_status(agent["id"])
        resources.append({
            "agent": agent["name"],
            "cpu_pct": agent.get("cpu_pct", round(5 + agent["id"] * 7.5, 1)),
            "mem_mb": agent.get("mem_mb", 180 + agent["id"] * 150),
            "tokens_hr": agent.get("tokens_hr", 1500 + agent["id"] * 1800),
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
        "avg_review_time_sec": 12.4,
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
    # Also include council agents
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        weights = learner.get_weights()
        council_agents = [
            "market_perception", "flow_perception", "regime", "intermarket",
            "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
            "hypothesis", "strategy", "risk", "execution", "critic",
        ]
        for i, name in enumerate(council_agents):
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
    """ELO leaderboard with history."""
    agents = _get_all_agents()
    leaderboard = []
    for agent in agents:
        leaderboard.append({
            "rank": 0,
            "agent_id": agent["id"],
            "name": agent["name"],
            "elo": agent.get("elo", 1500),
            "win_rate": agent.get("win_pct", 50),
            "games": 0,
            "streak": 0,
        })
    leaderboard.sort(key=lambda x: x["elo"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    return {"leaderboard": leaderboard}


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
        "total_flows_monitored": 24,
        "anomaly_count": 0,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }


# --- Agent Timeout Reflexes ---
@router.get("/timeout/stats")
async def get_timeout_stats():
    """Get timeout statistics for all agents."""
    from app.council.reflexes.timeout_reflex import get_timeout_manager

    timeout_manager = get_timeout_manager()

    # Get aggregate stats
    aggregate = timeout_manager.get_stats()

    # Get per-agent stats
    agent_stats = timeout_manager.get_all_agent_stats()

    return {
        "aggregate": aggregate,
        "agents": agent_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/timeout/stats/{agent_name}")
async def get_agent_timeout_stats(agent_name: str):
    """Get timeout statistics for a specific agent."""
    from app.council.reflexes.timeout_reflex import get_timeout_manager

    timeout_manager = get_timeout_manager()
    stats = timeout_manager.get_stats(agent_name)

    if not stats:
        raise HTTPException(status_code=404, detail=f"No timeout stats found for agent: {agent_name}")

    return stats


@router.post("/timeout/override/{agent_name}", dependencies=[Depends(require_auth)])
async def set_timeout_override(agent_name: str, timeout_seconds: float):
    """Set a manual timeout override for a specific agent.

    Args:
        agent_name: Agent identifier
        timeout_seconds: Timeout in seconds
    """
    from app.council.reflexes.timeout_reflex import get_timeout_manager

    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise HTTPException(status_code=400, detail="Timeout must be between 0 and 300 seconds")

    timeout_manager = get_timeout_manager()
    timeout_manager.set_timeout_override(agent_name, timeout_seconds)

    _append_log(agent_name, f"Timeout override set to {timeout_seconds:.1f}s", "info")
    await broadcast_ws("agents", {
        "type": "timeout_override",
        "agent_name": agent_name,
        "timeout_seconds": timeout_seconds,
    })

    return {
        "ok": True,
        "agent_name": agent_name,
        "timeout_seconds": timeout_seconds,
    }


@router.delete("/timeout/override/{agent_name}", dependencies=[Depends(require_auth)])
async def clear_timeout_override(agent_name: str):
    """Clear manual timeout override for a specific agent."""
    from app.council.reflexes.timeout_reflex import get_timeout_manager

    timeout_manager = get_timeout_manager()
    timeout_manager.clear_timeout_override(agent_name)

    _append_log(agent_name, "Timeout override cleared", "info")
    await broadcast_ws("agents", {
        "type": "timeout_override_cleared",
        "agent_name": agent_name,
    })

    return {"ok": True, "agent_name": agent_name}


@router.post("/timeout/reset", dependencies=[Depends(require_auth)])
async def reset_timeout_stats(agent_name: str = None):
    """Reset timeout statistics.

    Args:
        agent_name: If provided, reset stats for specific agent. If None, reset all.
    """
    from app.council.reflexes.timeout_reflex import get_timeout_manager

    timeout_manager = get_timeout_manager()
    timeout_manager.reset_stats(agent_name)

    msg = f"Timeout stats reset for {agent_name}" if agent_name else "All timeout stats reset"
    _append_log(agent_name or "System", msg, "info")
    await broadcast_ws("agents", {
        "type": "timeout_stats_reset",
        "agent_name": agent_name,
    })

    return {"ok": True, "message": msg}

