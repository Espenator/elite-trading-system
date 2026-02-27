# Elite Trading System - Backend API

**Last Updated: February 27, 2026**

FastAPI backend serving the Embodier.ai Elite Trading Intelligence System. Provides REST API endpoints for trading signals, order execution, agent management, ML training, backtesting, and real-time WebSocket data.

> **Status: All route files and services CODED. NOT yet tested end-to-end as a running application.**

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (DuckDB planned)
- **HTTP Client**: httpx (async)
- **Broker**: Alpaca Markets (paper + live)
- **Data Sources**: Finviz Elite, yFinance, Unusual Whales, FRED, SEC EDGAR
- **ML**: PyTorch (LSTM with AMP), XGBoost (GPU), scikit-learn
- **Configuration**: pydantic-settings, python-dotenv
- **WebSocket**: FastAPI WebSocket manager

---

## Directory Structure

```
backend/
  app/
    api/
      v1/               # 27+ REST API route files
        agents.py       # Agent management + lifecycle
        alerts.py       # System alerts
        backtest_routes.py  # Strategy backtesting
        data_sources.py # Data source health
        flywheel.py     # ML flywheel metrics
        logs.py         # System logs
        market.py       # Market data + regime
        ml_brain.py     # ML model management
        openclaw.py     # OpenClaw bridge router
        orders.py       # Alpaca order management
        patterns.py     # Pattern/screener queries
        performance.py  # Performance analytics
        portfolio.py    # Portfolio positions + P&L
        quotes.py       # Price and chart data
        risk.py         # Risk metrics + exposure
        risk_shield_api.py  # Risk Governor bridge
        sentiment.py    # Sentiment data
        settings_routes.py  # App settings
        signals.py      # Trading signal CRUD
        status.py       # System health check
        stocks.py       # Finviz screener queries
        strategy.py     # Strategy definitions
        system.py       # System config + /gpu endpoint
        training.py     # ML model training jobs
        youtube_knowledge.py  # YouTube research data
    models/             # SQLAlchemy ORM + LSTM trainer
    modules/
      ml_engine/        # XGBoost GPU trainer
      openclaw/         # OpenClaw swarm modules
    schemas/            # Pydantic request/response models
    services/           # 20+ service files
      alpaca_service.py     # Alpaca broker integration
      backtest_engine.py    # Historical signal backtester
      database.py           # SQLite database layer
      finviz_service.py     # Finviz stock screener
      fred_service.py       # FRED economic data
      kelly_position_sizer.py  # Kelly criterion sizing
      market_data_agent.py  # Market data aggregation
      ml_training.py        # PyTorch LSTM training
      openclaw_bridge_service.py  # OpenClaw bridge (976 lines)
      openclaw_db.py        # OpenClaw SQLite persistence
      sec_edgar_service.py  # SEC EDGAR filings
      signal_engine.py      # Signal scoring engine
      training_store.py     # ML model artifact storage
      unusual_whales_service.py  # Options flow data
      walk_forward_validator.py  # Walk-forward validation
    strategy/           # Trading strategy logic
  jobs/                 # Scheduled/background jobs
  tests/                # Test suite (needs building)
  tools/                # CLI utilities
  main.py              # FastAPI app entry point
  requirements.txt      # Python dependencies
  start_server.py       # Server startup script
```

---

## API Routes

All routes versioned under `/api/v1/`:

| Route | Method | Endpoint | Purpose |
|-------|--------|----------|--------|
| agents | GET/POST | `/api/v1/agents` | Agent list, start/stop lifecycle |
| signals | GET/POST | `/api/v1/signals` | Trading signal CRUD |
| orders | GET/POST | `/api/v1/orders` | Alpaca order management |
| market | GET | `/api/v1/market` | Market data, regime state |
| portfolio | GET | `/api/v1/portfolio` | Positions, P&L |
| risk | GET | `/api/v1/risk` | Risk metrics, exposure |
| backtest | POST | `/api/v1/backtest` | Strategy backtesting |
| ml-brain | GET/POST | `/api/v1/ml-brain` | ML model management |
| performance | GET | `/api/v1/performance` | Performance analytics |
| openclaw | POST/GET | `/api/v1/openclaw/*` | OpenClaw bridge |
| training | POST | `/api/v1/training` | ML training jobs |
| system | GET | `/api/v1/system`, `/gpu` | System + GPU health |
| status | GET | `/api/v1/status` | Health check |

---

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python start_server.py
```

### Required Environment Variables

- `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` (required for trading)
- `FINVIZ_API_KEY` (optional, for screener)
- `GPU_DEVICE` (optional, default: cuda:0)
- `TORCH_MIXED_PRECISION` (optional, default: true)

See `.env.example` for all available settings.

---

## Known Issues (Feb 27, 2026)

- Backend has never been started and tested end-to-end
- `openclaw_bridge_service.py` is a 976-line god module needing split
- `signal_engine.py` scoring too simplistic vs OpenClaw 5-pillar system
- `ml_training.py` LSTM has input_size=4 but system generates 25+ features
- No test suite exists yet
- Database initialization untested