"""
Agent Command Center API — status and control of the 5 AI agents.
GET returns agents + logs; POST start/stop/pause/restart update persisted status and append to activity log.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from app.websocket_manager import broadcast_ws
from app.services.database import db_service

router = APIRouter()


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
        "uptime": "72h 15m",
        "lastActionTimestamp": "2026-02-18T13:02:15Z",
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
        "uptime": "72h 15m",
        "lastActionTimestamp": "2026-02-18T13:01:48Z",
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
        "uptime": "72h 15m",
        "lastActionTimestamp": "2026-02-18T13:00:30Z",
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
        "uptime": "72h 15m",
        "lastActionTimestamp": "2026-02-18T12:58:12Z",
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
        "uptime": "48h 30m",
        "lastActionTimestamp": "2026-02-18T12:55:00Z",
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


@router.get("")
async def get_agents():
    """Return all 5 agents with status from DB override, and activity log (DB + defaults)."""
    status_overrides = _get_agent_status()
    agents = []
    for a in _AGENTS_TEMPLATE:
        agents.append({**a, "status": status_overrides.get(str(a["id"]), a["status"])})
    stored_logs = db_service.get_config("agent_activity_log")
    logs = (
        stored_logs if isinstance(stored_logs, list) and stored_logs else []
    ) or _DEFAULT_LOGS.copy()
    return {"agents": agents, "logs": logs}


def _agent_by_id(agent_id: int):
    a = next((x for x in _AGENTS_TEMPLATE if x["id"] == agent_id), None)
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


@router.post("/{agent_id}/start")
async def start_agent(agent_id: int):
    """Start an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "running")
    _append_log(agent["name"], "Agent started", "success")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "running"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "running"}


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: int):
    """Stop an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "stopped")
    _append_log(agent["name"], "Agent stopped", "info")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "stopped"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "stopped"}


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: int):
    """Pause an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "paused")
    _append_log(agent["name"], "Agent paused", "warning")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "paused"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "paused"}


@router.post("/{agent_id}/restart")
async def restart_agent(agent_id: int):
    """Restart an agent; persist status and append to activity log."""
    agent = _agent_by_id(agent_id)
    _set_agent_status(agent_id, "running")
    _append_log(agent["name"], "Agent restarted", "success")
    await broadcast_ws(
        "agents", {"type": "status_changed", "agent_id": agent_id, "status": "running"}
    )
    return {"ok": True, "agent_id": agent_id, "status": "running"}
