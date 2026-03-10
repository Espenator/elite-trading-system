# Elite Trading System
### Embodier.ai — Full-Stack AI Trading Intelligence Platform
**Version 4.1.0-dev** | Last Updated: March 10, 2026

CI Status: GREEN — 666 tests passing
Frontend: **ALL 14 PAGES COMPLETE** — pixel-fidelity match to 23 mockup images. Build clean.
Backend: **Backend successfully started!** Tests passing (666/666). Council running 35 agents.
Council: **35-agent DAG** in 7 stages — council-controlled trading via CouncilGate (v3.5.0)

---

React + FastAPI full-stack trading application with 14-route V3 widescreen dashboard, DuckDB database, **35-agent council DAG** with Bayesian weight learning, 12 Academic Edge Swarms (P0–P4), Alpaca + Finviz + Unusual Whales integrations, XGBoost ML pipeline, event-driven council-controlled order execution, **3-tier LLM intelligence** (Ollama → Perplexity → Claude), and Electron desktop app with PyInstaller-bundled backend.

## Current State (March 10, 2026)

| Area | Count | Status |
|------|-------|--------|
| Frontend pages | 14 (all sidebar routes) | **ALL COMPLETE** — pixel-matched to mockups, no mock data |
| Frontend components | 22 shared (ui/, layout/, dashboard/) | All wired, no orphaned imports |
| Backend API routes | 34 files in api/v1/ | All mounted in main.py |
| Backend services | 68+ files in services/ | Business logic + LLM clients + data sources + scanning + trading |
| Council agents | **35 agents** in 7-stage DAG | 11 Core + 12 Academic Edge (P0–P4) + 6 Supplemental + 3 Debate + 3 others |
| Council intelligence | WeightLearner + CouncilGate + SelfAwareness + Homeostasis | Bayesian self-learning agent weights |
| Council subsystems | 15 orchestration files | runner, arbiter, blackboard, task_spawner, shadow_tracker, etc. |
| LLM Intelligence | 3-tier router (698 lines) | Ollama (free, <500ms) → Perplexity (web, <3s) → Claude (deep, <10s) |
| Tests | 666 passing | Backend pytest + frontend build |
| Brain service | gRPC + Ollama | **WIRED** — hypothesis_agent calls brain gRPC |
| Event pipeline | MessageBus + CouncilGate + SignalEngine + OrderExecutor | BUILT — council-controlled trading |
| Database | DuckDB (WAL mode, pooling) + SQLite (config/orders) | BUILT |
| Authentication | Bearer token auth (fail-closed) | **DONE** — end-to-end: Electron generates → backend validates → frontend sends |
| WebSocket | Real-time pub/sub | **ACTIVE** — 5 pages wired (Dashboard, Risk, TradeExecution, MarketRegime) + bridges |
| Electron desktop app | `desktop/` | **BUILD-READY** — 11 bugs fixed, auth wired, IPC working. See [build plan](docs/ELECTRON-DESKTOP-BUILD-PLAN.md) |

## Council Architecture (35 Agents)

The council is the profit-critical decision engine. Every trade signal passes through the full 35-agent DAG before execution.

### Core Council (11 Agents — Original Spine)

| Agent | File | Weight | Role |
|-------|------|--------|------|
| Market Perception | market_perception_agent.py | 1.0 | Price action + volume analysis |
| Flow Perception | flow_perception_agent.py | 0.8 | Put/call ratio, options flow |
| Regime | regime_agent.py | 1.2 | Market regime classification |
| Social Perception | social_perception_agent.py | 0.7 | Social sentiment scoring |
| News Catalyst | news_catalyst_agent.py | 0.6 | Breaking news detection |
| YouTube Knowledge | youtube_knowledge_agent.py | 0.4 | Financial research extraction |
| Hypothesis | hypothesis_agent.py | 0.9 | LLM-generated trade hypotheses |
| Strategy | strategy_agent.py | 1.1 | Entry/exit/sizing logic |
| Risk | risk_agent.py | 1.5 | Portfolio heat, position limits, VaR |
| Execution | execution_agent.py | 1.3 | Volume + liquidity feasibility |
| Critic | critic_agent.py | 0.5 | R-multiple postmortem learning |

### Academic Edge Swarms (12 Agents — P0–P4)

| Priority | Agent | File | Weight | Academic Basis |
|----------|-------|------|--------|----------------|
| P0 | GEX / Options Flow | gex_agent.py | 0.9 | Gamma exposure pinning / vol compression |
| P0 | Insider Filing | insider_agent.py | 0.85 | SEC Form 4 cluster detection |
| P1 | Earnings Tone NLP | earnings_tone_agent.py | 0.8 | CFO hedging language delta |
| P1 | FinBERT Sentiment | finbert_sentiment_agent.py | 0.75 | Transformer-based financial NLP |
| P1 | Supply Chain Graph | supply_chain_agent.py | 0.7 | Contagion propagation modeling |
| P2 | 13F Institutional | institutional_flow_agent.py | 0.7 | Quarterly fund position consensus |
| P2 | Congressional Trading | congressional_agent.py | 0.6 | Political insider trading signals |
| P2 | Dark Pool Accumulation | dark_pool_agent.py | 0.7 | DIX bullish/bearish thresholds |
| P3 | Portfolio Optimizer | portfolio_optimizer_agent.py | 0.8 | Multi-agent RL allocation |
| P3 | Layered Memory (FinMem) | layered_memory_agent.py | 0.6 | Short/mid/long-term trade memory |
| P4 | Alternative Data | alt_data_agent.py | 0.5 | Satellite, web traffic, app download signals |
| P4 | Macro Regime | macro_regime_agent.py | 1.0 | Cross-asset VIX/credit/yield regime |

### Supplemental Agents (6)

| Agent | File | Role |
|-------|------|------|
| RSI | rsi_agent.py | Relative Strength Index signals |
| BBV | bbv_agent.py | Bollinger Band + Volume confirmation |
| EMA Trend | ema_trend_agent.py | Exponential moving average trend |
| Intermarket | intermarket_agent.py | Cross-market correlation signals |
| Relative Strength | relative_strength_agent.py | Sector/stock relative strength |
| Cycle Timing | cycle_timing_agent.py | Market cycle phase detection |

### Debate and Adversarial (3)

| Agent | File | Role |
|-------|------|------|
| Bull Debater | bull_debater.py | Argues bullish case for trade |
| Bear Debater | bear_debater.py | Argues bearish case against trade |
| Red Team | red_team_agent.py | Adversarial stress-testing of council decisions |

### Council Orchestration (15 files in backend/app/council/)

| File | Size | Purpose |
|------|------|---------|
| runner.py | 29.4 KB | 7-stage parallel DAG orchestrator — the profit spine |
| weight_learner.py | 14.8 KB | Bayesian self-learning agent weights |
| hitl_gate.py | 12.0 KB | Human-in-the-loop approval gate |
| blackboard.py | 11.1 KB | Shared memory state across DAG stages |
| self_awareness.py | 10.8 KB | System metacognition + Bayesian tracking |
| task_spawner.py | 10.7 KB | Dynamic agent registry + spawning |
| overfitting_guard.py | 9.4 KB | Overfitting detection for ML models |
| data_quality.py | 9.0 KB | Data quality scoring for agent inputs |
| council_gate.py | 8.9 KB | Bridge: SignalEngine → Council → OrderExecutor |
| shadow_tracker.py | 8.0 KB | Shadow portfolio tracking (paper vs live) |
| schemas.py | 7.6 KB | AgentVote + DecisionPacket dataclasses |
| feedback_loop.py | 7.5 KB | Post-trade feedback to agents |
| homeostasis.py | 6.3 KB | System stability + auto-healing |
| arbiter.py | 6.4 KB | Deterministic BUY/SELL/HOLD with Bayesian weights |
| agent_config.py | 5.4 KB | Settings-driven thresholds for all 35 agents |

## Trade Pipeline (v3.5.0 — Council-Controlled)

```
AlpacaStreamService
  -> market_data.bar
  -> EventDrivenSignalEngine
  -> signal.generated (score >= 65)
  -> CouncilGate (invokes 35-agent council)
  -> council.verdict (BUY/SELL/HOLD with Bayesian-weighted confidence)
  -> OrderExecutor (real DuckDB stats, real ATR, mock-source guard)
  -> order.submitted
  -> WebSocket bridges
  -> Frontend
```

Every signal passes through the full 35-agent council before any trade is executed. No hardcoded data — Kelly sizing uses real DuckDB trade statistics, ATR comes from real feature data, and the mock-source guard prevents trading on fake data.

## Council DAG (35 Agents, 7 Stages)

```
Stage 1 (Parallel — Perception + Academic Edge P0/P1/P2 — 13 agents):
  market_perception, flow_perception, regime, social_perception,
  news_catalyst, youtube_knowledge, intermarket,
  gex_agent, insider_agent, finbert_sentiment_agent,
  earnings_tone_agent, dark_pool_agent, macro_regime_agent

Stage 2 (Parallel — Technical + Data Enrichment — 8 agents):
  rsi, bbv, ema_trend, relative_strength, cycle_timing,
  supply_chain_agent, institutional_flow_agent, congressional_agent

Stage 3 (Parallel — Hypothesis + Memory — 2 agents):
  hypothesis (LLM via brain gRPC), layered_memory_agent

Stage 4 (Strategy):
  strategy

Stage 5 (Risk + Execution + Portfolio — 3 agents):
  risk, execution, portfolio_optimizer_agent

Stage 5.5 (Debate + Red Team — 3 agents):
  bull_debater, bear_debater, red_team

Stage 6 (Critic):
  critic

Stage 7 (Arbiter):
  arbiter (deterministic BUY/SELL/HOLD with Bayesian weights)

Post-Arbiter (Background):
  alt_data_agent (background enrichment)
```

## What Was Recently Done

### v4.1.0-dev (March 10, 2026) — Electron Build-Ready + Auth + WebSocket Wiring

**Electron Desktop App — 11 bugs fixed, now build-ready:**
- ✅ Deleted conflicting `electron-builder.yml` (package.json is source of truth)
- ✅ Fixed setup wizard IPC — replaced broken `require('electron')` with preload bridge
- ✅ Added missing `initialize()`/`shutdown()` to peer-monitor.js
- ✅ Added missing `activate()`/`deactivate()` to ollama-fallback.js
- ✅ Fixed service-orchestrator `initialize(role)` signature, wired brain-service
- ✅ Added backend binary validation, exponential restart backoff (max 5), port conflict detection
- ✅ Added 4 missing API key fields to setup wizard

**End-to-end API token authentication:**
- ✅ `device-config.js` generates secure token (crypto.randomBytes)
- ✅ `backend-manager.js` passes `API_AUTH_TOKEN` env var to backend
- ✅ `preload.js` exposes `getAuthToken()` to renderer
- ✅ `frontend-v2/src/config/api.js` reads token from Electron bridge or env var
- ✅ `backend/app/core/security.py` validates Bearer tokens (fail-closed)

**WebSocket real-time data wired to 4 additional pages:**
- ✅ Dashboard — market, signals, risk, trades channels
- ✅ RiskIntelligence — risk channel triggers refresh
- ✅ TradeExecution — trades, market, council_verdict channels
- ✅ MarketRegime — macro, market channels

### v3.5.1 (March 9, 2026) — P0/P1 Fixes Complete ✅

**All critical startup blockers resolved:**
- ✅ TurboScanner score scale fixed (0-1 → 0-100 conversion at line 833)
- ✅ Single council.verdict publication (council_gate.py:202 only)
- ✅ UnusualWhales publishes to MessageBus (perception.unusualwhales topic)
- ✅ Backend successfully started with uvicorn
- ✅ SelfAwareness actively called in runner.py (line 239)
- ✅ IntelligenceCache.start() called at startup (main.py:720)
- ✅ Brain service gRPC wired to hypothesis_agent (line 21)
- ✅ WebSocket bridges active (signals, orders, council, market data)
- ✅ All 12 Academic Edge agents wired into runner.py DAG stages
- ✅ 666 tests passing (100% pass rate)

**System Status:** Council now runs 35 agents across 7 stages. All P0 and P1 tasks complete.

### v3.5.0 (March 8, 2026) — 31-Agent Council + Brain Consciousness Audit

- **Council expanded from 13 to 31 agents** — added 12 Academic Edge Swarms (P0–P4) + 6 supplemental
- **Full brain consciousness audit** covering ~250+ Python files (42 bugs found — 4 critical, 5 high)
- **OpenClaw fully assimilated** — all modules migrated to FastAPI Brain agents, MessageBus communication
- **LLM Health Monitor** — classifies LLM HTTP errors, broadcasts health via WebSockets
- **agent_config.py** — settings-driven thresholds for all 31 agents with sensible defaults
- **Council subsystems built**: blackboard, task_spawner, shadow_tracker, self_awareness, homeostasis, overfitting_guard, data_quality, hitl_gate, feedback_loop

**Audit document:** [`docs/audits/brain_consciousness_audit_2026-03-08.pdf`](docs/audits/brain_consciousness_audit_2026-03-08.pdf)

**Critical findings from audit:**
- UnusualWhales options flow fetched but never published to MessageBus — council blind to it
- TurboScanner scores 0.0–1.0 but CouncilGate threshold is 65.0 — signals never enter council
- Double `council.verdict` publication (runner.py + council_gate.py) — potential duplicate orders
- SelfAwareness Bayesian tracking (286 lines) fully implemented but never called — dead code
- IntelligenceCache.start() never called — every council evaluation runs cold

### v3.4.0 (March 6, 2026) — ALL 14 Pages Complete + Mockup Fidelity Pass

Complete pixel-fidelity rebuild of ALL frontend pages to match `docs/mockups-v3/images/` mockup designs. Aurora dark theme with glass effects, cyan/emerald/amber/red color system, dense data-driven layouts. All 23 mockup images now have corresponding code. Zero orphaned imports. Zero dead code. Build passes clean.

### v3.2.0 (March 5, 2026) — Council-Controlled Intelligence
- **CouncilGate**: Bridge class intercepting all signals (score >= 65) and auto-invoking council
- **WeightLearner**: Bayesian self-learning agent weights
- **TradeStatsService**: Real win_rate/avg_win/avg_loss from DuckDB
- **OrderExecutor**: Listens to council.verdict, uses real stats + real ATR

### v3.1.0 (March 4, 2026) — 13-Agent Expansion
- Expanded council from 8 to 13 agents
- Updated council runner.py to 7-stage parallel DAG
- Added brain_service gRPC server + Ollama client

## Repository Map

```
elite-trading-system/
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app + startup wiring
│   │   ├── api/v1/                   # 34 API route files
│   │   ├── council/                  # Council decision engine
│   │   │   ├── agents/               # 35 agent implementations
│   │   │   ├── debate/               # Bull/Bear debate system
│   │   │   ├── directives/           # Council directives
│   │   │   ├── reflexes/             # Circuit breaker reflexes
│   │   │   ├── regime/               # Bayesian regime classification
│   │   │   ├── runner.py             # DAG orchestrator (profit spine)
│   │   │   ├── arbiter.py            # Final BUY/SELL/HOLD decision
│   │   │   ├── blackboard.py         # Shared memory
│   │   │   ├── council_gate.py       # Signal → Council → Executor bridge
│   │   │   └── weight_learner.py     # Bayesian weight adaptation
│   │   ├── core/                     # MessageBus, config, security, alignment
│   │   ├── features/                 # Feature aggregator
│   │   ├── knowledge/                # Heuristics + memory bank + embeddings
│   │   ├── models/                   # PyTorch LSTM + inference
│   │   ├── modules/                  # 7 modules (chart_patterns, ml_engine, openclaw, etc.)
│   │   └── services/                 # 68+ service files
│   │       ├── llm_clients/          # Claude, Ollama, Perplexity wrappers
│   │       ├── data_sources/         # Data feed integrations
│   │       ├── scanning/             # Signal scanning
│   │       └── trading/              # Trade execution
│   ├── tests/                        # 37 test files (666 tests)
│   ├── requirements.txt
│   └── run_server.py
├── brain_service/                    # gRPC + Ollama LLM inference (PC2)
│   ├── server.py                     # Async gRPC server
│   ├── ollama_client.py              # Ollama HTTP client
│   └── proto/brain.proto             # Service definition
├── desktop/                          # Electron desktop app (BUILD-READY)
│   ├── main.js                       # Electron main process
│   ├── preload.js                    # Context-isolated IPC bridge
│   ├── backend-manager.js            # PyInstaller backend launcher
│   ├── service-orchestrator.js       # Role-based service control
│   ├── peer-monitor.js               # 2-PC health monitoring
│   ├── ollama-fallback.js            # Local LLM fallback
│   ├── device-config.js              # Device identity + auth token
│   └── pages/setup.html              # First-run setup wizard
├── frontend-v2/                      # React 18 + Vite + TailwindCSS
│   └── src/
│       ├── pages/                    # 14 page components
│       ├── components/               # 22 shared components
│       └── config/api.js             # API + WebSocket + auth config
├── docs/                             # 60+ docs (architecture, audits, research)
├── docker-compose.yml                # Redis + Backend + Frontend
└── README.md
```

## What Is NOT Done (TODO)

### P0 — Critical (Blocks Trading) ✅ ALL COMPLETE
- [x] Fix TurboScanner score scale (0.0–1.0 vs CouncilGate 65.0 threshold)
- [x] Fix double `council.verdict` publication (runner.py + council_gate.py)
- [x] Wire UnusualWhales flow to MessageBus so council can see it
- [x] Start backend for first time (`uvicorn app.main:app`)

### P1 — High (Blocks Full Intelligence) ✅ ALL COMPLETE
- [x] Call SelfAwareness Bayesian tracking (286 lines of dead code)
- [x] Call IntelligenceCache.start() at startup
- [x] Wire brain_service gRPC to hypothesis_agent
- [x] Establish WebSocket real-time data connectivity
- [x] Wire 12 new Academic Edge agents into runner.py DAG stages

### P2 — Medium
- [x] ~~Add JWT authentication for live trading endpoints~~ → Bearer token auth implemented (fail-closed)
- [ ] Visual polish pass in browser at 2560px target resolution
- [x] ~~Wire WebSocket real-time data~~ → 4 pages wired (Dashboard, Risk, TradeExecution, MarketRegime)
- [ ] Wire WebSocket to remaining pages (Live Activity Feed, Blackboard Feed)
- [ ] Update agent_config.py to include weights for 6 supplemental agents explicitly
- [ ] Signal scoring weights calibration from historical data
- [ ] End-to-end pipeline integration test (signal → council → order)

### P3 — Low
- [ ] Build CircuitBreaker reflexes (brainstem <50ms)
- [ ] Multi-timeframe analysis in real-time path
- [ ] Clean up remaining OpenClaw dead code
- [ ] Add `anthropic` to requirements.txt (currently lazy-imported)

## Frontend Pages (14)

All pages in frontend-v2/src/pages/. All use useApi() hook. No mock data. **ALL 14 pages rebuilt to V3 mockup pixel fidelity (March 6, 2026).**

| # | Route | File | Status |
|---|-------|------|--------|
| 1 | /dashboard | Dashboard.jsx | **COMPLETE** |
| 2 | /agents | AgentCommandCenter.jsx + 5 tab files | **COMPLETE** |
| 3 | /signal-intelligence-v3 | SignalIntelligenceV3.jsx | **COMPLETE** |
| 4 | /sentiment | SentimentIntelligence.jsx | **COMPLETE** |
| 5 | /data-sources | DataSourcesMonitor.jsx | **COMPLETE** |
| 6 | /ml-brain | MLBrainFlywheel.jsx | **COMPLETE** |
| 7 | /patterns | Patterns.jsx | **COMPLETE** |
| 8 | /backtest | Backtesting.jsx | **COMPLETE** |
| 9 | /performance | PerformanceAnalytics.jsx | **COMPLETE** |
| 10 | /market-regime | MarketRegime.jsx | **COMPLETE** |
| 11 | /trades | Trades.jsx | **COMPLETE** |
| 12 | /risk | RiskIntelligence.jsx | **COMPLETE** |
| 13 | /trade-execution | TradeExecution.jsx | **COMPLETE** |
| 14 | /settings | Settings.jsx | **COMPLETE** |

## Backend API Routes (34 files in backend/app/api/v1/)

| File | Purpose |
|------|---------|
| agents.py | Agent Command Center — 5 template agents (NOT council) |
| alerts.py | Drawdown alerts, system alerts |
| alignment.py | Alignment/consensus endpoints |
| alpaca.py | Alpaca API proxy for frontend |
| backtest_routes.py | Strategy backtesting |
| cluster.py | Cluster management |
| cns.py | CNS (Central Nervous System) — homeostasis, circuit breaker, postmortems |
| cognitive.py | Cognitive telemetry dashboard |
| council.py | Council evaluate, status, weights endpoints |
| data_sources.py | Data source health |
| features.py | Feature aggregator endpoints |
| flywheel.py | ML flywheel metrics |
| llm_health.py | LLM health monitoring + circuit breaker status |
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
| swarm.py | Swarm intelligence operations |
| system.py | System config, GPU |
| training.py | ML training jobs |
| youtube_knowledge.py | YouTube research |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, TailwindCSS, Lightweight Charts, Recharts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB (analytics), SQLite (config), pydantic-settings |
| AI/ML | PyTorch LSTM, XGBoost, scikit-learn, HMM (hmmlearn), Kelly criterion, FinBERT |
| LLM Intelligence | **3-tier router**: Ollama (local, free) → Perplexity Sonar Pro (web) → Claude (deep reasoning) |
| Council | 35-agent DAG with Bayesian-weighted arbiter (7 stages) |
| Brain Service | gRPC + Ollama (local LLM on RTX GPU, dual-PC model pinning) |
| Knowledge | Heuristic engine + memory bank + embedding search (all-MiniLM-L6-v2) |
| Broker | Alpaca Markets (paper + live via alpaca-py) |
| Data | Alpaca Markets, Unusual Whales, Finviz, FRED, SEC EDGAR, NewsAPI |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| Authentication | Bearer token auth, fail-closed (backend/app/core/security.py) |
| Desktop | Electron 29 + PyInstaller bundled backend |
| CI/CD | GitHub Actions — pytest + npm build (666 tests) |
| Infra | Docker, docker-compose.yml, Redis (cross-PC messaging) |

## Intelligence Layer (3-Tier LLM Router)

The brain uses a cost-optimized 3-tier LLM architecture. Local models handle 80%+ of calls for free. Cloud APIs are reserved for high-value tasks only.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 1: BRAINSTEM (Ollama — local, FREE, <500ms)                  │
│  Models: llama3.2, mistral:7b, qwen3:14b                          │
│  Tasks: regime_classification, signal_scoring, feature_summary,    │
│         quick_hypothesis, risk_check                               │
│  PC1: fast models (llama3.2, mistral:7b)                          │
│  PC2: deep models (deepseek-r1:14b, mixtral:8x7b)                │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 2: CORTEX (Perplexity Sonar Pro — web-grounded, <3s)        │
│  Tasks: breaking_news, earnings_context, sector_rotation,          │
│         macro_context, institutional_flow                          │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 3: DEEP CORTEX (Anthropic Claude — deep reasoning, <10s)    │
│  Model: claude-sonnet-4-20250514                                   │
│  Tasks: strategy_critic, strategy_evolution, deep_postmortem,      │
│         trade_thesis, overnight_analysis, directive_evolution      │
└─────────────────────────────────────────────────────────────────────┘
```

**Safety:** Circuit breaker (3 fails → 5 min skip), rate limiting (1 rps deep cortex), $100/mo budget cap, automatic fallback chains.

**Key files:**
- `backend/app/services/llm_router.py` — Multi-tier routing with DuckDB cost tracking
- `backend/app/services/llm_clients/claude_client.py` — Anthropic AsyncAnthropic wrapper
- `backend/app/services/claude_reasoning.py` — Deep reasoning service (7 methods)
- `backend/app/services/intelligence_orchestrator.py` — Pre-council intelligence gathering
- `backend/app/services/brain_client.py` — gRPC client to PC2 Ollama
- `backend/app/services/adaptive_router.py` — Auto-escalates to cloud if local accuracy <45%

## Data Sources

- **Alpaca Markets** (alpaca-py) — Market data + order execution
- **Unusual Whales** — Options flow, dark pool, congressional trades
- **Finviz** (finviz) — Screener, fundamentals, VIX proxy
- **FRED** — Economic macro data
- **SEC EDGAR** — Company filings, insider transactions
- **NewsAPI** — Breaking news headlines

## Hardware (Dual-PC Setup)
- **PC 1 (ESPENMAIN)**: Development + Frontend + Backend API
- **PC 2**: RTX GPU cluster for ML training + Ollama inference (brain_service)
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

## License

Private repository — Embodier.ai


---

## Desktop App (Electron) — BUILD-READY

**Goal:** Double-click one icon. Everything starts. No more terminal juggling, port conflicts, or separate process management.

Embodier Trader is packaged as a native Electron 29 desktop application with PyInstaller-bundled Python backend. All 11 build-blocking bugs have been fixed.

### Operating Modes

| Mode | Description |
|------|-------------|
| **Full** | Single PC runs everything (backend + frontend + all services) |
| **Primary + Secondary** | ESPENMAIN runs trading/ML, Profit Trader runs brain-service (LLM) + scanner |
| **Degraded** | Primary continues trading if Secondary goes offline, with tiered fallback |

### Key Features
- One-click startup — Electron spawns backend automatically
- Role-aware — same installer, different behavior per machine
- Peer resilience — tiered fallback when 2nd PC goes down (retry -> local Ollama -> no-brain conservative mode)
- Secure auth — auto-generated API token flows from Electron → backend → frontend
- Port conflict detection + exponential restart backoff
- iPhone PWA — remote monitoring via Tailscale
- Auto-updater via GitHub Releases

### What Was Fixed (v4.1.0-dev)
- Setup wizard IPC (contextIsolation-compatible preload bridge)
- Missing peer-monitor and ollama-fallback methods
- Service orchestrator role handling + brain-service wiring
- Backend binary validation before spawn
- 4 missing API key fields in setup wizard
- Conflicting electron-builder.yml deleted

### Documentation
- [Electron Desktop Build Plan](docs/ELECTRON-DESKTOP-BUILD-PLAN.md) — Full 3-phase build plan with task checklists
- [Peer Resilience Architecture](docs/PEER-RESILIENCE-ARCHITECTURE.md) — Tiered fallback strategy for 2-PC mode
- [Status & TODO (March 9, 2026)](docs/STATUS-AND-TODO-2026-03-09.md) — Current project status
