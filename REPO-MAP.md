# Embodier Trader - Repository Map
> Auto-generated reference for AI coding assistants. Last updated: March 8, 2026 (v4.0.0).
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
|-- INTEGRATION_PLAN.md                # Frontend↔Backend integration gaps
|-- SETUP.md                           # Setup and quick start guide
|-- project_state.md                   # AI session initialization (READ FIRST)
|-- bundle_files.py                    # Bundle key files for AI context
|-- map_repo.py                        # Generate repo tree map
|-- docker-compose.yml                 # Docker orchestration (redis + backend + frontend)
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
|   |   |-- main.py                    # FastAPI app entry (v4.0.0, Embodier Trader)
|   |   |-- websocket_manager.py       # WebSocket broadcast manager
|   |   |
|   |   |-- api/
|   |   |   |-- ingestion.py           # Data ingestion/backfill (POST /api/ingestion/backfill)
|   |   |   |-- v1/                    # REST API endpoints (34 route files)
|   |   |       |-- __init__.py
|   |   |       |-- agents.py              # Agent Command Center (5 template agents)
|   |   |       |-- alerts.py              # Drawdown alerts, system alerts
|   |   |       |-- alignment.py           # Alignment/consensus endpoints
|   |   |       |-- alpaca.py              # Alpaca API proxy for frontend
|   |   |       |-- backtest_routes.py     # Strategy backtesting
|   |   |       |-- cluster.py             # Multi-PC cluster coordination
|   |   |       |-- cns.py                 # Central Nervous System endpoints
|   |   |       |-- cognitive.py           # Cognitive telemetry
|   |   |       |-- council.py             # Council evaluate, status, weights (32-agent)
|   |   |       |-- data_sources.py        # Data source health
|   |   |       |-- features.py            # Feature aggregator endpoints
|   |   |       |-- flywheel.py            # ML flywheel metrics
|   |   |       |-- llm_health.py          # LLM health monitoring
|   |   |       |-- logs.py                # System logs
|   |   |       |-- market.py              # Market data, regime, indices
|   |   |       |-- ml_brain.py            # ML model management
|   |   |       |-- openclaw.py            # OpenClaw bridge (legacy)
|   |   |       |-- orders.py              # Alpaca order CRUD
|   |   |       |-- patterns.py            # Pattern/screener (DB-backed)
|   |   |       |-- performance.py         # Performance analytics
|   |   |       |-- portfolio.py           # Portfolio positions, P&L
|   |   |       |-- quotes.py              # Price/chart data
|   |   |       |-- risk.py                # Risk metrics, Monte Carlo, VaR
|   |   |       |-- risk_shield_api.py     # Emergency controls
|   |   |       |-- sentiment.py           # Sentiment aggregation
|   |   |       |-- settings_routes.py     # Settings CRUD
|   |   |       |-- signals.py             # Trading signals
|   |   |       |-- status.py              # System health
|   |   |       |-- stocks.py              # Finviz screener
|   |   |       |-- strategy.py            # Regime-based strategies
|   |   |       |-- swarm.py               # Discovery swarm endpoints
|   |   |       |-- system.py              # System config, GPU
|   |   |       |-- training.py            # ML training jobs
|   |   |       |-- youtube_knowledge.py   # YouTube research
|   |   |
|   |   |-- council/                   # 32-Agent Council DAG (7 stages)
|   |   |   |-- __init__.py
|   |   |   |-- runner.py              # 7-stage parallel DAG orchestrator (profit spine)
|   |   |   |-- arbiter.py             # Deterministic BUY/SELL/HOLD + Bayesian weights
|   |   |   |-- schemas.py             # AgentVote + DecisionPacket dataclasses
|   |   |   |-- council_gate.py        # Bridge: SignalEngine -> Council -> OrderExecutor
|   |   |   |-- weight_learner.py      # Bayesian self-learning agent weights
|   |   |   |-- blackboard.py          # Shared BlackboardState across DAG stages
|   |   |   |-- agent_config.py        # Settings-driven thresholds for all 32 agents
|   |   |   |-- data_quality.py        # Data quality scoring for agent inputs
|   |   |   |-- feedback_loop.py       # Post-trade feedback to agents
|   |   |   |-- hitl_gate.py           # Human-in-the-loop approval gate
|   |   |   |-- homeostasis.py         # System stability + auto-healing
|   |   |   |-- overfitting_guard.py   # ML overfitting detection
|   |   |   |-- self_awareness.py      # System metacognition + Bayesian tracking
|   |   |   |-- shadow_tracker.py      # Shadow portfolio tracking (paper vs live)
|   |   |   |-- task_spawner.py        # Dynamic agent registry + spawning
|   |   |   |-- debate/
|   |   |   |   |-- debate_engine.py   # Debate orchestration
|   |   |   |   |-- debate_scorer.py   # Debate scoring + confidence delta
|   |   |   |   |-- debate_utils.py    # Shared debate utilities
|   |   |   |-- directives/
|   |   |   |   |-- loader.py          # Council directive loader
|   |   |   |-- reflexes/
|   |   |   |   |-- circuit_breaker.py # Brainstem <50ms reflexes
|   |   |   |-- regime/
|   |   |   |   |-- bayesian_regime.py # Bayesian regime classification
|   |   |   |-- agents/                # 32 agent implementations
|   |   |       |-- __init__.py
|   |   |       # --- Stage 1: Perception + Academic Edge P0/P1/P2 (13 agents) ---
|   |   |       |-- market_perception_agent.py   # Price action + volume
|   |   |       |-- flow_perception_agent.py     # Options flow, PCR
|   |   |       |-- regime_agent.py              # Market regime classification
|   |   |       |-- social_perception_agent.py   # Social sentiment scoring
|   |   |       |-- news_catalyst_agent.py       # Breaking news detection
|   |   |       |-- youtube_knowledge_agent.py   # Financial research extraction
|   |   |       |-- intermarket_agent.py         # Cross-market correlations
|   |   |       |-- gex_agent.py                 # Gamma exposure (P0)
|   |   |       |-- insider_agent.py             # SEC Form 4 clusters (P0)
|   |   |       |-- finbert_sentiment_agent.py   # FinBERT NLP (P1)
|   |   |       |-- earnings_tone_agent.py       # CFO hedging language (P1)
|   |   |       |-- dark_pool_agent.py           # DIX dark pool (P2)
|   |   |       |-- macro_regime_agent.py        # Cross-asset regime (P4)
|   |   |       # --- Stage 2: Technical + Data Enrichment (8 agents) ---
|   |   |       |-- rsi_agent.py                 # Multi-timeframe RSI
|   |   |       |-- bbv_agent.py                 # Bollinger Band mean-reversion
|   |   |       |-- ema_trend_agent.py           # EMA cascade classification
|   |   |       |-- relative_strength_agent.py   # Sector relative strength
|   |   |       |-- cycle_timing_agent.py        # Market cycle timing
|   |   |       |-- supply_chain_agent.py        # Contagion propagation (P1)
|   |   |       |-- institutional_flow_agent.py  # 13F consensus (P2)
|   |   |       |-- congressional_agent.py       # Political insider trades (P2)
|   |   |       # --- Stage 3: Hypothesis + Memory (2 agents) ---
|   |   |       |-- hypothesis_agent.py          # LLM-generated hypotheses
|   |   |       |-- layered_memory_agent.py      # FinMem short/mid/long-term (P3)
|   |   |       # --- Stage 4: Strategy (1 agent) ---
|   |   |       |-- strategy_agent.py            # Entry/exit/sizing logic
|   |   |       # --- Stage 5: Risk + Execution + Portfolio (3 agents) ---
|   |   |       |-- risk_agent.py                # Portfolio heat, VaR (VETO)
|   |   |       |-- execution_agent.py           # Volume/liquidity feasibility (VETO)
|   |   |       |-- portfolio_optimizer_agent.py # Multi-agent RL allocation (P3)
|   |   |       # --- Stage 5.5: Debate + Adversarial (3 agents) ---
|   |   |       |-- bull_debater.py              # Argues bullish case
|   |   |       |-- bear_debater.py              # Argues bearish case
|   |   |       |-- red_team_agent.py            # Adversarial stress-testing
|   |   |       # --- Stage 6: Critic (1 agent) ---
|   |   |       |-- critic_agent.py              # Postmortem R-multiple learning
|   |   |       # --- Post-Arbiter background (1 agent) ---
|   |   |       |-- alt_data_agent.py            # Satellite/web/app signals (P4)
|   |   |
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # App configuration (APP_VERSION source of truth)
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
|   |   |-- knowledge/                 # Cognitive intelligence layer
|   |   |   |-- __init__.py
|   |   |   |-- memory_bank.py         # Agent observation embeddings
|   |   |   |-- heuristic_engine.py    # Bayesian pattern extraction
|   |   |   |-- knowledge_graph.py     # Cross-agent synergy edges
|   |   |   |-- embedding_service.py   # Embedding generation
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
|   |   |   |-- execution_engine/      # Trade execution engine
|   |   |   |-- ml_engine/             # ML algorithms (XGBoost, drift, registry)
|   |   |   |   |-- config.py
|   |   |   |   |-- drift_detector.py
|   |   |   |   |-- feature_pipeline.py
|   |   |   |   |-- model_registry.py
|   |   |   |   |-- outcome_resolver.py
|   |   |   |   |-- trainer.py
|   |   |   |   |-- xgboost_trainer.py
|   |   |   |-- openclaw/              # OpenClaw (DEAD CODE — P4 cleanup)
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
|   |   |   |-- signals.py             # Signal data models
|   |   |
|   |   |-- services/                  # Business logic layer (57 files)
|   |   |   |-- __init__.py
|   |   |   # --- Core Trading ---
|   |   |   |-- signal_engine.py            # Signal scoring + EventDrivenSignalEngine
|   |   |   |-- order_executor.py           # Council-controlled order execution
|   |   |   |-- council_evaluator.py        # Council evaluation wrapper
|   |   |   |-- swarm_spawner.py            # Council spawner (20 concurrent)
|   |   |   |-- execution_simulator.py      # Paper trading simulator
|   |   |   |-- outcome_tracker.py          # Trade resolution + feedback loop
|   |   |   |-- alpaca_stream_service.py    # Alpaca WebSocket -> MessageBus
|   |   |   |-- alpaca_service.py           # Alpaca broker REST
|   |   |   # --- Discovery ---
|   |   |   |-- turbo_scanner.py            # 10 parallel DuckDB screens, 8000+ symbols
|   |   |   |-- hyper_swarm.py              # 50 micro-workers, Ollama triage (<500ms)
|   |   |   |-- autonomous_scout.py         # 4 scout loops (flow, screener, watchlist, backtest)
|   |   |   |-- market_wide_sweep.py        # Full universe batch scan
|   |   |   # --- ML & Intelligence ---
|   |   |   |-- ml_training.py              # ML training orchestration
|   |   |   |-- ml_scorer.py                # ML-based scoring
|   |   |   |-- unified_profit_engine.py    # Multi-brain weighted ensemble
|   |   |   |-- kelly_position_sizer.py     # Kelly criterion sizing (real DuckDB stats)
|   |   |   |-- backtest_engine.py          # Backtester + Monte Carlo
|   |   |   |-- walk_forward_validator.py   # Walk-forward validation
|   |   |   |-- intelligence_cache.py       # Intelligence caching
|   |   |   |-- intelligence_orchestrator.py # Intelligence orchestration
|   |   |   |-- perplexity_intelligence.py  # Perplexity LLM bridge
|   |   |   |-- claude_reasoning.py         # Claude AI reasoning
|   |   |   |-- expected_move_service.py    # Expected move calculation
|   |   |   # --- Data & Ingestion ---
|   |   |   |-- data_ingestion.py           # Multi-source ingestion pipeline
|   |   |   |-- unusual_whales_service.py   # Options flow + dark pool
|   |   |   |-- finviz_service.py           # Finviz stock screener
|   |   |   |-- fred_service.py             # FRED economic data
|   |   |   |-- sec_edgar_service.py        # SEC EDGAR filings + insider trades
|   |   |   |-- news_aggregator.py          # News aggregation
|   |   |   |-- market_data_agent.py        # Market data aggregation
|   |   |   |-- knowledge_ingest.py         # Knowledge ingestion
|   |   |   |-- alpaca_stream_manager.py    # Multi-stream orchestration
|   |   |   |-- alpaca_key_pool.py          # Multi-API key management
|   |   |   # --- Infrastructure & Monitoring ---
|   |   |   |-- database.py                 # DuckDB storage (WAL mode, pooling)
|   |   |   |-- feature_service.py          # DuckDB feature queries
|   |   |   |-- trade_stats_service.py      # Real trade stats from DuckDB
|   |   |   |-- brain_client.py             # gRPC client for brain_service
|   |   |   |-- llm_health_monitor.py       # LLM HTTP error classification
|   |   |   |-- cognitive_telemetry.py      # Cognitive metrics + dashboard
|   |   |   |-- gpu_telemetry.py            # GPU monitoring
|   |   |   |-- node_discovery.py           # Multi-PC node discovery
|   |   |   |-- correlation_radar.py        # Correlation analysis
|   |   |   |-- geopolitical_radar.py       # Geopolitical risk monitoring
|   |   |   |-- adaptive_router.py          # Adaptive routing
|   |   |   |-- ollama_node_pool.py         # Ollama node pool management
|   |   |   # --- LLM Services ---
|   |   |   |-- llm_dispatcher.py           # LLM request dispatcher
|   |   |   |-- llm_router.py               # Adaptive LLM routing
|   |   |   |-- llm_schemas.py              # LLM request/response schemas
|   |   |   |-- llm_clients/
|   |   |   |   |-- ollama_client.py        # Ollama client
|   |   |   |   |-- perplexity_client.py    # Perplexity client
|   |   |   |   |-- claude_client.py        # Claude client
|   |   |   # --- Other Services ---
|   |   |   |-- position_manager.py         # Position management
|   |   |   |-- settings_service.py         # Settings CRUD
|   |   |   |-- training_store.py           # ML artifact storage
|   |   |   |-- pattern_library.py          # Pattern management
|   |   |   |-- openclaw_bridge_service.py  # OpenClaw bridge
|   |   |   |-- openclaw_db.py              # OpenClaw SQLite database
|   |   |   |-- discord_swarm_bridge.py     # Discord bot bridge
|   |   |   |-- model_pinning.py            # Model versioning
|   |   |
|   |   |-- strategy/
|   |       |-- __init__.py
|   |       |-- backtest.py                 # Backtest framework
|   |
|   |-- tests/
|       |-- __init__.py
|       |-- conftest.py                     # Test fixtures
|       |-- test_api.py                     # API integration tests (151 tests)
|
|-- brain_service/                          # gRPC + Ollama LLM service (PC2 — port 50051)
|   |-- server.py                           # gRPC server
|   |-- ollama_client.py                    # Ollama client wrapper
|   |-- models.py                           # Data models
|   |-- proto/                              # Protocol buffer definitions
|   |-- compile_proto.py                    # Proto compiler
|   |-- requirements.txt
|   |-- README.md
|   |-- .env.example
|
|-- core/                                   # Standalone ML API module
|   |-- api/
|       |-- ml_api.py                       # ML API standalone module
|
|-- frontend-v2/                            # React frontend (Vite, port 3000)
|   |-- Dockerfile
|   |-- package.json
|   |-- package-lock.json
|   |-- index.html
|   |-- nginx.conf
|   |-- vite.config.js
|   |-- .env.example
|   |
|   |-- src/
|       |-- App.jsx                         # Root component + routing (14 routes)
|       |-- main.jsx                        # React entry point
|       |-- index.css                       # Global styles (Tailwind)
|       |-- V3-ARCHITECTURE.md              # Frontend architecture doc
|       |
|       |-- config/
|       |   |-- api.js                      # API base URL + endpoint mappings
|       |
|       |-- hooks/
|       |   |-- useApi.js                   # Central API hook (returns { data, loading, error })
|       |   |-- useSentiment.js             # Sentiment polling hook
|       |   |-- useWebSocket.js             # WebSocket hook (auto-reconnect, channel sub)
|       |
|       |-- services/
|       |   |-- dataSourcesApi.js           # Data sources API client
|       |   |-- openclawService.js          # OpenClaw API client
|       |   |-- websocket.js                # WebSocket connection manager
|       |
|       |-- lib/
|       |   |-- dataSourceIcons.js          # Data source icon mapping
|       |   |-- symbolIcons.js              # Stock symbol icons
|       |
|       |-- types/
|       |   |-- index.ts                    # Shared TypeScript interfaces
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
|       |   |-- ui/                         # Reusable UI primitives
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
|       |-- pages/                          # 14 sidebar route pages
|           |-- AgentCommandCenter.jsx      # /agents — 5 tab files
|           |-- Backtesting.jsx             # /backtest
|           |-- Dashboard.jsx               # /dashboard
|           |-- DataSourcesMonitor.jsx      # /data-sources
|           |-- MLBrainFlywheel.jsx         # /ml-brain
|           |-- MarketRegime.jsx            # /market-regime
|           |-- Patterns.jsx                # /patterns
|           |-- PerformanceAnalytics.jsx    # /performance
|           |-- RiskIntelligence.jsx        # /risk
|           |-- SentimentIntelligence.jsx   # /sentiment
|           |-- Settings.jsx                # /settings
|           |-- SignalIntelligenceV3.jsx    # /signal-intelligence-v3
|           |-- TradeExecution.jsx          # /trade-execution
|           |-- Trades.jsx                  # /trades
|           |-- agent-tabs/                 # Agent Command Center tab files
|               |-- AgentRegistryTab.jsx
|               |-- LiveWiringTab.jsx
|               |-- RemainingTabs.jsx
|               |-- SpawnScaleTab.jsx
|               |-- SwarmOverviewTab.jsx
|
|-- docs/                                   # Project documentation (35+ files)
|   |-- mockups-v3/images/                  # 23 design mockups (source of truth)
|   |-- audits/
|   |   |-- brain_consciousness_audit_2026-03-08.pdf
|   |-- architecture/
|   |   |-- AGENT-SWARM-DESIGN.md
|   |   |-- SECOND-BRAIN-ARCHITECTURE.md
|   |   |-- SYSTEM-ARCHITECTURE.md
|   |   |-- TRADING-ALGORITHM-ARCHITECTURE.md
|   |-- brain/
|   |   |-- API-CONNECTIVITY-REPORT-2026-03-02.md
|   |   |-- CLAUDE-INSTRUCTIONS.md
|   |   |-- CONTEXT.md
|   |   |-- FULL-CODEBASE-AUDIT-2026-03-02.md
|   |-- plans/
|   |   |-- 2026-03-02-stabilize-test-ml-loop.md
|   |   |-- MODEL-COUNCIL-PROMPT.md
|   |   |-- SLACK-TO-EMBODIER-MIGRATION.md
|   |-- research/                           # Trading research documents
|   |-- AGENT-SWARM-ARCHITECTURE-v2.md
|   |-- AI_TWO_PC_CODING_GUIDE.md
|   |-- API-COMPLETE-LIST-2026.md
|   |-- API-KEY-INVENTORY.md
|   |-- AUDIT-2026-03-01-FINAL.md
|   |-- CLEANUP-AND-SETUP-GUIDE.md
|   |-- CLUSTER-NETWORK-SETUP.md
|   |-- CODEBASE-REVIEW-2026-03-04.md
|   |-- COMET-DAILY-PLAYBOOK.md
|   |-- FULL-SYSTEM-AUDIT-2026-03-07.md
|   |-- HARDWARE-SPECS.md
|   |-- INDENTATION-FIX-GUIDE.md
|   |-- INTELLIGENCE-DASHBOARD-REVISION.md
|   |-- MOCKUP-FIDELITY-AUDIT.md
|   |-- NETWORK_TWO_PC_SETUP.md
|   |-- OPENCLAW-IMPLEMENTATION-GUIDE.md
|   |-- STATUS-AND-TODO-2026-02-28.md
|   |-- STATUS-AND-TODO-2026-03-06.md
|   |-- STATUS-AND-TODO-2026-03-07.md
|   |-- SUNDAY-SIGNAL-GENERATION-GUIDE.md
|   |-- SYSTEM-DESIGN-OVERVIEW.md
|   |-- TRADING-SYNC-README.md
|   |-- UI-DESIGN-SYSTEM.md
|
|-- directives/                             # AI directive documents
|   |-- global.md
|   |-- regime_bull.md
|   |-- regime_bear.md
|
|-- scripts/                               # Utility scripts (13 files)
    |-- auto-pull.ps1
    |-- build-desktop.ps1
    |-- build-desktop.sh
    |-- create-shortcut.ps1
    |-- download_mockups.ps1
    |-- fix_indentation.py                 # Batch Python indentation fixer
    |-- fresh-setup.ps1
    |-- install-trading-sync.ps1
    |-- migrate_openclaw.ps1
    |-- migrate_openclaw.sh
    |-- onedrive_sync.py
    |-- setup-auto-sync.ps1
    |-- setup-redis-firewall.ps1
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
11. **Knowledge Layer** - MemoryBank + HeuristicEngine + KnowledgeGraph learn from trade outcomes (`backend/app/knowledge/`)
12. **Version** - Single source of truth: `backend/app/core/config.py` → `APP_VERSION = "4.0.0"`

## Discovery + Trade Pipeline (v4.0.0)

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
  Escalated -> SwarmSpawner -> 32-Agent Council (7 stages) -> council.verdict

EXECUTION:
  council.verdict -> OrderExecutor (real DuckDB stats, real ATR, mock guard) -> Alpaca

LEARNING:
  order.filled -> OutcomeTracker -> MemoryBank + HeuristicEngine + KnowledgeGraph + WeightLearner
```

## Quick Reference: API Endpoints

All backend routes: `http://localhost:8000/api/v1/{service}`

v1/ services: `agents`, `alerts`, `alignment`, `alpaca`, `backtest`, `cluster`, `cns`, `cognitive`, `council`, `data-sources`, `features`, `flywheel`, `llm-health`, `logs`, `market`, `ml-brain`, `openclaw`, `orders`, `patterns`, `performance`, `portfolio`, `quotes`, `risk`, `risk-shield`, `sentiment`, `settings`, `signals`, `status`, `stocks`, `strategy`, `swarm`, `system`, `training`, `youtube-knowledge`

Additional: `http://localhost:8000/api/ingestion/backfill` (POST), `http://localhost:8000/api/ingestion/health` (GET)
