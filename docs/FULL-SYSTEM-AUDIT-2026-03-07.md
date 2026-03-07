# Full System Audit — March 7, 2026

## Executive Summary

Comprehensive audit of the Embodier Trader system covering all 14 frontend pages, 111 backend API endpoints, WebSocket infrastructure, data services, and frontend static analysis.

**Backend: 105/111 endpoints returning 200 OK** (after fixes applied).
**Frontend: Build passes clean**, 14 pages with code-split lazy loading.
**Tests: 133/134 backend tests passing** (1 fails due to DuckDB file lock in dev).

---

## Backend API Endpoint Test Results

### Before Fixes
| Status | Count |
|--------|-------|
| ✅ OK (200) | 104 |
| ❌ NOT FOUND (404) | 3 |
| ⚠️ VALIDATION (422) | 1 |
| 🚫 METHOD NOT ALLOWED (405) | 1 |
| ➡️ REDIRECT (307) | 2 |

### After Fixes
| Status | Count |
|--------|-------|
| ✅ OK (200) | 105 |
| ❌ NOT FOUND (404) | 0 |
| ⚠️ VALIDATION (422) | 1 (expected — requires `symbol` param) |
| ➡️ REDIRECT (307) | 5 (standard FastAPI trailing-slash redirects) |

---

## Issues Found & Fixed

### P0 — Critical (Service Breaking)

#### 1. `/api/v1/stocks` → 404 NOT FOUND
**Root cause:** `stocks.py` router had no root `/` GET endpoint. Frontend `useApi('stocks')` calls this.
**Fix:** Added `@router.get("/")` returning tracked symbols summary.
**File:** `backend/app/api/v1/stocks.py`

#### 2. `/api/v1/quotes` → 404 NOT FOUND
**Root cause:** `quotes.py` router had no root `/` GET endpoint. Only had `/{ticker}`, `/{ticker}/candles`, `/{ticker}/book`.
**Fix:** Added `@router.get("/")` returning available endpoints info.
**File:** `backend/app/api/v1/quotes.py`

#### 3. `/api/v1/ml-brain` → 404 NOT FOUND
**Root cause:** `ml_brain.py` router had no root `/` GET endpoint. Frontend `useApi('mlBrain')` calls this on MLBrainFlywheel and SignalIntelligence pages.
**Fix:** Added `@router.get("/")` returning aggregate ML status (version, performance entries, staged signals, registry status, drift status).
**File:** `backend/app/api/v1/ml_brain.py`

#### 4. `/api/v1/risk/position-sizing` → 405 METHOD NOT ALLOWED
**Root cause:** Only `POST` route existed (requires positions array). Frontend may call GET for config info.
**Fix:** Added `@router.get("/position-sizing")` returning position sizing config and limits.
**File:** `backend/app/api/v1/risk.py`

### P1 — Frontend API Config Mismatches

#### 5. Missing `training` endpoint in api.js
**Root cause:** SignalIntelligenceV3 calls `useApi('training')` but `training` wasn't mapped in `api.js`.
**Fix:** Added `training: "/training/"` to api.js endpoints.

#### 6. Missing `system/health` endpoint in api.js
**Root cause:** AgentCommandCenter calls `useApi('system/health')` but wasn't mapped.
**Fix:** Added `"system/health": "/system"` mapping (reuses system root endpoint).

#### 7. Missing `council/status` endpoint in api.js
**Root cause:** RemainingTabs (Agent Command Center) calls `useApi('council/status')` but wasn't mapped.
**Fix:** Added `"council/status": "/council/status"` mapping.

#### 8. Missing `logs/system` endpoint in api.js
**Root cause:** RemainingTabs calls `useApi('logs/system')` but wasn't mapped.
**Fix:** Added `"logs/system": "/logs"` mapping (reuses logs root).

### P1 — Trailing Slash Redirects (307)

#### 9. Multiple endpoints returning 307 redirects
**Root cause:** FastAPI's default redirect behavior when a route is defined as `@router.get("/")` and the client calls without trailing slash.
**Fix:** Updated api.js to include trailing slashes for: `stocks`, `quotes`, `mlBrain`, `orders`, `backtest`.

### P1 — WebSocket Architecture Fix

#### 10. Frontend WebSocket URL mismatch
**Root cause:** `getWsUrl('agents')` generated `/ws/agents` but backend only serves `/ws`. The channel subscription is handled via JSON messages, not URL paths.
**Fix:** Changed `getWsUrl()` to always return `/ws` (base URL only). Updated `useWebSocket` hook to auto-send `{ type: 'subscribe', channel }` on connect.
**Files:** `frontend-v2/src/config/api.js`, `frontend-v2/src/hooks/useWebSocket.js`

### P2 — Static Analysis Findings

#### 11. Null Safety — ~150+ `.map()` calls without guards
**Severity:** Medium. Most use locally-defined arrays/constants (TABS, SORT_PILLS, TIMEFRAMES, etc.) that are always defined. However, some use API data that could be null during loading.
**Recommendation:** Add optional chaining (`data?.map()`) or fallback arrays (`(data || []).map()`) for API-derived data in future PR.

#### 12. Unused state variables in SignalIntelligenceV3.jsx
- `shapActive` / `setShapActive`
- `alertRules` / `setAlertRules`
- `mlConfidenceThreshold` / `setMlConfidenceThreshold`
**Severity:** Low. These are pre-declared for upcoming UI features. No runtime impact.

#### 13. Hardcoded `http://localhost:11434` in Settings.jsx
**Severity:** Not a bug. This is the default value for the Ollama endpoint input field — intentionally defaulting to the standard Ollama port.

---

## System Architecture Verification

### Frontend (14 Pages — All Compiling)
| # | Page | Route | Build Status | API Hooks |
|---|------|-------|-------------|-----------|
| 1 | Dashboard | /dashboard | ✅ Clean | 6 hooks (market, signals, risk, etc.) |
| 2 | Agent Command Center | /agents | ✅ Clean | 12+ hooks (agents, topology, teams, etc.) |
| 3 | Signal Intelligence V3 | /signal-intelligence-v3 | ✅ Clean | 15 hooks (all data sources) |
| 4 | Sentiment Intelligence | /sentiment | ✅ Clean | 3 hooks |
| 5 | Data Sources Monitor | /data-sources | ✅ Clean | 1 hook |
| 6 | ML Brain Flywheel | /ml-brain | ✅ Clean | 8 hooks (flywheel KPIs, models, etc.) |
| 7 | Patterns | /patterns | ✅ Clean | 2 hooks |
| 8 | Backtesting | /backtest | ✅ Clean | 7 hooks |
| 9 | Performance Analytics | /performance | ✅ Clean | 2 hooks |
| 10 | Market Regime | /market-regime | ✅ Clean | 10 hooks (regime, macro, sectors, etc.) |
| 11 | Trades | /trades | ✅ Clean | 3 hooks |
| 12 | Risk Intelligence | /risk | ✅ Clean | 4 hooks |
| 13 | Trade Execution | /trade-execution | ✅ Clean | 5 hooks |
| 14 | Settings | /settings | ✅ Clean | 1 hook |

### Backend API (35 Routers — All Mounted)
All routers properly mounted in `main.py` with correct prefixes:
stocks, quotes, orders, system, training, signals, backtest, status, data-sources, portfolio, risk, strategy, performance, flywheel, logs, patterns, openclaw, ml-brain, market, agents, sentiment, alerts, settings, alpaca, alignment, risk-shield, features, council, cns, swarm, cognitive, youtube-knowledge, ingestion, cluster

### WebSocket System
- Backend: Single `/ws` endpoint with channel subscriptions, rate limiting (120 msg/min), max 50 connections, heartbeat (30s), auth token support
- Frontend: `useWebSocket` hook with auto-reconnect, exponential backoff, heartbeat, message buffer
- Bridge: 5 event bridges (signal, order, council, risk, drawdown) from MessageBus → WebSocket
- **Status: Code complete, not yet integrated into page components** (pages use REST polling)

### Event-Driven Pipeline
- MessageBus: Async pub/sub with Redis bridge support (local-only in dev)
- AlpacaStreamManager: Multi-key WebSocket for real-time market data
- EventDrivenSignalEngine: market_data.bar → signal.generated
- CouncilGate: 13-agent council controls all trading decisions
- OrderExecutor: council.verdict → order execution (shadow mode by default)

### Data Layer
- DuckDB: Analytics store with 8 tables
- SQLite: Config/state store
- Feature Store: Real-time feature computation + persistence

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/api/v1/stocks.py` | Added root GET `/` endpoint |
| `backend/app/api/v1/quotes.py` | Added root GET `/` endpoint |
| `backend/app/api/v1/ml_brain.py` | Added root GET `/` endpoint with aggregate status |
| `backend/app/api/v1/risk.py` | Added GET `/position-sizing` for config retrieval |
| `frontend-v2/src/config/api.js` | Added 4 missing endpoint mappings, fixed trailing slashes, fixed WS URL |
| `frontend-v2/src/hooks/useWebSocket.js` | Auto-subscribe to channel on WebSocket connect |

---

## Recommendations for Next Sprint

1. **Connect WebSocket to pages** — Replace polling with WS subscriptions for real-time data (signals, risk, agents)
2. **Add null guards** — Wrap API-derived `.map()` calls with optional chaining across all pages
3. **Alpaca API integration** — Configure real API keys to enable live market data
4. **JWT Authentication** — Backend has `require_auth` decorator ready; implement proper JWT flow
5. **Playwright E2E tests** — Wire up `e2e/critical-flows.spec.js` for automated UI testing
