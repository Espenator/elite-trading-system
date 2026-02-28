# Project State - Elite Trading System (Embodier.ai)

> Paste this file at the start of every new AI chat session.
> Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: February 28, 2026 5:00 PM EST

## Identity

- **Project**: Elite Trading System by Embodier.ai
- **Repo**: `github.com/Espenator/elite-trading-system` (private)
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

- **PC 1**: Development + Frontend + Backend API
- **PC 2**: RTX GPU cluster for ML training + Ollama inference
- Both PCs will route via OpenClaw agent orchestration

## Data Sources (CRITICAL - NO yfinance)

- **Alpaca Markets** (`alpaca-py`) - Market data + order execution
- **Unusual Whales** - Options flow + institutional activity
- **FinViz** (`finviz`) - Screener, fundamentals, VIX proxy
- **FRED** - Economic macro data
- **SEC EDGAR** - Company filings

## Architecture Summary

```
[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
       |                              |                         Alpaca/UW/FinViz
       WebSocket <-------------- websocket_manager.py
       |                              |
[OpenClaw Agents]    [ML Engine (XGBoost)]    [DuckDB Analytics]
```

## Key Code Patterns

1. **Frontend data**: Always use `useApi('endpoint')` hook - returns `{ data, loading, error }`
2. **No mock data**: All components wire to real `/api/v1/*` endpoints
3. **Python style**: 4-space indentation, never tabs
4. **JSX unicode**: BMP only (e.g. `\u21BB` not `\u{1F504}`)
5. **API pattern**: Route handler -> Service layer -> External API
6. **Mockups**: `docs/mockups-v3/images/` are the source of truth for UI design

## Current State (Feb 28, 2026 5:00 PM EST)

- CI: GREEN (22 tests, all passing)
- Frontend: 15 pages built, all wired to real API hooks
- Backend: 25 API routes defined, services layer implemented
- Backend server: Has NOT been run locally yet (IndentationErrors in some files remain)
- ML: XGBoost trainer + feature pipeline operational
- OpenClaw: Phase 2 complete (8 sub-modules integrated)
- WebSocket: Code exists but not connected end-to-end

### Pages Completed to 100% Mockup

| Page | Mockup | Commit | Status |
|------|--------|--------|--------|
| Data Sources Manager | 09-data-sources-manager.png | 083521a | **DONE AND COMPLETE** - 636 lines, split view, real API, NO mocks |
| Patterns & Screener | 07-screener-and-patterns.png | b18a267 | Real API wired, ~70% mockup match |

### Next Page to Build

- **Performance Analytics** (`PerformanceAnalytics.jsx`) - pending mockup alignment

## Known Issues

1. Backend `signals.py` has IndentationErrors (needs `scripts/fix_indentation.py`)
2. Backend has never been started (`uvicorn app.main:app`)
3. No authentication system yet
4. WebSocket not flowing real-time data yet

## File Reference

| File | What It Does |
|------|-------------|
| `REPO-MAP.md` | Full directory tree (100+ files) |
| `AI-CONTEXT-GUIDE.md` | 10 strategies for managing AI context |
| `bundle_files.py` | Bundle specific files for AI input |
| `map_repo.py` | Auto-generate repo tree |
| `frontend-v2/src/hooks/useApi.js` | Central data fetching hook |
| `backend/app/main.py` | FastAPI entry point |
| `backend/app/services/` | All business logic (15 services) |
| `docs/mockups-v3/images/` | Approved UI mockups |

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use `useApi()` hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups in `docs/mockups-v3/images/` before building UI
6. Run `npm run build` before committing frontend changes
7. Run `python -m pytest` before committing backend changes
