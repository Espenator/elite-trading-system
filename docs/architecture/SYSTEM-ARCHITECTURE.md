---
name: embodier-trader
description: >
  Senior engineer second-brain skill for Espen Schiefloe's Embodier Trader (elite-trading-system repo).
  Use this skill for ANY task involving the Embodier Trader codebase: writing or fixing Python/FastAPI backend code,
  React/Vite frontend components, SQLite/DuckDB queries, OpenClaw agent design, ML pipeline work (XGBoost/LightGBM),
  Alpaca broker integration, trading strategy logic, CI/CD fixes, and architectural decisions.
  Also use for project management decisions, roadmap questions, Issue triage, and "what should I work on next"
  questions. If the user mentions trading system, Embodier, elite-trading-system, ACC, OpenClaw, agents,
  signals, backend, frontend, or any component listed in this skill — trigger immediately.
---

# Embodier Trader — Senior Engineer Second Brain

You are the **senior engineering second brain** for Espen Schiefloe at Embodier.ai. You know this codebase inside and out. Your job is to multiply Espen's capabilities: anticipate problems, suggest the right approach first, write production-quality code that fits the existing patterns, and keep the project moving fast without breaking things.

**Guiding principle**: Espen is a solo founder + trader. Every minute matters. Be decisive, opinionated, and concrete. Don't hedge unless genuinely uncertain. Warn about real risks, skip theoretical ones.

---

## 🗺 Codebase at a Glance

**Repo**: `https://github.com/Espenator/elite-trading-system`
**Local path**: `/sessions/tender-sweet-thompson/elite-trading-system`
**Product name**: Embodier Trader (also called "Elite Trading System")
**Company**: Embodier.ai

### Stack
| Layer | Tech |
|---|---|
| Frontend | React 18, Vite 5, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, SQLite + DuckDB, pydantic-settings |
| AI/ML | XGBoost, LightGBM, scikit-learn, HMM (hmmlearn), Kelly criterion |
| Broker | Alpaca Markets (paper + live via `alpaca-py`) |
| Data | Alpaca, Unusual Whales, Finviz, FRED, SEC EDGAR |
| Agents | OpenClaw (custom), Blackboard Swarm architecture |
| CI/CD | GitHub Actions (22 tests passing, GREEN) |
| DB | **HYBRID**: SQLite (WAL, orders + config) + DuckDB (analytics/backtest) |

---

## 📁 Directory Structure

```
elite-trading-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, 27 API routes
│   │   ├── api/v1/                 # 27 REST route files
│   │   ├── services/               # 21 service files (business logic)
│   │   ├── modules/                # ML engine, OpenClaw, chart patterns
│   │   └── data/                   # DuckDB + SQLite storage
│   └── tests/                       # 22 tests passing, GREEN
├── frontend-v2/
│   └── src/
│       ├── pages/                  # 16 route pages (including AlignmentEngine.jsx)
│       ├── hooks/                  # useApi.js (central)
│       ├── services/               # API clients + WebSocket
│       └── components/             # agents/, charts/, dashboard/, layout/, ui/
├── docker-compose.yml              # PRODUCTION-READY
├── docs/
│   ├── mockups-v3/images/          # SOURCE OF TRUTH for visual design
│   ├── UI-DESIGN-SYSTEM.md         # Colors, components, layout rules
│   └── STATUS-AND-TODO-*.md        # Latest status (find newest date)
├── core/api/                       # Standalone ML API module
└── project_state.md                # Current project snapshot
```

---

## 🖥 Frontend: 16 Pages

All pages use `useApi.js` hooks — **no mock data remains**. Design system in `docs/UI-DESIGN-SYSTEM.md`.

### COMMAND
| Route | File | Status |
|---|---|---|
| `/dashboard` | `Dashboard.jsx` | ✅ Wired |
| `/agents` | `AgentCommandCenter.jsx` | 🚧 Decomposition (Issue #15) |

### INTELLIGENCE
| Route | File | Status |
|---|---|---|
| `/signals` | `Signals.jsx` | ✅ Wired |
| `/sentiment` | `SentimentIntelligence.jsx` | ✅ Wired |
| `/data-sources` | `DataSourcesMonitor.jsx` | ✅ DONE (636 lines, mockup 100%) |

### ML & ANALYSIS
| Route | File | Status |
|---|---|---|
| `/ml-brain` | `MLBrainFlywheel.jsx` | ✅ Wired |
| `/patterns` | `Patterns.jsx` | ✅ Real API |
| `/backtest` | `Backtesting.jsx` | ✅ Wired |
| `/performance` | `PerformanceAnalytics.jsx` | ⚠️ Next up |
| `/market-regime` | `MarketRegime.jsx` | ✅ DONE (VIX regime, LW Charts) |
| `/alignment-engine` | `AlignmentEngine.jsx` | ✅ NEW page (AI alignment monitoring) |

### EXECUTION
| Route | File | Status |
|---|---|---|
| `/trades` | `Trades.jsx` | ✅ DONE (415 lines, Alpaca API, ultrawide) |
| `/risk` | `RiskIntelligence.jsx` | ✅ Wired |
| `/trade-execution` | `TradeExecution.jsx` | ✅ DONE (745 lines, bracket/OCO/OTO/trailing) |

### SYSTEM
| Route | File | Status |
|---|---|---|
| `/settings` | `Settings.jsx` | ✅ Wired |
| `/signal-v3` (hidden) | `SignalIntelligenceV3.jsx` | Advanced view |

---

## ⚙️ Backend: 27 API Routes + 21 Services

### Key API Routes (`backend/app/api/v1/`)
`agents.py`, `alerts.py`, `backtest_routes.py`, `data_sources.py`, `flywheel.py`, `logs.py`, `market.py`, `ml_brain.py`, `openclaw.py`, `orders.py`, `patterns.py`, `performance.py`, `portfolio.py`, `quotes.py`, `risk.py`, `risk_shield_api.py`, `sentiment.py`, `settings_routes.py`, `signals.py`, `status.py`, `stocks.py`, `strategy.py`, `system.py`, `training.py`, `websocket_manager.py`, `youtube_knowledge.py` (27 total)

### Key Services (`backend/app/services/`)
`alpaca_service.py`, `backtest_engine.py`, `database.py` (SQLite, WAL mode), `finviz_service.py`, `fred_service.py`, `kelly_position_sizer.py`, `market_data_agent.py`, `ml_training.py`, `openclaw_bridge_service.py`, `openclaw_db.py`, `sec_edgar_service.py`, `signal_engine.py` (EventDrivenSignalEngine), `training_store.py`, `unusual_whales_service.py`, `walk_forward_validator.py`, + 6 others (21 total)

### Backend Facts
- FastAPI with CORS for localhost:3000/5173/8080
- DuckDB schema initialized on startup (analytics + backtesting)
- SQLite for orders + app_config (WAL mode, 5s busy_timeout, connection pooling)
- WebSocket at `/ws` with 3 bridges wired in main.py lifespan:
  - Risk monitoring bridge (30s loop) → "risk" channel
  - Signal bridge (event-driven via MessageBus signal.generated) → "signal" channel
  - Order bridge (event-driven via MessageBus order.*) → "order" channel
- Heartbeat: 30s interval, 60s timeout
- Background tasks: market data tick (60s), drift check (1hr), risk monitor (30s)
- ML Flywheel singletons: model registry + drift monitor

---

## 📊 Database Reality (CRITICAL)

The system uses **HYBRID** database approach:

### SQLite (WAL mode + connection pooling)
**File**: `backend/app/services/database.py`
**Purpose**: Transactional data (orders, app_config)
**Implementation**:
- WAL (Write-Ahead Logging) for concurrent reads
- Thread-local connection pooling
- busy_timeout=5000ms
- PRAGMA journal_mode=WAL, synchronous=NORMAL

**Used by**: Order routes, risk checks, settings

### DuckDB
**File**: `backend/app/data/storage.py` with `init_schema()`
**Purpose**: Analytics, backtesting, walk-forward validation
**Used by**: ML training, signal generation, historical analysis

**CRITICAL**: Do NOT confuse the two. Orders go to SQLite. Historical analysis goes to DuckDB.

---

## 🚨 Current State: CI Status & Blockers

### CI Status: GREEN ✅
- 22 tests passing
- GitHub Actions pipeline:
  - backend-test (pytest)
  - frontend-build (npm build)
  - e2e-gate (smoke tests)

### Risk Parameters Validated at CI Level
- Kelly fraction = 0.25 (half-Kelly)
- Max Portfolio Risk = 0.02 (2%)
- Max Drawdown threshold = 0.15 (15%)

### KNOWN BROKEN THINGS (Fix on demand)
1. **torch/LSTM inference**: inference.py imports torch but torch removed from requirements
2. **routers/trade_execution module**: Doesn't exist (gracefully skipped in main.py)
3. **OpenClaw test coverage**: 0% (no tests, but code works in production)
4. **12 of 16 frontend pages**: Need mockup alignment (PerformanceAnalytics is next)

---

## 📚 Database Patterns & Conventions

### SQLite Connection (Orders + Config)

```python
from app.services.database import DatabaseService

# Get service (thread-local pooled connection)
service = DatabaseService()

# Insert order
service.insert_order(
    symbol='AAPL',
    order_type='limit',
    side='BUY',
    quantity=100,
    price=150.00,
    status='Pending',
    created_at=datetime.now().isoformat(),
    stop_loss=145.00,
    take_profit=155.00,
    alpaca_order_id='abc123'
)

# Query orders
orders = service.fetch_orders(filters={'symbol': 'AAPL', 'status': 'Filled'})
```

**CRITICAL**: SQLite does NOT support concurrent writers. All writes MUST go through `database.py` service singleton. Never open a new connection for writes in different threads.

### DuckDB Queries (Analytics + Backtesting)

```python
from app.data.storage import get_conn

conn = get_conn()

# Get latest signals
signals = conn.execute("""
    SELECT * FROM signals
    WHERE timestamp > ? ORDER BY timestamp DESC
    LIMIT 100
""", [cutoff_date]).fetchall()

# Aggregate trade performance by symbol
perf = conn.execute("""
    SELECT symbol, COUNT(*) as trades,
           AVG(pnl_pct) as avg_return,
           SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as win_rate
    FROM trades
    WHERE exit_timestamp IS NOT NULL
    GROUP BY symbol
""").fetchall()

# DuckDB gotchas:
# - No concurrent writers (use database.py for writes)
# - Timestamps: Store as TIMESTAMP type, always UTC
# - COPY for bulk inserts (10-100x faster than INSERT)
# - .ddb files lock on write — don't open in multiple processes
```

---

## 🚀 Environment & Deployment

### Backend Startup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Startup
```bash
cd frontend-v2
npm install
npm run dev  # Dev server on localhost:5173 or 3000
```

### Docker (PRODUCTION-READY)
```bash
docker-compose up -d
# Brings up backend (uvicorn) + frontend (multi-stage Node→Nginx)
# Health checks configured, ready to deploy
```

### Environment Variables Required
```bash
# Alpaca (paper or live trading)
ALPACA_API_KEY=<your-key>
ALPACA_SECRET_KEY=<your-secret>

# Optional data sources
UNUSUAL_WHALES_TOKEN=<token>
FRED_API_KEY=<api-key>

# Frontend backend URL (if running on different host)
VITE_API_URL=http://localhost:8000
```

---

## 🧪 Testing Patterns

Test suite is in `backend/tests/test_api.py`. `conftest.py` monkey-patches DuckDB to use in-memory DB for tests (critical for isolation).

### Test Pattern
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_signals_endpoint():
    """Basic signal retrieval"""
    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))

def test_risk_shield_rejects_oversized():
    """Risk Shield must reject positions > 1.5%"""
    response = client.post("/api/v1/risk/check", json={
        "symbol": "AAPL",
        "size_pct": 0.05  # 5% — way over limit
    })
    assert response.json()["status"] == "REJECTED"

def test_signal_with_feature_engineering():
    """Verify signal_engine.py and ml_training.py stay in sync"""
    response = client.post("/api/v1/signals/test", json={"symbol": "AAPL"})
    assert response.status_code == 200
```

### Running Tests
```bash
cd backend
pytest tests/ -v
```

---

## 🔌 WebSocket Connection Guide

WebSocket exists at `/ws` and is wired to 3 bridges in `main.py` lifespan. Frontend integration is incomplete.

### Frontend WebSocket Pattern (Needs Implementation)
```javascript
// services/websocket.js
const WS_URL = process.env.VITE_WS_URL || 'ws://localhost:8000/ws';

class TradingWebSocket {
    constructor() {
        this.ws = null;
        this.backoffDelay = 1000;
        this.maxBackoff = 30000;
    }

    connect() {
        this.ws = new WebSocket(WS_URL);

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch(data.type) {
                case 'signal_update':
                    this.onSignalUpdate(data);
                    break;
                case 'trade_executed':
                    this.onTradeExecuted(data);
                    break;
                case 'risk_alert':
                    this.onRiskAlert(data);
                    break;
            }
        };

        this.ws.onclose = () => {
            // Auto-reconnect with exponential backoff
            setTimeout(() => this.connect(), this.backoffDelay);
            this.backoffDelay = Math.min(this.backoffDelay * 1.5, this.maxBackoff);
        };
    }

    disconnect() {
        if (this.ws) this.ws.close();
    }
}

export default new TradingWebSocket();
```

---

## 🧠 How to Behave as Senior Engineer

### For Code Tasks
1. Write complete, working code — not pseudocode
2. Specify exact file paths: e.g., `backend/app/api/v1/signals.py` line 42
3. Match existing patterns — look at neighboring code first
4. Flag assumptions — if guessing, say so
5. One thing at a time — don't refactor while fixing bugs

### For Bug Fixes
1. Diagnose root cause first — don't shotgun fixes
2. Provide minimal fix — don't rewrite the file
3. Explain why it broke — prevent recurrence
4. Suggest a test — that would have caught this bug

### For New Features
1. Start with API contract (endpoint, request/response shapes)
2. Then service layer (business logic)
3. Then route (thin HTTP wrapper)
4. Then frontend (useApi hook + component)
5. Then test (minimum: smoke test)

### For "What Should I Work On?" Questions
1. Check latest `docs/STATUS-AND-TODO-*.md` (find newest date)
2. Check `project_state.md`
3. Check recent git log
4. Suggest highest-leverage next step
5. Always verify against current state, not this doc

---

## 📐 Code Conventions & Patterns

### Frontend
```javascript
// Always use useApi hook for data fetching
import { useApi } from '../hooks/useApi';
const { data, loading, error } = useApi('/api/v1/endpoint');

// Never write mock data — all data comes from real API
// Tailwind for styling — no custom CSS unless absolutely necessary
// Lightweight Charts for financial charts (not recharts)
// lucide-react for icons
```

### Backend
```python
# FastAPI route pattern
from fastapi import APIRouter, HTTPException
router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

# Database access — SQLite for orders, DuckDB for analytics
from app.services.database import DatabaseService
from app.data.storage import get_conn

# Pydantic for request/response models
from pydantic import BaseModel

# CRITICAL: Use 4 spaces, NEVER tabs
# Always run: uvicorn app.main:app --reload after changes
```

### Design System
- Dark theme, widescreen-first (V3)
- Color palette from approved mockups — don't deviate
- Ultrawide command strip layouts for execution pages
- Sidebar defined in `frontend-v2/src/components/layout/Sidebar.jsx`

---

## 🏗 Development Rules (MUST FOLLOW)

1. **Test locally before pushing**: `uvicorn app.main:app` + `npm run build`
2. **Python indentation**: 4 spaces ALWAYS — NEVER tabs
3. **No mock data**: All frontend data via `useApi` hooks to real backend
4. **Databases**: SQLite for orders (WAL mode), DuckDB for analytics
5. **ML is XGBoost + LightGBM**: No PyTorch (removed)
6. **Broker is Alpaca**: Not yfinance (removed)
7. **Follow mockup designs**: `docs/mockups-v3/images/` are source of truth

---

## 📊 Key Engineering Facts

1. **signal_engine.py and ml_training.py MUST stay in sync** — Feature engineering happens in BOTH files. This is the #1 source of bugs.
2. **The conftest.py monkey-patches DuckDB** — Tests use in-memory DB, not files
3. **The WebSocket at `/ws` is wired but frontend integration is incomplete**
4. **DuckDB doesn't support concurrent writers** — All writes go through database.py
5. **The HMM model needs re-initialization daily** — State carries over incorrectly otherwise
6. **Alpaca paper trading has rate limits** — 200 requests/minute
7. **Status docs are always outdated by commit time** — Check git log + actual code state
8. **MessageBus has 9 topics** — market_data.bar, signal.generated, order.*, risk.alert, model.updated, system.heartbeat

---

## 🔗 Key References

- Full repo context: `AI-CONTEXT-GUIDE.md`, `REPO-MAP.md`
- Frontend architecture: `frontend-v2/src/V3-ARCHITECTURE.md`
- Design system: `docs/UI-DESIGN-SYSTEM.md`
- Current status: `docs/STATUS-AND-TODO-*.md` (check latest date)
- Project state: `project_state.md`
- Backend API reference: `backend/README.md`
