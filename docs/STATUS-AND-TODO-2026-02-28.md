# Embodier Trader - Status & TODO Update

## Date: February 28, 2026 (8:00 AM EST)
## Author: AI Assistant (Comet) + Espen
## Repository: github.com/Espenator/elite-trading-system

---

## CURRENT PROJECT STATUS

### Summary

All 15 frontend pages and 25 backend API routes exist as code files. **The app does NOT run.** CI has been failing for 100+ consecutive runs. The gap is: (1) Python syntax errors across backend files, (2) nothing has been wired together and tested end-to-end.

### What Exists (Verified Feb 28)

- [x] 15 frontend page files in `frontend-v2/src/pages/`
- [x] 25 backend API route files in `backend/app/api/v1/`
- [x] 15 backend service files in `backend/app/services/`
- [x] 2 frontend hooks: `useApi.js`, `useSentiment.js`
- [x] 2 frontend services: `openclawService.js`, `websocket.js`
- [x] WebSocket manager (backend) + client (frontend)
- [x] CI workflow: `ci.yml` (backend-test + frontend-build)
- [x] DuckDB database layer in `app/data/storage.py`
- [x] main.py lifespan bug fixed (risk_monitor_task, background tasks)
- [x] requirements.txt cleaned (no duplicate httpx, no torch, no technical-analysis)
- [x] hourly-scanner.yml removed (deprecated)
- [x] orders.py indentation fixed
- [x] Design system finalized in `docs/UI-DESIGN-SYSTEM.md`
- [x] 6+ approved UI mockup images in `docs/mockups-v3/images/`

### What's Broken (Why App Doesn't Work)

- [ ] **CI FAILING**: `signals.py` has IndentationError (line 63, tab/space mixing) -- likely more files too
- [ ] **Backend has never been started** (`uvicorn app.main:app` never run)
- [ ] **13 of 15 frontend pages still have mock/hardcoded data** (only Dashboard + AgentCommandCenter audited)
- [ ] **torch removed** from requirements.txt but LSTM inference code in `models/inference.py` imports torch
- [ ] No integration testing between frontend <-> backend <-> database
- [ ] WebSocket real-time data flow untested
- [ ] Database initialization untested
- [ ] .env file needs proper API keys configured
- [ ] Test suite minimal: 1 test file (`test_api.py`)

### Deep Research Audit Score: 4.2/10 (Target: 9/10)

| Dimension | Score | Target | Key Blocker |
|---|---|---|---|
| Backend Architecture | 7/10 | 9/10 | OpenClaw monoliths, no DI |
| Signal Pipeline | 4/10 | 9/10 | Simplistic scoring, 3 indicators |
| ML/AI Integration | 6/10 | 9/10 | Only 5 features, no ensemble |
| Real-Time Data | 3/10 | 9/10 | No streaming, polling only |
| Testing | 0/10 | 9/10 | Zero meaningful test coverage |

---

## BLOCKING ISSUES (Fix Before Anything Else)

| # | Issue | File(s) | Fix |
|---|---|---|---|
| B1 | IndentationError in signals.py line 63 | `backend/app/api/v1/signals.py` | Fix tab/space mixing |
| B2 | Likely more IndentationErrors in other v1/ files | All 25 files in `api/v1/` | Run `python -c "import app.api.v1"` locally to find all |
| B3 | torch import will fail (removed from requirements) | `backend/app/models/inference.py` | Add torch back OR rewrite inference without torch |
| B4 | Backend never started | `backend/app/main.py` | Run `uvicorn app.main:app` locally, fix ALL import errors |

---

## PLAN TO WORKING APP (8 Days / ~30 Hours)

### Phase A: Make It Start (Day 1) - ~4 hours

| # | Task | Status |
|---|---|---|
| A1 | Fix ALL backend IndentationErrors across api/v1/ files | IN PROGRESS (orders.py done, signals.py + others pending) |
| A2 | Run `uvicorn app.main:app` -- fix ALL import errors | NOT STARTED |
| A3 | Run `npm run dev` -- verify frontend builds and renders | NOT STARTED |
| A4 | Configure .env with Alpaca paper keys at minimum | NOT STARTED |
| A5 | Verify DuckDB initializes and creates tables on startup | NOT STARTED |

### Phase B: Wire Core Loop (Days 2-3) - ~8 hours

| # | Task | Frontend | Backend | Status |
|---|---|---|---|---|
| B1 | Dashboard shows real market data | Dashboard.jsx | market.py, portfolio.py | PARTIAL (useApi wired) |
| B2 | Signals page shows real scan results | Signals.jsx | signals.py | NOT STARTED |
| B3 | Trade Execution places paper orders | TradeExecution.jsx | orders.py | NOT STARTED |
| B4 | Trades page shows real positions | Trades.jsx | portfolio.py | NOT STARTED |
| B5 | WebSocket pushes real-time updates | websocket.js | websocket_manager.py | NOT STARTED |

### Phase C: Wire Remaining Pages (Days 4-5) - ~8 hours

| # | Page | Backend | Status |
|---|---|---|---|
| C1 | ML Brain & Flywheel | ml_brain.py | NOT STARTED |
| C2 | Backtesting Lab | backtest_routes.py | NOT STARTED |
| C3 | Performance Analytics | performance.py | NOT STARTED |
| C4 | Market Regime | market.py | NOT STARTED |
| C5 | Risk Intelligence | risk.py | NOT STARTED |
| C6 | Agent Command Center | agents.py | PARTIAL (useApi wired) |
| C7 | Patterns / Screener | patterns.py | NOT STARTED |
| C8 | Sentiment Intelligence | sentiment.py | NOT STARTED |
| C9 | Data Sources Monitor | data_sources.py | NOT STARTED |
| C10 | Settings | settings_routes.py | NOT STARTED |

### Phase D: Polish & Testing (Days 6-8) - ~10 hours

| # | Task | Status |
|---|---|---|
| D1 | Compare each page against mockups in docs/mockups-v3/ | NOT STARTED |
| D2 | Add loading states, error states, empty states | NOT STARTED |
| D3 | Full end-to-end test: all 15 pages | NOT STARTED |
| D4 | Place a paper trade through the UI | NOT STARTED |
| D5 | Verify WebSocket updates flow in real-time | NOT STARTED |

---

## CHANGES MADE TODAY (Feb 28, 2026)

- [x] Fixed orders.py IndentationError (kelly_edge field + kelly_warnings block)
- [x] Rewrote root README.md with honest actual status
- [x] Rewrote backend/README.md (15 services not 20+, DuckDB not SQLite, torch removed)
- [x] Created this STATUS-AND-TODO-2026-02-28.md
- [x] Removed hourly-scanner.yml (deprecated)
- [x] Verified: ScreenerAndPatterns.jsx doesn't exist (already deleted)
- [x] Verified: main.py lifespan already fixed in prior commit
- [x] Verified: requirements.txt already cleaned in prior commit

---

## COMMIT DISCIPLINE (MANDATORY)

**Before every commit, run locally:**
```bash
cd backend && python -c "from app.main import app; print('Backend imports OK')"
cd frontend-v2 && npm run build
```

Do NOT push code that has not been tested locally. AI-assisted development sessions caused 100+ consecutive CI failures by pushing untested code.

---

## MOCKUP vs IMPLEMENTATION AUDIT (Feb 28, 2026 - 9:00 AM EST)

### CI Blockers Found

| # | Issue | File | Fix |
|---|---|---|---|
| CI-1 | Frontend build fails: invalid JS syntax at line 90:2 | `frontend-v2/src/services/websocket.js` | Fix brace/syntax parse error in connect() catch block |
| CI-2 | Backend test fails: `yfinance==0.2.0` not found in pip | `backend/requirements.txt` | REMOVE yfinance entirely - we use Alpaca, Unusual Whales, Finviz as data sources |

### Patterns.jsx - TWO Issues Found

| # | Issue | Lines | Fix |
|---|---|---|---|
| P-1 | `PATTERN_TYPES` array has hardcoded static winRate/avgR. `assignPattern()` fakes pattern detection using symbol hash | ~80-145 | Wire to `GET /api/v1/patterns` which returns real detected patterns. Backend endpoint is CLEAN and READY. |
| P-2 | `SECTOR_PATTERN_DATA` is entirely hardcoded static array (10 sectors with fake sizes/patterns/winRates) | ~155-170 | Compute from real API data - aggregate patterns by sector from `/api/v1/patterns` response |

### Screener & Patterns (Patterns.jsx) vs Mockup 07 - ~25% Complete

| Mockup Feature | Status |
|---|---|
| Two-panel layout (Screening Engine + Pattern Intelligence) | MISSING - has single screener |
| Scan Agent Fleet with Scanner Agent Cards | MISSING |
| Trading Metric Controls (Beta, Alpha, MFI, Short Interest, RS, Options Flow, Vol Regime, Volume Profile, Dark Pool, Institutional, Sector Momentum) | PARTIAL - only Price/RSI/Volume/MarketCap |
| Pattern Agent Fleet with LLM Model + ML Architecture cards | MISSING |
| ML Metric Controls (Validation Score, Sharpe, Profit Factor, Drawdown, Walk-Forward, OOS Accuracy, Monte Carlo CI) | MISSING |
| Spawn/Clone/Kill Agent buttons | MISSING |
| Consolidated Live Feed (timestamped detections) | MISSING |
| Pattern Arsenal (chart pattern thumbnails) | MISSING |
| Forming Detections (live chart visuals) | MISSING |
| Status bar (Connections, Agents, Patterns, Scans, GPU%) | MISSING |

### Data Sources Manager (DataSourcesMonitor.jsx) vs Mockup 09 - ~55% Complete

| Mockup Feature | Status |
|---|---|
| Header with title | DONE |
| Top metrics bar (Connected X/Y, System Health%, Ingestion rate, OpenClaw Bridge, WS status) | PARTIAL - has counts but missing health%, ingestion, bridge, WS |
| AI-powered Add Source input with provider quick-buttons | PARTIAL - has AI Detect modal but not inline |
| Source List with category tabs + search | DONE - category tabs present |
| Source rows (icon, name, category, status, latency, sparkline, records, uptime%) | PARTIAL - card grid not row list, missing sparklines/records/uptime |
| Split-view Credential Editor Panel (right side) | PARTIAL - modal not persistent panel |
| Connection log footer with timestamps | MISSING |
| System telemetry footer | MISSING |
| LIVE PING indicator | MISSING |
| API wiring to real backend | DONE - dataSourcesApi.js fully wired |

### Data Sources: Alpaca, Unusual Whales, Finviz (PRIMARY)

These are our three primary data providers. yfinance is NOT used anywhere and must be removed from requirements.txt.


---

## SESSION UPDATE — Feb 28, 2026 (Comet AI)

### Fixes Applied This Session

- [x] **Patterns.jsx P-1 FIXED** (commit b18a267): Removed `assignPattern()` hash-based fake pattern assignment. Removed static `PATTERN_TYPES` winRate/avgR. Now fetches real patterns from `/api/v1/patterns`. Sector heatmap (`sectorPatternData`) computed from real API data instead of hardcoded `SECTOR_PATTERN_DATA` array.
- [x] **requirements.txt yfinance REMOVED** (commit de0a344): `yfinance>=0.2.31` deleted. Confirmed no Python files import yfinance. Data sources are Alpaca Markets, Unusual Whales, Finviz (PRIMARY).
- [x] **websocket.js already fixed** (prior commit): CI parse error was resolved.
- [x] **STATUS-AND-TODO-2026-02-28.md updated** (commit docs session): Added full mockup vs implementation audit tables.

### Patterns.jsx — Remaining Gaps vs Mockup 07

The page title is now "Patterns & Screener" and calls real APIs. The following mockup features are still missing:

- [ ] **Scan Agent Fleet panel** — spawnable/killable Scanner Agent Cards with Name/Type/Timeframe config
- [ ] **Advanced Trading Metric sliders**: Beta Threshold, Alpha Target, MFI 0-100, Short Interest, Relative Strength vs SPX, Options Flow Filter, Volatility Regime, Volume Profile, Dark Pool Activity, Institutional Accumulation, Sector Momentum
- [ ] **Pattern Agent Fleet** — Pattern Agent Cards with LLM Model + ML Architecture selection
- [ ] **ML Metric Controls** — Recursive Self-Improvement toggle, Academic Validation Score, Sharpe Ratio, Profit Factor, Max Drawdown, Walk-Forward Efficiency, OOS Accuracy, Monte Carlo CI, Pattern Complexity, Sub-Agent Swarm Size
- [ ] **Spawn/Clone/Kill Agent buttons** for both fleets
- [ ] **Consolidated Live Feed** — timestamped real-time detection stream
- [ ] **Pattern Arsenal** — chart pattern thumbnail grid
- [ ] **Forming Detections** — live chart visuals for patterns in progress
- [ ] **Status bar** (Connections, Agents, Patterns, Scans, GPU%)

### DataSourcesMonitor.jsx — Remaining Gaps vs Mockup 09

Core API integration is complete. The following mockup features are still missing:

- [ ] **Top metrics bar**: System Health%, Ingestion rate (rec/min), OpenClaw Bridge status, WS: CONNECTED indicator
- [ ] **Inline AI-powered Add Source input** with quick-pick provider buttons (Polygon.io, Benzinga, Alpha Vantage, Quandl, IEX Cloud, CoinGecko) — currently only modal button
- [ ] **Source rows as table** (not card grid): columns for name, category, status, latency, mini sparkline, records/day, uptime%
- [ ] **Split-view Credential Editor Panel** (right-side persistent) with: Base URL, WebSocket URL, Rate Limit, Polling Interval, Account Type fields + Test Connection log with timestamps
- [ ] **Connection log** with timestamped entries per source
- [ ] **System telemetry footer** (WSI, API counts)
- [ ] **LIVE PING indicator** per source row

### Next Priority Items

1. DataSourcesMonitor: Add top metrics bar (system health, ingestion rate, bridge/WS status)
2. DataSourcesMonitor: Convert card grid to table layout with sparklines + uptime%
3. DataSourcesMonitor: Make credential editor a persistent right panel (not modal)
4. Patterns: Add Advanced Trading Metric sliders (Beta/Alpha/MFI/Dark Pool/Options Flow/Short Interest)
5. Patterns: Add Consolidated Live Feed panel (real-time detection stream)
6. Patterns: Add Pattern Arsenal + Forming Detections panels
7. Backend: Fix all remaining IndentationErrors in signals.py and other files
8. Backend: Start uvicorn, verify all 25 API routes return valid data end-to-end
