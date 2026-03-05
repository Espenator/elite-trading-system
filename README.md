# Elite Trading System
### Embodier.ai — Full-Stack AI Trading Intelligence Platform
**Version 3.2.0** | Last Updated: March 5, 2026

CI Status: GREEN — 151 tests passing
Backend: Ready to start (uvicorn never run yet). Frontend builds clean.
Council: 13-agent DAG in 7 stages — council-controlled trading via CouncilGate (v3.2.0)

---

React + FastAPI full-stack trading application with 15-route V3 widescreen dashboard, DuckDB database, 13-agent council DAG with Bayesian weight learning, Alpaca + Finviz integrations, XGBoost ML pipeline, event-driven council-controlled order execution, and gRPC brain service for local Ollama LLM inference.

## Current State (March 5, 2026)

| Area | Count | Status |
|------|-------|--------|
| Frontend pages | 15 (14 sidebar + 1 hidden) | All wired to useApi hooks, no mock data |
| Backend API routes | 29 files in api/v1/ | All mounted in main.py |
| Backend services | 24 files in services/ | Business logic layer |
| Council agents | 13 agents in 7-stage DAG | BUILT + CONNECTED to event pipeline via CouncilGate |
| Council intelligence | WeightLearner + CouncilGate | Bayesian self-learning agent weights |
| Tests | 151 passing | Backend pytest + frontend build |
| Brain service | gRPC + Ollama | BUILT — not yet wired to council |
| Event pipeline | MessageBus + CouncilGate + SignalEngine + OrderExecutor | BUILT — council-controlled trading |
| Database | DuckDB (WAL mode, pooling) | BUILT |
| Authentication | None | Not started |
| WebSocket | Code exists | Not connected to frontend |

## Trade Pipeline (v3.2.0 — Council-Controlled)

```
AlpacaStreamService
  -> market_data.bar
  -> EventDrivenSignalEngine
  -> signal.generated (score >= 65)
  -> CouncilGate (invokes 13-agent council)
  -> council.verdict (BUY/SELL/HOLD with Bayesian-weighted confidence)
  -> OrderExecutor (real DuckDB stats, real ATR, mock-source guard)
  -> order.submitted
  -> WebSocket bridges
  -> Frontend
```

Every signal passes through the full 13-agent council before any trade is executed. No hardcoded data — Kelly sizing uses real DuckDB trade statistics, ATR comes from real feature data, and the mock-source guard prevents trading on fake data.

## What Was Recently Done

### v3.2.0 (March 5, 2026) — Council-Controlled Intelligence
- **CouncilGate**: New bridge class that intercepts all signals (score >= 65) and auto-invokes the 13-agent council before any trade
- **WeightLearner**: Bayesian self-learning agent weights — agents that vote correctly get higher weight over time
- **TradeStatsService**: Real win_rate/avg_win/avg_loss from DuckDB replaces all hardcoded Kelly parameters
- **OrderExecutor**: Now listens to council.verdict (not raw signals), uses real stats + real ATR, mock-source guard
- **Arbiter**: Uses Bayesian learned weights from WeightLearner instead of static weights
- **Feature Aggregator**: Expanded with intermarket, cycle, extended indicators (EMA-5/10/20, VIX, SPY correlation, sector breadth)
- **Pipeline**: main.py wires CouncilGate into startup — council controls all trading decisions

### v3.1.0 (March 4, 2026) — 13-Agent Expansion
- Expanded council from 8 to 13 agents — added RSI, BBV, EMA Trend, Intermarket, Relative Strength, Cycle Timing
- Updated council runner.py to 7-stage parallel DAG
- Added brain_service gRPC server + Ollama client
- Added 6 new service files: alpaca_stream_service, brain_client, data_ingestion, execution_simulator, feature_service, order_executor
- Added 6 new API routes: alpaca, alignment, features, council, youtube_knowledge
- Production cleanup: logging, Docker hardening, security headers
- Complete README rewrite with accurate file counts

## What Is NOT Done (TODO)

- [ ] P1: Build BlackboardState (shared memory across DAG stages)
- [ ] P3: Build CircuitBreaker reflexes (brainstem <50ms)
- [ ] P4: Clean up OpenClaw dead code
- [ ] P5: Build TaskSpawner (dynamic agent registry)
- [ ] P6: Unify Agent Command Center UI (show real 13-agent council, not 5 template agents)
- [ ] P7: Wire brain_service gRPC (hypothesis_agent is still a stub)
- [ ] Signal scoring weights calibration from historical data
- [ ] Multi-timeframe analysis in real-time path
- [ ] BLOCKER-1: Start backend for first time (uvicorn app.main:app)
- [ ] BLOCKER-2: Establish WebSocket real-time data connectivity
- [ ] BLOCKER-3: Add JWT authentication for live trading endpoints

## Architecture

### Five Systems (Fragmentation Status)

| System | Location | Status |
|--------|----------|--------|
| 1. Agent Command Center (5 polling agents) | api/v1/agents.py | BUILT — template agents, not real |
| 2. Council (13-agent DAG) | council/ | **CONNECTED** to event pipeline via CouncilGate (v3.2.0) |
| 3. OpenClaw (copied Flask system) | modules/openclaw/ | DEAD CODE — needs cleanup |
| 4. Event-Driven Pipeline | core/message_bus.py, services/ | **CONNECTED** to council via CouncilGate (v3.2.0) |
| 5. CNS Architecture | Partially built | CouncilGate (P0) + WeightLearner (P8) built, rest TODO |

### Council DAG (13 Agents, 7 Stages)

```
Stage 1 (Parallel): market_perception, flow_perception, regime, intermarket
Stage 2 (Parallel): rsi, bbv, ema_trend, relative_strength, cycle_timing
Stage 3: hypothesis (to be wired to brain_service LLM)
Stage 4: strategy (entry/exit/sizing)
Stage 5 (Parallel): risk, execution
Stage 6: critic (postmortem learning)
Stage 7: arbiter (deterministic BUY/SELL/HOLD with Bayesian weights)
```

### Event-Driven Pipeline (v3.2.0)

```
AlpacaStreamService -> market_data.bar -> EventDrivenSignalEngine -> signal.generated (score >= 65)
  -> CouncilGate -> 13-Agent Council -> council.verdict -> OrderExecutor -> Alpaca
```

### CNS Architecture (Target)

| Layer | Role | Status |
|-------|------|--------|
| Brainstem (<50ms) | CircuitBreaker reflexes | TO BUILD |
| Spinal Cord (~1500ms) | 13-agent council DAG | **BUILT** |
| Cortex (300-800ms) | hypothesis + critic via brain_service | NOT WIRED |
| Thalamus | BlackboardState shared memory | TO BUILD |
| Autonomic | Bayesian WeightLearner | **BUILT** (v3.2.0) |
| PNS Sensory | Alpaca WS, Unusual Whales, FinViz, FRED, EDGAR | **BUILT** |
| PNS Motor | OrderExecutor -> Alpaca Orders (via council.verdict) | **BUILT** |
| Event Bus | MessageBus pub/sub | **BUILT** |
| Council Gate | SignalEngine -> Council -> OrderExecutor | **BUILT** (v3.2.0) |

## Frontend Pages (15)

All pages in frontend-v2/src/pages/. All use useApi() hook. No mock data.

| # | Route | File | Status |
|---|-------|------|--------|
| 1 | /dashboard | Dashboard.jsx | Wired to useApi |
| 2 | /agents | AgentCommandCenter.jsx | DEPLOYED — thin shell + 8 tabs |
| 3 | /signals | Signals.jsx | Wired to useApi |
| 4 | /sentiment | SentimentIntelligence.jsx | Wired to useApi |
| 5 | /data-sources | DataSourcesMonitor.jsx | DONE 100% |
| 6 | /ml-brain | MLBrainFlywheel.jsx | Wired to useApi |
| 7 | /patterns | Patterns.jsx | DONE — real API |
| 8 | /backtest | Backtesting.jsx | Wired to useApi |
| 9 | /performance | PerformanceAnalytics.jsx | ~20% — needs mockup alignment |
| 10 | /market-regime | MarketRegime.jsx | DONE 100% |
| 11 | /trades | Trades.jsx | DONE 100% |
| 12 | /risk | RiskIntelligence.jsx | Wired to useApi |
| 13 | /trade-execution | TradeExecution.jsx | DONE 100% |
| 14 | /settings | Settings.jsx | Wired to useApi |
| 15 | /signal-v3 | SignalIntelligenceV3.jsx | Hidden route |

## Backend API Routes (29 files in backend/app/api/v1/)

| File | Purpose |
|------|---------|
| agents.py | Agent Command Center — 5 template agents (NOT council) |
| alerts.py | Drawdown alerts, system alerts |
| alignment.py | Alignment/consensus endpoints |
| alpaca.py | Alpaca API proxy for frontend |
| backtest_routes.py | Strategy backtesting |
| council.py | Council evaluate, status, weights endpoints |
| data_sources.py | Data source health |
| features.py | Feature aggregator endpoints |
| flywheel.py | ML flywheel metrics |
| logs.py | System logs |
| market.py | Market data, regime, indices |
| ml_brain.py | ML model management |
| openclaw.py | OpenClaw bridge |
| orders.py | Alpaca order CRUD |
| patterns.py | Pattern/screener (DB-backed) |
| performance.py | Performance analytics |
| portfolio.py | Portfolio positions, P&L |
| quotes.py | Price/chart data |
| risk.py | Risk metrics, Monte Carlo |
| risk_shield_api.py | Emergency controls |
| sentiment.py | Sentiment aggregation |
| settings_routes.py | Settings CRUD |
| signals.py | Trading signals |
| status.py | System health |
| stocks.py | Finviz screener |
| strategy.py | Regime-based strategies |
| system.py | System config, GPU |
| training.py | ML training jobs |
| youtube_knowledge.py | YouTube research |

## Backend Services (24 files in backend/app/services/)

| File | Purpose |
|------|---------|
| alpaca_service.py | Alpaca broker REST |
| alpaca_stream_service.py | Alpaca WebSocket -> MessageBus |
| backtest_engine.py | Backtester + Monte Carlo |
| brain_client.py | gRPC client for brain_service |
| data_ingestion.py | Data ingestion pipeline |
| database.py | DuckDB layer (WAL, pooling) |
| execution_simulator.py | Paper trading simulator |
| feature_service.py | DuckDB feature queries |
| finviz_service.py | Finviz screening |
| fred_service.py | FRED economic data |
| kelly_position_sizer.py | Kelly criterion sizing |
| market_data_agent.py | Market data aggregation |
| ml_training.py | LSTM/XGBoost training |
| openclaw_bridge_service.py | OpenClaw bridge |
| openclaw_db.py | OpenClaw SQLite |
| order_executor.py | Event-driven order execution (council-controlled) |
| sec_edgar_service.py | SEC EDGAR filings |
| settings_service.py | Settings CRUD service |
| signal_engine.py | Signal scoring + EventDrivenSignalEngine |
| trade_stats_service.py | Real DuckDB trade stats for Kelly sizing (NEW v3.2.0) |
| training_store.py | ML artifact storage |
| unusual_whales_service.py | Options flow |
| walk_forward_validator.py | Walk-forward validation |

## Council Files (backend/app/council/)

| File | Purpose |
|------|---------|
| runner.py | 7-stage parallel DAG orchestrator |
| arbiter.py | Deterministic BUY/SELL/HOLD with Bayesian weights |
| schemas.py | AgentVote + DecisionPacket dataclasses |
| council_gate.py | Bridge: SignalEngine -> Council -> OrderExecutor (NEW v3.2.0) |
| weight_learner.py | Bayesian self-learning agent weights (NEW v3.2.0) |
| agents/ | 13 agent modules |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB, pydantic-settings |
| AI/ML | XGBoost, scikit-learn, HMM (hmmlearn), Kelly criterion |
| Council | 13-agent DAG with Bayesian-weighted arbiter (7 stages) |
| Brain Service | gRPC + Ollama (local LLM on RTX GPU) |
| Broker | Alpaca Markets (paper + live via alpaca-py) |
| Data | Alpaca Markets, Unusual Whales, Finviz, FRED, SEC EDGAR |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| CI/CD | GitHub Actions — pytest + npm build (151 tests) |
| Infra | Docker, docker-compose.yml |

## Data Sources (NO yfinance)

- Alpaca Markets (alpaca-py) — Market data + order execution
- Unusual Whales — Options flow
- Finviz (finviz) — Screener, fundamentals, VIX proxy
- FRED — Economic macro data
- SEC EDGAR — Company filings

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
cp .env.example .env  # Edit .env with Alpaca API keys
python start_server.py

# Frontend setup (new terminal)
cd frontend-v2
npm install
npm run dev
```

## Open Issues (10)

| # | Title | Priority |
|---|-------|----------|
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
