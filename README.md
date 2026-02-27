# Elite Trading System

**Embodier.ai Full-Stack AI Trading Intelligence Platform**

> **Last Updated: February 27, 2026 (1:00 PM EST)**
> **Status: UI code complete, backend code complete, NOT yet wired into a running application.**
> **Next Step: Generate remaining UI mockups (model council 3 versions each), then wire frontend to backend.**

React + FastAPI full-stack trading application with 15-route V3 widescreen dashboard (14 sidebar + 1 hidden), SQLite database, Alpaca + Finviz integrations, 42+ OpenClaw Python agents in a Blackboard Swarm, LSTM/XGBoost ML pipeline, and real-time order execution.

> **Part of the Embodier.ai Elite Trading ecosystem.** All 42+ [OpenClaw](https://github.com/Espenator/openclaw) Python agents and the Blackboard Swarm architecture are integrated in `core/` and `backend/`. The openclaw repo is archived.

---

## AI CONTEXT: READ THIS FIRST

If you are an AI assistant reading this repo, here is exactly where we are:

1. **All 15 frontend pages exist** with V3 UI code (14 sidebar + 1 hidden route)
2. **All 27+ backend API routes exist** in `backend/app/api/v1/`
3. **All 20+ backend services exist** in `backend/app/services/`
4. **The app does NOT run end-to-end yet** -- nothing has been wired and tested together
5. **6 approved UI mockup images** exist in `docs/mockups-v3/images/` -- 11 pages still need mockups
6. **Design system is finalized** -- see `docs/UI-DESIGN-SYSTEM.md` for exact colors, fonts, spacing
7. **Agent Command Center** is the largest page (1,995 lines, 8 internal tabs, 5 decomposed components)
8. **Approved mockup tabs differ from code tabs** -- mockup shows: Swarm Overview, Agent Registry, Spawn & Scale, Live Wiring Map, Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry. Code has: Overview, Agents, Swarm Control, Candidates, LLM Flow, Brain Map, Leaderboard, Blackboard. Code should be aligned to mockup.

### Key Documentation Files

| File | Purpose |
|------|--------|
| `frontend-v2/src/V3-ARCHITECTURE.md` | **AUTHORITATIVE** frontend architecture (15 routes, charting audit, component map) |
| `docs/UI-DESIGN-SYSTEM.md` | **AUTHORITATIVE** design system (colors, fonts, spacing from approved mockups) |
| `docs/STATUS-AND-TODO-2026-02-27.md` | Current project status and 8-day plan to working app |
| `docs/UI-PRODUCTION-PLAN-14-PAGES.md` | Per-page UI specification from intelligence council |
| `docs/mockups-v3/images/` | 6 approved mockup images (source of truth for visual design) |
| `docs/mockups-v3/FULL-MOCKUP-SPEC.md` | Full mockup specification for all 14 pages |
| `docs/DEEP_RESEARCH_AUDIT_2026-02-27.md` | Deep code audit findings |

---

## Project Status (Feb 27, 2026 - 1:00 PM EST)

| Component | Status | Notes |
|-----------|--------|-------|
| React Frontend-v2 (15 routes) | V3 UI CODED | 7 pages complete (no charts/LW only), 4 hybrid Recharts+LW, 3 Recharts-only, 1 complex (Agent CC) |
| FastAPI Backend (27+ routes) | CODED | All route files exist, NOT tested end-to-end |
| SQLite Database | CODED | Schema exists, initialization untested |
| Alpaca Integration | CODED | `alpaca_service.py` -- live/paper trading + market data |
| Finviz Integration | CODED | `finviz_service.py` -- stock screener + chart data |
| OpenClaw Bridge | CODED | `openclaw_db.py` + `openclaw.py` -- SQLite persistence |
| Backtest Engine | CODED | `backtest_engine.py` -- Sharpe/PnL/MaxDD |
| LSTM Training | CODED | `ml_training.py` -- PyTorch GPU/CPU |
| XGBoost GPU | CODED | Trainer AMP, XGBoost GPU, /gpu endpoint |
| Design System | COMPLETE | Colors, fonts, spacing finalized in `docs/UI-DESIGN-SYSTEM.md` |
| Approved Mockups | 6 of 17 | Agent CC (3 views), Signal Intel, Sentiment Intel, Agent Registry |
| Frontend-Backend Wiring | NOT STARTED | Critical gap -- nothing connected end-to-end |
| WebSocket Live Updates | NOT STARTED | Backend manager exists, frontend client exists, not connected |
| Authentication | NOT STARTED | No auth system |

### What Works Right Now
- [x] Frontend builds and renders all 15 routes with placeholder/mock data
- [x] Backend code compiles (CI passes after recent fixes)
- [x] Design system tokens match approved mockups
- [x] 6 approved UI mockup images committed to git

### What Does NOT Work
- [ ] Backend has never been started and tested end-to-end
- [ ] No frontend page fetches real data from backend
- [ ] Database initialization untested
- [ ] WebSocket real-time data flow not connected
- [ ] 11 pages still need approved UI mockup images
- [ ] Agent CC tab names don't match approved mockup

---

## Approved UI Mockups (Source of Truth)

All UI must match these approved images exactly. Located in `docs/mockups-v3/images/`:

| # | File | Page | Status |
|---|------|------|--------|
| 1 | `01-agent-command-center-final.png` | Agent CC - Swarm Overview | APPROVED |
| 2 | `03-signal-intelligence.png` | Signal Intelligence V3 | APPROVED |
| 3 | `04-sentiment-intelligence.png` | Sentiment Intelligence | APPROVED |
| 4 | `05-agent-command-center.png` | Agent CC - Live Wiring | APPROVED |
| 5 | `05b-agent-command-center-spawn.png` | Agent CC - Spawn & Scale | APPROVED |
| 6 | `agent-rgistery.png` | Agent CC - Agent Registry | APPROVED |
| 7 | Dashboard | Intelligence Dashboard | NEEDS MOCKUP |
| 8 | Signals | Signal Intelligence (sidebar) | NEEDS MOCKUP |
| 9 | DataSourcesMonitor | Data Sources Monitor | NEEDS MOCKUP |
| 10 | MLBrainFlywheel | ML Brain & Flywheel | NEEDS MOCKUP |
| 11 | Patterns | Screener & Patterns | NEEDS MOCKUP |
| 12 | Backtesting | Backtesting Lab | NEEDS MOCKUP |
| 13 | PerformanceAnalytics | Performance Analytics | NEEDS MOCKUP |
| 14 | MarketRegime | Market Regime | NEEDS MOCKUP |
| 15 | Trades | Active Trades | NEEDS MOCKUP |
| 16 | RiskIntelligence | Risk Intelligence | NEEDS MOCKUP |
| 17 | TradeExecution + Settings | Trade Execution + Settings | NEEDS MOCKUP |

---

## V3 Frontend Architecture (15 routes)

See `frontend-v2/src/V3-ARCHITECTURE.md` for complete details.

### COMMAND (2 pages)
| Page | File | Route | Status |
|------|------|-------|--------|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` | V3 CODED (Recharts + LW) |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | V3 CODED (8 tabs, 1995 lines) |

### INTELLIGENCE (4 routes, 3 in sidebar)
| Page | File | Route | Status |
|------|------|-------|--------|
| Signal Intelligence | `Signals.jsx` | `/signals` | V3 COMPLETE |
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | V3 CODED (Recharts) |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | V3 CODED (Recharts) |
| Signal Intelligence V3 | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | V3 CODED (hidden route) |

### ML & ANALYSIS (5 pages)
| Page | File | Route | Status |
|------|------|-------|--------|
| ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | V3 CODED (Recharts) |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | V3 COMPLETE |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` | V3 CODED (Recharts + LW) |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | V3 CODED (Recharts + LW) |
| Market Regime | `MarketRegime.jsx` | `/market-regime` | V3 COMPLETE (LW only) |

### EXECUTION (3 pages)
| Page | File | Route | Status |
|------|------|-------|--------|
| Active Trades | `Trades.jsx` | `/trades` | V3 COMPLETE |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | V3 COMPLETE |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` | V3 COMPLETE |

### SYSTEM (1 page)
| Page | File | Route | Status |
|------|------|-------|--------|
| Settings | `Settings.jsx` | `/settings` | V3 COMPLETE |

---

## Agent Command Center - 8 Internal Tabs

The most complex page. Approved mockup tabs (from `01-agent-command-center-final.png`):

| Tab | Description | Code Status |
|-----|-------------|-------------|
| Swarm Overview | Health matrix, activity feed, topology, resource monitor, alerts | Built |
| Agent Registry | Master agent table, config panel, SHAP importance | Built |
| Spawn & Scale | Orchestrator, team spawn/kill, bias controls | Built |
| Live Wiring Map | Network topology, connection health, API route map | Built |
| Blackboard & Comms | Real-time pub/sub feed, HITL ring buffer | Placeholder |
| Conference & Consensus | Conference pipeline, consensus voting | Built |
| ML Ops | Brain map, leaderboard, model metrics | Placeholder |
| Logs & Telemetry | LLM flow alerts, system logs | Placeholder |

---

## Backend Architecture

See `backend/README.md` for full backend documentation.

### API Routes (`backend/app/api/v1/`)
| Route | Endpoints | Purpose |
|-------|-----------|--------|
| `agents.py` | GET/POST `/api/v1/agents` | Agent management + lifecycle |
| `signals.py` | GET/POST `/api/v1/signals` | Trading signal CRUD |
| `orders.py` | GET/POST `/api/v1/orders` | Alpaca order management |
| `market.py` | GET `/api/v1/market` | Market data + regime |
| `portfolio.py` | GET `/api/v1/portfolio` | Portfolio positions + P&L |
| `risk.py` | GET `/api/v1/risk` | Risk metrics + exposure |
| `backtest_routes.py` | POST `/api/v1/backtest` | Strategy backtesting |
| `ml_brain.py` | GET/POST `/api/v1/ml-brain` | ML model management |
| `performance.py` | GET `/api/v1/performance` | Performance analytics |
| `openclaw.py` | POST/GET `/api/v1/openclaw/*` | OpenClaw bridge |
| `training.py` | POST `/api/v1/training` | ML model training jobs |
| `system.py` | GET `/api/v1/system`, `/gpu` | System config + GPU health |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind CSS, LW Charts, Recharts (migrating) |
| Backend | Python 3.11+, FastAPI, SQLite (DuckDB planned) |
| Broker | Alpaca Markets (paper + live) |
| Data | Finviz Elite, yFinance, Unusual Whales, FRED, SEC EDGAR |
| ML | XGBoost (GPU), LSTM (PyTorch AMP), scikit-learn |
| WebSocket | FastAPI WebSocket + custom JS client |
| Agents | 42+ OpenClaw Python agents, Blackboard Swarm |
| Deployment | Two-PC (ESPENMAIN dev + ProfitTrader prod) |

---

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

---

## OpenClaw Integration

All 42+ OpenClaw Python agents now live in `core/` and `backend/`. Key systems:
- Blackboard Swarm architecture with pub/sub messaging
- Real-time streaming via Alpaca WebSocket
- 100-point composite scoring with ML ensemble
- HMM regime detection (GREEN/YELLOW/RED)
- Risk Governor with 8 safety checks
- Conference consensus engine

---

## License

Private repository -- Embodier.ai