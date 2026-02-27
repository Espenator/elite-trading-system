# Elite Trading System

**Embodier.ai Full-Stack AI Trading Intelligence Platform**

> **Last Updated: February 27, 2026 (3:00 PM EST)**
> **Status: UI code complete, backend code complete, NOT yet wired into a running application.**
> **Next Step: Complete Perplexity council review, align Agent Command Center tabs to mockup, then wire frontend to backend.**

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
9. **7 of 15 pages still use Recharts** -- these must be migrated to Lightweight Charts where applicable (see charting audit below)
10. **Backend has never been started** -- FastAPI server exists but has not been run or tested
11. **No authentication system** -- no login, no user sessions
12. **No WebSocket real-time data flowing** -- WebSocket code exists but is not connected
13. **3 Agent Command Center tabs use placeholder/mock data** -- not wired to backend

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

## Project Status (Feb 27, 2026 - 3:00 PM EST)

| Component | Status | Notes |
|-----------|--------|-------|
| React Frontend-v2 (15 routes) | V3 UI CODED | 7 pages complete (no charts/LW only), 4 hybrid Recharts+LW, 3 Recharts-only, 1 complex (Agent CC) |
| FastAPI Backend (27+ routes) | CODE EXISTS | Never started/tested. Routes in `backend/app/api/v1/` |
| SQLite Database | SCHEMA EXISTS | Tables defined, never populated with real data |
| OpenClaw Agents (42+) | CODE EXISTS | Python agents in `core/` -- never run in production |
| Alpaca Integration | CODE EXISTS | WebSocket + REST in services -- never tested live |
| Authentication | NOT STARTED | No login system exists |
| End-to-End Wiring | NOT STARTED | Frontend and backend have never communicated |
| UI Mockups | 6 of 17 DONE | 6 approved images, 11 pages still need mockups |

---

## Frontend Architecture (V3 Widescreen)

### All 15 Routes
| # | Route | Page | Charting Status | Lines |
|---|-------|------|----------------|-------|
| 1 | `/` | Dashboard | Recharts + LW Charts (hybrid) | ~800 |
| 2 | `/portfolio` | Portfolio Manager | Recharts only (PieChart, BarChart) | ~600 |
| 3 | `/scanner` | Market Scanner | No charts (data table) | ~500 |
| 4 | `/orders` | Order Management | No charts (data table) | ~450 |
| 5 | `/risk` | Risk Management | Recharts only (RadarChart, BarChart) | ~550 |
| 6 | `/agents` | Agent Command Center | Recharts + LW Charts (hybrid) | ~1,995 |
| 7 | `/journal` | Trading Journal | Recharts only (LineChart, BarChart) | ~500 |
| 8 | `/backtesting` | Backtesting Engine | Recharts + LW Charts (hybrid) | ~700 |
| 9 | `/settings` | Settings | No charts | ~400 |
| 10 | `/alerts` | Alerts & Notifications | No charts | ~350 |
| 11 | `/research` | Research & Analysis | LW Charts only | ~600 |
| 12 | `/ml-models` | ML Model Hub | Recharts + LW Charts (hybrid) | ~650 |
| 13 | `/news` | News & Sentiment | No charts | ~450 |
| 14 | `/social` | Social & Community | No charts | ~400 |
| 15 | `/debug` | Debug Panel (hidden) | No charts | ~300 |

### Agent Command Center Sub-Pages (8 Tabs)
The Agent Command Center (`/agents`) is the most complex page with 8 internal tabs and 5 decomposed components:

**Current Code Tabs:**
1. Overview -- Agent status summary dashboard
2. Agents -- Individual agent cards and details
3. Swarm Control -- Blackboard Swarm management
4. Candidates -- Stock candidate pipeline
5. LLM Flow -- Language model routing visualization
6. Brain Map -- Neural network topology view
7. Leaderboard -- Agent performance rankings
8. Blackboard -- Shared blackboard state viewer

**Decomposed Components** (in `components/agents/`):
- `AgentCard.jsx` -- Individual agent display
- `SwarmVisualization.jsx` -- Swarm network graph
- `AgentMetrics.jsx` -- Performance metrics panels
- `BlackboardView.jsx` -- Blackboard state display
- `ConferencePanel.jsx` -- Conference consensus view

**NOTE:** Code tabs should be aligned to approved mockup tabs (Swarm Overview, Agent Registry, Spawn & Scale, Live Wiring Map, Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry).

### Charting Migration Status
- **Lightweight Charts (target):** Used in Dashboard, Research, parts of Backtesting and ML Models
- **Recharts (to migrate):** Still used in Portfolio, Risk, Journal, and parts of Dashboard, Agents, Backtesting, ML Models
- **7 `MISSING V3` wrapper comments** exist in `components/charts/` indicating planned but unbuilt LW Charts wrappers

---

## Backend Architecture

### FastAPI Server (`backend/app/main.py`)
- Mounts all API v1 routers
- CORS middleware configured
- SQLite database initialization
- WebSocket endpoint for real-time data

### API Routes (`backend/app/api/v1/`)
| Router File | Endpoints | Purpose |
|------------|-----------|----------|
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
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, Recharts (migrating away) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| AI/ML | LSTM, XGBoost, HMM, OpenClaw agents |
| Broker | Alpaca Markets (paper + live trading) |
| Data | Finviz, Alpaca WebSocket, Yahoo Finance |
| Architecture | Blackboard Swarm, pub/sub messaging |

---

## Repository Structure

```
elite-trading-system/
├── frontend-v2/          # React frontend (V3 widescreen UI)
│   ├── src/
│   │   ├── pages/        # 15 page components
│   │   ├── components/   # Shared components (charts/, agents/, layout/)
│   │   ├── services/     # API service layer
│   │   ├── hooks/        # Custom React hooks
│   │   ├── App.jsx       # Router with 15 routes
│   │   └── V3-ARCHITECTURE.md  # Frontend architecture doc
│   └── package.json
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/v1/       # 27+ API route files
│   │   ├── services/     # 20+ service implementations
│   │   ├── models/       # SQLAlchemy models
│   │   └── main.py       # FastAPI app entry point
│   ├── tests/            # Backend test suite
│   └── requirements.txt
├── core/                 # OpenClaw Python agents (42+)
├── docs/                 # Project documentation
│   ├── mockups-v3/       # UI mockups and specs
│   ├── UI-DESIGN-SYSTEM.md
│   ├── STATUS-AND-TODO-2026-02-27.md
│   └── DEEP_RESEARCH_AUDIT_2026-02-27.md
├── scripts/              # Utility scripts
├── docker-compose.yml    # Docker setup
└── .env.example          # Environment variables template
```

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
