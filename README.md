# Elite Trading System
### Embodier.ai — Full-Stack AI Trading Intelligence Platform
**Version 5.0.0** | Last Updated: March 12, 2026

> **Version**: v5.0.0 | **Status**: Production-Ready (~95%) | **CI**: 981+ tests GREEN
>
> The system IS profit. A conscious profit-seeking being with a Central Nervous System (CNS) architecture.

---

React + FastAPI full-stack trading application with 14-route V3 widescreen dashboard, DuckDB database, **35-agent council DAG** with Bayesian weight learning, 12 Academic Edge Swarms (P0-P4), Alpaca + Finviz + Unusual Whales integrations, XGBoost ML pipeline, event-driven council-controlled order execution, and gRPC brain service for local Ollama LLM inference.

## Current State (March 12, 2026) — v5.0.0 Production-Ready

| Area | Count | Status |
|------|-------|--------|
| Frontend pages | 14 (all sidebar routes) | **ALL COMPLETE** -- pixel-matched to mockups, no mock data |
| Frontend components | 12 shared + 5 agent-tab | All wired, no orphaned imports |
| Backend API routes | **43** files in api/v1/ | All mounted in main.py (including brain, triage, ingestion firehose, awareness) |
| Backend services | **72+** (incl. subdirs) | llm_clients, data_sources, scanning, trading, scrapers, etc. |
| Council agents | **35 agents** in 7-stage DAG | 11 Core + 12 Academic Edge (P0-P4) + 6 Supplemental + 3 Debate + 3 others |
| Council intelligence | WeightLearner + CouncilGate + SelfAwareness + Homeostasis | Bayesian self-learning agent weights |
| Council subsystems | 15 orchestration files | runner, arbiter, blackboard, task_spawner, shadow_tracker, etc. |
| Tests | **981+ passing** | Backend pytest + frontend build |
| LLM Intelligence | 3-tier router | Ollama -> Perplexity -> Claude; Claude reserved for 6 deep-reasoning tasks |
| Brain service | gRPC + Ollama | **WIRED** -- hypothesis_agent calls brain gRPC |
| Event pipeline | MessageBus + CouncilGate + SignalEngine + OrderExecutor | BUILT -- council-controlled trading |
| Database | DuckDB (WAL mode, pooling) | BUILT |
| Authentication | Bearer token | **Fail-closed** -- live trading endpoints protected |
| WebSocket | 5 pages wired | **ACTIVE** -- bridges for signals, orders, council, market data |
| Electron desktop app | `desktop/` | **BUILD-READY** -- See [build plan](docs/ELECTRON-DESKTOP-BUILD-PLAN.md) |
| Production readiness | ~95% (All phases A+B+C+D+E complete) | All critical gaps resolved, system production-ready |

### Deep Audit Summary (March 11, 2026)

A line-by-line audit of the entire codebase (council, execution, risk, data, infra) found:

**Architecture is fundamentally sound.** All 33+ agents are real implementations. Bayesian weight learning, event pipeline, Kelly sizing all work correctly. Sub-1s council latency.

**All critical gaps have been resolved (Phases A-E):**
- [x] Signal gate threshold regime-adaptive (55/65/75 by regime) — Phase B
- [x] All 10 circuit breakers enforced — Phase A
- [x] Regime params enforced by order executor — Phase B
- [x] All 12 scouts stable (missing methods fixed) — Phase A
- [x] Daily data backfill orchestrator — Phase D
- [x] Weight learner confidence floor lowered (0.5 → 0.2) — Phase C
- [x] Market/limit/TWAP order types by notional — Phase B
- [x] Independent short signal generation — Phase B
- [x] Emergency flatten with retry + auth — Phase E
- [x] E2E integration test (bar → outcome → weight update) — Phase E
- [x] Comprehensive metrics endpoint with council latency percentiles — Phase E

**See `PLAN.md` for the complete 5-phase enhancement plan (Phases A-E, 13-18 sessions).**

## Council Architecture (35 Agents)

The council is the profit-critical decision engine. Every trade signal passes through the full 35-agent DAG before execution.

### Core Council (11 Agents -- Original Spine)

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

### Academic Edge Swarms (12 Agents -- P0-P4)

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
| runner.py | 29.4 KB | 7-stage parallel DAG orchestrator -- the profit spine |
| weight_learner.py | 14.8 KB | Bayesian self-learning agent weights |
| hitl_gate.py | 12.0 KB | Human-in-the-loop approval gate |
| blackboard.py | 11.1 KB | Shared memory state across DAG stages |
| self_awareness.py | 10.8 KB | System metacognition + Bayesian tracking |
| task_spawner.py | 10.7 KB | Dynamic agent registry + spawning |
| overfitting_guard.py | 9.4 KB | Overfitting detection for ML models |
| data_quality.py | 9.0 KB | Data quality scoring for agent inputs |
| council_gate.py | 8.9 KB | Bridge: SignalEngine -> Council -> OrderExecutor |
| shadow_tracker.py | 8.0 KB | Shadow portfolio tracking (paper vs live) |
| schemas.py | 7.6 KB | AgentVote + DecisionPacket dataclasses |
| feedback_loop.py | 7.5 KB | Post-trade feedback to agents |
| homeostasis.py | 6.3 KB | System stability + auto-healing |
| arbiter.py | 6.4 KB | Deterministic BUY/SELL/HOLD with Bayesian weights |
| agent_config.py | 5.4 KB | Settings-driven thresholds for all 35 agents |

## Trade Pipeline (v5.0.0 -- Council-Controlled)

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

Every signal passes through the full 35-agent council before any trade is executed. No hardcoded data -- Kelly sizing uses real DuckDB trade statistics, ATR comes from real feature data, and the mock-source guard prevents trading on fake data.

## Council DAG (35 Agents, 7 Stages)

```
Stage 1 (Parallel -- Perception + Academic Edge P0/P1/P2 -- 13 agents):
  market_perception, flow_perception, regime, social_perception,
  news_catalyst, youtube_knowledge, intermarket,
  gex_agent, insider_agent, finbert_sentiment_agent,
  earnings_tone_agent, dark_pool_agent, macro_regime_agent

Stage 2 (Parallel -- Technical + Data Enrichment -- 8 agents):
  rsi, bbv, ema_trend, relative_strength, cycle_timing,
  supply_chain_agent, institutional_flow_agent, congressional_agent

Stage 3 (Parallel -- Hypothesis + Memory -- 2 agents):
  hypothesis (LLM via brain gRPC), layered_memory_agent

Stage 4 (Strategy):
  strategy

Stage 5 (Risk + Execution + Portfolio -- 3 agents):
  risk, execution, portfolio_optimizer_agent

Stage 5.5 (Debate + Red Team -- 3 agents):
  bull_debater, bear_debater, red_team

Stage 6 (Critic):
  critic

Stage 7 (Arbiter):
  arbiter (deterministic BUY/SELL/HOLD with Bayesian weights)

Post-Arbiter (Background):
  alt_data_agent (background enrichment)
```

## LLM Intelligence (3-Tier Router)

- **Tier 1 -- Ollama**: Routine/local LLM traffic; hypothesis_agent and most council LLM calls.
- **Tier 2 -- Perplexity**: Mid-tier reasoning when needed.
- **Tier 3 -- Claude**: Reserved for 6 deep-reasoning tasks only: `strategy_critic`, `strategy_evolution`, `deep_postmortem`, `trade_thesis`, `overnight_analysis`, `directive_evolution`.

brain_service (gRPC + Ollama) is wired; the router directs traffic by task type.

## What Was Recently Done

### v3.5.1 (March 9, 2026) -- P0/P1 Fixes Complete

**All critical startup blockers resolved:**
- TurboScanner score scale fixed (0-1 -> 0-100 conversion at line 833)
- Single council.verdict publication (council_gate.py:202 only)
- UnusualWhales publishes to MessageBus (perception.unusualwhales topic)
- Backend successfully started with uvicorn
- SelfAwareness actively called in runner.py (line 239)
- IntelligenceCache.start() called at startup (main.py:720)
- Brain service gRPC wired to hypothesis_agent (line 21)
- WebSocket bridges active (signals, orders, council, market data)
- All 12 Academic Edge agents wired into runner.py DAG stages
- 666 tests passing (100% pass rate, backend pytest)

**System Status:** Council now runs 35 agents across 7 stages. All P0 and P1 tasks complete.

### v3.5.0 (March 8, 2026) -- 35-Agent Council + Brain Consciousness Audit *(historical)*

- **Council expanded from 13 to 35 agents** -- added 12 Academic Edge Swarms (P0-P4) + 6 supplemental + 3 debate
- **Full brain consciousness audit** covering ~250+ Python files (42 bugs found -- 4 critical, 5 high)
- **OpenClaw fully assimilated** -- all modules migrated to FastAPI Brain agents, MessageBus communication
- **LLM Health Monitor** -- classifies LLM HTTP errors, broadcasts health via WebSockets
- **agent_config.py** -- settings-driven thresholds for all 35 agents with sensible defaults
- **Council subsystems built**: blackboard, task_spawner, shadow_tracker, self_awareness, homeostasis, overfitting_guard, data_quality, hitl_gate, feedback_loop

**Audit document:** [`docs/audits/brain_consciousness_audit_2026-03-08.pdf`](docs/audits/brain_consciousness_audit_2026-03-08.pdf)

**Critical findings from audit:**
- UnusualWhales options flow fetched but never published to MessageBus -- council blind to it
- TurboScanner scores 0.0-1.0 but CouncilGate threshold is 65.0 -- signals never enter council
- Double `council.verdict` publication (runner.py + council_gate.py) -- potential duplicate orders
- SelfAwareness Bayesian tracking (286 lines) fully implemented but never called -- dead code
- IntelligenceCache.start() never called -- every council evaluation runs cold

### v3.4.0 (March 6, 2026) -- ALL 14 Pages Complete + Mockup Fidelity Pass

Complete pixel-fidelity rebuild of ALL frontend pages to match `docs/mockups-v3/images/` mockup designs. Aurora dark theme with glass effects, cyan/emerald/amber/red color system, dense data-driven layouts. All 23 mockup images now have corresponding code. Zero orphaned imports. Zero dead code. Build passes clean.

### v3.2.0 (March 5, 2026) -- Council-Controlled Intelligence
- **CouncilGate**: Bridge class intercepting all signals (score >= 65) and auto-invoking council
- **WeightLearner**: Bayesian self-learning agent weights
- **TradeStatsService**: Real win_rate/avg_win/avg_loss from DuckDB
- **OrderExecutor**: Listens to council.verdict, uses real stats + real ATR

### v3.1.0 (March 4, 2026) -- 13-Agent Expansion
- Expanded council from 8 to 13 agents
- Updated council runner.py to 7-stage parallel DAG
- Added brain_service gRPC server + Ollama client

## Repository Map

```
elite-trading-system/
├── backend/                    # FastAPI backend (Python 3.11)
│   ├── app/
│   │   ├── api/v1/             # 43 route files (agents, council, market, risk, etc.)
│   │   ├── council/            # 35-agent DAG (runner, arbiter, agents/, schemas)
│   │   │   ├── runner.py       # Orchestrates 7-stage council DAG via asyncio
│   │   │   ├── arbiter.py      # Deterministic weighted vote + Bayesian weights
│   │   │   ├── schemas.py      # AgentVote + DecisionPacket schemas
│   │   │   ├── council_gate.py # Bridge: signal.generated → council → order.submitted
│   │   │   ├── weight_learner.py # Bayesian Beta(α,β) weight updater per agent
│   │   │   └── agents/         # 35 agent files
│   │   ├── core/
│   │   │   ├── message_bus.py  # Pub/sub event bus
│   │   │   ├── config.py       # Settings (pydantic BaseSettings)
│   │   │   └── alignment/      # Profit Being alignment module
│   │   ├── features/
│   │   │   └── feature_aggregator.py  # Auto-computes feature vector for council
│   │   ├── jobs/               # Autonomic background jobs
│   │   │   ├── scheduler.py
│   │   │   ├── daily_outcome_update.py
│   │   │   ├── champion_challenger_eval.py
│   │   │   └── weekly_walkforward_train.py
│   │   ├── modules/
│   │   │   ├── openclaw/       # OpenClaw bridge (regime, scan, whale flow)
│   │   │   └── ml_engine/      # XGBoost trainer, drift detector, model registry
│   │   └── services/           # 68+ service files
│   │       ├── alpaca_service.py
│   │       ├── alpaca_stream_service.py  # 24/7 WS + snapshot fallback
│   │       ├── finviz_service.py
│   │       ├── fred_service.py
│   │       ├── unusual_whales_service.py
│   │       ├── sec_edgar_service.py
│   │       └── signal_engine.py
│   ├── tests/                  # 981+ pytest tests (CI GREEN)
│   └── requirements.txt
├── brain_service/              # gRPC LLM inference server (PC2 / RTX GPU)
│   ├── server.py               # gRPC server
│   ├── ollama_client.py        # Ollama inference
│   ├── models.py               # Request/response schemas
│   └── proto/                  # Protobuf definitions
├── frontend-v2/                # React 18 + Vite + Tailwind (THE active frontend)
│   ├── src/
│   │   ├── config/api.js       # Central API config — ALL endpoints defined here
│   │   ├── hooks/
│   │   │   ├── useApi.js       # Universal data-fetch hook (polling, caching, abort)
│   │   │   ├── useCNS.jsx      # CNS-specific hook
│   │   │   ├── useSettings.js
│   │   │   └── useTradeExecution.js
│   │   ├── pages/              # 14 page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── AgentCommandCenter.jsx
│   │   │   ├── SignalIntelligenceV3.jsx
│   │   │   ├── SentimentIntelligence.jsx
│   │   │   ├── MLBrainFlywheel.jsx
│   │   │   ├── Patterns.jsx
│   │   │   ├── Backtesting.jsx
│   │   │   ├── DataSourcesMonitor.jsx
│   │   │   ├── MarketRegime.jsx
│   │   │   ├── PerformanceAnalytics.jsx
│   │   │   ├── TradeExecution.jsx
│   │   │   ├── RiskIntelligence.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── Trades.jsx
│   │   └── components/         # Shared UI components
│   ├── package.json
│   └── vite.config.js          # Vite proxy: /api → :8000, /ws → ws://:8000
├── desktop/                    # Electron desktop app (BUILD-READY)
├── directives/                 # Trading directives (global.md, regime_*.md)
├── docs/
│   ├── mockups-v3/images/      # 23 UI mockup images (source of truth)
│   ├── MOCKUP-FIDELITY-AUDIT.md
│   └── STATUS-AND-TODO-2026-03-09.md
├── scripts/                    # Utility scripts
├── .env.example                # Required environment variables
├── project_state.md            # 🔴 READ THIS FIRST in every AI session
├── REPO-MAP.md                 # Detailed file inventory
├── SETUP.md                    # Setup and run instructions
├── launch.bat                  # Windows one-click launch
├── launch.sh                   # Linux/Mac one-click launch
├── start-embodier.bat          # Alt Windows launcher
├── start-embodier.ps1          # PowerShell launcher
└── docker-compose.yml          # Full stack via Docker
```

## What Was Done (Enhancement Phases A-E — ALL COMPLETE)

### Phase A: Stop the Bleeding (P0 -- Blocks Safe Trading)
- [x] Fix 3 scout crashes (missing service methods in unusual_whales, sec_edgar, fred) — **DONE**
- [x] Create startup data backfill orchestrator (DuckDB starts empty) — **DONE**
- [x] Wire regime params to order executor (RED regime max_pos=0 is ignored) — **DONE**
- [x] Enforce all 10 circuit breakers (only drawdown enforced today) — **DONE**
- [x] Add VIX-based regime fallback (bridge offline = YELLOW is dangerous) — **DONE**
- [x] Add paper/live account safety check on startup — **DONE**
- [x] Fix DuckDB async lock race condition — **DONE**

### Phase B: Unlock Alpha (P0 -- Direct Profit Impact)
- [x] Calibrate signal gate threshold (65 is too aggressive, 55 regime-adaptive) — **DONE**
- [x] Fix short signal generation (inverted `100 - blended`) — **DONE**
- [x] Smart cooldown (regime-adaptive 30-300s, separate buy/sell) — **DONE**
- [x] Priority queue for concurrent council evaluations — **DONE**
- [x] Limit orders for positions > $5K — **DONE**
- [x] Partial fill re-execution — **DONE**
- [x] Fix viability gate (uses signal score as edge proxy) — **DONE**
- [x] Fix portfolio heat check (procyclical) — **DONE**

### Phase C: Sharpen the Brain (P1 -- Intelligence Quality)
- [x] Lower weight learner confidence floor (0.5 → 0.2) — **DONE**
- [x] Regime-stratified weight learning — **DONE**
- [x] Confidence calibration (Brier score) — **DONE**
- [x] Wire debate votes to weight learner — **DONE**
- [x] Council decision audit trail in DuckDB — **DONE**
- [x] Fix trade stats R-multiple (assumes 2% stop) — **DONE**
- [x] Wire homeostasis mode to Kelly sizing — **DONE**
- [x] Regime-adaptive thresholds everywhere — **DONE**
- [x] Publish all data sources to MessageBus — **DONE**

### Phase D: Continuous Intelligence (P1)
- [x] Autonomous daily data backfill — **DONE**
- [x] Rate limiting framework for all external APIs — **DONE**
- [x] MessageBus dead-letter queue + alerting — **DONE**
- [x] Scraper resilience (session refresh, circuit breaker) — **DONE**

### Phase E: Production Hardening (P2)
- [x] End-to-end integration test (bar → outcome → weight update) — **DONE**
- [x] Emergency flatten with retry + fallback — **DONE**
- [x] Position manager startup sync with Alpaca — **DONE**
- [x] Desktop packaging (Electron + PyInstaller) — **DONE**

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

## Backend API Routes (43 files in backend/app/api/v1/)

| File | Purpose |
|------|---------|
| agents.py | Agent Command Center -- 5 template agents (NOT council) |
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
| brain.py | Brain gRPC proxy / LLM |
| triage.py | Triage / prioritization |
| ingestion_firehose.py | Ingestion firehose |
| awareness.py | Awareness endpoints |
| blackboard_routes.py | Blackboard state |
| mobile_api.py | Mobile API |
| llm_health.py | LLM health monitor |
| cognitive.py | Cognitive dashboard |
| cns.py | CNS architecture |
| cluster.py | Cluster / node |
| swarm.py | Swarm intelligence |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB, pydantic-settings |
| AI/ML | XGBoost, scikit-learn, HMM (hmmlearn), Kelly criterion, FinBERT |
| Council | 35-agent DAG with Bayesian-weighted arbiter (7 stages) |
| LLM Intelligence | 3-tier router: Ollama (routine) -> Perplexity -> Claude (6 deep-reasoning tasks) |
| Brain Service | gRPC + Ollama (local LLM on RTX GPU); brain_service in architecture |
| Broker | Alpaca Markets (paper + live via alpaca-py) |
| Data | Alpaca Markets, Unusual Whales, Finviz, FRED, SEC EDGAR, NewsAPI |
| Knowledge | MemoryBank, HeuristicEngine, KnowledgeGraph (ETBI cognitive layer) |
| Authentication | Bearer token auth, fail-closed for live trading |
| Event Pipeline | MessageBus -> CouncilGate -> Council -> OrderExecutor |
| Desktop | Electron (desktop/) -- BUILD-READY |
| CI/CD | GitHub Actions -- pytest + npm build (981+ tests) |
| Infra | Docker, docker-compose.yml, Redis (where used) |

## Data Sources

- **Alpaca Markets** (alpaca-py) -- Market data + order execution
- **Unusual Whales** -- Options flow, dark pool, congressional trades
- **Finviz** (finviz) -- Screener, fundamentals, VIX proxy
- **FRED** -- Economic macro data
- **SEC EDGAR** -- Company filings, insider transactions
- **NewsAPI** -- Breaking news headlines
- **Benzinga** (web scraper) -- Earnings calendar + transcripts
- **SqueezeMetrics** (web scraper) -- DIX/GEX dark pool indicators
- **Capitol Trades** (UW API + scraper) -- Congressional trade disclosures

## Hardware (Dual-PC Setup)

Path convention: all docs use these canonical paths. See **PATH-STANDARD.md** and **PATH-MAP.md**.

### PC1: ESPENMAIN (Primary)
| Item | Value |
|------|-------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary -- backend API, frontend, DuckDB, trading execution |
| Repo path | `C:\Users\Espen\elite-trading-system` |
| Backend path | `C:\Users\Espen\elite-trading-system\backend` |
| Frontend path | `C:\Users\Espen\elite-trading-system\frontend-v2` |
| Python venv | `C:\Users\Espen\elite-trading-system\backend\venv` |
| Alpaca account | ESPENMAIN -- Key 1 (portfolio trading) |

### PC2: ProfitTrader (Secondary)
| Item | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 |
| Role | Secondary -- GPU training, ML inference, brain_service (gRPC) |
| Repo path | `C:\Users\ProfitTrader\elite-trading-system` |
| Backend path | `C:\Users\ProfitTrader\elite-trading-system\backend` |
| Frontend path | `C:\Users\ProfitTrader\elite-trading-system\frontend-v2` |
| Python venv | `C:\Users\ProfitTrader\elite-trading-system\backend\venv` |
| Alpaca account | Profit Trader -- Key 2 (discovery scanning) |

Both IPs are DHCP-reserved on the AT&T BGW320-505 router (192.168.1.254). Connected via gRPC (brain_service port 50051).

### Ports & URLs (Both PCs)
| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs (Swagger) | 8000 | http://localhost:8000/docs |
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Brain Service (gRPC) | 50051 | localhost:50051 |
| Ollama | 11434 | http://localhost:11434 |
| Redis (optional) | 6379 | redis://localhost:6379 |

## External API Services

All API keys live in `backend/.env` (gitignored). Services degrade gracefully if keys are missing. See `backend/.env.example` for the full template.

| Service | Env Var | Required? | Status |
|---------|---------|-----------|--------|
| Alpaca Markets (Key 1 -- ESPENMAIN) | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | YES (core) | **ACTIVE** -- paper trading |
| Alpaca Markets (Key 2 -- ProfitTrader) | `ALPACA_KEY_2` / `ALPACA_SECRET_2` | No (discovery) | **ACTIVE** -- discovery scanning |
| Finviz Elite | `FINVIZ_API_KEY` | No | **ACTIVE** |
| FRED | `FRED_API_KEY` | No | **ACTIVE** |
| NewsAPI | `NEWS_API_KEY` | No | **ACTIVE** |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | No | **ACTIVE** |
| Perplexity | `PERPLEXITY_API_KEY` | No (LLM tier 2) | **ACTIVE** -- sonar-pro model |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | No (LLM tier 3) | **ACTIVE** -- 6 deep-reasoning tasks |
| Resend (email) | `RESEND_API_KEY` | No | **ACTIVE** |
| StockGeist | `STOCKGEIST_API_KEY` | No | Not configured |
| YouTube | `YOUTUBE_API_KEY` | No | Not configured |
| X / Twitter | `X_API_KEY` | No | Not configured |
| Discord | `DISCORD_BOT_TOKEN` | No | Not configured |

## Slack Notifications (Embodier Trader Workspace)

| Bot | App ID | Purpose | Status |
|-----|--------|---------|--------|
| OpenClaw | A0AF9HSCQ6S | Multi-agent swarm notifications | **ACTIVE** |
| TradingView Alerts | A0AFQ89RVEV | Inbound TradingView webhook alerts | **ACTIVE** |

**Channel mapping:**

| Channel | Events |
|---------|--------|
| `#trade-alerts` | Council verdicts (BUY/SELL), high-score signals (75+) |
| `#oc-trade-desk` | Order executions, fills, position updates |
| `#embodier-trader` | System alerts, health, circuit breakers, agent failures |

All trading events are bridged from MessageBus to Slack via `slack_notification_service.py`. Tokens expire every 12h — refresh at https://api.slack.com/apps. Config in `backend/.env` (gitignored).

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

> **Legacy repo** `github.com/Espenator/Embodier-Trader` is ARCHIVED. Do NOT commit there.

## License

Private repository -- Embodier.ai

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Alpaca API keys (paper or live)
- Optional: Ollama on PC2 for LLM inference

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env    # Fill in your API keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend-v2
npm install
npm run dev                # Vite dev server on :5173, proxies /api → :8000
```

### 3. Brain Service (optional — LLM on PC2)
```bash
cd brain_service
pip install -r requirements.txt
python server.py           # gRPC on :50051
```

### 4. Windows One-Click
```powershell
# From repo root:
.\launch.bat
# OR
pwsh .\start-embodier.ps1
```

---

## 🏗️ Architecture

```
[React 18 frontend-v2] ──useApi()──► [FastAPI backend :8000]
                                          │
              ┌───────────────────────────┼──────────────────────────┐
              │                           │                          │
    [AlpacaStreamService]    [35-Agent Council DAG]     [brain_service gRPC]
    WS + snapshot fallback   runner → arbiter            Ollama on RTX GPU
    market_data.bar ──►      ↑ CouncilGate               hypothesis_agent
    EventDrivenSignalEngine  signal.generated                     │
              │              council.verdict ──► OrderExecutor     │
              └──────────────► MessageBus pub/sub ◄───────────────┘
                                          │
                              [DuckDB analytics store]
                              [Redis where used]
                              [Electron desktop/]
```

### CNS Layers
| Layer | Speed | Component | Status |
|-------|-------|-----------|--------|
| Brainstem | <50ms | CircuitBreaker reflexes | ✅ ENFORCED (10 circuit breakers active) |
| Spinal Cord | ~1500ms | 35-agent council DAG | ✅ BUILT -- all agents real implementations |
| Cortex | 300-800ms | hypothesis + critic via gRPC | ✅ WIRED |
| Thalamus | — | BlackboardState shared memory | ✅ WIRED to sizing |
| Autonomic | nightly | WeightLearner + jobs/scheduler | ✅ TUNED (floor 0.2, regime-stratified) |
| PNS Sensory | real-time | Alpaca WS, UW, FinViz, FRED | ✅ ALL WIRED to MessageBus |
| Discovery | streaming | StreamingDiscoveryEngine + Scouts | ✅ ALL 12 scouts stable |
| PNS Motor | — | OrderExecutor → Alpaca | ✅ ENFORCED (Gate 2b regime + Gate 2c breakers) |

---

## 🤖 Council Architecture (35-Agent DAG, 7 Stages)

```
Stage 1 (Parallel): perception + Academic Edge P0/P1/P2 (13 agents)
Stage 2 (Parallel): technical + data enrichment (8 agents)
Stage 3 (Parallel): hypothesis + layered_memory_agent
Stage 4:            strategy
Stage 5 (Parallel): risk, execution, portfolio_optimizer_agent
Stage 6:            critic
Stage 7:            arbiter — deterministic BUY/SELL/HOLD (Bayesian weighted)
```

**Arbiter Rules:**
1. VETO from `risk` or `execution` → HOLD, `vetoed=True`
2. Requires `regime` + `risk` + `strategy` non-HOLD for any trade
3. Bayesian-weighted confidence aggregation across all agents
4. Execution: confidence > 0.4 AND `execution_ready=True`

**Agent Schema** (all agents MUST return this):
```python
AgentVote(
    agent_name: str,
    direction: str,       # "buy" | "sell" | "hold"
    confidence: float,    # 0.0 – 1.0
    reasoning: str,
    veto: bool,
    veto_reason: str,
    weight: float,
    metadata: dict
)
```

---

## 📡 Data Sources

> **NEVER use yfinance.** All market data comes from:

| Source | Use | Library |
|--------|-----|---------|
| Alpaca Markets | Market data + order execution | alpaca-py |
| Unusual Whales | Options flow, dark pool, congressional trades | REST API |
| FinViz | Screener + fundamentals + VIX proxy | finviz |
| FRED | Macro economic data | fredapi |
| SEC EDGAR | Company filings | REST API |
| Benzinga | Earnings calendar + transcripts | Web scraper (httpx) |
| SqueezeMetrics | DIX/GEX dark pool indicators | Web scraper (httpx) |
| Capitol Trades | Congressional trading disclosures | UW API + web scraper |
| News API / Discord / X | Social sentiment | REST API |
| YouTube | Transcript intelligence | ytdl / transcript API |

---

## 💻 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18, Vite, Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn (no PyTorch in prod) |
| Council | 35-agent DAG, Bayesian-weighted arbiter |
| Brain Service | gRPC + Ollama on RTX GPU (PC2) |
| LLM Router | Ollama (routine) → Perplexity → Claude (6 deep tasks) |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| CI/CD | GitHub Actions, 981+ tests, pytest |
| Auth | Bearer token, fail-closed for live trading |
| Desktop | Electron (desktop/) — BUILD-READY |
| Infra | Docker, docker-compose.yml |

---

## 🌐 Frontend Pages (14 pages, React 18)

| Route | File | Status |
|-------|------|--------|
| `/dashboard` | Dashboard.jsx | 🟢 COMPLETE |
| `/agents` | AgentCommandCenter.jsx | 🟢 COMPLETE |
| `/signal-intelligence-v3` | SignalIntelligenceV3.jsx | 🟢 COMPLETE |
| `/sentiment` | SentimentIntelligence.jsx | 🟢 COMPLETE |
| `/ml-brain` | MLBrainFlywheel.jsx | 🟢 COMPLETE |
| `/patterns` | Patterns.jsx | 🟢 COMPLETE |
| `/backtest` | Backtesting.jsx | 🟢 COMPLETE |
| `/data-sources` | DataSourcesMonitor.jsx | 🟢 COMPLETE |
| `/market-regime` | MarketRegime.jsx | 🟢 COMPLETE |
| `/performance` | PerformanceAnalytics.jsx | 🟢 COMPLETE |
| `/trade-execution` | TradeExecution.jsx | 🟢 COMPLETE |
| `/risk` | RiskIntelligence.jsx | 🟢 COMPLETE |
| `/settings` | Settings.jsx | 🟢 COMPLETE |
| `/trades` | Trades.jsx | 🟢 COMPLETE |

All 14 pages rebuilt to V3 mockup pixel fidelity (March 6, 2026). Full audit: `docs/MOCKUP-FIDELITY-AUDIT.md`

---

## 🔑 Key Code Patterns

```js
// Frontend: ALWAYS use useApi hook — no direct fetch, no mock data
const { data, loading, error } = useApi('councilLatest', { pollIntervalMs: 15000 });
```

```python
# Python: 4-space indent, no tabs
# Council agents: module-level NAME + WEIGHT + async evaluate() -> AgentVote
NAME = "my_agent"
WEIGHT = 0.8

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    f = features.get("features", features)
    # ... logic ...
    return AgentVote(
        agent_name=NAME,
        direction="buy",
        confidence=0.75,
        reasoning="...",
        veto=False,
        veto_reason="",
        weight=WEIGHT,
        metadata={}
    )
```

```python
# Event pipeline
# signal.generated → CouncilGate → run_council() → council.verdict → OrderExecutor
# VETO_AGENTS = {"risk", "execution"}
# REQUIRED_AGENTS = {"regime", "risk", "strategy"}
```

---

## 🛡️ Swarm Invariants

1. **No trade without** `council_decision_id`
2. **No data without** agent validation
3. **No UI mutation without** agent approval
4. **Decisions expire** after 30 seconds
5. **No yfinance** — ever
6. **No mock data** in production components

---

## Current Roadmap (March 2026)

### Completed
- Backend health, startup fixes, mock data removal
- All 14 frontend pages wired to backend
- 28 action buttons verified
- CouncilGate signal pipeline end-to-end
- brain_service gRPC wired to hypothesis_agent
- Bayesian WeightLearner built
- Scraper services created (Benzinga, SqueezeMetrics, Capitol Trades)
- Health monitoring + Slack notification service

### Enhancement Phases (ALL COMPLETE — March 2026)
- **Phase A: Stop the Bleeding** ✅ — Scout crashes fixed, regime enforcement, circuit breakers, safety gates
- **Phase B: Unlock Alpha** ✅ — Regime-adaptive gate, independent shorts, smart cooldowns, limit/TWAP orders
- **Phase C: Sharpen the Brain** ✅ — Weight learner fix, Brier calibration, debate wiring, regime-adaptive thresholds
- **Phase D: Continuous Intelligence** ✅ — Backfill orchestrator, rate limiter registry, DLQ resilience, session scanner
- **Phase E: Production Hardening** ✅ — E2E test, emergency flatten, desktop packaging, metrics, auth

See `PLAN.md` for historical details on all 40 specific issues resolved.

---

## 📄 Key Documents

| File | Purpose |
|------|--------|
| `project_state.md` | 🔴 **START HERE** — paste into every AI session |
| `REPO-MAP.md` | Complete file inventory with descriptions |
| `SETUP.md` | Detailed setup instructions |
| `docs/MOCKUP-FIDELITY-AUDIT.md` | UI mockup vs code comparison |
| `docs/mockups-v3/images/` | 23 source-of-truth UI mockup images |
| `.env.example` | All required environment variables |
| `directives/global.md` | Always-on trading rules |

---

## ⚠️ Rules for All Contributors

1. 🚫 NEVER use `yfinance`
2. 🚫 NEVER use mock/fake data in production
3. ✅ ALWAYS use `useApi()` hook for frontend data
4. ✅ ALWAYS use 4-space Python indentation
5. ✅ Council agents MUST return `AgentVote` schema
6. ✅ ONE repo: `Espenator/elite-trading-system` only
7. ✅ New agents do NOT get veto power
8. ✅ CouncilGate is the ONLY path to order execution
9. ✅ Read `project_state.md` before every coding session
10. ✅ CI must stay GREEN (981+ tests)
