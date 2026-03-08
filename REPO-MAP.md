# Embodier Trader - Repository Map
> Auto-generated reference for AI coding assistants. Last updated: March 7, 2026 (v3.5.0-dev).
> Run `python map_repo.py` to regenerate, or `python bundle_files.py` to bundle key files.
> **Current Focus**: Continuous Discovery Architecture (Issue #38)

## Tech Stack
- **Backend**: Python 3.11, FastAPI, DuckDB
- **Frontend**: React 18 (Vite), Lightweight Charts, Tailwind CSS
- **Council**: 32-agent DAG with Bayesian-weighted arbiter (7 stages)
- **Discovery**: TurboScanner + HyperSwarm + 12 Scout Agents (Issue #38 — streaming transition)
- **Knowledge**: MemoryBank + HeuristicEngine + KnowledgeGraph (outcome-driven learning)
- **Data Sources**: Alpaca Markets, Unusual Whales, FinViz, FRED, SEC EDGAR (NO yfinance)
- **Event Pipeline**: MessageBus -> CouncilGate -> Council -> OrderExecutor
- **Brain Service**: gRPC + Ollama (local LLM on RTX GPU)
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) — 151 tests passing
- **Infra**: Docker, docker-compose.yml

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
|   |   |-- api/v1/                    # REST API endpoints (29 routes)
|   |   |   |-- __init__.py
|   |   |   |-- agents.py              # Agent Command Center (5 template agents)
|   |   |   |-- alerts.py              # Drawdown alerts, system alerts
|   |   |   |-- alignment.py           # Alignment/consensus endpoints
|   |   |   |-- alpaca.py              # Alpaca API proxy for frontend
|   |   |   |-- backtest_routes.py     # Strategy backtesting
|   |   |   |-- council.py             # Council evaluate, status, weights (13-agent)
|   |   |   |-- data_sources.py        # Data source health
|   |   |   |-- features.py            # Feature aggregator endpoints
|   |   |   |-- flywheel.py            # ML flywheel metrics
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
|   |   |   |-- system.py              # System config, GPU
|   |   |   |-- training.py            # ML training jobs
|   |   |   |-- youtube_knowledge.py   # YouTube research
|   |   |
|   |   |-- council/                   # 13-Agent Council DAG (7 stages)
|   |   |   |-- __init__.py
|   |   |   |-- runner.py              # 7-stage parallel DAG orchestrator
|   |   |   |-- arbiter.py             # Deterministic arbiter + Bayesian weights
|   |   |   |-- schemas.py             # AgentVote + DecisionPacket dataclasses
|   |   |   |-- council_gate.py        # Bridge: SignalEngine -> Council -> OrderExecutor (NEW v3.2.0)
|   |   |   |-- weight_learner.py      # Bayesian self-learning agent weights (NEW v3.2.0)
|   |   |   |-- agents/
|   |   |       |-- __init__.py
|   |   |       |-- market_perception_agent.py   # Stage 1: market conditions
|   |   |       |-- flow_perception_agent.py     # Stage 1: options flow PCR
|   |   |       |-- regime_agent.py              # Stage 1: market regime alignment
|   |   |       |-- intermarket_agent.py         # Stage 1: cross-market correlations
|   |   |       |-- rsi_agent.py                 # Stage 2: multi-timeframe RSI
|   |   |       |-- bbv_agent.py                 # Stage 2: Bollinger Band mean-reversion
|   |   |       |-- ema_trend_agent.py           # Stage 2: EMA cascade classification
|   |   |       |-- relative_strength_agent.py   # Stage 2: sector relative strength
|   |   |       |-- cycle_timing_agent.py        # Stage 2: market cycle timing
|   |   |       |-- hypothesis_agent.py          # Stage 3: brain_service LLM (stub)
|   |   |       |-- strategy_agent.py            # Stage 4: entry/exit/sizing
|   |   |       |-- risk_agent.py                # Stage 5: risk assessment (VETO)
|   |   |       |-- execution_agent.py           # Stage 5: execution readiness (VETO)
|   |   |       |-- critic_agent.py              # Stage 6: postmortem learning
|   |   |
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # App configuration
|   |   |   |-- message_bus.py         # Async pub/sub event bus
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
|   |   |-- services/                 # Business logic layer (24 files)
|   |   |   |-- __init__.py
|   |   |   |-- alpaca_service.py          # Alpaca broker REST
|   |   |   |-- alpaca_stream_service.py   # Alpaca WebSocket -> MessageBus
|   |   |   |-- backtest_engine.py         # Backtester + Monte Carlo
|   |   |   |-- brain_client.py            # gRPC client for brain_service
|   |   |   |-- data_ingestion.py          # Data ingestion pipeline
|   |   |   |-- database.py               # DuckDB layer (WAL, pooling)
|   |   |   |-- execution_simulator.py     # Paper trading simulator
|   |   |   |-- feature_service.py         # DuckDB feature queries
|   |   |   |-- finviz_service.py          # Finviz screening
|   |   |   |-- fred_service.py            # FRED economic data
|   |   |   |-- kelly_position_sizer.py    # Kelly criterion sizing
|   |   |   |-- market_data_agent.py       # Market data aggregation
|   |   |   |-- ml_training.py             # LSTM/XGBoost training
|   |   |   |-- openclaw_bridge_service.py # OpenClaw bridge
|   |   |   |-- openclaw_db.py             # OpenClaw SQLite
|   |   |   |-- order_executor.py          # Council-controlled order execution
|   |   |   |-- sec_edgar_service.py       # SEC EDGAR filings
|   |   |   |-- settings_service.py        # Settings CRUD service
|   |   |   |-- signal_engine.py           # Signal scoring + EventDrivenSignalEngine
|   |   |   |-- trade_stats_service.py     # Real DuckDB trade stats (NEW v3.2.0)
|   |   |   |-- training_store.py          # ML artifact storage
|   |   |   |-- unusual_whales_service.py  # Options flow
|   |   |   |-- walk_forward_validator.py  # Walk-forward validation
|   |   |
|   |   |-- strategy/
|   |       |-- __init__.py
|   |       |-- backtest.py            # Backtest framework
|   |
|   |-- tests/
|       |-- __init__.py
|       |-- conftest.py                # Test fixtures
|       |-- test_api.py                # API integration tests (151 tests)
|
|-- brain_service/                     # gRPC + Ollama LLM service (PC2)
|
|-- core/
|   |-- api/
|       |-- ml_api.py                  # ML API standalone module
|
|-- frontend-v2/                       # React frontend (Vite)
|   |-- Dockerfile
|   |-- package.json
|   |-- package-lock.json
|   |-- index.html
|   |-- nginx.conf
|   |-- vite.config.js
|   |-- .env.example
|   |
|   |-- src/
|       |-- App.jsx                    # Root component + routing
|       |-- main.jsx                   # React entry point
|       |-- index.css                  # Global styles (Tailwind)
|       |-- V3-ARCHITECTURE.md         # Frontend architecture doc
|       |
|       |-- config/
|       |   |-- api.js                 # API base URL config
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

1. **No yfinance** - All market data via Alpaca, Unusual Whales, FinViz, FRED, SEC EDGAR
2. **Real API only** - No mock data in production components
3. **useApi hook** - Central data fetching: `useApi('endpoint')` returns `{ data, loading, error }`
4. **Council-controlled trading** - All signals pass through 32-agent council via CouncilGate before execution
5. **Bayesian weight learning** - WeightLearner adjusts agent influence based on trade outcomes
6. **DuckDB** - Primary analytics database (WAL mode, connection pooling)
7. **OpenClaw** - Legacy code with useful scanner/agent pieces, scheduled for cleanup (P4)
8. **CI** - 151 tests passing, GitHub Actions on every push
9. **Brain Service** - gRPC + Ollama on PC2 for LLM inference (not yet wired to council)
10. **Discovery** - Transitioning from periodic polling to continuous streaming (Issue #38)
11. **Knowledge Layer** - MemoryBank + HeuristicEngine + KnowledgeGraph learn from trade outcomes

## Discovery + Trade Pipeline (v3.5.0-dev)

```
DISCOVERY (continuous — Issue #38):
  StreamingDiscoveryEngine (Alpaca * stream) -> volume/price anomalies
  12 Scout Agents (UW flow, insider, news, sentiment, etc.) -> discoveries
  TurboScanner (60s, 10 DuckDB screens, 8000+ symbols) -> signals
  MarketWideSweep (4hr full, 30min incremental) -> signals
  All -> swarm.idea (MessageBus)

TRIAGE:
  swarm.idea -> HyperSwarm (50 workers, Ollama <500ms) -> score >= 65 escalated

EVALUATION:
  Escalated -> SwarmSpawner -> 17-Agent Council (7 stages) -> council.verdict

EXECUTION:
  council.verdict -> OrderExecutor (real DuckDB stats, real ATR, mock guard) -> Alpaca

LEARNING:
  order.filled -> OutcomeTracker -> MemoryBank + HeuristicEngine + KnowledgeGraph + WeightLearner
```

## Quick Reference: API Endpoints

All backend routes: `http://localhost:8000/api/v1/{service}`

Services: `agents`, `alerts`, `alignment`, `alpaca`, `backtest`, `council`, `data-sources`, `features`, `flywheel`, `logs`, `market`, `ml-brain`, `openclaw`, `orders`, `patterns`, `performance`, `portfolio`, `quotes`, `risk`, `risk-shield`, `sentiment`, `settings`, `signals`, `status`, `stocks`, `strategy`, `system`, `training`, `youtube-knowledge`
