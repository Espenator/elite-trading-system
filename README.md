# 📈 Elite Trading System

**Full-Stack AI Trading Platform — UI/UX, Database, and GPU Training Pipeline**

React + FastAPI full-stack trading application with 15-page dashboard, SQLite database, Alpaca + Finviz integrations, LSTM model training, XGBoost GPU ensemble, and real-time order execution. Serves as the user-facing control center for the Embodier.ai trading ecosystem.

> **Part of the Embodier.ai Elite Trading ecosystem.** This repo (PC2) provides the full-stack UI/UX, database, and GPU training pipeline. [OpenClaw](https://github.com/Espenator/openclaw) (PC1) is the 42-agent intelligence engine with Blackboard Swarm architecture.

---

## 📊 Project Status (Audit: Feb 24, 2026)

| Component | Status | Notes |
|---|---|---|
| React Frontend (15 pages) | ✅ **Complete** | Dashboard, Signals, TradeExecution, Backtest, etc. |
| FastAPI Backend | ✅ **Complete** | REST API with versioned endpoints (`/api/v1/`) |
| SQLite Database | ✅ **Complete** | Orders, trades, signals, positions via `database.py` |
| Alpaca Integration | ✅ **Complete** | `alpaca_service.py` — live/paper trading + market data |
| Finviz Integration | ✅ **Complete** | `finviz_service.py` — stock screener + chart data |
| Dark/Light Theme | ✅ **Complete** | Full theme system with CSS variables |
| Model Training Page | ✅ **Complete** | `ModelTraining.tsx` — LSTM training UI |
| API v1 Routes | ✅ **Complete** | signals, orders, quotes, stocks, status, system, training, backtest, openclaw |
| OpenClaw Bridge API | ✅ **Complete** | `openclaw_db.py` + `openclaw.py` — SQLite persistence, POST/GET endpoints, signals + ingests tables |
| Backtest Engine | ✅ **Complete** | `backtest_engine.py` — historical signal sim, Sharpe/PnL/MaxDD; `/run` + `/run/detail` endpoints |
| LSTM Training Pipeline | ✅ **Complete** | `ml_training.py` — PyTorch GPU/CPU, trains on openclaw signals, model versioning |
| APEX Phase 2 — LSTM Trainer | ✅ **Complete** | `trainer.py` — mixed-precision AMP, gradient clipping, early stopping, checkpointing |
| APEX Phase 2 — XGBoost Engine | ✅ **Complete** | `xgboost_trainer.py` — GPU `gpu_hist`, grid search, CV, feature importance |
| APEX Phase 2 — GPU Config | ✅ **Complete** | `config.py` — GPU_DEVICE, TORCH_MIXED_PRECISION, XGBOOST_GPU_ID, TRAINING_SCHEDULE |
| APEX Phase 2 — GPU Monitor | ✅ **Complete** | `system.py` — `/gpu` endpoint for nvidia-smi health monitoring |
| WebSocket Live Updates | 🔧 **Planned** | Real-time push from OpenClaw streaming engine |
| Notification System | 🔧 **Planned** | Replace Slack alerts with in-app toast/bell notifications |
| Authentication | 🔧 **Planned** | User login/session management for production deployment |

---

### 🔴 Remaining To-Dos

- [x] **Build OpenClaw Bridge endpoint** — `openclaw_db.py` + `openclaw.py` with SQLite persistence (DONE)
- [x] **Implement backtest strategy runner** — `backtest_engine.py` with Sharpe/PnL/MaxDD + REST endpoints (DONE)
- [x] **LSTM training pipeline backend** — `ml_training.py` connected to GPU training with model versioning (DONE)
- [x] **APEX Phase 2 GPU pipeline** — Trainer AMP, XGBoost GPU, config, /gpu endpoint (DONE)
- [ ] **Add WebSocket support** — Push real-time signals, position updates, and streaming engine events to frontend
- [ ] **Build notification service** — In-app notification bell + toast alerts to replace Slack dependency
- [ ] **Add trade journal tables** — Migrate OpenClaw `sheets_logger.py` data to `database.py` (`trades`, `signals`, `journal`, `audit_trail` tables)
- [ ] **Add authentication** — User login/session management for production deployment
- [ ] **Performance Analytics data pipeline** — Wire `PerformanceAnalytics.jsx` to backend win rate, Sharpe, drawdown calculations
- [ ] **Resolve 1 open GitHub issue** — See [Issues](https://github.com/Espenator/elite-trading-system/issues)

---

### 🟢 Migration Plan: Receiving OpenClaw Data

OpenClaw currently logs to Google Sheets (deprecated) and Slack (optional). This system will replace both:

| OpenClaw Source | Elite Trader Destination | Status |
|---|---|---|
| `sheets_logger.py` Trade Log | `database.py` → `trades` table | 🔧 To Build |
| `sheets_logger.py` Signals | `openclaw_signals` table (via `openclaw_db.py`) | ✅ Done |
| `sheets_logger.py` Ingests | `openclaw_ingests` table (via `openclaw_db.py`) | ✅ Done |
| `sheets_logger.py` Daily Journal | `database.py` → `journal` table | 🔧 To Build |
| `sheets_logger.py` Audit Trail | `database.py` → `audit_trail` table | 🔧 To Build |
| Slack pipeline summaries | `Dashboard.jsx` | ✅ Page Ready |
| Slack score alerts | `Signals.jsx` | ✅ Page Ready |
| Slack trade notifications | `TradeExecution.jsx` | ✅ Page Ready |
| Slack performance reports | `PerformanceAnalytics.jsx` | ✅ Page Ready |

---

## 🏗 Architecture Overview

```
Elite Trading System (PC2)
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/             # REST API endpoints
│   │   │   ├── backtest_routes.py
│   │   │   ├── openclaw.py     # OpenClaw bridge router (NEW)
│   │   │   ├── orders.py       # Alpaca order management
│   │   │   ├── quotes.py       # Price/chart data
│   │   │   ├── signals.py      # Trading signals CRUD
│   │   │   ├── status.py       # System health
│   │   │   ├── stocks.py       # Finviz screener
│   │   │   ├── system.py       # System config + /gpu endpoint
│   │   │   └── training.py     # ML model training
│   │   ├── core/               # App config (GPU_DEVICE, AMP, XGBoost)
│   │   ├── models/             # SQLAlchemy ORM + LSTM trainer (AMP)
│   │   │   ├── trainer.py      # APEX Phase 2: mixed-precision LSTM
│   │   │   └── inference.py
│   │   ├── modules/
│   │   │   └── ml_engine/      # ML engine module
│   │   │       └── xgboost_trainer.py  # APEX Phase 2: GPU XGBoost
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # External service integrations
│   │   │   ├── alpaca_service.py
│   │   │   ├── backtest_engine.py  # NEW: historical signal backtester
│   │   │   ├── database.py     # SQLite database layer
│   │   │   ├── finviz_service.py
│   │   │   ├── ml_training.py  # NEW: PyTorch GPU/CPU LSTM service
│   │   │   └── openclaw_db.py  # NEW: OpenClaw bridge SQLite service
│   │   ├── strategy/           # Trading strategy logic
│   │   └── main.py             # FastAPI app entry point
│   ├── jobs/                   # Scheduled/background jobs
│   └── tools/                  # CLI utilities
│
├── frontend/                   # React + Vite frontend
│   └── src/
│       ├── components/         # Reusable UI components
│       ├── context/            # React context providers
│       ├── pages/              # 15 page components
│       ├── routes/             # React Router config
│       ├── services/           # API client services
│       ├── styles/             # CSS themes (dark/light)
│       ├── types/              # TypeScript interfaces
│       └── utils/              # Helper functions
│
└── start_all.bat               # Windows launcher for both servers
```

---

## 🖥 Frontend Pages (15)

| Page | File | Purpose |
|---|---|---|
| Dashboard | `Dashboard.jsx` | Main trading dashboard with portfolio overview |
| Signals | `Signals.jsx` | OpenClaw signal feed with composite scores |
| Trade Execution | `TradeExecution.jsx` | Order entry, Alpaca live/paper execution |
| Order History | `OrderHistory.jsx` | Historical orders and fills |
| Backtest | `Backtest.jsx` | Strategy backtesting interface |
| Screener Results | `ScreenerResults.tsx` | Finviz stock screener results |
| Performance Analytics | `PerformanceAnalytics.jsx` | Win rate, Sharpe, P&L charts |
| Portfolio Heatmap | `PortfolioHeatmap.tsx` | Visual sector/position heatmap |
| Risk Configuration | `RiskConfiguration.jsx` | Risk parameters and limits |
| Strategy Settings | `StrategySettings.jsx` | Strategy configuration panel |
| Model Training | `ModelTraining.tsx` | LSTM/ML model training interface |
| Account | `Account.jsx` | Alpaca account info and balances |
| Account Settings | `AccountSettings.jsx` | User preferences and API keys |
| Settings | `Settings.jsx` | Application settings |
| Not Found | `NotFound.jsx` | 404 error page |

---

## 🔌 API Endpoints

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

---

## 🔗 Integration with OpenClaw

This repo (PC2) is the **full-stack UI/UX application**. [OpenClaw](https://github.com/Espenator/openclaw) (PC1) is the **intelligence engine** with:

- 42+ Python agents in a Blackboard Swarm architecture
- Real-time streaming via Alpaca WebSocket
- 100-point composite scoring with ML ensemble
- HMM regime detection (GREEN/YELLOW/RED)
- Risk Governor with 8 safety checks

### Bridge Architecture

```
PC1 (OpenClaw)                    PC2 (Elite Trading System)
┌──────────────────┐              ┌──────────────────────────┐
│ Blackboard Swarm │              │ FastAPI Backend           │
│ 42+ Python Agents│──── API ────>│ /api/v1/openclaw/signals  │
│ Streaming Engine │              │ /api/v1/openclaw/ingests  │
│ Risk Governor    │              │ /api/v1/openclaw/backtest │
│                  │              │ SQLite (openclaw_db.py)   │
│ lstm_bridge      │──── GPU ────>│ LSTM Trainer (AMP)        │
│ service.py       │   models     │ XGBoost Trainer (GPU)     │
└──────────────────┘              │                           │
                                  │ React Frontend            │
                                  │ 15 Pages + Dashboard      │
                                  └──────────────────────────┘
```

---

## 🚀 Quick Start

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
cd frontend
npm install
npm run dev

# Or start both at once (Windows)
start_all.bat
```

## ⚙️ Configuration

Backend configuration via `.env` file.

Required: `ALPACA_API_KEY` + `ALPACA_SECRET_KEY`

APEX Phase 2 GPU settings (optional, auto-detected):
- `GPU_DEVICE` — cuda device index (default: `cuda:0`)
- `TORCH_MIXED_PRECISION` — enable AMP (default: `true`)
- `XGBOOST_GPU_ID` — XGBoost GPU device (default: `0`)
- `TRAINING_SCHEDULE` — cron for scheduled retraining
- `MODEL_ARTIFACTS_PATH` — path for saved model checkpoints

See `backend/.env.example` for all available environment variables.

---

## 📄 License

Private repository — Embodier.ai
# 📈 Elite Trading System

**Full-Stack AI Trading Platform — UI/UX, Database, and GPU Training Pipeline**

React + FastAPI full-stack trading application with 15-page dashboard, SQLite database, Alpaca + Finviz integrations, LSTM model training, and real-time order execution. Serves as the user-facing control center for the Embodier.ai trading ecosystem.

> **Part of the Embodier.ai Elite Trading ecosystem.** This repo (PC2) provides the full-stack UI/UX, database, and GPU training pipeline. [OpenClaw](https://github.com/Espenator/openclaw) (PC1) is the 42-agent intelligence engine with Blackboard Swarm architecture.

---

## 📊 Project Status (Audit: Feb 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| React Frontend (15 pages) | ✅ **Complete** | Dashboard, Signals, TradeExecution, Backtest, etc. |
| FastAPI Backend | ✅ **Complete** | REST API with versioned endpoints (`/api/v1/`) |
| SQLite Database | ✅ **Complete** | Orders, trades, signals, positions via `database.py` |
| Alpaca Integration | ✅ **Complete** | `alpaca_service.py` — live/paper trading + market data |
| Finviz Integration | ✅ **Complete** | `finviz_service.py` — stock screener + chart data |
| Dark/Light Theme | ✅ **Complete** | Full theme system with CSS variables |
| Model Training Page | ✅ **Complete** | `ModelTraining.tsx` — LSTM training UI |
| API v1 Routes | ✅ **Complete** | signals, orders, quotes, stocks, status, system, training, backtest |
| OpenClaw Bridge API | 🔧 **In Progress** | Needs `/api/v1/signals` endpoint to receive OpenClaw scores |
| Backtest Engine | 🔧 **In Progress** | `Backtest.jsx` page exists, needs backend strategy runner |
| WebSocket Live Updates | 🔧 **Planned** | Real-time push from OpenClaw streaming engine |
| Notification System | 🔧 **Planned** | Replace Slack alerts with in-app toast/bell notifications |

### 🔴 Remaining To-Dos

- [ ] **Build OpenClaw Bridge endpoint** — Add `/api/v1/openclaw/signals` POST route to receive composite scores, regime state, and trade recommendations from PC1
- [ ] **Implement backtest strategy runner** — Backend logic for `backtest_routes.py` to run historical simulations using OpenClaw scoring
- [ ] **Add WebSocket support** — Push real-time signals, position updates, and streaming engine events to frontend
- [ ] **Build notification service** — In-app notification bell + toast alerts to replace Slack dependency (pipeline summaries, score alerts, trade fills)
- [ ] **Add trade journal tables** — Migrate OpenClaw `sheets_logger.py` data to `database.py` (`trades`, `signals`, `journal`, `audit_trail` tables)
- [ ] **LSTM training pipeline backend** — Connect `ModelTraining.tsx` to actual GPU training jobs, model versioning, and inference endpoint
- [ ] **Add authentication** — User login/session management for production deployment
- [ ] **Performance Analytics data pipeline** — Wire `PerformanceAnalytics.jsx` to backend win rate, Sharpe, drawdown calculations
- [ ] **Resolve 1 open GitHub issue** — See [Issues](https://github.com/Espenator/elite-trading-system/issues)

### 🟢 Migration Plan: Receiving OpenClaw Data

OpenClaw currently logs to Google Sheets (deprecated) and Slack (optional). This system will replace both:

| OpenClaw Source | Elite Trader Destination | Status |
|----------------|--------------------------|--------|
| `sheets_logger.py` Trade Log | `database.py` → `trades` table | 🔧 To Build |
| `sheets_logger.py` Signals | `database.py` → `signals` table | 🔧 To Build |
| `sheets_logger.py` Daily Journal | `database.py` → `journal` table | 🔧 To Build |
| `sheets_logger.py` Audit Trail | `database.py` → `audit_trail` table | 🔧 To Build |
| Slack pipeline summaries | `Dashboard.jsx` | ✅ Page Ready |
| Slack score alerts | `Signals.jsx` | ✅ Page Ready |
| Slack trade notifications | `TradeExecution.jsx` | ✅ Page Ready |
| Slack performance reports | `PerformanceAnalytics.jsx` | ✅ Page Ready |

---

## 🏗 Architecture Overview

```
Elite Trading System (PC2)
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/             # REST API endpoints
│   │   │   ├── backtest_routes.py
│   │   │   ├── orders.py       # Alpaca order management
│   │   │   ├── quotes.py       # Price/chart data
│   │   │   ├── signals.py      # Trading signals CRUD
│   │   │   ├── status.py       # System health
│   │   │   ├── stocks.py       # Finviz screener
│   │   │   ├── system.py       # System config
│   │   │   └── training.py     # ML model training
│   │   ├── core/               # App config, middleware
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── modules/            # Business logic modules
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # External service integrations
│   │   │   ├── alpaca_service.py
│   │   │   ├── database.py     # SQLite database layer
│   │   │   └── finviz_service.py
│   │   ├── strategy/           # Trading strategy logic
│   │   └── main.py             # FastAPI app entry point
│   ├── jobs/                   # Scheduled/background jobs
│   └── tools/                  # CLI utilities
│
├── frontend/                   # React + Vite frontend
│   └── src/
│       ├── components/         # Reusable UI components
│       ├── context/            # React context providers
│       ├── pages/              # 15 page components (see below)
│       ├── routes/             # React Router config
│       ├── services/           # API client services
│       ├── styles/             # CSS themes (dark/light)
│       ├── types/              # TypeScript interfaces
│       └── utils/              # Helper functions
│
└── start_all.bat               # Windows launcher for both servers
```

---

## 🖥 Frontend Pages (15)

| Page | File | Purpose |
|------|------|---------|
| Dashboard | `Dashboard.jsx` | Main trading dashboard with portfolio overview |
| Signals | `Signals.jsx` | OpenClaw signal feed with composite scores |
| Trade Execution | `TradeExecution.jsx` | Order entry, Alpaca live/paper execution |
| Order History | `OrderHistory.jsx` | Historical orders and fills |
| Backtest | `Backtest.jsx` | Strategy backtesting interface |
| Screener Results | `ScreenerResults.tsx` | Finviz stock screener results |
| Performance Analytics | `PerformanceAnalytics.jsx` | Win rate, Sharpe, P&L charts |
| Portfolio Heatmap | `PortfolioHeatmap.tsx` | Visual sector/position heatmap |
| Risk Configuration | `RiskConfiguration.jsx` | Risk parameters and limits |
| Strategy Settings | `StrategySettings.jsx` | Strategy configuration panel |
| Model Training | `ModelTraining.tsx` | LSTM/ML model training interface |
| Account | `Account.jsx` | Alpaca account info and balances |
| Account Settings | `AccountSettings.jsx` | User preferences and API keys |
| Settings | `Settings.jsx` | Application settings |
| Not Found | `NotFound.jsx` | 404 error page |

---

## 🔌 API Endpoints

All backend routes are versioned under `/api/v1/`:

| Route Module | Endpoints | Purpose |
|-------------|-----------|---------|
| `signals.py` | GET/POST `/api/v1/signals` | Trading signal CRUD |
| `orders.py` | GET/POST `/api/v1/orders` | Alpaca order management |
| `quotes.py` | GET `/api/v1/quotes` | Price and chart data |
| `stocks.py` | GET `/api/v1/stocks` | Finviz screener queries |
| `status.py` | GET `/api/v1/status` | System health check |
| `system.py` | GET `/api/v1/system` | System configuration |
| `training.py` | POST `/api/v1/training` | ML model training jobs |
| `backtest_routes.py` | POST `/api/v1/backtest` | Strategy backtesting |

---

## 🔗 Integration with OpenClaw

This repo (PC2) is the **full-stack UI/UX application**. [OpenClaw](https://github.com/Espenator/openclaw) (PC1) is the **intelligence engine** with:

- 42+ Python agents in a Blackboard Swarm architecture
- Real-time streaming via Alpaca WebSocket
- 100-point composite scoring with ML ensemble
- HMM regime detection (GREEN/YELLOW/RED)
- Risk Governor with 8 safety checks

### Bridge Architecture

```
PC1 (OpenClaw)                     PC2 (Elite Trading System)
┌──────────────────┐               ┌──────────────────────┐
│ Blackboard Swarm │               │ FastAPI Backend       │
│ 42+ Python Agents│──── API ────> │ /api/v1/signals      │
│ Streaming Engine │               │ /api/v1/orders       │
│ Risk Governor    │               │ /api/v1/status       │
│                  │               │ SQLite Database       │
│ lstm_bridge      │──── GPU ────> │ LSTM Trainer          │
│ service.py       │    models     │ inference.py          │
└──────────────────┘               │                      │
                                   │ React Frontend        │
                                   │ 15 Pages + Dashboard  │
                                   └──────────────────────┘
```

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Alpaca API keys

# Start backend
python start_server.py

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# Or start both at once (Windows)
start_all.bat
```

---

## ⚙️ Configuration

Backend configuration via `.env` file. Required: `ALPACA_API_KEY` + `ALPACA_SECRET_KEY`. Finviz Elite API key optional but recommended for screener functionality.

See `backend/.env.example` for all available environment variables.

---

## 📄 License

Private repository — Embodier.ai
