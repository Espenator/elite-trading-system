# Elite Trading System

**Embodier.ai Full-Stack AI Trading Intelligence Platform**
> **Last Updated: March 3, 2026**
> **CI Status: GREEN — 70 tests passing**
> **App Status: Backend ready to start. Frontend builds. All 15 pages audited and wired to real API hooks (useApi). No mock data remaining.**
> **Data Sources Manager: DONE AND COMPLETE — 636 lines, 100% pixel-perfect match to mockup 09, real API via dataSourcesApi.js (commit 083521a).**
> **Active Trades: DONE AND COMPLETE — 415 lines, ultrawide command strip layout, real Alpaca API via useApi hooks, positions + orders + risk panels, NO mocks (commit 6b2e7ad).**
> **Agent Command Center: DEPLOYED — decomposed from 77KB monolith into thin shell + 8 tabs + 6 shared components. All committed.**

React + FastAPI full-stack trading application with 15-route V3 widescreen dashboard (14 sidebar + 1 hidden), DuckDB database, Alpaca + Finviz integrations, OpenClaw Python agents, LSTM/XGBoost ML pipeline, and real-time order execution.

> **Part of the Embodier.ai Elite Trading ecosystem.** OpenClaw Python agents and the Blackboard Swarm architecture are integrated in `core/` and `backend/`. The [openclaw repo](https://github.com/Espenator/openclaw) is archived.

---

## AI CONTEXT: READ THIS FIRST

If you are an AI assistant reading this repo, here is the **honest current state**:

1. **15 frontend page files exist** in `frontend-v2/src/pages/` (14 sidebar + 1 hidden route)
2. **25 backend API route files exist** in `backend/app/api/v1/` (see actual list below)
3. **15 backend service files exist** in `backend/app/services/` (see actual list below)
4. **2 frontend hooks exist**: `useApi.js` and `useSentiment.js` — all pages use useApi hooks for real data
5. **All 15 pages audited and wired**: Production audit complete Feb 28, 2026. All mock data removed, all buttons/charts connected to real API endpoints
6. **CI is GREEN**: 70 tests passing across backend and frontend builds
7. **Backend has NEVER been started** — `uvicorn app.main:app` has never been run successfully, but startup blockers are resolved
8. **No authentication system** — no login, no user sessions
9. **No WebSocket real-time data flowing** — WebSocket code exists but is not connected
10. **Database**: DuckDB (not SQLite as previously claimed in some docs)
11. **Test suite**: 70 tests passing — backend + frontend CI green
12. **torch/PyTorch removed** from requirements.txt — ML currently XGBoost + scikit-learn only
13. **Agent Command Center**: Fully decomposed and deployed — thin shell + 8 tabs + 6 shared components all committed

### Key Documentation Files

| File | Purpose |
|---|---|
| `frontend-v2/src/V3-ARCHITECTURE.md` | Frontend architecture (15 routes, charting audit, component map) |
| `docs/UI-DESIGN-SYSTEM.md` | Design system (colors, fonts, spacing from approved mockups) |
| `docs/mockups-v3/images/` | Approved mockup images (source of truth for visual design) |
| `docs/STATUS-AND-TODO-2026-02-28.md` | Current project status and roadmap |
| `docs/API-COMPLETE-LIST-2026.md` | Complete API reference (25 routes) |
| `docs/AUDIT-2026-03-01-FINAL.md` | Latest final codebase audit |
| `backend/README.md` | Backend-specific architecture and API route reference |

### Rules Going Forward

**Run `uvicorn app.main:app` and `npm run build` locally before every commit.**

## Frontend Pages & Sidebar Menu (V3)

Sidebar defined in `frontend-v2/src/components/layout/Sidebar.jsx`. Routes in `frontend-v2/src/App.jsx`.

### COMMAND

| # | Route | Sidebar Label | File | Status |
|---|---|---|---|---|
| 1 | `/dashboard` | Intelligence Dashboard | `Dashboard.jsx` | Audited — wired to useApi |
| 2 | `/agents` | Agent Command Center | `AgentCommandCenter.jsx` | **DEPLOYED — thin shell + 8 tabs + 6 shared components** |

### INTELLIGENCE

| # | Route | Sidebar Label | File | Status |
|---|---|---|---|---|
| 3 | `/signals` | Signal Intelligence | `Signals.jsx` | Audited — wired to useApi |
| 4 | `/sentiment` | Sentiment Intelligence | `SentimentIntelligence.jsx` | Audited — wired to useApi |
| 5 | `/data-sources` | Data Sources Manager | `DataSourcesMonitor.jsx` | **DONE — 100% mockup 09, real API (083521a)** |

### ML & ANALYSIS

| # | Route | Sidebar Label | File | Status |
|---|---|---|---|---|
| 6 | `/ml-brain` | ML Brain & Flywheel | `MLBrainFlywheel.jsx` | Audited — wired to useApi |
| 7 | `/patterns` | Screener & Patterns | `Patterns.jsx` | **DONE — real API wired (b18a267)** |
| 8 | `/backtest` | Backtesting Lab | `Backtesting.jsx` | Audited — wired to useApi |
| 9 | `/performance` | Performance Analytics | `PerformanceAnalytics.jsx` | Audited — pending mockup alignment |
| 10 | `/market-regime` | Market Regime | `MarketRegime.jsx` | **DONE — 100% complete, real API, VIX regime, LW Charts, NO mocks** |

### EXECUTION

| # | Route | Sidebar Label | File | Status |
|---|---|---|---|---|
| 11 | `/trades` | Active Trades | `Trades.jsx` | **DONE — 415 lines, ultrawide command strip, real Alpaca API, NO mocks (6b2e7ad)** |
| 12 | `/risk` | Risk Intelligence | `RiskIntelligence.jsx` | Audited — wired to useApi |
| 13 | `/trade-execution` | Trade Execution | `TradeExecution.jsx` | **DONE — 745 lines, full Alpaca v2 API, bracket/OCO/OTO/trailing, NO mocks (77e01ce)** |

### SYSTEM

| # | Route | Sidebar Label | File | Status |
|---|---|---|---|---|
| 14 | `/settings` | Settings | `Settings.jsx` | Audited — wired to useApi |

### Hidden Route

| # | Route | File | Notes |
|---|---|---|---|
| 15 | `/signal-v3` | `SignalIntelligenceV3.jsx` | Advanced signal view, not in sidebar |

## Backend Architecture

### FastAPI Server (`backend/app/main.py`)

- Mounts all 25 API v1 routers
- CORS middleware configured for localhost:3000/5173/8080
- DuckDB schema initialization on startup
- WebSocket endpoint at `/ws`
- Background tasks: market data tick (60s), drift check (1hr), risk monitor (30s), heartbeat
- ML Flywheel singletons (model registry + drift monitor)

### API Routes (`backend/app/api/v1/`) — 25 files

| File | Purpose |
|---|---|
| `agents.py` | Agent management, lifecycle, swarm control |
| `alerts.py` | System alerts, drawdown alerts |
| `backtest_routes.py` | Strategy backtesting |
| `data_sources.py` | Data source health monitoring |
| `flywheel.py` | ML flywheel metrics |
| `logs.py` | System log retrieval |
| `market.py` | Market data, regime state, indices |
| `ml_brain.py` | ML model management, conference, registry |
| `openclaw.py` | OpenClaw bridge router |
| `orders.py` | Alpaca order creation and management |
| `patterns.py` | Pattern/screener queries |
| `performance.py` | Performance analytics, risk-reward |
| `portfolio.py` | Portfolio positions, P&L, Kelly metrics |
| `quotes.py` | Price and chart data |
| `risk.py` | Risk metrics, exposure, drawdown |
| `risk_shield_api.py` | RiskShield emergency controls |
| `sentiment.py` | Sentiment aggregation |
| `settings_routes.py` | App settings CRUD |
| `signals.py` | Trading signals from LSTM model |
| `status.py` | System health check |
| `stocks.py` | Finviz screener queries |
| `strategy.py` | Adaptive regime-based strategies |
| `system.py` | System config, GPU status |
| `training.py` | ML model training jobs |
| `youtube_knowledge.py` | YouTube research data |

### Services (`backend/app/services/`) — 15 files

| File | Purpose |
|---|---|
| `alpaca_service.py` | Alpaca broker REST integration |
| `backtest_engine.py` | Historical signal backtester + Monte Carlo |
| `database.py` | DuckDB database layer |
| `finviz_service.py` | Finviz stock screening |
| `fred_service.py` | FRED economic data |
| `kelly_position_sizer.py` | Kelly criterion position sizing |
| `market_data_agent.py` | Market data aggregation |
| `ml_training.py` | LSTM/XGBoost training |
| `openclaw_bridge_service.py` | OpenClaw bridge (large module) |
| `openclaw_db.py` | OpenClaw SQLite persistence |
| `sec_edgar_service.py` | SEC EDGAR filings |
| `signal_engine.py` | Signal scoring engine |
| `training_store.py` | ML model artifact storage |
| `unusual_whales_service.py` | Options flow data |
| `walk_forward_validator.py` | Walk-forward validation |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB, pydantic-settings |
| AI/ML | XGBoost, scikit-learn, HMM (hmmlearn), Kelly criterion |
| Broker | Alpaca Markets (paper + live via alpaca-py) |
| Data | Alpaca Markets, Unusual Whales, Finviz, FRED, SEC EDGAR |
| CI/CD | GitHub Actions (pytest + npm build) |
| Architecture | OpenClaw agents, Blackboard Swarm |

## CI/CD

Single workflow: `.github/workflows/ci.yml`

- **backend-test**: Python 3.11, `pip install -r requirements.txt`, `pytest tests/ -v --cov=app`
- **frontend-build**: Node 20, `npm ci`, `npm run build`
- Triggers on push/PR to `main`

**Current CI status**: GREEN — 70 tests passing (backend + frontend).

## Quick Start

```bash
# Clone
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Alpaca API keys
python start_server.py

# Frontend setup (new terminal)
cd frontend-v2
npm install
npm run dev
```

## License

Private repository — Embodier.ai

### Pages vs Mockup Completion Status

| Page | Mockup | API Wired | Mockup Complete % | Status |
|---|---|---|---|---|
| Agent Command Center | ACC-tabs mockup | YES | ~90% | **DEPLOYED — decomposed into tabs + shared components** |
| Data Sources Manager | 09-data-sources-manager.png | YES | **100%** | **DONE AND COMPLETE** |
| Patterns & Screener | 07-screener-and-patterns.png | YES | ~70% | Real API wired, needs mockup polish |
| Performance Analytics | TBD | YES | ~20% | **NEXT — pending mockup alignment** |
| Active Trades | Active-Trades.png | YES | **100%** | **DONE AND COMPLETE** |
| Trade Execution | Trade-Execution mockup | YES | **100%** | **DONE AND COMPLETE** |
| Market Regime | 10-market-regime.png | YES | **100%** | **DONE AND COMPLETE** |

### Primary Data Sources (NO yfinance)

- **Alpaca Markets** (`alpaca-py`) — Market data + order execution
- **Unusual Whales** — Options flow
- **Finviz** (`finviz`) — Screener, fundamentals, VIX proxy

## Repository Structure & AI Tools

For AI assistants working with this codebase:

| File | Purpose |
|---|---|
| `REPO-MAP.md` | Full directory tree with file descriptions |
| `AI-CONTEXT-GUIDE.md` | 5 strategies for managing AI context limits |
| `map_repo.py` | Auto-generate repo tree (run locally) |
| `bundle_files.py` | Bundle key files into single text for AI input |

### Quick Repo Overview

```
elite-trading-system/
|-- backend/           # FastAPI (Python 3.11) - 25 API routes, 15 services
|   |-- app/api/v1/    # REST endpoints
|   |-- app/services/  # Business logic (Alpaca, FinViz, UW APIs)
|   |-- app/modules/   # ML engine, OpenClaw, chart patterns
|   |-- tests/         # 70 tests (CI green)
|
|-- frontend-v2/       # React 18 (Vite) - 14 pages + sidebar
|   |-- src/pages/     # Route pages (each self-contained)
|   |-- src/hooks/     # useApi.js (central data hook)
|   |-- src/services/  # API clients + WebSocket
|   |-- src/components/ # UI components (agents, charts, dashboard, layout, ui)
|
|-- core/api/          # Standalone ML API module
|-- docs/              # Mockups, status docs, design system
|-- scripts/           # Utility scripts (indentation fixer, migrations)
```

See `REPO-MAP.md` for the complete file-by-file tree.

---

## CNS Agent Architecture (Phase 2)

> **Status: DESIGNED — Implementation pending**

The Embodier Trader operates as a conscious profit-seeking being with a Central Nervous System (CNS) architecture:

### Agent Hierarchy

| Layer | Agents | Role |
|---|---|---|
| **Brainstem** | Ollama (local) | Fast reflexes — stop-loss, circuit breakers, position sizing |
| **Cortex** | Perplexity Sonar API | Real-time market intelligence, news sentiment, sector analysis |
| **Deep Cortex** | Claude API | Complex strategy synthesis, multi-day pattern recognition |
| **Blackboard** | SharedState | Central memory — all agents read/write unified state |

### Core Components

- **BlackboardState**: Shared memory across all agents (market data, signals, positions, risk)
- **CircuitBreaker**: Automatic trading halts on anomaly detection
- **TaskSpawner**: Dynamic agent creation based on market conditions
- **Self-Awareness Module**: Performance tracking, confidence calibration, drift detection
- **Homeostasis Engine**: Keeps risk within target bounds automatically

## Recursive Self-Improvement (Phase 3 — RSI)

> **Status: DESIGNED — Architecture documented**

The system teaches itself through three pillars:

1. **Pattern Discovery Engine** — Automated detection of mean-reversion, sector rotation, fear/greed cycles
2. **Strategy Evolution Lab** — Genetic algorithm optimization of trading strategies with backtesting
3. **Persistent Memory Center** — Long-term storage of discovered patterns, strategy performance, market regimes

### Multi-LLM Intelligence Tiers

```
Tier 1: Ollama (Local)     — <100ms latency, position management, risk checks
Tier 2: Perplexity Sonar   — Real-time search, news, market intelligence ($5/1M tokens)
Tier 3: Claude API          — Deep analysis, strategy synthesis, pattern validation
```

Routed via LiteLLM with automatic failover and cost optimization.

## License

Private repository — Embodier.ai

