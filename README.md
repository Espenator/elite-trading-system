# Elite Trading System

**Embodier.ai Full-Stack AI Trading Intelligence Platform**

> **Last Updated: February 28, 2026 (8:00 AM EST)**
> **Status: Production audit in progress. All pages wired to real API hooks (useApi). Mock/hardcoded data being systematically removed.**
> **Next Step: Complete production audit of all 15 pages, fix remaining mock data, test end-to-end.**

React + FastAPI full-stack trading application with 15-route V3 widescreen dashboard (14 sidebar + 1 hidden), SQLite database, Alpaca + Finviz integrations, 42+ OpenClaw Python agents in a Blackboard Swarm, LSTM/XGBoost ML pipeline, and real-time order execution.

> **Part of the Embodier.ai Elite Trading ecosystem.** All 42+ [OpenClaw](https://github.com/Espenator/openclaw) Python agents and the Blackboard Swarm architecture are integrated in `core/` and `backend/`. The openclaw repo is archived.

---

## AI CONTEXT: READ THIS FIRST

If you are an AI assistant reading this repo, here is exactly where we are:

1. **All 15 frontend pages exist** with V3 UI code (14 sidebar + 1 hidden route)
2. **All 27+ backend API routes exist** in `backend/app/api/v1/`
3. **All 20+ backend services exist** in `backend/app/services/`
4. **Frontend pages use `useApi` hook** for real-time polling -- no mock data should remain
5. **6 approved UI mockup images** exist in `docs/mockups-v3/images/`
6. **Design system is finalized** -- see `docs/UI-DESIGN-SYSTEM.md` for exact colors, fonts, spacing
7. **Agent Command Center** has been audited and wired to real API data
8. **Intelligence Dashboard** has been audited and wired to real API data
9. **Sidebar navigation** is organized into 5 sections: COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM
10. **Backend has never been started** -- FastAPI server exists but has not been run or tested
11. **No authentication system** -- no login, no user sessions
12. **No WebSocket real-time data flowing** -- WebSocket code exists but is not connected

### Key Documentation Files

| File | Purpose |
|------|--------|
| `frontend-v2/src/V3-ARCHITECTURE.md` | **AUTHORITATIVE** frontend architecture (15 routes, charting audit, component map) |
| `docs/UI-DESIGN-SYSTEM.md` | **AUTHORITATIVE** design system (colors, fonts, spacing from approved mockups) |
| `docs/mockups-v3/images/` | Approved mockup images (source of truth for visual design) |
| `docs/mockups-v3/FULL-MOCKUP-SPEC.md` | Full mockup specification for all 14 pages |

---

## Frontend Pages & Sidebar Menu (V3 - CURRENT)

The sidebar is defined in `frontend-v2/src/components/layout/Sidebar.jsx`. Routes are in `frontend-v2/src/App.jsx`.

### COMMAND Section

| # | Route | Sidebar Label | File | Audit Status |
|---|-------|--------------|------|-------------|
| 1 | `/dashboard` | **Intelligence Dashboard** | `Dashboard.jsx` | DONE - wired to useApi |
| 2 | `/agents` | **Agent Command Center** | `AgentCommandCenter.jsx` | DONE - wired to useApi |

### INTELLIGENCE Section

| # | Route | Sidebar Label | File | Audit Status |
|---|-------|--------------|------|-------------|
| 3 | `/signals` | **Signal Intelligence** | `Signals.jsx` | Pending audit |
| 4 | `/sentiment` | **Sentiment Intelligence** | `SentimentIntelligence.jsx` | Pending audit |
| 5 | `/data-sources` | **Data Sources Manager** | `DataSourcesMonitor.jsx` | Pending audit |

### ML & ANALYSIS Section

| # | Route | Sidebar Label | File | Audit Status |
|---|-------|--------------|------|-------------|
| 6 | `/ml-brain` | **ML Brain & Flywheel** | `MLBrainFlywheel.jsx` | Pending audit |
| 7 | `/patterns` | **Screener & Patterns** | `Patterns.jsx` | Pending audit |
| 8 | `/backtest` | **Backtesting Lab** | `Backtesting.jsx` | Pending audit |
| 9 | `/performance` | **Performance Analytics** | `PerformanceAnalytics.jsx` | Pending audit |
| 10 | `/market-regime` | **Market Regime** | `MarketRegime.jsx` | Pending audit |

### EXECUTION Section

| # | Route | Sidebar Label | File | Audit Status |
|---|-------|--------------|------|-------------|
| 11 | `/trades` | **Active Trades** | `Trades.jsx` | Pending audit |
| 12 | `/risk` | **Risk Intelligence** | `RiskIntelligence.jsx` | Pending audit |
| 13 | `/trade-execution` | **Trade Execution** | `TradeExecution.jsx` | Pending audit |

### SYSTEM Section

| # | Route | Sidebar Label | File | Audit Status |
|---|-------|--------------|------|-------------|
| 14 | `/settings` | **Settings** | `Settings.jsx` | Pending audit |

### Hidden Route

| # | Route | File | Notes |
|---|-------|------|------|
| 15 | `/signal-v3` | `SignalIntelligenceV3.jsx` | Advanced signal view, not in sidebar |

---

## Frontend Component Structure

```
frontend-v2/src/
  components/
    agents/          # Agent Command Center sub-components
    charts/          # Chart wrappers (PatternFrequencyLC, MiniChart, etc.)
    dashboard/       # Dashboard sub-components
    layout/          # Sidebar.jsx, Layout.jsx, Header.jsx
    ui/              # Shared UI (Button, TextField, Slider, Checkbox, DataTable, etc.)
      ErrorBoundary.jsx
      RegimeBanner.jsx
  config/
    api.js           # getApiUrl() helper
  hooks/
    useApi.js        # Central API hook with polling support
  lib/
    dataSourceIcons.js  # Data source icon mappings
  pages/             # All 15 page files (see table above)
  services/          # API service layer
  App.jsx            # Router with all 15 routes
  main.jsx           # Entry point
```

## Backend Architecture

### FastAPI Server (`backend/app/main.py`)

- Mounts all API v1 routers
- CORS middleware configured
- SQLite database initialization
- WebSocket endpoint for real-time data

### API Routes (`backend/app/api/v1/`)

| Router File | Endpoints | Purpose |
|------------|-----------|--------|
| `trading.py` | 5+ routes | Order execution, positions, trade history |
| `market_data.py` | 4+ routes | Real-time quotes, historical data, screener |
| `agents.py` | 6+ routes | Agent status, control, swarm management |
| `portfolio.py` | 4+ routes | Holdings, performance, allocation |
| `ml_models.py` | 4+ routes | Model predictions, training, status |
| `risk.py` | 3+ routes | Risk metrics, limits, exposure |
| `backtesting.py` | 3+ routes | Strategy backtests, results |
| `alerts.py` | 3+ routes | Alert management, notifications |

### Services (`backend/app/services/`)

20+ service files handling:
- Alpaca broker integration (REST + WebSocket)
- Finviz screening and data
- OpenClaw agent orchestration
- ML model inference (LSTM, XGBoost)
- Risk calculation engine
- HMM regime detection
- Blackboard Swarm pub/sub
- Conference consensus engine

### Core Agents (`core/`)

42+ Python agents in Blackboard Swarm architecture:
- Streaming engine for real-time data
- Risk Governor with 8 safety checks
- LSTM bridge for time-series prediction
- HMM regime detection (GREEN/YELLOW/RED)
- 100-point composite scoring with ML ensemble

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, lucide-react icons |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| AI/ML | LSTM, XGBoost, HMM, OpenClaw agents |
| Broker | Alpaca Markets (paper + live trading) |
| Data | Finviz, Alpaca WebSocket, Yahoo Finance |
| Architecture | Blackboard Swarm, pub/sub messaging |

## Repository Structure

```
elite-trading-system/
  frontend-v2/           # React frontend (V3 widescreen UI)
    public/
      data-sources/      # Data source icons/images
    src/
      components/        # Shared components
      config/            # API configuration
      hooks/             # Custom React hooks (useApi)
      lib/               # Utility libraries
      pages/             # 15 page components
      services/          # API service layer
      App.jsx            # Router with 15 routes
      V3-ARCHITECTURE.md # Frontend architecture doc
    package.json
  backend/               # FastAPI backend
    app/
      api/v1/            # 27+ API route files
      services/          # 20+ service implementations
      models/            # SQLAlchemy models
      main.py            # FastAPI app entry point
    tests/               # Backend test suite
    requirements.txt
  core/                  # OpenClaw Python agents (42+)
  docs/                  # Project documentation
    mockups-v3/          # UI mockups and specs
    UI-DESIGN-SYSTEM.md
  scripts/               # Utility scripts
  docker-compose.yml     # Docker setup
  .env.example           # Environment variables template
```

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

Private repository -- Embodier.ai
