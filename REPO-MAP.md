# Elite Trading System - Repository Map

> Auto-generated reference for AI coding assistants. Last updated: February 28, 2026.
> Run `python map_repo.py` to regenerate, or `python bundle_files.py` to bundle key files.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, DuckDB, SQLAlchemy
- **Frontend**: React 18 (Vite), Lightweight Charts, Tailwind CSS
- **Data Sources**: Alpaca Markets API, Unusual Whales API, FinViz API
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`)
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
|   |   |-- main.py                    # FastAPI app entry point
|   |   |-- websocket_manager.py       # WebSocket broadcast manager
|   |   |
|   |   |-- api/v1/                     # REST API endpoints (15 services)
|   |   |   |-- __init__.py
|   |   |   |-- agents.py              # Agent management
|   |   |   |-- alerts.py              # Alert system
|   |   |   |-- backtest_routes.py     # Backtesting engine
|   |   |   |-- data_sources.py        # Data source status
|   |   |   |-- flywheel.py            # Learning flywheel
|   |   |   |-- logs.py                # System logs
|   |   |   |-- market.py              # Market data
|   |   |   |-- ml_brain.py            # ML brain status
|   |   |   |-- openclaw.py            # OpenClaw integration
|   |   |   |-- orders.py              # Order management
|   |   |   |-- patterns.py            # Pattern detection
|   |   |   |-- performance.py         # Performance metrics
|   |   |   |-- portfolio.py           # Portfolio tracking
|   |   |   |-- quotes.py              # Stock quotes
|   |   |   |-- risk.py                # Risk management
|   |   |   |-- risk_shield_api.py     # Risk shield
|   |   |   |-- sentiment.py           # Sentiment analysis
|   |   |   |-- settings_routes.py     # User settings
|   |   |   |-- signals.py             # Trading signals
|   |   |   |-- status.py              # System status
|   |   |   |-- stocks.py              # Stock data
|   |   |   |-- strategy.py            # Strategy config
|   |   |   |-- system.py              # System health
|   |   |   |-- training.py            # ML training
|   |   |   |-- youtube_knowledge.py   # YouTube insights
|   |   |
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # App configuration
|   |   |
|   |   |-- data/
|   |   |   |-- __init__.py
|   |   |   |-- storage.py             # DuckDB storage layer
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
|   |   |   |-- openclaw/              # OpenClaw multi-agent system
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
|   |   |-- services/                  # Business logic layer
|   |   |   |-- __init__.py
|   |   |   |-- alpaca_service.py      # Alpaca Markets API
|   |   |   |-- backtest_engine.py     # Backtesting logic
|   |   |   |-- database.py            # DB connection + pooling
|   |   |   |-- finviz_service.py      # FinViz API
|   |   |   |-- fred_service.py        # FRED economic data
|   |   |   |-- kelly_position_sizer.py # Kelly criterion sizing
|   |   |   |-- market_data_agent.py   # Market data aggregation
|   |   |   |-- ml_training.py         # ML training pipeline
|   |   |   |-- openclaw_bridge_service.py
|   |   |   |-- openclaw_db.py
|   |   |   |-- sec_edgar_service.py   # SEC filings
|   |   |   |-- signal_engine.py       # Signal generation
|   |   |   |-- training_store.py      # Training data store
|   |   |   |-- unusual_whales_service.py # Unusual Whales API
|   |   |   |-- walk_forward_validator.py # Walk-forward validation
|   |   |
|   |   |-- strategy/
|   |   |   |-- __init__.py
|   |   |   |-- backtest.py            # Backtest framework
|   |
|   |-- tests/
|       |-- __init__.py
|       |-- conftest.py                # Test fixtures
|       |-- test_api.py                # API integration tests
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
|       |   |-- types/
|       |       |-- index.ts           # Shared TypeScript interfaces
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
|       |-- pages/                     # Route pages (14 total)
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

1. **No yfinance** - All market data via Alpaca, Unusual Whales, FinViz APIs
2. **Real API only** - No mock data in production components
3. **useApi hook** - Central data fetching: `useApi('endpoint')` returns `{ data, loading, error }`
4. **WebSocket** - Real-time updates via `websocket.js` service
5. **DuckDB** - Primary analytics database (WAL mode, connection pooling)
6. **OpenClaw** - Multi-agent trading system with 8+ sub-modules
7. **CI** - 146 tests passing (12 test files), GitHub Actions on every push

## Quick Reference: API Endpoints

All backend routes: `http://localhost:8000/api/v1/{service}`

Services: `agents`, `alerts`, `backtest`, `data-sources`, `flywheel`, `logs`, `market`, `ml-brain`, `openclaw`, `orders`, `patterns`, `performance`, `portfolio`, `quotes`, `risk`, `sentiment`, `settings`, `signals`, `status`, `stocks`, `strategy`, `system`, `training`, `youtube-knowledge`
