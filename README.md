# Elite Trading System

**Full-Stack AI Trading Platform -- UI/UX, Database, and GPU Training Pipeline**

React + FastAPI full-stack trading application with 15-page V3 widescreen dashboard, SQLite database, Alpaca + Finviz integrations, LSTM model training, XGBoost GPU ensemble, and real-time order execution. Serves as the user-facing control center for the Embodier.ai trading ecosystem.

> **Part of the Embodier.ai Elite Trading ecosystem.** This is the unified full-stack trading platform. All 42+ [OpenClaw](https://github.com/Espenator/openclaw) Python agents and the Blackboard Swarm architecture are now integrated in `core/` and `backend/`. The openclaw repo is archived.

---

## Project Status (Audit: Feb 26, 2026)

| Component | Status | Notes |
|---|---|---|
| React Frontend-v2 (15 pages) | 15/15 V3 Coded | 11 complete with LW Charts, 4 coded with Recharts (need LW Charts migration) |
| FastAPI Backend | Complete | REST API with versioned endpoints (`/api/v1/`) |
| SQLite Database | Complete | Orders, trades, signals, positions via `database.py` |
| Alpaca Integration | Complete | `alpaca_service.py` -- live/paper trading + market data |
| Finviz Integration | Complete | `finviz_service.py` -- stock screener + chart data |
| OpenClaw Bridge API | Complete | `openclaw_db.py` + `openclaw.py` -- SQLite persistence, POST/GET endpoints |
| Backtest Engine | Complete | `backtest_engine.py` -- historical signal sim, Sharpe/PnL/MaxDD |
| LSTM Training Pipeline | Complete | `ml_training.py` -- PyTorch GPU/CPU, model versioning |
| APEX Phase 2 -- GPU Pipeline | Complete | Trainer AMP, XGBoost GPU, config, /gpu endpoint |
| WebSocket Live Updates | Planned | Real-time push from OpenClaw streaming engine |
| Notification System | Planned | Replace Slack alerts with in-app toast/bell notifications |
| Authentication | Planned | User login/session management for production deployment |

### Remaining To-Dos

- [x] **Build OpenClaw Bridge endpoint** -- `openclaw_db.py` + `openclaw.py` with SQLite persistence (DONE)
- [x] **Implement backtest strategy runner** -- `backtest_engine.py` with Sharpe/PnL/MaxDD + REST endpoints (DONE)
- [x] **LSTM training pipeline backend** -- `ml_training.py` connected to GPU training with model versioning (DONE)
- [x] **APEX Phase 2 GPU pipeline** -- Trainer AMP, XGBoost GPU, config, /gpu endpoint (DONE)
- [x] **V3 UI code for all 15 pages** -- All pages now have V3 widescreen layout code (DONE)
- [ ] **Migrate 4 Recharts pages to LW Charts** -- SentimentIntelligence, DataSourcesMonitor, Patterns, Settings
- [ ] **Wire real API data** -- Replace simulated/mock data with live backend endpoints
- [ ] **Add WebSocket support** -- Push real-time signals, position updates, and streaming engine events to frontend
- [ ] **Build notification service** -- In-app notification bell + toast alerts to replace Slack dependency
- [ ] **Add trade journal tables** -- Migrate OpenClaw `sheets_logger.py` data to `database.py`
- [ ] **Add authentication** -- User login/session management for production deployment

### Intelligence Council Audit (Feb 26, 2026)

A 3-model AI council (GPT-5.2, Claude Opus 4.6, Gemini 3.1 Pro) reviewed the full codebase against the Agent Intelligence architecture document. Key findings:

**Where Council Was Correct:**
- Zero test coverage -- no `tests/` directory, only 2 utility scripts in `backend/tools/`
- SQLite write lock bottleneck -- `database.py` creates new connections per call, no WAL mode, no pooling
- `mockData.js` still present in `frontend-v2/src/data/` despite Issue #8 cleanup
- `signal_engine.py` scoring too simplistic (bull/bear candle only vs. OpenClaw's 5-pillar system)
- `ml_training.py` LSTM has input_size=4 but system generates 25+ features
- `openclaw_bridge_service.py` is 976-line god module needing split

**Where Council Was Wrong/Outdated:**
- "Risk Engine missing" -- INCORRECT: `risk_shield_api.py` wires to OpenClaw `risk_governor.py` (474 lines, 9 safety checks)
- "Only 2/5 systems complete" -- OUTDATED: Phase 2 copy brought full OpenClaw swarm (clawbots, execution, intelligence, scorer, streaming, world_intel)
- "Backtester missing" -- INCORRECT: `backtest_engine.py` exists with Sharpe/MaxDD/Calmar metrics

### Code Improvement Roadmap (Feb 26, 2026)

| Priority | Task | File(s) | Status |
|---|---|---|---|
| P0 | Add test suite | `backend/tests/` | NOT STARTED |
| P0 | Fix database.py (WAL, pooling, indexes) | `backend/app/services/database.py` | DONE |
| P0 | Delete mockData.js | `frontend-v2/src/data/mockData.js` | DONE |
| P1 | Wire OpenClaw pillar scores into signal_engine | `backend/app/services/signal_engine.py` | NOT STARTED |
| P1 | Fix LSTM architecture (input_size, normalization) | `backend/app/services/ml_training.py` | NOT STARTED |
| P1 | Split openclaw_bridge_service into modules | `backend/app/services/openclaw_bridge_*.py` | NOT STARTED |
| P1 | Wire risk_governor into execution path | `backend/app/services/alpaca_service.py` | NOT STARTED |
| P2 | Add missing DB tables (trades journal, model_versions) | `backend/app/services/database.py` | NOT STARTED |
| P2 | Build meta-learning orchestrator | `backend/app/services/meta_learner.py` | NOT STARTED |
| P2 | Wire swarm tournament from apex_orchestrator | `backend/app/services/swarm_manager.py` | NOT STARTED |
| P3 | Add schema migration tracking | `backend/app/services/database.py` | NOT STARTED |

## V3 Frontend Architecture (15 Pages)

Consolidated from 18 pages down to 15 for cleaner UX. See `frontend-v2/src/V3-ARCHITECTURE.md` for full details.

### COMMAND (2 pages)

| Page | File | Route | Status |
|---|---|---|---|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` | V3 COMPLETE |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | V3 COMPLETE |

### INTELLIGENCE (3 pages)

| Page | File | Route | Status |
|---|---|---|---|
| Signal Intelligence | `Signals.jsx` | `/signals` | V3 COMPLETE |
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | V3 CODED - NEEDS LW CHARTS |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | V3 CODED - NEEDS LW CHARTS |

### ML & ANALYSIS (6 pages)

| Page | File | Route | Status |
|---|---|---|---|
| ML Insights | `MLInsights.jsx` | `/ml-insights` | V3 COMPLETE |
| ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | V3 COMPLETE |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | V3 CODED - NEEDS LW CHARTS |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` | V3 COMPLETE |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | V3 COMPLETE |
| Market Regime | `MarketRegime.jsx` | `/market-regime` | V3 COMPLETE |

### EXECUTION (3 pages)

| Page | File | Route | Status |
|---|---|---|---|
| Active Trades | `Trades.jsx` | `/trades` | V3 COMPLETE |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | V3 COMPLETE |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` | V3 COMPLETE |

### SYSTEM (1 page)

| Page | File | Route | Status |
|---|---|---|---|
| Settings | `Settings.jsx` | `/settings` | V3 CODED - NEEDS LW CHARTS |

## Architecture Overview

```
Elite Trading System
backend/                    # FastAPI Python backend
  app/
    api/v1/                 # REST API endpoints
      backtest_routes.py
      openclaw.py           # OpenClaw bridge router
      orders.py             # Alpaca order management
      quotes.py             # Price/chart data
      signals.py            # Trading signals CRUD
      status.py             # System health
      stocks.py             # Finviz screener
      system.py             # System config + /gpu endpoint
      training.py           # ML model training
    core/                   # App config (GPU_DEVICE, AMP, XGBoost)
    models/                 # SQLAlchemy ORM + LSTM trainer (AMP)
      trainer.py            # APEX Phase 2: mixed-precision LSTM
      inference.py
    modules/
      ml_engine/
        xgboost_trainer.py  # APEX Phase 2: GPU XGBoost
    schemas/                # Pydantic request/response schemas
    services/               # External service integrations
      alpaca_service.py
      backtest_engine.py    # Historical signal backtester
      database.py           # SQLite database layer
      finviz_service.py
      ml_training.py        # PyTorch GPU/CPU LSTM service
      openclaw_db.py        # OpenClaw bridge SQLite service
    strategy/               # Trading strategy logic
  main.py                   # FastAPI app entry point
  jobs/                     # Scheduled/background jobs
  tools/                    # CLI utilities
frontend-v2/                # React + Vite V3 frontend
  src/
    components/             # Reusable UI components
    config/                 # API URLs, constants
    data/                   # Static data, enums
    hooks/                  # useApi, useWebSocket, custom hooks
    lib/                    # Utility functions
    pages/                  # 15 V3 page components
    services/               # API service layer
    V3-ARCHITECTURE.md      # Authoritative architecture doc
frontend/                   # Legacy frontend (deprecated)
docs/
  mockups-v3/               # V3 UI mockup specifications
    FULL-MOCKUP-SPEC.md
```

## API Endpoints

All backend routes are versioned under `/api/v1/`:

| Route Module | Endpoints | Purpose |
|---|---|---|
| `signals.py` | GET/POST `/api/v1/signals` | Trading signal CRUD |
| `orders.py` | GET/POST `/api/v1/orders` | Alpaca order management |
| `quotes.py` | GET `/api/v1/quotes` | Price and chart data |
| `stocks.py` | GET `/api/v1/stocks` | Finviz screener queries |
| `status.py` | GET `/api/v1/status` | System health check |
| `system.py` | GET `/api/v1/system`, GET `/api/v1/gpu` | System config + GPU health |
| `training.py` | POST `/api/v1/training` | ML model training jobs |
| `backtest_routes.py` | POST `/api/v1/backtest` | Strategy backtesting |
| `openclaw.py` | POST/GET `/api/v1/openclaw/*` | OpenClaw bridge (signals, ingests, backtest) |

## OpenClaw (Now Integrated)

All 42+ OpenClaw Python agents and the Blackboard Swarm architecture now live in `core/` and `backend/`. The [openclaw repo](https://github.com/Espenator/openclaw) is archived. Key integrated components:

- 42+ Python agents in a Blackboard Swarm architecture
- Real-time streaming via Alpaca WebSocket
- 100-point composite scoring with ML ensemble
- HMM regime detection (GREEN/YELLOW/RED)
- Risk Governor with 8 safety checks

### Internal Architecture

```
Elite Trading System (Unified)
+----------------------------------------------+
| core/               (OpenClaw Agents)        |
|   42+ Python Agents, Blackboard Swarm        |
|   Streaming Engine, Risk Governor            |
|   LSTM Bridge, HMM Regime Detection          |
+----------------------------------------------+
|                    |                         |
| backend/           | frontend-v2/            |
|   FastAPI Backend   |   React + Vite V3       |
|   /api/v1/openclaw  |   15 Pages Widescreen   |
|   /api/v1/signals   |   WebSocket Dashboard   |
|   SQLite + ORM      |                         |
|   LSTM Trainer(AMP) |                         |
|   XGBoost (GPU)     |                         |
+----------------------------------------------+
```

## Data Migration Status (OpenClaw -> Elite Trader)

OpenClaw data sources (Google Sheets, Slack) have been replaced by native integrations. Migration status:

| OpenClaw Source | Elite Trader Destination | Status |
|---|---|---|
| `sheets_logger.py` Trade Log | `database.py` -> `trades` table | To Build |
| `sheets_logger.py` Signals | `openclaw_signals` table (via `openclaw_db.py`) | Done |
| `sheets_logger.py` Ingests | `openclaw_ingests` table (via `openclaw_db.py`) | Done |
| `sheets_logger.py` Daily Journal | `database.py` -> `journal` table | To Build |
| `sheets_logger.py` Audit Trail | `database.py` -> `audit_trail` table | To Build |
| Slack pipeline summaries | `Dashboard.jsx` | Page Ready |
| Slack score alerts | `Signals.jsx` | Page Ready |
| Slack trade notifications | `TradeExecution.jsx` | Page Ready |
| Slack performance reports | `PerformanceAnalytics.jsx` | Page Ready |

## Quick Start

```bash
# Clone
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Alpaca API keys + GPU settings

# Start backend
python start_server.py

# Frontend setup (new terminal)
cd frontend-v2
npm install
npm run dev

# Or start both at once (Windows)
start_all.bat
```

## Configuration

Backend configuration via `.env` file.

Required: `ALPACA_API_KEY` + `ALPACA_SECRET_KEY`

APEX Phase 2 GPU settings (optional, auto-detected):
- `GPU_DEVICE` -- cuda device index (default: `cuda:0`)
- `TORCH_MIXED_PRECISION` -- enable AMP (default: `true`)
- `XGBOOST_GPU_ID` -- XGBoost GPU device (default: `0`)
- `TRAINING_SCHEDULE` -- cron for scheduled retraining
- `MODEL_ARTIFACTS_PATH` -- path for saved model checkpoints

See `backend/.env.example` for all available environment variables.

## Key Documentation

| File | Description |
|---|---|
| `frontend-v2/src/V3-ARCHITECTURE.md` | **AUTHORITATIVE** V3 15-page architecture |
| `frontend-v2/public/assets/mockups/` | Approved mockup designs |
| `OLEH-CONTINUATION-GUIDE.md` | Developer continuation guide with priorities |
| `OLEH-HANDOFF.md` | Original handoff with backend wiring details |

## License

Private repository -- Embodier.ai
