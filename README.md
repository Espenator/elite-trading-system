# Elite Trading System

**Embodier.ai Full-Stack AI Trading Intelligence Platform**

> **Last Updated: March 4, 2026**
> **CI Status: GREEN — 70 tests passing**
> **Backend: Ready to start (uvicorn never run yet). Frontend builds clean.**
> **Council: 13-agent DAG in 7 stages — expanded from 8 on Mar 4, 2026**

React + FastAPI full-stack trading application with 15-route V3 widescreen dashboard, DuckDB database, 13-agent council DAG, Alpaca + Finviz integrations, XGBoost ML pipeline, event-driven order execution, and gRPC brain service for local Ollama LLM inference.

---

## Current State (March 4, 2026)

| Area | Count | Status |
|---|---|---|
| Frontend pages | 15 (14 sidebar + 1 hidden) | All wired to useApi hooks, no mock data |
| Backend API routes | 29 files in `api/v1/` | All mounted in main.py |
| Backend services | 21 files in `services/` | Business logic layer |
| Council agents | 13 agents in 7-stage DAG | BUILT — runner.py orchestrates |
| Tests | 70 passing | Backend pytest + frontend build |
| Brain service | gRPC + Ollama | BUILT — not yet wired to council |
| Event pipeline | MessageBus + SignalEngine + OrderExecutor | BUILT — auto-starts in main.py |
| Database | DuckDB (WAL mode, pooling) | BUILT |
| Authentication | None | Not started |
| WebSocket | Code exists | Not connected to frontend |

### What Was Recently Done (Mar 1-4, 2026)

- Expanded council from 8 to 13 agents — added RSI, BBV, EMA Trend, Intermarket, Relative Strength, Cycle Timing
- Updated council runner.py to 7-stage parallel DAG
- Added brain_service gRPC server + Ollama client
- Added 6 new service files: alpaca_stream_service, brain_client, data_ingestion, execution_simulator, feature_service, order_executor
- Added 6 new API routes: alpaca, alignment, features, council, youtube_knowledge
- Production cleanup: logging, Docker hardening, security headers
- CI expanded to 70 tests

### What Is NOT Done (TODO)

- [ ] **P0**: Wire council to event pipeline (subscribe to `signal.generated`, auto-invoke `run_council()`)
- [ ] **P1**: Build BlackboardState (shared memory across DAG stages)
- [ ] **P2**: Add missing feature keys to feature_aggregator.py (EMA-5/10/20, intermarket, relative strength, cycle timing, VIX)
- [ ] **P3**: Build CircuitBreaker reflexes (brainstem <50ms)
- [ ] **P4**: Clean up OpenClaw dead code in `modules/openclaw/`
- [ ] **P5**: Build TaskSpawner (dynamic agent registry)
- [ ] **P6**: Unify Agent Command Center (show real 13-agent council, not 5 template agents)
- [ ] **P7**: Wire brain_service gRPC to hypothesis_agent and critic_agent
- [ ] **P8**: Build agent self-awareness (Bayesian weights, streak detection)
- [ ] **BLOCKER-1**: Start backend for first time (`uvicorn app.main:app`)
- [ ] **BLOCKER-2**: Establish WebSocket real-time data connectivity
- [ ] **BLOCKER-3**: Add JWT authentication for live trading endpoints
- [ ] Fix stale docstrings in council/__init__.py, schemas.py, api/v1/council.py status endpoint

---

## Architecture

### Five Systems (Current Fragmentation)

The codebase has five disconnected agent/decision systems. Unifying them into the CNS architecture is the primary goal.

| System | Location | Status |
|---|---|---|
| 1. Agent Command Center (5 polling agents) | `api/v1/agents.py` | BUILT — template agents, not real |
| 2. Council (13-agent DAG) | `council/` | BUILT — on-demand via POST only |
| 3. OpenClaw (copied Flask system) | `modules/openclaw/` | DEAD CODE — needs cleanup |
| 4. Event-Driven Pipeline | `core/message_bus.py`, `services/signal_engine.py`, `services/order_executor.py` | BUILT — runs independently of council |
| 5. CNS Architecture | Not yet built | DESIGNED — BlackboardState, TaskSpawner, CircuitBreaker |

### Council DAG (13 Agents, 7 Stages)

```
Stage 1 (Parallel): market_perception, flow_perception, regime, intermarket
Stage 2 (Parallel): rsi, bbv, ema_trend, relative_strength, cycle_timing
Stage 3: hypothesis (to be wired to brain_service LLM)
Stage 4: strategy (entry/exit/sizing)
Stage 5 (Parallel): risk, execution
Stage 6: critic (postmortem learning)
Stage 7: arbiter (deterministic BUY/SELL/HOLD)
```

### Event-Driven Pipeline (BUILT)

```
AlpacaStreamService -> market_data.bar -> EventDrivenSignalEngine
  -> signal.generated (score >= 65) -> OrderExecutor -> order.submitted
  -> WebSocket bridges -> Frontend
```

### CNS Architecture (Target — NOT BUILT)

| Layer | Role | Status |
|---|---|---|
| Brainstem (<50ms) | CircuitBreaker reflexes | TO BUILD |
| Spinal Cord (~1500ms) | 13-agent council DAG | BUILT |
| Cortex (300-800ms) | hypothesis + critic via brain_service | NOT WIRED |
| Thalamus | BlackboardState shared memory | TO BUILD |
| Autonomic | Bayesian weights, overnight learning | TO BUILD |
| PNS Sensory | Alpaca WS, Unusual Whales, FinViz, FRED, EDGAR | BUILT |
| PNS Motor | OrderExecutor -> Alpaca Orders | BUILT |
| Event Bus | MessageBus pub/sub | BUILT |

---

## Frontend Pages (15)

All pages in `frontend-v2/src/pages/`. All use `useApi()` hook. No mock data.

| # | Route | File | Status |
|---|---|---|---|
| 1 | `/dashboard` | Dashboard.jsx | Wired to useApi |
| 2 | `/agents` | AgentCommandCenter.jsx | DEPLOYED — thin shell + 8 tabs |
| 3 | `/signals` | Signals.jsx | Wired to useApi |
| 4 | `/sentiment` | SentimentIntelligence.jsx | Wired to useApi |
| 5 | `/data-sources` | DataSourcesMonitor.jsx | **DONE 100%** |
| 6 | `/ml-brain` | MLBrainFlywheel.jsx | Wired to useApi |
| 7 | `/patterns` | Patterns.jsx | **DONE** — real API |
| 8 | `/backtest` | Backtesting.jsx | Wired to useApi |
| 9 | `/performance` | PerformanceAnalytics.jsx | ~20% — needs mockup alignment |
| 10 | `/market-regime` | MarketRegime.jsx | **DONE 100%** |
| 11 | `/trades` | Trades.jsx | **DONE 100%** |
| 12 | `/risk` | RiskIntelligence.jsx | Wired to useApi |
| 13 | `/trade-execution` | TradeExecution.jsx | **DONE 100%** |
| 14 | `/settings` | Settings.jsx | Wired to useApi |
| 15 | `/signal-v3` | SignalIntelligenceV3.jsx | Hidden route |

---

## Backend API Routes (29 files in `backend/app/api/v1/`)

| File | Purpose |
|---|---|
| `agents.py` | Agent Command Center — 5 template agents (NOT council) |
| `alerts.py` | Drawdown alerts, system alerts |
| `alignment.py` | Alignment/consensus endpoints |
| `alpaca.py` | Alpaca API proxy for frontend |
| `backtest_routes.py` | Strategy backtesting |
| `council.py` | Council evaluate (POST /evaluate) |
| `data_sources.py` | Data source health |
| `features.py` | Feature aggregator endpoints |
| `flywheel.py` | ML flywheel metrics |
| `logs.py` | System logs |
| `market.py` | Market data, regime, indices |
| `ml_brain.py` | ML model management |
| `openclaw.py` | OpenClaw bridge |
| `orders.py` | Alpaca order CRUD |
| `patterns.py` | Pattern/screener (DB-backed) |
| `performance.py` | Performance analytics |
| `portfolio.py` | Portfolio positions, P&L |
| `quotes.py` | Price/chart data |
| `risk.py` | Risk metrics, Monte Carlo |
| `risk_shield_api.py` | Emergency controls |
| `sentiment.py` | Sentiment aggregation |
| `settings_routes.py` | Settings CRUD |
| `signals.py` | Trading signals |
| `status.py` | System health |
| `stocks.py` | Finviz screener |
| `strategy.py` | Regime-based strategies |
| `system.py` | System config, GPU |
| `training.py` | ML training jobs |
| `youtube_knowledge.py` | YouTube research |

## Backend Services (21 files in `backend/app/services/`)

| File | Purpose |
|---|---|
| `alpaca_service.py` | Alpaca broker REST |
| `alpaca_stream_service.py` | Alpaca WebSocket -> MessageBus |
| `backtest_engine.py` | Backtester + Monte Carlo |
| `brain_client.py` | gRPC client for brain_service |
| `data_ingestion.py` | Data ingestion pipeline |
| `database.py` | DuckDB layer (WAL, pooling) |
| `execution_simulator.py` | Paper trading simulator |
| `feature_service.py` | DuckDB feature queries |
| `finviz_service.py` | Finviz screening |
| `fred_service.py` | FRED economic data |
| `kelly_position_sizer.py` | Kelly criterion sizing |
| `market_data_agent.py` | Market data aggregation |
| `ml_training.py` | LSTM/XGBoost training |
| `openclaw_bridge_service.py` | OpenClaw bridge |
| `openclaw_db.py` | OpenClaw SQLite |
| `order_executor.py` | Event-driven order execution |
| `sec_edgar_service.py` | SEC EDGAR filings |
| `settings_service.py` | Settings CRUD service |
| `signal_engine.py` | Signal scoring + EventDrivenSignalEngine |
| `training_store.py` | ML artifact storage |
| `unusual_whales_service.py` | Options flow |
| `walk_forward_validator.py` | Walk-forward validation |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB, pydantic-settings |
| AI/ML | XGBoost, scikit-learn, HMM (hmmlearn), Kelly criterion |
| Council | 13-agent DAG with deterministic arbiter (7 stages) |
| Brain Service | gRPC + Ollama (local LLM on RTX GPU) |
| Broker | Alpaca Markets (paper + live via alpaca-py) |
| Data | Alpaca Markets, Unusual Whales, Finviz, FRED, SEC EDGAR |
| Event Pipeline | MessageBus, Alpaca WebSocket, SignalEngine, OrderExecutor |
| CI/CD | GitHub Actions — pytest + npm build (70 tests) |
| Infra | Docker, docker-compose.yml |

## Data Sources (NO yfinance)

- **Alpaca Markets** (alpaca-py) — Market data + order execution
- **Unusual Whales** — Options flow
- **Finviz** (finviz) — Screener, fundamentals, VIX proxy
- **FRED** — Economic macro data
- **SEC EDGAR** — Company filings

## Hardware (Dual-PC Setup)

- PC 1: Development + Frontend + Backend API
- PC 2: RTX GPU cluster for ML training + Ollama inference (brain_service)
- Connected via gRPC (brain_service port 50051)

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

## Open Issues (10)

| # | Title | Priority |
|---|---|---|
| #24 | 100% Mockup Fidelity per-page checklist | UI |
| #21 | Align 7 pages to 90%+ mockup fidelity | UI |
| #20 | Complete Recharts to Lightweight Charts migration | UI |
| #19 | BLOCKER-3: Add JWT authentication | BLOCKER |
| #18 | BLOCKER-2: WebSocket connectivity | BLOCKER |
| #17 | BLOCKER-1: Start backend first time | BLOCKER |
| #15 | Codebase cleanup & architecture consolidation | Architecture |
| #8 | Full codebase cleanup — mock data, hardcoded keys | Audit |
| #3 | Replace training.py mock data with real DB | ML |
| #2 | Build ClawBot Panel — Swarm Command Center | Frontend |

## License

Private repository — Embodier.ai
