# CLAUDE.md — Embodier Trader (Elite Trading System)
# This file is read automatically by Claude Code at session start.
# Last updated: March 11, 2026 (Phase A complete) — v4.1.0-dev

## Project Identity
- **Name**: Embodier Trader by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC)
- **Owner**: Espenator (Espen, Asheville NC)
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. CNS architecture.
- **Production Readiness**: ~75% — Phase A critical fixes applied, enforcement gaps closed (see PLAN.md)

## Two-PC Development Setup

**Paths:** Use **repo-relative** paths everywhere (e.g. `backend/`, `frontend-v2/`). See `PATH-STANDARD.md` for the single source of truth. Machine-specific absolute paths: `PATH-MAP.md`.

### PC1: ESPENMAIN (Primary)
| Item | Value |
|------|-------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary — backend API, frontend, DuckDB, trading execution |
| Repo root | Workspace root. Canonical: ESPENMAIN `C:\Users\Espen\elite-trading-system`, ProfitTrader `C:\Users\ProfitTrader\elite-trading-system`. See PATH-STANDARD.md. |
| Backend | `backend/` |
| Frontend | `frontend-v2/` |
| Python venv | `backend/venv` |
| Alpaca account | ESPENMAIN (paper trading) — Key 1 |

### PC2: ProfitTrader (Secondary)
| Item | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 |
| Role | Secondary — GPU training, ML inference, brain_service (gRPC) |
| Repo root | Workspace root on PC2 (see PATH-STANDARD.md) |
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
- **Data Sources**: Alpaca Markets, Unusual Whales, FinViz, FRED, SEC EDGAR, NewsAPI, Benzinga (scraper), SqueezeMetrics (scraper), Capitol Trades (scraper)
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

| Service | Env Var | Required? | Status |
|---------|---------|-----------|--------|
| Alpaca Markets | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | YES (core) | Needs key |
| Finviz Elite | `FINVIZ_API_KEY` | No | Needs key |
| FRED | `FRED_API_KEY` | No | **CONFIGURED** |
| NewsAPI | `NEWS_API_KEY` | No | **CONFIGURED** |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | No | **CONFIGURED** |
| Perplexity | `PERPLEXITY_API_KEY` | No (LLM tier 2) | Needs key |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | No (LLM tier 3) | Needs key |
| Resend (email) | `RESEND_API_KEY` | No | **CONFIGURED** |
| Benzinga (scraper) | `BENZINGA_EMAIL` / `BENZINGA_PASSWORD` | No | **CONFIGURED** — web scraper, no API key |
| SqueezeMetrics (scraper) | `SQUEEZEMETRICS_ENABLED` | No | **CONFIGURED** — scrapes public DIX/GEX |
| Capitol Trades (scraper) | — (uses UW API) | No | **CONFIGURED** — via Unusual Whales + scrape fallback |

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

1. **Paths:** Use repo-relative paths in docs and when referring to files (e.g. `backend/app/main.py`). Workspace root = repo root. See `PATH-STANDARD.md`.
2. **No mock data** in production components — all data via real API endpoints
3. **All frontend data** via `useApi()` hook — never raw fetch or hardcoded values
4. **No yfinance** anywhere — removed from requirements, use Alpaca/FinViz/UW
5. **Python 4-space indentation** — never tabs
6. **Council agents** must return `AgentVote` schema from `council/schemas.py`
7. **VETO_AGENTS** = `{"risk", "execution"}` only — no other agent can veto
8. **CouncilGate** bridges signals to council — do NOT bypass
9. **Discovery must be continuous** — no polling-based scanners (Issue #38)
10. **Scouts publish to `swarm.idea`** topic on MessageBus
11. **ONE repo** — all code in Espenator/elite-trading-system
12. **No secrets in committed files** — all keys in `.env` (gitignored)
13. **Dashboard route** must be inside `<Layout />` wrapper in App.jsx (fixes sidebar)

## Quick Start (PowerShell)

From **repo root** (workspace root in Cursor/Claude):

```powershell
# Terminal 1 — Backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend-v2
npm run dev
```

Or from repo root: `.\start-embodier.ps1` (launcher derives paths from script location)

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
| Git push/pull setup | `docs/GIT-PUSH-SETUP.md`, `scripts/set-git-remote-from-token.ps1`, `.github-token` or `GITHUB_TOKEN` |

## Completed Work (March 10-11, 2026)

### Phase 1: Backend Health — COMPLETE
- Fixed uvloop CPU spin, DiscordSwarmBridge crash, TurboScanner blocking
- Fixed SourceCategory enum, JSON float('inf'), service gating
- All 25+ services start without errors

### Phase 1.3: Mock Data Removal — COMPLETE
- logs.py: real Python logging ring buffer (500 entries)
- backtest_routes.py: real DB query replaces fake R001-R004
- agents.py: real psutil metrics replaces fake CPU/memory

### Phase 1.5: Debug & Data Sources — COMPLETE
- Council registry: added 4 missing agents + Stage 5.5
- ELO leaderboard: sourced from real WeightLearner Bayesian weights
- Route aliases: 4 frontend-backend path mismatches fixed
- Created 4 scraper services (benzinga, squeezemetrics, capitol_trades, senate_stock_watcher)
- API keys configured in .env

### Phase 2: Frontend-Backend Wiring — COMPLETE
- All 14 pages audited for API response shape mismatches, all fixed
- 28 action buttons verified — all have backend endpoints
- 5 missing endpoints added
- Slack notification service + TradingView webhook receiver created

### Phase 6: UI Controls — COMPLETE
### Phase 7: Monitoring — COMPLETE

### Phase A: Stop the Bleeding — COMPLETE (March 11, 2026)
- **A1**: Fixed 5 crashing scouts — added `get_top_flow_alerts()`, `get_congressional_trades()`, `get_gex_levels()` to unusual_whales_service, `get_recent_insider_transactions()` to sec_edgar_service, `get_latest_macro_snapshot()` to fred_service, plus singleton getters for all 3
- **A2**: Enhanced auto-backfill to check `daily_ohlcv` (not just indicators), added post-backfill verification
- **A3**: Regime enforcement wired — order executor Gate 2b blocks entries when regime max_pos=0 or kelly_scale=0 (RED/CRISIS), VIX-based regime fallback when OpenClaw bridge offline
- **A4**: Circuit breaker enforcement — order executor Gate 2c checks live leverage (max 2x) and position concentration (max 25%)
- **A5**: Paper/live safety gate — `validate_account_safety()` on startup forces SHADOW mode if account type mismatches TRADING_MODE
- **A6**: DuckDB async lock race — thread-safe double-checked locking for asyncio.Lock creation
- **A7**: Background loop supervisor — `_supervised_loop()` wrapper with crash recovery (3 retries, Slack alerts)

## Deep Audit Results (March 11, 2026)

A line-by-line audit of the entire codebase identified 40 specific issues across 4 categories.
See `PLAN.md` for the full enhancement plan (Phases A-E).

### Top 10 Issues Blocking Maximum Profits

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 1 | Signal gate threshold 65 filters 20-40% of profitable signals | council_gate.py | Profit Killer |
| 2 | ~~3 of 12 scouts crash on first cycle~~ **FIXED** (Phase A) | scouts/ | Silent Failure |
| 3 | ~~No daily data backfill~~ **FIXED** (Phase A) | data_ingestion.py | Silent Failure |
| 4 | ~~10 circuit breakers but only 1 enforced~~ **FIXED** (Phase A — leverage + concentration enforced) | risk.py | Unenforced Safeguard |
| 5 | ~~Regime params ignored by order executor~~ **FIXED** (Phase A) | strategy.py | Unenforced Safeguard |
| 6 | Short signals inverted — `100 - blended` blocks bearish setups | signal_engine.py | Profit Killer |
| 7 | Weight learner drops 50%+ of outcomes (0.5 confidence floor) | weight_learner.py | Intelligence Gap |
| 8 | Only market orders — pays full bid-ask spread on every trade | order_executor.py | Profit Killer |
| 9 | Partial fills never re-executed — 60-80% fill rate silently | order_executor.py | Profit Killer |
| 10 | ~~No regime fallback~~ **FIXED** (Phase A — VIX-based fallback) | strategy.py | Unenforced Safeguard |

### What IS Working Well (Do NOT Break)
1. All 33+ council agents are real implementations (not stubs)
2. Bayesian weight updates are mathematically correct
3. VETO agents (risk, execution) properly enforced
4. Event-driven architecture achieves sub-1s council latency
5. Kelly criterion implementation is mathematically sound
6. 3-tier LLM router (Ollama → Perplexity → Claude)
7. 666 tests passing, CI GREEN
8. Health monitoring endpoints are comprehensive
9. HITL gate implemented and ready
10. Bracket order support with ATR-based stop/TP

## Production Readiness Status
- See `PLAN.md` for the full 5-phase enhancement plan (Phases A-E)
- See `docs/DIVIDE-AND-CONQUER-PLAN.md` for PC1/PC2 task division
- **Completed**: Backend health, mock data removal, frontend wiring, UI controls, monitoring, Phase A
- **Phase A: Stop the Bleeding** — COMPLETE (scout crashes fixed, regime enforcement wired, circuit breakers enforced, paper/live safety gate, DuckDB lock fix, background loop supervisor)
- **Phase B: Unlock Alpha** — NOT STARTED (calibrate gate, fix shorts, smart cooldown, limit orders, partial fills)
- **Phase C: Sharpen the Brain** — NOT STARTED (weight learner fix, confidence calibration, regime-adaptive thresholds)
- **Phase D: Continuous Intelligence** — NOT STARTED (autonomous backfill, rate limiting, scraper resilience)
- **Phase E: Production Hardening** — NOT STARTED (E2E test, emergency flatten, desktop packaging)
- **Estimated total effort**: 13-18 focused sessions
