# Project State - Elite Trading System (Embodier.ai)

> Paste this file at the start of every new AI chat session.
> Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 4, 2026

## Identity

- **Project**: Elite Trading System by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (private)
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, CI GREEN (151 tests)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) + SQLite (settings/orders) |
| ML | XGBoost, scikit-learn, LSTM (PyTorch optional) |
| Agents | 8-Agent Council (debate pattern) + OpenClaw multi-agent system |
| Alignment | 6 Constitutive Design Patterns (Bright Lines, Bible, Metacognition, Constellation, Critique, Signal Identity) |
| CI/CD | GitHub Actions (151 tests passing) |
| Infra | Docker, docker-compose.yml |
| Local AI | Ollama via gRPC Brain Service (PC2) |
| Auth | Bearer token (API_AUTH_TOKEN) on 47 state-changing endpoints |

## Hardware (Dual-PC Setup)

- **ESPENMAIN** (PC 1): Development + Frontend + Backend API
- **Profit Trader** (PC 2): RTX GPU cluster for ML training + Ollama inference + Brain Service (gRPC :50051)
- Both PCs share the same git repo and `.env` configuration

## Data Sources (CRITICAL - NO yfinance)

- **Alpaca Markets** (alpaca-py) - Market data + order execution
- **Unusual Whales** - Options flow + institutional activity
- **FinViz** (finviz) - Screener, fundamentals, VIX proxy
- **FRED** - Economic macro data
- **SEC EDGAR** - Company filings
- **StockGeist** - Sentiment analysis
- **News API** - Market news

## Architecture

```
[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
                    |                  |
              WebSocket <----  MessageBus (event-driven)
                    |                  |
              15 pages          28+ API routes at /api/v1/*
                                       |
                              8-Agent Council (DAG)
                              Alignment Engine (6 patterns)
                              ML Engine (XGBoost + LSTM)
                              OpenClaw (multi-agent scanner)
                              DuckDB Analytics
```

### Council DAG (6-Stage Pipeline)
```
Stage 1: [market_perception, flow_perception, regime]  (parallel)
Stage 2: [hypothesis]  (LLM via Brain Service)
Stage 3: [strategy]  (playbook constraints)
Stage 4: [risk, execution]  (parallel, VETO power)
Stage 5: [critic]  (post-trade learning)
Stage 6: [arbiter]  (deterministic weighted vote)
```

### Feedback Loop (NEW - March 4, 2026)
```
Council Decision → record_decision() → feedback_loop store
Trade Outcome → record_outcome() → update agent accuracy stats
Weight Update → update_agent_weights() → persist to settings → agents read on next eval
```

## Key Code Patterns

1. Frontend data: Always use `useApi('endpoint')` hook
2. No mock data: All components wire to real `/api/v1/*` endpoints
3. Python style: 4-space indentation, never tabs
4. JSX unicode: BMP only
5. API pattern: Route handler → Service layer → External API
6. Mockups: `docs/mockups-v3/images/` are the source of truth
7. Auth: `getAuthHeaders()` on all POST/PUT/DELETE from frontend
8. Council thresholds: Read from `settings_service` → `council` category (configurable via Settings page)

## Current State (Mar 4, 2026)

- **CI**: GREEN (151 tests, all passing)
- **Frontend**: 15 pages built, all wired to real API hooks
- **Backend**: 28+ API routes defined, services layer implemented
- **Authentication**: Bearer token on 56+ state-changing endpoints (`security.py`)
- **ML**: XGBoost trainer + feature pipeline operational, atomic writes for model registry
- **OpenClaw**: Phase 2 complete (8 sub-modules integrated)
- **Council**: 8-agent debate with configurable thresholds via settings service
- **Feedback Loop**: Council decisions recorded, outcomes tracked, agent weights auto-adjusted
- **Alignment Engine**: 6 constitutive design patterns operational
- **Feature Aggregator**: Real OHLCV, technicals, flow, regime from DuckDB
- **WebSocket**: Signal→MessageBus→WebSocket bridges wired (signals, orders, council, risk)
- **Brain Service**: gRPC wired to hypothesis + critic agents (needs `BRAIN_ENABLED=true`)
- **CORS**: Restricted to configured origins with specific methods/headers
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **Startup Validation**: Live trading mode blocks startup if ALPACA keys or AUTH_TOKEN missing
- **Memory Safety**: Bounded order history (deque), cache cleanup, pagination limits

## Completed Work (March 4, 2026 Session)

### Codebase Review & Bug Fixes
- Reviewed 200+ files, found 105+ issues categorized P0-P3
- Fixed all 105+ bugs across 58 files in one commit
- Categories: 18 crash bugs (P0), 22 security issues (P1), 35 logic errors (P2), 30+ org issues (P3)

### Authentication System (NEW)
- Created `backend/app/core/security.py` with `require_auth` / `optional_auth` FastAPI dependencies
- Protected 47 POST/PUT/DELETE/PATCH endpoints across 12 route files
- Frontend sends `Authorization: Bearer <token>` via `getAuthHeaders()` on all mutations
- Backwards compatible: no token in paper/dev mode = pass-through

### Configurable Agent Thresholds (NEW)
- Created `backend/app/council/agent_config.py` — central config reader
- Added `council` category to settings service with all agent thresholds
- Updated all 8 agents to read thresholds from settings instead of hardcoding
- Agent weights, RSI levels, PCR thresholds, volume minimums all configurable via Settings page

### Feedback Loop (NEW)
- Created `backend/app/council/feedback_loop.py` — records decisions + outcomes
- Council runner auto-records every decision with all agent votes
- Order executor feeds trade outcomes back to feedback loop
- `update_agent_weights()` recomputes weights from accuracy history
- API endpoints: `GET /council/performance`, `POST /council/update-weights`

### Cleanup
- Deleted dead `backend/routers/trade_execution.py` (superseded by OrderExecutor service)

### Production Hardening (March 4, 2026 — Session 2)
- **Auth expanded**: Added `require_auth` to 9 more endpoints (alpaca DELETE positions, PUT risk, patterns POST/DELETE, sentiment POST/DELETE, ml-brain POST conference)
- **Error leak fix**: Replaced `str(e)` in HTTPException with generic messages across 6 API files (stocks, quotes, alerts, risk_shield, ml_brain)
- **Memory safety**: OrderExecutor._orders → bounded `deque(maxlen=10000)`, Alpaca cache auto-cleanup at 500+ keys, data ingestion pagination limited to 100 pages
- **Atomic writes**: model_registry `_save_runs()` and `_save_champions()` now write to .tmp then rename; same for feature_pipeline manifest
- **CORS tightened**: Replaced `allow_methods=["*"]` / `allow_headers=["*"]` with explicit lists
- **Security headers**: Added middleware for X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **Startup validation**: config.py blocks startup in `TRADING_MODE=live` if ALPACA keys or AUTH_TOKEN missing
- **DuckDB shutdown**: Explicit connection close in lifespan shutdown handler
- **Frontend localhost fix**: openclawService.js derives WS URL from window.location in production
- **Env docs**: Updated frontend-v2/.env.example with VITE_API_URL, VITE_WS_URL, VITE_ENABLE_AGENT_MOCKS

## Remaining Work / Phase 1 TODOs

1. **Enable Brain Service**: Set `BRAIN_ENABLED=true`, ensure Ollama running on PC2
2. **Data Ingestion**: Run initial OHLCV + technicals ingestion to populate DuckDB tables
3. **Scheduler**: Enable `SCHEDULER_ENABLED=true` for automated daily scans
4. **Frontend Council Page**: Wire council performance stats to Agent Command Center dashboard
5. **Live Testing**: Run full pipeline end-to-end with Alpaca paper trading
6. **Notification Wiring**: Connect Discord/Telegram/Email alerts to trade events
7. **Risk Shield TODOs**: Wire kill_switch, hedge_all, reduce_50, freeze_entries to Alpaca API (4 stubs remain)
8. **Structured Logging**: Switch to JSON logging format with correlation IDs for production observability
9. **Rate Limiting**: Add slowapi rate limiter to API endpoints
10. **Database Migrations**: Add Alembic for schema versioning and rollback capability

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use useApi() hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups before building UI
6. Run `npm run build` before committing frontend changes
7. Run `python -m pytest` before committing backend changes
8. ALWAYS add auth (`dependencies=[Depends(require_auth)]`) to new POST/PUT/DELETE endpoints
9. ALWAYS use `getAuthHeaders()` in frontend POST/PUT/DELETE fetch calls
10. Council agent thresholds go in `agent_config.py` / settings service, NOT hardcoded
11. NEVER expose `str(e)` in HTTPException details — use generic messages, log details server-side
12. Use atomic writes (write to .tmp, rename) for any JSON file persistence
13. All in-memory caches MUST have size bounds (deque maxlen, periodic cleanup, or LRU)
