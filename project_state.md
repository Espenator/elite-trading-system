# Project State - Elite Trading System (Embodier.ai)

> Paste this file at the start of every new AI chat session.
> Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 1, 2026

## Identity

- **Project**: Elite Trading System by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (private)
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, CI GREEN

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn, LSTM (no PyTorch in prod) |
| Agents | OpenClaw multi-agent system (8+ sub-modules) |
| CI/CD | GitHub Actions (22 tests passing) |
| Infra | Docker, docker-compose.yml |
| Local AI | Ollama (planned for agent inference) |

## Hardware (Dual-PC Setup)

- PC 1: Development + Frontend + Backend API
- PC 2: RTX GPU cluster for ML training + Ollama inference
- Both PCs will route via OpenClaw agent orchestration

## Data Sources (CRITICAL - NO yfinance)

- Alpaca Markets (alpaca-py) - Market data + order execution
- Unusual Whales - Options flow + institutional activity
- FinViz (finviz) - Screener, fundamentals, VIX proxy
- FRED - Economic macro data
- SEC EDGAR - Company filings

## Architecture

[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
15 pages, 25 API routes, WebSocket via websocket_manager.py
OpenClaw Agents, ML Engine (XGBoost), DuckDB Analytics

## Key Code Patterns

1. Frontend data: Always use useApi('endpoint') hook
2. No mock data: All components wire to real /api/v1/* endpoints
3. Python style: 4-space indentation, never tabs
4. JSX unicode: BMP only
5. API pattern: Route handler -> Service layer -> External API
6. Mockups: docs/mockups-v3/images/ are the source of truth

## Current State (Mar 1, 2026)

- CI: GREEN (22 tests, all passing)
- Frontend: 15 pages built, all wired to real API hooks
- Backend: 25 API routes defined, services layer implemented
- Backend server: Ready to start (startup blockers fixed Mar 1)
- ML: XGBoost trainer + feature pipeline operational
- OpenClaw: Phase 2 complete (8 sub-modules integrated)
- WebSocket: Code exists but not connected end-to-end
- CORS: Restricted to localhost:3000, localhost:5173, localhost:8080

## Fixed Issues (Mar 1, 2026)

1. ~~Backend signals.py had missing return statement~~ FIXED
2. ~~main.py had hard ImportError on routers.trade_execution~~ FIXED (now try/except)
3. ~~main.py imported unused accept_connection~~ FIXED (removed)

## Remaining Issues

1. Backend has never been started locally (uvicorn app.main:app) -- blockers now removed
2. No authentication system yet
3. WebSocket not flowing real-time data yet
4. routers/trade_execution module does not exist yet (skipped gracefully)

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use useApi() hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups before building UI
6. Run npm run build before committing frontend changes
7. Run python -m pytest before committing backend changes
