# Project State - Elite Trading System (Embodier.ai)

> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 1, 2026 2:00 AM EST

## Identity

- **Project**: Elite Trading System by Embodier.ai
- **Repo**: `github.com/Espenator/elite-trading-system` (private)
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, CI GREEN

## Tech Stack

| Layer | Technology |
|-------|---------------|
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
       |                              |                    Alpaca/UW/FinViz
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

## Current State (Mar 1, 2026 2:00 AM EST)

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
| Active Trades | 10-active-trades.html / Active-Trades.png | 6b2e7ad | **DONE AND COMPLETE** - 415 lines, ultrawide command strip, real Alpaca API, NO mocks |
| Trade Execution | Trade-Execution mockup (Perplexity) | 77e01ce | **DONE AND COMPLETE** - 745 lines, full Alpaca v2 API (bracket/OCO/OTO/trailing), 12-col grid, NO mocks |
| Market Regime | 10-market-regime.png | (Comet session) | **DONE AND COMPLETE** - Real API wired, VIX regime classification, LW Charts only, NO mocks |

### Agent Command Center - AUDIT IN PROGRESS (Mar 1, 2026)

**Status**: Deep audit complete, redesign needed. AgentCommandCenter.jsx is 1,995 lines with 8 internal tabs.

**Issues Found**:
1. Duplicate mockup images (top/bottom saved as same file)
2. 4-5 sub-tab mockups were never created
3. Tab names in code don't match architecture doc
4. Mock data still present in 3 placeholder tabs (Brain Map, Leaderboard, Blackboard)
5. openclawService.js only has 6/16 needed functions
6. Mockup filename typo: "agent rgistery.png" needs rename to "05c-agent-registry.png"

**Current 8 Tabs in Code**: Overview, Agents, Swarm Control, Candidates, LLM Flow, Brain Map, Leaderboard, Blackboard

**Plan**: 4-phase redesign - (1) Align tab names, (2) Generate missing mockups, (3) Rewrite code to match, (4) Wire all real APIs

### Next Page to Build

- **Agent Command Center** (`AgentCommandCenter.jsx`) - Full redesign of 8 internal tabs to match corrected mockups
- Then: **Performance Analytics** (`PerformanceAnalytics.jsx`) - pending mockup alignment

## Known Issues

1. Backend `signals.py` has IndentationErrors (needs `scripts/fix_indentation.py`)
2. Backend has never been started (`uvicorn app.main:app`)
3. No authentication system yet
4. WebSocket not flowing real-time data yet
5. Agent Command Center has duplicate/missing mockups and mismatched tabs (audit Mar 1)

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
| `frontend-v2/src/V3-ARCHITECTURE.md` | AUTHORITATIVE frontend architecture doc |

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use `useApi()` hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups in `docs/mockups-v3/images/` before building UI
6. Run `npm run build` before committing frontend changes
7. Run `python -m pytest` before committing backend changes
