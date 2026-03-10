# Embodier Trader - Repository Map
> Reference for AI coding assistants. Last updated: March 10, 2026 (v4.1.0-dev).
> **Current Focus**: Production hardening — Electron desktop app, end-to-end testing

## Tech Stack
- **Backend**: Python 3.11, FastAPI, DuckDB (analytics) + SQLite (config/orders)
- **Frontend**: React 18 (Vite 5), Lightweight Charts, Recharts, Tailwind CSS
- **Council**: 35-agent DAG with Bayesian-weighted arbiter (7 stages)
- **LLM Intelligence**: 3-tier router — Ollama (local, free) → Perplexity (web) → Claude (deep reasoning)
- **Knowledge**: MemoryBank + HeuristicEngine + KnowledgeGraph + Embedding Search (all-MiniLM-L6-v2)
- **Data Sources**: Alpaca Markets, Unusual Whales, FinViz, FRED, SEC EDGAR, NewsAPI (NO yfinance)
- **Event Pipeline**: MessageBus → CouncilGate → Council → OrderExecutor
- **Brain Service**: gRPC + Ollama (local LLM on RTX GPU, dual-PC model pinning)
- **Authentication**: Bearer token auth, fail-closed (backend/app/core/security.py)
- **Desktop**: Electron 29 + PyInstaller bundled backend (BUILD-READY)
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) — 666 tests passing
- **Infra**: Docker, docker-compose.yml, Redis (cross-PC messaging)

## Directory Tree

```
elite-trading-system/
|-- .github/workflows/ci.yml          # CI pipeline
|-- .env.example                       # Root env template
|-- .gitattributes
|-- .gitignore
|-- README.md                          # Project overview + status
|-- REPO-MAP.md                        # THIS FILE
|-- AI-CONTEXT-GUIDE.md                # AI context strategies
|-- project_state.md                   # AI session initialization (READ FIRST)
|-- bundle_files.py                    # Bundle key files for AI context
|-- map_repo.py                        # Generate repo tree map
|-- docker-compose.yml                 # Docker orchestration
|
|-- backend/                           # FastAPI Python backend
|   |-- Dockerfile
|   |-- README.md
|   |-- requirements.txt
|   |-- start_server.py
|   |-- activate_venv.bat
|   |-- setup_venv.bat
|   |-- start.bat
|   |-- .env.example
|   |
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py                    # FastAPI app entry (v3.2.0, Embodier Trader)
|   |   |-- websocket_manager.py       # WebSocket broadcast manager
|   |   |
|   |   |-- api/v1/                    # REST API endpoints (34 route files)
|   |   |   |-- agents.py              # Agent Command Center
|   |   |   |-- alerts.py              # Drawdown alerts, system alerts
|   |   |   |-- alignment.py           # Alignment/consensus endpoints
|   |   |   |-- alpaca.py              # Alpaca API proxy for frontend
|   |   |   |-- backtest_routes.py     # Strategy backtesting
|   |   |   |-- cluster.py             # Cluster management
|   |   |   |-- cns.py                 # CNS: homeostasis, circuit breaker, postmortems
|   |   |   |-- cognitive.py           # Cognitive telemetry dashboard
|   |   |   |-- council.py             # Council evaluate, status, weights (35-agent)
|   |   |   |-- data_sources.py        # Data source health
|   |   |   |-- features.py            # Feature aggregator endpoints
|   |   |   |-- flywheel.py            # ML flywheel metrics
|   |   |   |-- llm_health.py          # LLM health monitoring + circuit breaker
|   |   |   |-- logs.py                # System logs
|   |   |   |-- market.py              # Market data, regime, indices
|   |   |   |-- ml_brain.py            # ML model management
|   |   |   |-- openclaw.py            # OpenClaw bridge
|   |   |   |-- orders.py              # Alpaca order CRUD
|   |   |   |-- patterns.py            # Pattern/screener (DB-backed)
|   |   |   |-- performance.py         # Performance analytics
|   |   |   |-- portfolio.py           # Portfolio positions, P&L
|   |   |   |-- quotes.py              # Price/chart data
|   |   |   |-- risk.py                # Risk metrics, Monte Carlo
|   |   |   |-- risk_shield_api.py     # Emergency controls
|   |   |   |-- sentiment.py           # Sentiment aggregation
|   |   |   |-- settings_routes.py     # Settings CRUD
|   |   |   |-- signals.py             # Trading signals
|   |   |   |-- status.py              # System health
|   |   |   |-- stocks.py              # Finviz screener
|   |   |   |-- strategy.py            # Regime-based strategies
|   |   |   |-- swarm.py               # Swarm intelligence operations
|   |   |   |-- system.py              # System config, GPU
|   |   |   |-- training.py            # ML training jobs
|   |   |   |-- youtube_knowledge.py   # YouTube research
|   |   |
|   |   |-- council/                   # 35-Agent Council DAG (7 stages)
|   |   |   |-- __init__.py
|   |   |   |-- runner.py              # 7-stage parallel DAG orchestrator (profit spine)
|   |   |   |-- arbiter.py             # Deterministic arbiter + Bayesian weights
|   |   |   |-- schemas.py             # AgentVote + DecisionPacket dataclasses
|   |   |   |-- council_gate.py        # Bridge: SignalEngine -> Council -> OrderExecutor
|   |   |   |-- weight_learner.py      # Bayesian self-learning agent weights
|   |   |   |-- blackboard.py          # Shared memory state across DAG stages
|   |   |   |-- self_awareness.py      # System metacognition + Bayesian tracking
|   |   |   |-- task_spawner.py        # Dynamic agent registry + spawning
|   |   |   |-- homeostasis.py         # System stability + auto-healing
|   |   |   |-- hitl_gate.py           # Human-in-the-loop approval gate
|   |   |   |-- feedback_loop.py       # Post-trade feedback to agents
|   |   |   |-- agent_config.py        # Settings-driven thresholds for all 35 agents
|   |   |   |-- debate/                # Bull/Bear debate + red team
|   |   |   |-- directives/            # Council directives
|   |   |   |-- reflexes/              # Circuit breaker reflexes
|   |   |   |-- regime/                # Bayesian regime classification
|   |   |   |-- agents/                # 35 agent implementations
|   |   |       |-- (11 core + 12 academic edge + 6 technical + 3 debate + 3 others)
|   |   |
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # App configuration (359 settings)
|   |   |   |-- message_bus.py         # Async pub/sub event bus
|   |   |   |-- security.py            # Bearer token auth (fail-closed)
|   |   |   |-- alignment/             # 8 alignment/constraint files
|   |   |
|   |   |-- data/
|   |   |   |-- __init__.py
|   |   |   |-- storage.py             # DuckDB storage layer
|   |   |
|   |   |-- features/
|   |   |   |-- __init__.py
|   |   |   |-- feature_aggregator.py  # FeatureVector with 50+ indicators
|   |   |
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- inference.py           # Model inference
|   |   |   |-- lstm_daily.py          # LSTM model
|   |   |   |-- trainer.py             # Model trainer
|   |   |
|   |   |-- modules/
|   |   |   |-- __init__.py
|   |   |   |-- chart_patterns/        # Chart pattern detection
|   |   |   |-- execution_engine/      # Trade execution
|   |   |   |-- ml_engine/             # ML algorithms engine
|   |   |   |   |-- config.py
|   |   |   |   |-- drift_detector.py
|   |   |   |   |-- feature_pipeline.py
|   |   |   |   |-- model_registry.py
|   |   |   |   |-- outcome_resolver.py
|   |   |   |   |-- trainer.py
|   |   |   |   |-- xgboost_trainer.py
|   |   |   |-- openclaw/             # OpenClaw (DEAD CODE — P4 cleanup)
|   |   |   |   |-- app.py
|   |   |   |   |-- config.py
|   |   |   |   |-- main.py
|   |   |   |   |-- clawbots/
|   |   |   |   |-- execution/
|   |   |   |   |-- integrations/
|   |   |   |   |-- intelligence/
|   |   |   |   |-- pine/
|   |   |   |   |-- scanner/
|   |   |   |   |-- scorer/
|   |   |   |   |-- streaming/
|   |   |   |   |-- world_intel/
|   |   |   |-- social_news_engine/    # Social/news sentiment
|   |   |   |-- symbol_universe/       # Symbol management
|   |   |   |-- youtube_agent/         # YouTube analysis
|   |   |
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- signals.py            # Signal data models
|   |   |
|   |   |-- knowledge/                # ETBI cognitive intelligence
|   |   |   |-- heuristic_engine.py    # Regime-aware heuristic activation
|   |   |   |-- memory_bank.py         # Agent observations per symbol/regime
|   |   |   |-- embedding_service.py   # Batch embeddings (all-MiniLM-L6-v2)
|   |   |   |-- knowledge_graph.py     # Cross-agent pattern relationships
|   |   |
|   |   |-- services/                 # Business logic layer (68+ files)
|   |   |   |-- llm_router.py             # 3-tier LLM routing (Ollama/Perplexity/Claude)
|   |   |   |-- llm_clients/              # Claude, Ollama, Perplexity wrappers
|   |   |   |   |-- claude_client.py       # Anthropic AsyncAnthropic SDK
|   |   |   |   |-- ollama_client.py       # Ollama HTTP client
|   |   |   |-- claude_reasoning.py        # Deep reasoning service (7 methods)
|   |   |   |-- intelligence_orchestrator.py # Pre-council multi-tier gathering
|   |   |   |-- adaptive_router.py         # Auto-escalate to cloud if local <45%
|   |   |   |-- brain_client.py            # gRPC client for brain_service (PC2)
|   |   |   |-- alpaca_service.py          # Alpaca broker REST
|   |   |   |-- alpaca_stream_service.py   # Alpaca WebSocket -> MessageBus
|   |   |   |-- order_executor.py          # Council-controlled order execution
|   |   |   |-- signal_engine.py           # Signal scoring + EventDrivenSignalEngine
|   |   |   |-- data_sources/              # Data feed integrations
|   |   |   |-- scanning/                  # Signal scanning
|   |   |   |-- trading/                   # Trade execution services
|   |   |   |-- (+ 50 more service files)
|   |   |
|   |   |-- strategy/
|   |       |-- __init__.py
|   |       |-- backtest.py            # Backtest framework
|   |
|   |-- tests/                         # 37 test files (666 tests passing)
|       |-- conftest.py                # Test fixtures
|       |-- test_api.py                # API integration tests
|
|-- brain_service/                     # gRPC + Ollama LLM service (PC2)
|   |-- server.py                      # Async gRPC server (port 50051)
|   |-- ollama_client.py               # Ollama HTTP client
|   |-- proto/brain.proto              # Service definition (InferCandidateContext, CriticPostmortem, Embed)
|
|-- core/
|   |-- api/
|       |-- ml_api.py                  # ML API standalone module
|
|-- desktop/                           # Electron desktop app (BUILD-READY)
|   |-- main.js                        # Electron main process
|   |-- preload.js                     # Context-isolated IPC bridge
|   |-- backend-manager.js             # PyInstaller backend launcher
|   |-- service-orchestrator.js        # Role-based service control
|   |-- peer-monitor.js                # 2-PC health monitoring
|   |-- ollama-fallback.js             # Local LLM fallback
|   |-- device-config.js               # Device identity + auth token generation
|   |-- pages/setup.html               # First-run setup wizard
|
|-- frontend-v2/                       # React frontend (Vite 5)
|   |-- Dockerfile
|   |-- package.json
|   |-- vite.config.js                 # Dev server port 3000, proxy /api + /ws
|   |-- .env.example
|   |
|   |-- src/
|       |-- App.jsx                    # Root component + routing
|       |-- main.jsx                   # React entry + auth init from Electron
|       |-- index.css                  # Global styles (Tailwind)
|       |-- V3-ARCHITECTURE.md         # Frontend architecture doc
|       |
|       |-- config/
|       |   |-- api.js                 # API URLs + WebSocket + auth headers
|       |
|       |-- hooks/
|       |   |-- useApi.js              # Central API hook
|       |   |-- useSentiment.js        # Sentiment polling hook
|       |
|       |-- services/
|       |   |-- dataSourcesApi.js      # Data sources API client
|       |   |-- openclawService.js     # OpenClaw API client
|       |   |-- websocket.js           # WebSocket connection manager
|       |
|       |-- lib/
|       |   |-- dataSourceIcons.js     # Data source icon mapping
|       |   |-- symbolIcons.js         # Stock symbol icons
|       |-- types/
|       |   |-- index.ts              # Shared TypeScript interfaces
|       |
|       |-- components/
|       |   |-- ErrorBoundary.jsx
|       |   |-- RegimeBanner.jsx
|       |   |-- agents/
|       |   |   |-- AgentResourceMonitor.jsx
|       |   |   |-- ConferencePipeline.jsx
|       |   |   |-- DriftMonitor.jsx
|       |   |   |-- SwarmTopology.jsx
|       |   |   |-- SystemAlerts.jsx
|       |   |-- charts/
|       |   |   |-- DataSourceSparkLC.jsx
|       |   |   |-- EquityCurveChart.jsx
|       |   |   |-- MiniChart.jsx
|       |   |   |-- MonteCarloLC.jsx
|       |   |   |-- PatternFrequencyLC.jsx
|       |   |   |-- RiskEquityLC.jsx
|       |   |   |-- RiskHistoryChart.jsx
|       |   |   |-- SentimentTimelineLC.jsx
|       |   |-- dashboard/
|       |   |   |-- ActivePositions.jsx
|       |   |   |-- LiveSignalFeed.jsx
|       |   |   |-- MLStatusCard.jsx
|       |   |   |-- MarketRegimeCard.jsx
|       |   |   |-- PerformanceCard.jsx
|       |   |   |-- QuickStats.jsx
|       |   |-- layout/
|       |   |   |-- Header.jsx
|       |   |   |-- Layout.jsx
|       |   |   |-- Sidebar.jsx
|       |   |-- ui/                    # Reusable UI primitives
|       |       |-- Badge.jsx
|       |       |-- Button.jsx
|       |       |-- Card.jsx
|       |       |-- Checkbox.jsx
|       |       |-- DataTable.jsx
|       |       |-- PageHeader.jsx
|       |       |-- Select.jsx
|       |       |-- Slider.jsx
|       |       |-- SymbolIcon.jsx
|       |       |-- TextField.jsx
|       |       |-- Toggle.jsx
|       |
|       |-- pages/                     # Route pages (15 total)
|           |-- AgentCommandCenter.jsx
|           |-- Backtesting.jsx
|           |-- Dashboard.jsx
|           |-- DataSourcesMonitor.jsx
|           |-- MLBrainFlywheel.jsx
|           |-- MarketRegime.jsx
|           |-- Patterns.jsx
|           |-- PerformanceAnalytics.jsx
|           |-- RiskIntelligence.jsx
|           |-- SentimentIntelligence.jsx
|           |-- Settings.jsx
|           |-- SignalIntelligenceV3.jsx
|           |-- Signals.jsx
|           |-- TradeExecution.jsx
|           |-- Trades.jsx
|
|-- docs/                              # Project documentation
|   |-- mockups-v2/                    # V2 design mockups
|   |-- mockups-v3/                    # V3 approved mockups (current)
|   |   |-- images/                    # Mockup PNG files
|   |-- DEEP_RESEARCH_AUDIT_2026-02-27.md
|   |-- INDENTATION-FIX-GUIDE.md
|   |-- STATUS-AND-TODO-2026-02-26.md
|   |-- STATUS-AND-TODO-2026-02-27.md
|   |-- STATUS-AND-TODO-2026-02-28.md
|   |-- UI-DESIGN-SYSTEM.md
|   |-- UI-PRODUCTION-PLAN-14-PAGES.md
|
|-- scripts/                           # Utility scripts
    |-- download_mockups.ps1
    |-- fix_indentation.py             # Batch Python indentation fixer
    |-- migrate_openclaw.ps1
    |-- migrate_openclaw.sh
```

## Key Architecture Notes

1. **No yfinance** — All market data via Alpaca, Unusual Whales, FinViz, FRED, SEC EDGAR
2. **Real API only** — No mock data in production components
3. **useApi hook** — Central data fetching: `useApi('endpoint')` returns `{ data, loading, error }`
4. **Council-controlled trading** — All signals pass through 35-agent council via CouncilGate before execution
5. **Bayesian weight learning** — WeightLearner adjusts agent influence based on trade outcomes
6. **3-tier LLM router** — Ollama (free, <500ms) → Perplexity (web, <3s) → Claude (deep, <10s). Cost-optimized: local handles 80%+
7. **DuckDB** — Primary analytics database (WAL mode, connection pooling)
8. **Bearer token auth** — Fail-closed: no token = all state-changing endpoints blocked
9. **CI** — 666 tests passing, GitHub Actions on every push
10. **Brain Service** — gRPC + Ollama on PC2 for LLM inference, wired to hypothesis_agent
11. **Knowledge Layer** — MemoryBank + HeuristicEngine + KnowledgeGraph + Embedding search
12. **Electron desktop** — One-click startup, role-aware (full/primary/secondary), peer resilience
13. **WebSocket** — Real-time pub/sub: 5 pages wired (Dashboard, Risk, TradeExecution, MarketRegime) + bridges

## Trade Pipeline (v4.1.0-dev)

```
DISCOVERY:
  TurboScanner (60s, 10 DuckDB screens) -> signals
  12 Scout Agents (UW flow, insider, news, sentiment) -> discoveries
  All -> swarm.idea (MessageBus)

TRIAGE:
  swarm.idea -> IdeaTriageService (dedup, priority scoring) -> HyperSwarm -> score >= 0.65 escalated

EVALUATION (35-agent council, 7 stages):
  IntelligenceOrchestrator (Ollama + Perplexity + optional Claude)
    -> Knowledge recall (MemoryBank + HeuristicEngine)
    -> Circuit breaker check (brainstem reflexes)
    -> Council DAG: perception → technical → hypothesis → strategy → risk → debate → arbiter
    -> council.verdict (BUY/SELL/HOLD with Bayesian-weighted confidence)

EXECUTION:
  council.verdict -> OrderExecutor (real DuckDB stats, real ATR, mock guard) -> Alpaca

LEARNING:
  order.filled -> OutcomeTracker -> MemoryBank + HeuristicEngine + KnowledgeGraph + WeightLearner
```

## Quick Reference: API Endpoints

All backend routes: `http://localhost:8000/api/v1/{service}`

Services: `agents`, `alerts`, `alignment`, `alpaca`, `backtest`, `cluster`, `cns`, `cognitive`, `council`, `data-sources`, `features`, `flywheel`, `llm-health`, `logs`, `market`, `ml-brain`, `openclaw`, `orders`, `patterns`, `performance`, `portfolio`, `quotes`, `risk`, `risk-shield`, `sentiment`, `settings`, `signals`, `status`, `stocks`, `strategy`, `swarm`, `system`, `training`, `youtube-knowledge`
