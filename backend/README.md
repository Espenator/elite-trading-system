# Elite Trading System - Backend API

**Last Updated: March 3, 2026**

FastAPI backend serving the Embodier.ai Elite Trading Intelligence System. Provides REST API endpoints for trading signals, order execution, agent management, ML training, backtesting, and real-time WebSocket data.

> **Status: All route files and services coded. 146 tests passing across 12 test files. CI green.**

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: DuckDB (via `app/data/storage.py` and `app/services/database.py`)
- **HTTP Client**: httpx (async)
- **Broker**: Alpaca Markets (paper + live via alpaca-py)
- **Data Sources**: Finviz Elite, Unusual Whales, FRED, SEC EDGAR, Alpaca Markets
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

## Known Issues (March 3, 2026)

- Backend needs first end-to-end runtime test (`uvicorn app.main:app --reload`)
- `openclaw_bridge_service.py` is a large module needing split
- `signal_engine.py` scoring may need alignment with OpenClaw 5-pillar system
- torch/PyTorch removed from requirements.txt -- LSTM inference code may fail

**Critical**: Run `uvicorn app.main:app` locally before committing any backend changes.

---

## Alignment Engine (Constitutive Design Patterns)

The Alignment Engine enforces 6 constitutive design patterns that govern all trading decisions. Every trade must pass a preflight alignment check before execution.

### Backend Files

| File | Purpose |
|------|--------|
| `backend/app/api/v1/alignment.py` | FastAPI router: state, patterns, audit, constitution, drift, preflight |

### Frontend Files

| File | Purpose |
|------|--------|
| `frontend-v2/src/pages/AlignmentEngine.jsx` | Full alignment dashboard (embedded in Settings.jsx Alignment tab + TradeExecution.jsx governance card, no own route) |
| `frontend-v2/src/components/ui/AlignmentPreflight.jsx` | Reusable preflight card component |
| `frontend-v2/src/pages/TradeExecution.jsx` | Preflight integrated into trade form |
| `frontend-v2/src/pages/Settings.jsx` | Settings page with Alignment tab (embeds AlignmentEngine component) |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/alignment/state` | Current alignment state + drift score |
| GET | `/api/v1/alignment/patterns` | List all 6 design patterns + status |
| GET | `/api/v1/alignment/audit` | Audit log entries |
| GET | `/api/v1/alignment/constitution` | Current constitution text/rules |
| GET | `/api/v1/alignment/drift-history` | Historical drift scores |
| POST | `/api/v1/alignment/preflight` | Run preflight check for a trade |
| GET | `/api/v1/alignment/verdicts` | Recent preflight verdicts |

### The 6 Constitutive Design Patterns

1. **Constitutional Constraint** — Hard limits defined in constitution (max position, drawdown, etc.)
2. **Drift Detection** — Continuous monitoring of system behavior vs. intended alignment
3. **Preflight Gate** — Every trade must pass all patterns before execution
4. **Audit Trail** — Immutable log of every alignment decision
5. **Pattern Registry** — Central registry of all active patterns and their health
6. **Graceful Degradation** — System reduces capability rather than violating alignment

---

## Frontend Pages & Routes

| Sidebar Section | Page | Route | File |
|----------------|------|-------|------|
| COMMAND | Intelligence Dashboard | `/dashboard` | `Dashboard.jsx` |
| COMMAND | Agent Command Center | `/agents` `/agents/:tab` | `AgentCommandCenter.jsx` |
| INTELLIGENCE | Signal Intelligence | `/signals` | `Signals.jsx` |
| INTELLIGENCE | Sentiment Intelligence | `/sentiment` | `SentimentIntelligence.jsx` |
| INTELLIGENCE | Data Sources Manager | `/data-sources` | `DataSourcesMonitor.jsx` |
| INTELLIGENCE | Signal Intelligence V3 | `/signal-intelligence-v3` | `SignalIntelligenceV3.jsx` |
| ML & ANALYSIS | ML Brain & Flywheel | `/ml-brain` | `MLBrainFlywheel.jsx` |
| ML & ANALYSIS | Screener & Patterns | `/patterns` | `Patterns.jsx` |
| ML & ANALYSIS | Backtesting Lab | `/backtest` | `Backtesting.jsx` |
| ML & ANALYSIS | Performance Analytics | `/performance` | `PerformanceAnalytics.jsx` |
| ML & ANALYSIS | Market Regime | `/market-regime` | `MarketRegime.jsx` |
| EXECUTION | Active Trades | `/trades` | `Trades.jsx` |
| EXECUTION | Risk Intelligence | `/risk` | `RiskIntelligence.jsx` |
| EXECUTION | Trade Execution | `/trade-execution` | `TradeExecution.jsx` |
| EXECUTION | Alignment Engine | `/alignment-engine` | `AlignmentEngine.jsx` |
| SYSTEM | Settings | `/settings` | `Settings.jsx` |

---

## Smoke Tests (Prove It's Real)

Run these after `start.bat` or `uvicorn app.main:app`:

```bash
# 1. Swagger UI — verify alignment tag appears
curl -s http://localhost:8000/openapi.json | python -m json.tool | findstr alignment

# 2. Preflight — verify 200 + correct schema
curl -s -X POST http://localhost:8000/api/v1/alignment/preflight \
  -H "Content-Type: application/json" \
  -d '{"symbol":"SPY","side":"buy","quantity":1,"strategy":"manual"}'
# Expected: {"allowed":true,"blockedBy":null,"summary":"BUY 1.0 SPY...",...}

# 3. Blocked trade — verify blocked response
curl -s -X POST http://localhost:8000/api/v1/alignment/preflight \
  -H "Content-Type: application/json" \
  -d '{"symbol":"SPY","side":"buy","quantity":99999,"strategy":""}'
# Expected: {"allowed":false,"blockedBy":"Position Size Limit",...}

# 4. All GET endpoints return 200
for ep in state patterns audit constitution drift-history verdicts; do
  echo "$ep: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/alignment/$ep)";
done

# 5. Execution gate — verify blocked order returns 403
curl -s -X POST http://localhost:8000/api/v1/orders/advanced \
  -H "Content-Type: application/json" \
  -d '{"symbol":"SPY","side":"buy","qty":"99999"}'
# Expected: 403 {"detail":{"error":"ALIGNMENT_BLOCKED",...}}
```

**UI Network Tab check:** Open DevTools > Network, navigate to `/settings` (Alignment tab) or `/trade-execution`, verify all 5 alignment API fetches return 200.

---

## Execution-Path Enforcing Gate

Every order submitted via `POST /api/v1/orders/advanced` now runs the alignment preflight **before** reaching the Alpaca broker. This gate:
- Cannot be bypassed by calling the endpoint directly
- Returns HTTP 403 with `ALIGNMENT_BLOCKED` error if preflight fails
- Logs the verdict for audit trail
- Lives in `backend/app/api/v1/orders.py` lines 58-79

---

## Verdict Persistence

Verdicts and audit entries are persisted to `data/alignment/verdicts.jsonl` and `data/alignment/audit.jsonl` (JSONL format). Data survives server restarts. Override the directory with `ALIGNMENT_DATA_DIR` env var.

---

## Contract Tests

Run: `cd backend && pytest tests/test_alignment_contract.py -v`

| Test | What it locks |
|------|---------------|
| `test_preflight_returns_200` | Endpoint exists, not 404 |
| `test_preflight_schema_has_required_top_keys` | {allowed, blockedBy, summary, checks, timestamp} |
| `test_preflight_allowed_is_bool` | `allowed` is bool, not string |
| `test_preflight_checks_is_list_of_dicts` | Each check has {name, passed} |
| `test_preflight_timestamp_is_iso_string` | Parseable ISO 8601 |
| `test_preflight_allowed_trade_passes` | Small trade = allowed |
| `test_preflight_blocked_trade_returns_blocker` | Oversized = blocked + reason |
| `test_preflight_summary_contains_symbol` | UI gets context |
| `test_preflight_six_checks` | All 6 design patterns run |
| `test_alignment_get_endpoints_return_200` | All 6 GET endpoints alive |


---

## Frontend UI Architecture (14 Sidebar Pages)

> See `frontend-v2/src/V3-ARCHITECTURE.md` for complete details.

| # | Section | Page | Route |
|---|---------|------|-------|
| 1 | COMMAND | Dashboard | `/` |
| 2 | COMMAND | Agent Command Center | `/agents` |
| 3 | INTELLIGENCE | Sentiment Intelligence | `/sentiment` |
| 4 | INTELLIGENCE | Data Sources Monitor | `/data-sources` |
| 5 | INTELLIGENCE | Signal Intelligence | `/signal-intelligence-v3` |
| 6 | ML & ANALYSIS | ML Brain & Flywheel | `/ml-brain` |
| 7 | ML & ANALYSIS | Screener & Patterns | `/patterns` |
| 8 | ML & ANALYSIS | Backtesting Lab | `/backtesting` |
| 9 | ML & ANALYSIS | Performance Analytics | `/performance` |
| 10 | ML & ANALYSIS | Market Regime | `/market-regime` |
| 11 | EXECUTION | Active Trades | `/trades` |
| 12 | EXECUTION | Risk Intelligence | `/risk` |
| 13 | EXECUTION | Trade Execution | `/trade-execution` |
| 14 | SYSTEM | Settings | `/settings` |

**Agent Command Center Sub-Pages (8 tabs):** Overview, Agents, Swarm Control, Candidates, LLM Flow, Brain Map, Leaderboard, Blackboard

**Settings Sub-Tabs (11):** Profile, API Keys, Trading, Risk, AI/ML, Agents, Data Sources, Notifications, Appearance, Audit Log, Alignment (embeds AlignmentEngine)