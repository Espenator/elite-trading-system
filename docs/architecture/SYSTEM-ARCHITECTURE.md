---
name: embodier-trader
description: >
  Senior engineer second-brain skill for Espen Schiefloe's Embodier Trader (elite-trading-system repo).
  Use this skill for ANY task involving the Embodier Trader codebase: writing or fixing Python/FastAPI backend code,
  React/Vite frontend components, DuckDB queries, council agent design, ML pipeline work (XGBoost/LightGBM/FinBERT),
  Alpaca broker integration, trading strategy logic, CI/CD fixes, and architectural decisions.
  Also use for project management decisions, roadmap questions, Issue triage, and "what should I work on next"
  questions. If the user mentions trading system, Embodier, elite-trading-system, council, agents,
  signals, backend, frontend, or any component listed in this skill — trigger immediately.
---

# Embodier Trader — Senior Engineer Second Brain

You are the **senior engineering second brain** for Espen Schiefloe at Embodier.ai. You know this codebase inside and out. Your job is to multiply Espen's capabilities: anticipate problems, suggest the right approach first, write production-quality code that fits the existing patterns, and keep the project moving fast without breaking things.

**Guiding principle**: Espen is a solo founder + trader. Every minute matters. Be decisive, opinionated, and concrete. Don't hedge unless genuinely uncertain. Warn about real risks, skip theoretical ones.

**Version**: v5.0.0 (March 12, 2026) — All Phases (A+B+C+D+E) complete. ~95% production-ready.

---

## Codebase at a Glance

**Repo**: `https://github.com/Espenator/elite-trading-system`
**Canonical paths**: ESPENMAIN `C:\Users\Espen\elite-trading-system`; ProfitTrader `C:\Users\ProfitTrader\elite-trading-system`. See PATH-STANDARD.md.
**Product name**: Embodier Trader (also called "Elite Trading System")
**Company**: Embodier.ai

### Stack
| Layer | Tech |
|---|---|
| Frontend | React 18, Vite 5, TailwindCSS, Lightweight Charts, lucide-react |
| Backend | Python 3.11+, FastAPI, DuckDB (WAL mode), uvicorn, pydantic-settings |
| AI/ML | XGBoost, LightGBM, FinBERT, scikit-learn, HMM (hmmlearn), Kelly criterion |
| LLM | 3-tier router: Ollama (routine) → Perplexity (search) → Claude (deep reasoning) |
| Brain Service | gRPC + Ollama on RTX GPU (PC2, port 50051) |
| Broker | Alpaca Markets (2 accounts: ESPENMAIN trading + ProfitTrader discovery) |
| Data Sources | Alpaca, Unusual Whales, Finviz Elite, FRED, SEC EDGAR, NewsAPI, Benzinga, SqueezeMetrics, Capitol Trades |
| Council | 35-agent DAG with Bayesian-weighted arbiter (7 stages) |
| Scouts | 12 continuous discovery scouts (flow, gamma, insider, macro, etc.) |
| CI/CD | GitHub Actions (981+ tests passing, GREEN) |
| DB | DuckDB (analytics, WAL mode, connection pooling, thread-safe async lock) |
| Infra | Dual-PC (ESPENMAIN + ProfitTrader via gRPC), Docker, Slack bots |

---

## Directory Structure

```
elite-trading-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, 44 router registrations, 6-phase startup
│   │   ├── api/v1/                 # 43 REST route files (364+ endpoints)
│   │   │   ├── agents.py, alerts.py, alignment.py, alpaca.py, awareness.py
│   │   │   ├── backtest_routes.py, blackboard_routes.py, brain.py
│   │   │   ├── cluster.py, cns.py, cognitive.py, council.py
│   │   │   ├── data_sources.py, features.py, flywheel.py, health.py
│   │   │   ├── ingestion_firehose.py, llm_health.py, logs.py, market.py
│   │   │   ├── metrics_api.py, ml_brain.py, mobile_api.py, openclaw.py
│   │   │   ├── orders.py, patterns.py, performance.py, portfolio.py
│   │   │   ├── quotes.py, risk.py, risk_shield_api.py, sentiment.py
│   │   │   ├── settings_routes.py, signals.py, status.py, stocks.py
│   │   │   ├── strategy.py, swarm.py, system.py, training.py
│   │   │   ├── triage.py, webhooks.py, youtube_knowledge.py
│   │   ├── services/               # 72+ service modules (incl. subdirectories)
│   │   │   ├── scouts/             # 12 discovery scouts
│   │   │   ├── llm_clients/        # ollama, perplexity, claude clients
│   │   │   ├── channel_agents/     # 6 channel agents + orchestrator + router
│   │   │   ├── firehose_agents/    # 4 firehose ingest agents
│   │   │   ├── intelligence/       # cache + orchestrator
│   │   │   ├── integrations/       # 6 data source adapters
│   │   │   └── (68+ top-level service files)
│   │   ├── council/                # 35-agent DAG
│   │   │   ├── agents/             # 32 agent files
│   │   │   ├── debate/             # debate_engine, scorer, utils
│   │   │   ├── regime/             # bayesian_regime
│   │   │   ├── reflexes/           # circuit_breaker
│   │   │   ├── runner.py, arbiter.py, weight_learner.py
│   │   │   ├── council_gate.py, schemas.py, registry.py
│   │   │   ├── shadow_tracker.py, self_awareness.py, homeostasis.py
│   │   │   ├── overfitting_guard.py, hitl_gate.py, feedback_loop.py
│   │   │   └── blackboard.py, agent_config.py, data_quality.py, task_spawner.py
│   │   ├── core/                   # MessageBus, security, config
│   │   ├── data/                   # DuckDB storage + init_schema()
│   │   └── websocket_manager.py    # 25 channels, token auth, heartbeat
│   └── tests/                       # 981+ tests passing, GREEN
├── frontend-v2/
│   └── src/
│       ├── pages/                  # 14 route pages
│       ├── hooks/                  # useApi, useSentiment, useSettings, useTradeExecution
│       ├── services/               # websocket.js, tradeExecutionService.js
│       ├── config/                 # api.js (189 endpoint definitions)
│       └── components/
│           ├── dashboard/          # CNSVitals, PerformanceWidgets, ProfitBrainBar, etc.
│           ├── layout/             # Layout, Sidebar, Header, StatusFooter, NotificationCenter
│           └── ui/                 # Badge, Button, Card, DataTable, PageHeader, Select, etc.
├── docker-compose.yml              # Full stack deployment
├── CLAUDE.md                       # Project instructions (auto-loaded by Claude Code)
├── PLAN.md                         # 5-phase enhancement plan (Phases A-E)
└── docs/                           # Architecture, design system, mockups
```

---

## Frontend: 14 Pages

All pages use `useApi.js` hooks — **no mock data remains**. Aurora dark theme with glass effects, cyan/emerald/amber/red color system.

### COMMAND
| Route | File | Status |
|---|---|---|
| `/dashboard` | `Dashboard.jsx` | Done |
| `/agents` | `AgentCommandCenter.jsx` | Done |

### INTELLIGENCE
| Route | File | Status |
|---|---|---|
| `/signals` | `Signals.jsx` (hidden: `SignalIntelligenceV3.jsx`) | Done |
| `/sentiment` | `SentimentIntelligence.jsx` | Done |
| `/data-sources` | `DataSourcesMonitor.jsx` | Done |

### ML & ANALYSIS
| Route | File | Status |
|---|---|---|
| `/ml-brain` | `MLBrainFlywheel.jsx` | Done |
| `/patterns` | `Patterns.jsx` | Done |
| `/backtest` | `Backtesting.jsx` | Done |
| `/performance` | `PerformanceAnalytics.jsx` | Done |
| `/market-regime` | `MarketRegime.jsx` | Done |

### EXECUTION
| Route | File | Status |
|---|---|---|
| `/trades` | `Trades.jsx` | Done |
| `/risk` | `RiskIntelligence.jsx` | Done |
| `/trade-execution` | `TradeExecution.jsx` | Done |

### SYSTEM
| Route | File | Status |
|---|---|---|
| `/settings` | `Settings.jsx` | Done |

---

## Backend: 43 API Routes + 72+ Services

### Key API Routes (`backend/app/api/v1/`)

43 route files providing 364+ endpoints. Highlights:

| Route File | Purpose |
|---|---|
| `signals.py` | Signal CRUD + generation triggers |
| `council.py` | Council invocation + verdict history |
| `orders.py` | Order management via Alpaca |
| `risk.py`, `risk_shield_api.py` | Risk checks + shield API |
| `brain.py` | Brain service (gRPC to PC2) |
| `cns.py` | Central Nervous System endpoints |
| `swarm.py` | Swarm intelligence + scout data |
| `cognitive.py` | Cognitive layer (memory, heuristics) |
| `awareness.py` | System self-awareness |
| `ingestion_firehose.py` | Real-time data ingestion |
| `triage.py` | Idea triage pipeline |
| `webhooks.py` | TradingView + Slack webhooks |
| `cluster.py` | Dual-PC cluster management |

### Key Services (`backend/app/services/`)

72+ service modules organized in subdirectories:

| Service Area | Key Files | Count |
|---|---|---|
| **Core Trading** | signal_engine.py, order_executor.py, position_manager.py, alpaca_service.py | 6 |
| **Scouts** | flow_hunter, gamma, insider, macro, news, congress, earnings, etc. | 12 |
| **LLM Clients** | ollama_client.py, perplexity_client.py, claude_client.py | 3 |
| **Channel Agents** | alpaca, discord, finviz, news, UW channel agents | 6 |
| **Data Sources** | unusual_whales, finviz, fred, sec_edgar, benzinga, squeezemetrics, capitol_trades, senate_stock_watcher | 8 |
| **ML/Intelligence** | ml_training.py, ml_scorer.py, ml_signal_publisher.py, intelligence_cache/orchestrator | 5 |
| **Infrastructure** | scheduler.py, health_registry.py, slack_alerter.py, data_ingestion.py | 10+ |
| **Integrations** | 6 data source adapters (alpaca, finviz, fred, openclaw, sec_edgar, UW) | 6 |

### Backend Architecture

- FastAPI with CORS for localhost:3000/5173/5174/8080
- **6-phase lifespan startup** in main.py
- **44 router registrations**
- DuckDB schema initialized on startup (analytics + backtesting)
- **Auth**: Bearer token (`API_AUTH_TOKEN` env var), fail-closed for live trading
- **WebSocket**: 25 channels with token auth, heartbeat (30s interval, 60s timeout)
  - Channels: order, risk, kelly, signals, council, health, market_data, alerts, outcomes, system, agents, data_sources, trades, logs, sentiment, alignment, council_verdict, homeostasis, circuit_breaker, swarm, macro, market, etc.
- **Background tasks**: scheduler.py orchestrates daily_outcome_update, champion_challenger_eval, weekly_walkforward_train
- **Supervised loops**: `_supervised_loop()` wrapper with crash recovery (3 retries + Slack alerts)
- **Data pipeline**: AlpacaStream → SignalEngine → CouncilGate → Council (35 agents) → OrderExecutor → Alpaca

---

## Database: DuckDB

**File**: `data/elite_trading.duckdb`
**Storage module**: `backend/app/data/storage.py` with `init_schema()`

### DuckDB (WAL mode + connection pooling)

- **Purpose**: All analytics, historical signals, trades, walk-forward validation, backtesting
- **Implementation**: WAL mode, connection pooling, thread-safe double-checked locking for asyncio.Lock
- **Used by**: ML training, signal generation, reporting, order tracking, scout data

```python
from app.data.storage import get_conn

conn = get_conn()

# Get latest signals
signals = conn.execute("""
    SELECT * FROM signals
    WHERE timestamp > ? ORDER BY timestamp DESC
    LIMIT 100
""", [cutoff_date]).fetchall()

# DuckDB gotchas:
# - Thread-safe async lock (double-checked locking) — Phase A6 fix
# - Timestamps: Store as TIMESTAMP type, always UTC
# - COPY for bulk inserts (10-100x faster than INSERT)
```

---

## CI Status & Testing

### CI Status: GREEN
- 981+ tests passing
- GitHub Actions pipeline:
  - backend-test (pytest)
  - frontend-build (npm build)
  - e2e-gate (smoke tests)

### Risk Parameters Validated at CI Level
- Kelly fraction = 0.25 (half-Kelly)
- Max Portfolio Risk = 0.02 (2%)
- Max Drawdown threshold = 0.15 (15%)

### Test Pattern
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_signals_endpoint():
    response = client.get("/api/v1/signals")
    assert response.status_code == 200

# conftest.py monkey-patches DuckDB to use in-memory DB (isolation)
```

### Running Tests
```bash
cd backend
pytest tests/ -v
```

---

## Environment & Deployment

### Two-PC Development Setup

| PC | Hostname | IP | Role |
|---|---|---|---|
| PC1 | ESPENMAIN | 192.168.1.105 | Backend API, frontend, DuckDB, trading execution |
| PC2 | ProfitTrader | 192.168.1.116 | GPU training, ML inference, brain_service (gRPC) |

### Ports & URLs

| Service | Port | URL |
|---|---|---|
| Backend API | 8000 | http://localhost:8000 |
| API Docs (Swagger) | 8000 | http://localhost:8000/docs |
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Brain Service (gRPC) | 50051 | localhost:50051 |
| Ollama | 11434 | http://localhost:11434 |

### Backend Startup
```powershell
cd C:\Users\Espen\elite-trading-system\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Startup
```powershell
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm run dev
```

### Docker
```bash
docker-compose up -d
# Full stack: backend (uvicorn) + frontend (multi-stage Node→Nginx)
```

### Environment Variables
See `backend/.env.example` for full template. Key vars:

| Service | Env Var | Required? |
|---|---|---|
| Alpaca | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | YES (core) |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | No (configured) |
| FRED | `FRED_API_KEY` | No (configured) |
| NewsAPI | `NEWS_API_KEY` | No (configured) |
| Resend | `RESEND_API_KEY` | No (configured) |
| Perplexity | `PERPLEXITY_API_KEY` | No (LLM tier 2) |
| Anthropic | `ANTHROPIC_API_KEY` | No (LLM tier 3) |
| Finviz | `FINVIZ_API_KEY` | No |

---

## WebSocket Integration

WebSocket at `/ws` with 25 channel whitelist, token auth, heartbeat.

### Frontend WebSocket
```javascript
// frontend-v2/src/services/websocket.js
// Manages connections, channel subscriptions, auto-reconnect
// Used by 5+ pages: signals, orders, council, market data, dashboard

// frontend-v2/src/config/api.js
// WS_CHANNELS defines all frontend channel subscriptions
```

### Backend WebSocket
```python
# backend/app/websocket_manager.py
# 25 channels: order, risk, kelly, signals, council, health, etc.
# Token auth, heartbeat (30s/60s), channel validation
# broadcast_ws(channel, data) to push updates
```

---

## Code Conventions & Patterns

### Frontend
```javascript
// Always use useApi hook for data fetching
import { useApi } from '../hooks/useApi';
const { data, loading, error } = useApi('/api/v1/endpoint');

// Never write mock data — all data comes from real API
// TailwindCSS for styling — Aurora dark theme, glass effects
// Lightweight Charts for financial charts
// lucide-react for icons
```

### Backend
```python
# FastAPI route pattern
from fastapi import APIRouter, HTTPException
router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

# Database access — DuckDB for everything
from app.data.storage import get_conn

# Council agents — must return AgentVote
from app.council.schemas import AgentVote

# CRITICAL: Use 4 spaces, NEVER tabs
```

---

## Development Rules (MUST FOLLOW)

1. **Test locally before pushing**: `uvicorn app.main:app` + `npm run build`
2. **Python indentation**: 4 spaces ALWAYS — NEVER tabs
3. **No mock data**: All frontend data via `useApi` hooks to real backend
4. **No yfinance**: Removed — use Alpaca/FinViz/UW
5. **ML is XGBoost + LightGBM**: No PyTorch (removed)
6. **Broker is Alpaca**: Two accounts (ESPENMAIN + ProfitTrader)
7. **Council agents return AgentVote**: From `council/schemas.py`
8. **VETO_AGENTS = {"risk", "execution"}**: No other agent can veto
9. **CouncilGate bridges signals to council**: Do NOT bypass
10. **Discovery is continuous**: 12 scouts, no polling

---

## Key Engineering Facts

1. **signal_engine.py and ml_training.py MUST stay in sync** — Feature engineering in BOTH files
2. **The conftest.py monkey-patches DuckDB** — Tests use in-memory DB
3. **WebSocket has 25 channels** — All validated against whitelist
4. **DuckDB uses thread-safe double-checked locking** — Phase A6 fix
5. **HMM model needs re-initialization daily** — State carries over incorrectly
6. **Alpaca paper trading has rate limits** — 200 requests/minute
7. **3-tier LLM router**: Ollama (routine) → Perplexity (search) → Claude (deep reasoning, 6 tasks only)
8. **Brain service on PC2**: gRPC + Ollama on RTX GPU, wired to hypothesis_agent
9. **12 scouts run continuously**: flow_hunter, gamma, insider, macro, news, congress, etc.
10. **`_supervised_loop()` wrapper**: All background tasks auto-recover (3 retries + Slack alerts)
11. **Order executor enforces Gate 2b (regime) and Gate 2c (circuit breakers)** — Phase A fix
12. **VIX-based regime fallback** when OpenClaw bridge is offline
13. **Status docs are always outdated** — Check git log + actual code state

---

## Key References

- Project instructions: `CLAUDE.md` (auto-loaded, primary source of truth)
- Enhancement plan: `PLAN.md` (Phases A-E)
- Full repo context: `AI-CONTEXT-GUIDE.md`, `REPO-MAP.md`
- Frontend architecture: `frontend-v2/src/V3-ARCHITECTURE.md`
- Design system: `docs/UI-DESIGN-SYSTEM.md`
- PC1/PC2 division: `docs/DIVIDE-AND-CONQUER-PLAN.md`
