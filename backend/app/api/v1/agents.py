"""
Agent Command Center API — status and control of the 5 AI agents.
Each agent: status (running/paused/stopped/error), CPU/Memory, last action, current task, config, Start/Stop/Pause/Restart.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_agents():
    """Return all 5 agents with status, CPU/Memory, current task, config, and activity log (last 100)."""
    return {
        "agents": [
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
                    "sources": [
                        "finviz",
                        "alpaca",
                        "unusual_whales",
                        "fred",
                        "sec_edgar",
                    ],
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
                "config": {
                    "retrainDay": "sunday",
                    "minAccuracy": 0.65,
                    "gpuEnabled": True,
                },
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
                "config": {
                    "channels": 8,
                    "autoProcess": True,
                    "extractAlgos": True,
                },
            },
        ],
        "logs": [
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
        ],
    }


@router.post("/{agent_id}/start")
async def start_agent(agent_id: int):
    return {"ok": True, "agent_id": agent_id, "status": "running"}


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: int):
    return {"ok": True, "agent_id": agent_id, "status": "stopped"}


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: int):
    return {"ok": True, "agent_id": agent_id, "status": "paused"}


@router.post("/{agent_id}/restart")
async def restart_agent(agent_id: int):
    return {"ok": True, "agent_id": agent_id, "status": "running"}
