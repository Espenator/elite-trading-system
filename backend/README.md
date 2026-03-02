# Elite Trading System - Backend API

**Last Updated: February 28, 2026**

FastAPI backend serving the Embodier.ai Elite Trading Intelligence System. Provides REST API endpoints for trading signals, order execution, agent management, ML training, backtesting, and real-time WebSocket data.

> **Status: All route files and services CODED. NOT yet tested end-to-end. CI FAILING due to IndentationErrors in multiple api/v1/ files (tab/space mixing from AI-assisted commits).**

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: DuckDB (via `app/data/storage.py` and `app/services/database.py`)
- **HTTP Client**: httpx (async)
- **Broker**: Alpaca Markets (paper + live via alpaca-py)
- **Data Sources**: Finviz Elite, yFinance, Unusual Whales, FRED, SEC EDGAR
- **ML**: XGBoost, scikit-learn, hmmlearn (torch/PyTorch was removed from requirements.txt)
- **Configuration**: pydantic-settings, python-dotenv
- **WebSocket**: FastAPI WebSocket manager

---

## Directory Structure

```
backend/
  app/
    api/
      v1/                  # 25 REST API route files
        agents.py          # Agent management + lifecycle
        alerts.py          # System alerts
        backtest_routes.py # Strategy backtesting
        data_sources.py    # Data source health
        flywheel.py        # ML flywheel metrics
        logs.py            # System logs
        market.py          # Market data + regime
        ml_brain.py        # ML model management
        openclaw.py        # OpenClaw bridge router
        orders.py          # Alpaca order management
        patterns.py        # Pattern/screener queries
        performance.py     # Performance analytics
        portfolio.py       # Portfolio positions + P&L
        quotes.py          # Price and chart data
        risk.py            # Risk metrics + exposure
        risk_shield_api.py # Risk Governor bridge
        sentiment.py       # Sentiment data
        settings_routes.py # App settings
        signals.py         # Trading signal CRUD
        status.py          # System health check
        stocks.py          # Finviz screener queries
        strategy.py        # Strategy definitions
        system.py          # System config + /gpu endpoint
        training.py        # ML model training jobs
        youtube_knowledge.py # YouTube research data
    core/                  # Config, settings
    data/                  # DuckDB storage layer
    models/                # LSTM trainer, inference
    modules/
      ml_engine/           # XGBoost trainer, drift detector, model registry
      openclaw/            # OpenClaw swarm modules
    schemas/               # Pydantic request/response models
    services/              # 15 service files (see below)
      alpaca_service.py    # Alpaca broker integration
      backtest_engine.py   # Historical signal backtester
      database.py          # DuckDB/SQLite database layer
      finviz_service.py    # Finviz stock screener
      fred_service.py      # FRED economic data
      kelly_position_sizer.py # Kelly criterion sizing
      market_data_agent.py # Market data aggregation
      ml_training.py       # LSTM/XGBoost training
      openclaw_bridge_service.py # OpenClaw bridge
      openclaw_db.py       # OpenClaw SQLite persistence
      sec_edgar_service.py # SEC EDGAR filings
      signal_engine.py     # Signal scoring engine
      training_store.py    # ML model artifact storage
      unusual_whales_service.py # Options flow data
      walk_forward_validator.py # Walk-forward validation
    strategy/              # Trading strategy logic
    main.py                # FastAPI app entry point
    websocket_manager.py   # WebSocket connection manager
  tests/
    conftest.py            # Test fixtures
    test_api.py            # API tests (minimal)
  requirements.txt         # Python dependencies
  start_server.py          # Server startup script
  Dockerfile               # Docker build
```

---

## API Routes

All routes versioned under `/api/v1/`:

| Route | Method | Endpoint | Purpose |
|---|---|---|---|
| agents | GET/POST | `/api/v1/agents` | Agent list, start/stop lifecycle |
| signals | GET | `/api/v1/signals` | Trading signals from LSTM model |
| orders | GET/POST | `/api/v1/orders` | Alpaca order management |
| market | GET | `/api/v1/market` | Market data, regime state |
| portfolio | GET | `/api/v1/portfolio` | Positions, P&L, Kelly metrics |
| risk | GET | `/api/v1/risk` | Risk metrics, exposure, drawdown |
| backtest | POST | `/api/v1/backtest` | Strategy backtesting |
| ml-brain | GET/POST | `/api/v1/ml-brain` | ML model management |
| performance | GET | `/api/v1/performance` | Performance analytics |
| openclaw | POST/GET | `/api/v1/openclaw/*` | OpenClaw bridge |
| training | POST | `/api/v1/training` | ML training jobs |
| system | GET | `/api/v1/system` | System + GPU health |
| status | GET | `/api/v1/status` | Health check |
| alerts | GET | `/api/v1/alerts` | System alerts |
| data-sources | GET | `/api/v1/data-sources` | Data source health |
| flywheel | GET | `/api/v1/flywheel` | ML flywheel metrics |
| logs | GET | `/api/v1/logs` | System logs |
| patterns | GET | `/api/v1/patterns` | Pattern/screener |
| quotes | GET | `/api/v1/quotes` | Price data |
| risk-shield | GET/POST | `/api/v1/risk-shield` | Emergency risk controls |
| sentiment | GET | `/api/v1/sentiment` | Sentiment aggregation |
| settings | GET/PUT | `/api/v1/settings` | App settings |
| stocks | GET | `/api/v1/stocks` | Finviz screener |
| strategy | GET | `/api/v1/strategy` | Strategy definitions |
| youtube | GET | `/api/v1/youtube` | YouTube research |

---

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
cp .env.example .env    # Edit .env with your API keys
python start_server.py
```

### Required Environment Variables

- `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` (required for trading)
- `FINVIZ_API_KEY` (optional, for screener)
- `TRADING_MODE` (paper or live, default: paper)

See `.env.example` for all available settings.

---

## Known Issues (Feb 28, 2026)

- **IndentationErrors** in multiple api/v1/ files (signals.py, possibly others) -- tab/space mixing from AI-assisted commits pushed without local testing
- Backend has never been started and tested end-to-end
- `openclaw_bridge_service.py` is a large module needing split
- `signal_engine.py` scoring too simplistic vs OpenClaw 5-pillar system
- `ml_training.py` has input_size mismatch with actual feature count
- Test suite is minimal (1 test file)
- Database initialization untested
- torch/PyTorch removed from requirements.txt -- LSTM inference code may fail

**Critical**: Run `uvicorn app.main:app` locally before committing any backend changes.

---

## Alignment Engine (Constitutive Design Patterns)

The Alignment Engine enforces 6 constitutive design patterns that govern all trading decisions. Every trade must pass a preflight alignment check before execution.

### Backend Files

| File | Purpose |
|------|--------|
| `core/alignment/constitution.py` | Core constitution rules + drift detection |
| `core/alignment/preflight.py` | Pre-trade alignment check (all 6 patterns) |
| `core/alignment/audit_logger.py` | Immutable alignment audit trail |
| `core/alignment/patterns.py` | Pattern registry + status tracking |
| `app/api/v1/alignment_api.py` | REST endpoints for alignment engine |
| `app/services/alignment_service.py` | Service layer wiring patterns together |

### Frontend Files

| File | Purpose |
|------|--------|
| `frontend-v2/src/pages/AlignmentEngine.jsx` | Full dashboard: state, patterns, drift, constitution, audit |
| `frontend-v2/src/components/ui/AlignmentPreflight.jsx` | Reusable preflight card component |
| `frontend-v2/src/pages/TradeExecution.jsx` | Preflight integrated into trade form |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/alignment/state` | Current alignment state + drift score |
| GET | `/api/alignment/patterns` | List all 6 design patterns + status |
| GET | `/api/alignment/audit` | Audit log entries |
| GET | `/api/alignment/constitution` | Current constitution text/rules |
| GET | `/api/alignment/drift-history` | Historical drift scores |
| POST | `/api/alignment/preflight` | Run preflight check for a trade |

### The 6 Constitutive Design Patterns

1. **Constitutional Constraint** — Hard limits defined in constitution (max position, drawdown, etc.)
2. **Drift Detection** — Continuous monitoring of system behavior vs. intended alignment
3. **Preflight Gate** — Every trade must pass all patterns before execution
4. **Audit Trail** — Immutable log of every alignment decision
5. **Pattern Registry** — Central registry of all active patterns and their health
6. **Graceful Degradation** — System reduces capability rather than violating alignment
