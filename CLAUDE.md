# CLAUDE.md — Embodier Trader (Elite Trading System)
# This file is read automatically by Claude Code at session start.
# Last updated: March 11, 2026 — v4.1.0-dev

## Project Identity
- **Name**: Embodier Trader by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC)
- **Owner**: Espenator (Espen, Asheville NC)
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. CNS architecture.

## Two-PC Development Setup

### PC1: ESPENMAIN (Primary)
| Item | Value |
|------|-------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary — backend API, frontend, DuckDB, trading execution |
| Repo path | `C:\Users\Espen\elite-trading-system` |
| Backend | `C:\Users\Espen\elite-trading-system\backend` |
| Frontend | `C:\Users\Espen\elite-trading-system\frontend-v2` |
| Python venv | `C:\Users\Espen\elite-trading-system\backend\venv` |
| Alpaca account | ESPENMAIN (paper trading) — Key 1 |

### PC2: ProfitTrader (Secondary)
| Item | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 |
| Role | Secondary — GPU training, ML inference, brain_service (gRPC) |
| Repo path | `C:\Users\ProfitTrader\elite-trading-system` |
| Alpaca account | Profit Trader (discovery) — Key 2 |

Both IPs are DHCP-reserved on the AT&T BGW320-505 router (192.168.1.254).

## Ports & URLs

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs (Swagger) | 8000 | http://localhost:8000/docs |
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Brain Service (gRPC) | 50051 | localhost:50051 |
| Ollama | 11434 | http://localhost:11434 |
| Redis (optional) | 6379 | redis://localhost:6379 |

Note: Vite may fall back to 5174 or 3001 if 5173 is in use.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, DuckDB, uvicorn
- **Frontend**: React 18 (Vite), TailwindCSS, Lightweight Charts, react-router-dom v6
- **Council**: 35-agent DAG with Bayesian-weighted arbiter (7 stages)
- **Data Sources**: Alpaca Markets, Unusual Whales, FinViz, FRED, SEC EDGAR, NewsAPI
- **LLM**: 3-tier router — Ollama (routine) → Perplexity (search) → Claude (deep reasoning)
- **Event Pipeline**: MessageBus → CouncilGate → Council → OrderExecutor
- **Database**: DuckDB (analytics), in-memory state
- **CI**: GitHub Actions, 666+ tests passing

## Alpaca Accounts (Paper Trading)

| Label | Purpose | Base URL |
|-------|---------|----------|
| Key 1: ESPENMAIN | Trading (portfolio) | https://paper-api.alpaca.markets/v2 |
| Key 2: Profit Trader | Discovery scanning | https://paper-api.alpaca.markets/v2 |

Keys are stored in `backend/.env` (gitignored). See `backend/.env.example` for the template.

## Slack Bots (Embodier Trader Workspace)

| Bot | App ID | Purpose |
|-----|--------|---------|
| OpenClaw | A0AF9HSCQ6S | Multi-agent swarm notifications |
| TradingView Alerts | A0AFQ89RVEV | Inbound TradingView webhook alerts |

Slack tokens are short-lived (12h expiry) and must be refreshed via Slack API console.

## External API Services

All API keys live in `backend/.env` (NEVER commit real keys). Services degrade gracefully if keys are missing:

| Service | Env Var | Required? |
|---------|---------|-----------|
| Alpaca Markets | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | YES (core) |
| Finviz Elite | `FINVIZ_API_KEY` | No |
| FRED | `FRED_API_KEY` | No |
| NewsAPI | `NEWS_API_KEY` | No |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | No |
| Perplexity | `PERPLEXITY_API_KEY` | No (LLM tier 2) |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | No (LLM tier 3) |
| Resend (email) | `RESEND_API_KEY` | No |

## Architecture Quick Reference

### Frontend (React)
- Router: `frontend-v2/src/App.jsx` — all routes inside `<Layout />` wrapper
- Layout: `components/layout/Layout.jsx` — provides Sidebar, Header, StatusFooter via `<Outlet />`
- Sidebar: 5 sections (COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM) — 14 nav items
- Data fetching: `useApi()` hook — all pages use this, never raw fetch
- Config: `src/config/api.js` — 189 endpoint definitions
- WebSocket: `src/services/websocket.js` — CNS channel subscriptions

### Backend (FastAPI)
- Entry: `backend/app/main.py` — 40 router registrations, 6-phase lifespan startup
- Routes: `backend/app/api/v1/` — 34 route files, 364+ endpoints
- Services: `backend/app/services/` — 68+ service modules
- Council: `backend/app/council/` — 35-agent DAG, arbiter, schemas, weight_learner
- WebSocket: `backend/app/websocket_manager.py` — channel whitelist + broadcast
- Auth: Bearer token (`API_AUTH_TOKEN` env var), fail-closed for live trading
- DB: DuckDB at `data/elite_trading.duckdb`

### Event Pipeline
```
AlpacaStream → SignalEngine → CouncilGate → Council (35 agents) → OrderExecutor → Alpaca
                                    ↕
                            MessageBus (pub/sub)
```

## Rules (CRITICAL — do not violate)

1. **No mock data** in production components — all data via real API endpoints
2. **All frontend data** via `useApi()` hook — never raw fetch or hardcoded values
3. **No yfinance** anywhere — removed from requirements, use Alpaca/FinViz/UW
4. **Python 4-space indentation** — never tabs
5. **Council agents** must return `AgentVote` schema from `council/schemas.py`
6. **VETO_AGENTS** = `{"risk", "execution"}` only — no other agent can veto
7. **CouncilGate** bridges signals to council — do NOT bypass
8. **Discovery must be continuous** — no polling-based scanners (Issue #38)
9. **Scouts publish to `swarm.idea`** topic on MessageBus
10. **ONE repo** — all code in Espenator/elite-trading-system
11. **No secrets in committed files** — all keys in `.env` (gitignored)
12. **Dashboard route** must be inside `<Layout />` wrapper in App.jsx (fixes sidebar)

## Quick Start (PowerShell on ESPENMAIN)

```powershell
# Terminal 1 — Backend
cd C:\Users\Espen\elite-trading-system\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm run dev
```

Or use the launcher: `.\start-embodier.ps1`

## Key Files for Common Tasks

| Task | Read these files |
|------|-----------------|
| Frontend page fix | `App.jsx`, the page `.jsx`, `useApi.js`, `api.js` |
| Backend API fix | The route in `api/v1/`, the service in `services/` |
| Council/agent fix | `council/runner.py`, `council/arbiter.py`, `council/schemas.py`, agent file |
| Pipeline fix | `council_gate.py`, `signal_engine.py`, `order_executor.py` |
| WebSocket fix | `websocket_manager.py`, `frontend-v2/src/services/websocket.js` |
| Sidebar/layout fix | `Layout.jsx`, `Sidebar.jsx`, `App.jsx` |
| Auth fix | `core/security.py`, `backend/.env` |

## Recent Fixes (March 10-11, 2026)
- Moved Dashboard route inside `<Layout />` to get correct v3 sidebar
- Removed duplicate mini-sidebar from Dashboard.jsx
- Expanded WebSocket `WS_ALLOWED_CHANNELS` whitelist (10 → 23 channels)
- Replaced `window.location.href` with React Router `navigate()` in Dashboard
- Fixed broken `/cognitive-dashboard` route → `/dashboard`

### Backend Stability Fixes (March 11, 2026) — Phase 1 Complete
- **uvloop CPU spin fix**: Added `loop='asyncio'` to both `run_server.py` and `start_server.py` — uvloop causes 35-90% CPU with many concurrent asyncio tasks
- **DiscordSwarmBridge crash**: Removed unsupported kwargs (`on_signal`, `publish_to_bus`) from `discord_channel_agent.py`
- **TurboScanner event loop blocking**: Renamed 10 DuckDB scan methods from async to sync, wrapped in `asyncio.to_thread()`
- **SourceCategory enum**: Added `LLM = "llm"` to `data_sources.py` (pydantic 500 fix)
- **JSON float('inf')**: Added `_sanitize_floats()` to `swarm.py` for TurboScanner data
- **Service gating**: Added env-var gates (`SCOUTS_ENABLED`, `TURBO_SCANNER_ENABLED`, `MARKET_SWEEP_ENABLED`, `AUTO_BACKFILL`, `BACKGROUND_LOOPS`)

### Mock Data Removal (March 11, 2026) — Phase 1.3 Complete
- **logs.py**: Replaced 8 hardcoded fake entries with real Python logging ring buffer (RingBufferHandler, 500 entries)
- **backtest_routes.py /runs**: Replaced fake R001-R004 with real DB query
- **agents.py**: Removed `_DEFAULT_LOGS` mock activity; honest "Awaiting first tick" defaults

### Frontend-Backend Wiring (March 11, 2026) — Phase 2 In Progress
- All 63 endpoints tested: 60x 200 OK
- Frontend builds with no errors (14 pages)
- Added 5 missing backend endpoints: PUT /strategy/regime-params, POST /training/retrain, POST /openclaw/scan, PUT /agents/{id}/weight, POST /agents/{id}/toggle
- Added `scanners`/`intels` aliases in `api.js` → agents router
- API_AUTH_TOKEN set in `.env` (required for state-changing endpoints)

## Production Readiness Status
- See `PLAN.md` for the full 8-phase production readiness plan
- **Phase 1: Backend Health** — COMPLETE
- **Phase 2: Frontend Wiring** — IN PROGRESS (endpoint audit done, 5 missing endpoints added)
- **Phase 3-8**: Not started (Council, Auto-Trade, Data Firehose, UI Controls, Monitoring, Desktop)
