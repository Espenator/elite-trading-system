# Embodier Trader — End-to-End Audit Report

**Date:** March 12, 2026  
**Scope:** UI/UX, frontend logic, API integration, backend services, WebSocket, agent orchestration, ML Brain, Signal Intelligence, signal→order pipeline  
**App:** http://localhost:5173 (Vite + React) | Backend: FastAPI (44 routers)

---

## Executive Summary

- **Routes & navigation:** All 14 sidebar routes exist and match `App.jsx`; no dead links.
- **WebSocket:** Reconnect and channel re-subscribe implemented; Dashboard does not subscribe to any channel; Signal Intelligence, Trade Execution, Risk, Market Regime, Sentiment, and agent tabs use WS for live updates.
- **Backend:** 44 routers; app-level `/healthz`, `/readyz`, `/health`; 8 routers have their own health endpoints; 36 rely on app-level only. One 501 (SMS alerts). Ingestion health returns 200 with error body instead of 503.
- **Signal→order pipeline:** End-to-end wired: `market_data.bar` → EventDrivenSignalEngine → `signal.generated` → CouncilGate → council → `council.verdict` → OrderExecutor → Alpaca. No broken link.
- **Critical gaps:** Flywheel KPIs/history not auto-updated from outcome_resolver; KILL SWITCH and several Agent Command Center buttons are stubs; mock/fallback data used when API empty (Signal Intelligence, Trade Execution, Data Sources, Performance); backtest results/optimization/walk-forward return stubs; live inference does not use model registry champion.

---

## PHASE 1 — Browser & UI Audit (Findings)

### [AgentCommandCenter] | [🟡] | [Gap]
- **Description:** KILL SWITCH only shows toast; no backend call to halt agents or emergency stop.
- **Root Cause:** No API or WebSocket wired for emergency halt in the UI.
- **Fix:** Wire to `POST /api/v1/risk-shield/emergency-action` or `POST /api/v1/orders/emergency-stop` (or equivalent) and call from KILL SWITCH onClick.
- **Files Affected:** `frontend-v2/src/pages/AgentCommandCenter.jsx`

### [AgentCommandCenter] | [🟡] | [Gap]
- **Description:** Footer "LLM Flow 847", "Conference 8/12", "Load 2.4/4.0" are hardcoded; not from API.
- **Root Cause:** Static copy for layout only.
- **Fix:** Replace with `useApi("system")` or conference/load data from backend if available.
- **Files Affected:** `frontend-v2/src/pages/AgentCommandCenter.jsx`

### [DataSourcesMonitor] | [🟡] | [Gap]
- **Description:** Test Connection, Save, Cancel, Reset in credential/detail panel have no API calls.
- **Root Cause:** Buttons not wired to settings/connection test or save endpoints.
- **Fix:** Implement settings/connection test and save endpoints and wire buttons, or hide/disable until supported.
- **Files Affected:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`

### [DataSourcesMonitor] | [🟡] | [Gap]
- **Description:** LIVE PING, Show/Copy/Rotate on source cards not wired to backend.
- **Root Cause:** No handlers or API for these actions.
- **Fix:** Add API for ping/copy/rotate or remove if not supported.
- **Files Affected:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`

### [DataSourcesMonitor] | [🟡] | [Gap]
- **Description:** Connection Log is hardcoded; not from API.
- **Root Cause:** Static placeholder lines.
- **Fix:** Load from API or remove/replace with "No log" empty state.
- **Files Affected:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`

### [DataSourcesMonitor] | [🟡] | [Convention]
- **Description:** SUPPLY_CHAIN_SOURCES includes `yfinance`; CLAUDE.md says "no yfinance".
- **Root Cause:** Display list only; not used for requests.
- **Fix:** Remove yfinance from list or mark as "legacy/unused".
- **Files Affected:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`

### [DataSourcesMonitor] | [🟡] | [Bug]
- **Description:** LatencySparkline may be called with no points (SourceCard); component may break or show nothing.
- **Root Cause:** Latency history not passed from API; sparkline expects points.
- **Fix:** Pass latency history from API or hide sparkline when no data.
- **Files Affected:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`

### [SignalIntelligenceV3] | [🟡] | [Gap]
- **Description:** Fallback signals array (9 hardcoded signals) when API returns empty; violates "no mock data" rule.
- **Root Cause:** Intentional fallback for demo/empty state.
- **Fix:** Use explicit empty state UI instead of fake data (e.g. "No signals — run scanner or wait for live signals").
- **Files Affected:** `frontend-v2/src/pages/SignalIntelligenceV3.jsx`

### [SignalIntelligenceV3] | [🟡] | [Gap]
- **Description:** Download/Upload/Share buttons have no onClick handlers.
- **Root Cause:** Not implemented.
- **Fix:** Implement export/import/share or remove/disable.
- **Files Affected:** `frontend-v2/src/pages/SignalIntelligenceV3.jsx`

### [SignalIntelligenceV3] | [🟡] | [Gap]
- **Description:** Accept/Reject/Watch on signal rows do not call backend (HITL or orders).
- **Root Cause:** Local state only.
- **Fix:** Wire to HITL approve/reject or orders API if backend supports.
- **Files Affected:** `frontend-v2/src/pages/SignalIntelligenceV3.jsx`

### [TradeExecution] | [🟡] | [Gap]
- **Description:** Fallback order book, news, system status, positions when API empty; can look like real data.
- **Root Cause:** Placeholder for empty state.
- **Fix:** Use clear empty state messaging instead of fake structures.
- **Files Affected:** `frontend-v2/src/pages/TradeExecution.jsx`

### [RemainingTabs] | [🟡] | [Gap]
- **Description:** BlackboardCommsTab uses hardcoded `topics` and `hitlBuffer`; not from API.
- **Root Cause:** Mock data for layout.
- **Fix:** Use `useApi("agentHitlBuffer")` and real blackboard/conference data like SwarmOverviewTab.
- **Files Affected:** `frontend-v2/src/pages/agent-tabs/RemainingTabs.jsx`

### [SentimentIntelligence] | [🟢] | [Enhancement]
- **Description:** Auto Discover failure only logs to console.error.
- **Root Cause:** No user-facing error surface.
- **Fix:** Show toast or inline error state on failure.
- **Files Affected:** `frontend-v2/src/pages/SentimentIntelligence.jsx`

### [Dashboard] | [🟢] | [Enhancement]
- **Description:** WebSocket connect/disconnect but no channel subscription; dashboard does not get live signal/trade updates.
- **Root Cause:** Design choice.
- **Fix:** Optionally subscribe to `signals` and `trades` for live refresh.
- **Files Affected:** `frontend-v2/src/pages/Dashboard.jsx`

---

## PHASE 2 — Component & Code Audit (Findings)

### [api.js] | [🟡] | [Gap]
- **Description:** `risk/config` and `sentiment/discover` are used via composed paths; no keys in api.js, causing DEV warning.
- **Root Cause:** getApiUrl(key) used with non-existent key; path built from key string.
- **Fix:** Add `"risk/config": "/risk/config"` and `"sentiment/discover": "/sentiment/discover"` to api.js endpoints.
- **Files Affected:** `frontend-v2/src/config/api.js`, `frontend-v2/src/pages/MarketRegime.jsx`, `frontend-v2/src/pages/SentimentIntelligence.jsx`

### [useApi.js / api.js] | [🟢] | [Enhancement]
- **Description:** When endpointOverride is set, URL base uses `import.meta.env.VITE_API_URL`; otherwise BASE_URL from API_CONFIG; slight inconsistency.
- **Root Cause:** Two code paths for URL construction.
- **Fix:** Use same base (e.g. API_CONFIG.BASE_URL or shared helper) in both paths.
- **Files Affected:** `frontend-v2/src/hooks/useApi.js`, `frontend-v2/src/config/api.js`

### [PerformanceAnalytics.jsx] | [🟡] | [Gap]
- **Description:** FALLBACK_KPI, FALLBACK_AGENTS, FALLBACK_TRADES, etc. when API empty; can be mistaken for real data.
- **Root Cause:** Mockup fallback values for empty state.
- **Fix:** Use empty/zero state or explicit "No data" UI instead of fake numbers.
- **Files Affected:** `frontend-v2/src/pages/PerformanceAnalytics.jsx`

### [tradeExecutionService / api.js] | [🟢] | [Enhancement]
- **Description:** Composed paths (e.g. getApiUrl('market') + '/price-ladder', orders + '/close') not named in api.js.
- **Root Cause:** Paths built in code.
- **Fix:** Add keys e.g. marketPriceLadder, ordersClose, ordersAdjust for consistency and to avoid unmapped-key warnings.
- **Files Affected:** `frontend-v2/src/config/api.js`, `frontend-v2/src/services/tradeExecutionService.js`

### [Hooks / Services] | [🟢] | [Enhancement]
- **Description:** No PropTypes or TypeScript; no explicit contract with backend.
- **Root Cause:** JS-only codebase.
- **Fix:** Add PropTypes or migrate to TypeScript and shared types where useful.
- **Files Affected:** `frontend-v2/src/hooks/*.js`, `frontend-v2/src/services/*.js`

### [api.js / .env] | [🟡] | [Gap]
- **Description:** VITE_API_AUTH_TOKEN (and VITE_FMP_API_KEY if used in frontend) are embedded in client bundle if set at build; secret exposure risk.
- **Root Cause:** VITE_ vars are inlined at build.
- **Fix:** Document that auth should be provided at runtime (e.g. Electron, login flow) or avoid VITE_ for tokens; keep FMP key server-side only.
- **Files Affected:** `frontend-v2/.env.example`, `frontend-v2/src/config/api.js`

---

## PHASE 3 — Backend Services Audit (Findings)

### [ingestion.py] | [🟡] | [Bug]
- **Description:** GET /api/ingestion/health returns 200 with `{"status": "error", "detail": "..."}` on failure; readiness probes expect 503 for "not ready".
- **Root Cause:** Exception caught and returned as JSON instead of raising HTTPException.
- **Fix:** On failure, raise HTTPException(status_code=503, detail=...) so probes get 503.
- **Files Affected:** `backend/app/api/ingestion.py`

### [alerts.py] | [🟡] | [Gap]
- **Description:** POST /api/v1/alerts/test-sms returns 501 "SMS alerts not configured".
- **Root Cause:** Intentional until SMS provider (e.g. Twilio) integrated.
- **Fix:** Keep 501 or implement with Twilio and return 200 when configured.
- **Files Affected:** `backend/app/api/v1/alerts.py`

### [config.py] | [🟢] | [Enhancement]
- **Description:** localhost:5174 not in default CORS origins; frontend may run on 5174 if 5173 in use.
- **Root Cause:** effective_cors_origins only includes 5173, 3000, 3002, 8501.
- **Fix:** Add http://localhost:5174 and http://127.0.0.1:5174 to default list or document CORS_ORIGINS for dev.
- **Files Affected:** `backend/app/core/config.py`

### [xgboost_trainer.py] | [🟡] | [Bug]
- **Description:** Raw `duckdb.connect("elite_trading.duckdb", read_only=True)`; hardcoded path bypasses duckdb_store and connection pooling.
- **Root Cause:** Legacy path; not using duckdb_storage.
- **Fix:** Use duckdb_store (e.g. get_thread_cursor) and shared DB path from config/store.
- **Files Affected:** `backend/app/modules/ml_engine/xgboost_trainer.py`

### [Routers] | [🟢] | [Enhancement]
- **Description:** 36 routers have no /health or /ready endpoint; only app-level /healthz, /readyz, /health exist.
- **Root Cause:** Routers were not designed with per-service health.
- **Fix:** Add GET /health (or /ready) per router that returns 200 + minimal status, or document that app-level is sufficient.
- **Files Affected:** `backend/app/api/v1/*.py` (stocks, quotes, orders, signals, agents, council, etc.)

### [scheduler.py] | [🟢] | [Enhancement]
- **Description:** APScheduler job start/end not logged per run; only exception and "triggered" logged.
- **Root Cause:** Minimal logging.
- **Fix:** Log start (and optionally end) for each job run for auditability.
- **Files Affected:** `backend/app/jobs/scheduler.py`

---

## PHASE 4 — Agent System Audit (Findings)

### [AgentCommandCenter] | [🟡] | [Gap]
- **Description:** KILL SWITCH only shows toast; no backend call to emergency halt.
- **Root Cause:** No API wired.
- **Fix:** Call POST /api/v1/risk-shield/emergency-action or orders/emergency-stop from KILL SWITCH.
- **Files Affected:** `frontend-v2/src/pages/AgentCommandCenter.jsx`

### [SwarmOverviewTab] | [🟡] | [Gap]
- **Description:** Restart All, Stop All, Spawn Team, Run Conference, Emergency Kill only show toast; no API.
- **Root Cause:** Buttons not wired to agents batch or council APIs.
- **Fix:** Wire to agentApi.batchRestart/batchStop/batchStart; Run Conference to council trigger if exists; Emergency Kill to same as KILL SWITCH.
- **Files Affected:** `frontend-v2/src/pages/agent-tabs/SwarmOverviewTab.jsx`

### [RemainingTabs / BlackboardCommsTab] | [🟡] | [Gap]
- **Description:** HITL list and Approve/Reject are mock; no useHitlBuffer or approve/reject API.
- **Root Cause:** Hardcoded hitlBuffer and toast.
- **Fix:** Use useApi("agentHitlBuffer") and postHitlDecision (same as SwarmOverviewTab HITLQueue).
- **Files Affected:** `frontend-v2/src/pages/agent-tabs/RemainingTabs.jsx`

### [SpawnScaleTab] | [🟡] | [Gap]
- **Description:** EXECUTE PROMPT, Quick Spawn templates, Active Spawned table "Kill" are UI-only; no spawn/kill API.
- **Root Cause:** No backend for dynamic spawn/kill.
- **Fix:** Add spawn/kill APIs and wire buttons, or mark "coming soon" and hide/disable.
- **Files Affected:** `frontend-v2/src/pages/agent-tabs/SpawnScaleTab.jsx`

### [AgentRegistryTab / agents.py] | [🟢] | [Bug]
- **Description:** Table expects status (e.g. "Running"), cpu, mem; backend returns status ("running"), cpuPercent, memoryMb. Status filter uses "Running"/"Stopped"; backend uses "running"/"stopped".
- **Root Cause:** API shape and casing differ from UI expectations.
- **Fix:** Normalize in API (alias cpu/cpuPercent, mem/memoryMb, status capitalization) or map in frontend; use same casing for filter.
- **Files Affected:** `frontend-v2/src/pages/agent-tabs/AgentRegistryTab.jsx`, `backend/app/api/v1/agents.py`

### [agents.py] | [🟢] | [Enhancement]
- **Description:** HITL buffer is in-memory; lost on restart.
- **Root Cause:** _hitl_buffer in agents.py is process-local.
- **Fix:** Persist to DB or Redis if HITL must survive restarts.
- **Files Affected:** `backend/app/api/v1/agents.py`

### [agents.py] | [🟢] | [Enhancement]
- **Description:** GET /agents/flow-anomalies always returns empty list; no anomaly detection implemented.
- **Root Cause:** Placeholder endpoint.
- **Fix:** Implement or document as placeholder.
- **Files Affected:** `backend/app/api/v1/agents.py`

---

## PHASE 5 — ML Brain & Signal Intelligence Audit (Findings)

### [Flywheel / outcome_resolver] | [🔴] | [Bug]
- **Description:** Flywheel KPIs and history (accuracy30d, history) stay empty or stale; dashboard does not reflect resolved outcomes. outcome_resolver is updated on fill; flywheel_data is only updated by POST /flywheel/record; no job syncs outcome_resolver → flywheel_data.
- **Root Cause:** Two separate stores; no automatic sync.
- **Fix:** In daily_outcome_update.run() (or a dedicated job), after reading get_flywheel_metrics(), call flywheel record (e.g. shared record_flywheel() with accuracy/resolved counts) or have flywheel API read from outcome_resolver when flywheel_data history is empty.
- **Files Affected:** `backend/app/jobs/daily_outcome_update.py`, `backend/app/api/v1/flywheel.py`, optionally `backend/app/modules/ml_engine/outcome_resolver.py`

### [MLBrainFlywheel.jsx] | [🟡] | [Gap]
- **Description:** "Deployed Inference Fleet" shows static green "running" pulse; KPIs fall back to hardcoded defaults (e.g. 91.4%, 24 ignitions). No use of /flywheel/scheduler or /flywheel/engine for status.
- **Root Cause:** No API for scheduler/engine status; fallbacks are static.
- **Fix:** Use useApi('flywheelScheduler') or flywheelEngine for status; show "Running" only when scheduler reports running; label or reduce default fallbacks.
- **Files Affected:** `frontend-v2/src/pages/MLBrainFlywheel.jsx`

### [flywheel.py] | [🟡] | [Gap]
- **Description:** /flywheel/models and /flywheel/features always return empty list; no backend logic to populate from registry or feature pipeline.
- **Root Cause:** Stub implementations.
- **Fix:** Populate from model_registry.get_all_champions() and feature pipeline manifest, or return 404/"not available" with clear message.
- **Files Affected:** `backend/app/api/v1/flywheel.py`

### [signals.py / SignalIntelligenceV3] | [🟡] | [Gap]
- **Description:** EventDrivenSignalEngine live signals are not part of GET /signals/; page shows LSTM + TurboScanner only. Live signal.generated stream not aggregated for the page.
- **Root Cause:** GET /signals/ aggregates LSTM and TurboScanner only; EventDrivenSignalEngine only publishes to MessageBus.
- **Fix:** Document that "Signal Intelligence" = API snapshot; optionally add "live signals" feed from WS or small buffer of recent signal.generated for the page.
- **Files Affected:** `backend/app/api/v1/signals.py`, `frontend-v2/src/pages/SignalIntelligenceV3.jsx`, docs

### [backtest_routes.py] | [🟡] | [Gap]
- **Description:** /backtest/results, /optimization, /walkforward, /montecarlo, /rolling-sharpe, /trade-distribution, etc. return zeros/empty; stub payloads.
- **Root Cause:** Implementations return static stubs.
- **Fix:** Implement from BacktestEngine or strategy/backtest.py (persist run results and serve from DB), or return 501 "Not implemented" and hide/disable in UI until ready.
- **Files Affected:** `backend/app/api/v1/backtest_routes.py`, `frontend-v2/src/pages/Backtesting.jsx`

### [ml_scorer / model_registry] | [🟡] | [Gap]
- **Description:** Live scoring uses fixed paths (xgb_latest.json, lstm_daily_latest.pt); registry champion is not used for inference. Champion/challenger promotion does not update live inference.
- **Root Cause:** ml_scorer and inference load from config/path, not model_registry.get_champion_model_path().
- **Fix:** After champion_challenger promotion, copy or symlink champion artifact to xgb_latest.json (and equivalent for LSTM if used), or have ml_scorer/inference resolve model path via registry.
- **Files Affected:** `backend/app/services/ml_scorer.py`, `backend/app/api/v1/signals.py`, `backend/app/modules/ml_engine/model_registry.py`, trainer/walkforward jobs

### [order_executor.py] | [🟢] | [Enhancement]
- **Description:** outcome_resolver.record_outcome() is called on fill with outcome=1 and prediction=1 if score≥0.5; "outcome" is at entry, not realized P&L.
- **Root Cause:** Outcome recorded at entry fill, not at exit.
- **Fix:** Record outcome when position is closed (or in daily job from trade history) with actual win/loss and optional prediction from signal.
- **Files Affected:** `backend/app/services/order_executor.py`, optionally outcome_tracker / daily job

---

## PHASE 6 — Gap Analysis & Enhancement Ideas

### Critical Bugs (breaks functionality)
| # | Item | Location |
|---|------|----------|
| 1 | Flywheel KPIs/history never auto-updated from outcome_resolver | Backend flywheel_data vs outcome_resolver |
| 2 | Ingestion health returns 200 with error body (breaks 503-based readiness) | backend/app/api/ingestion.py |
| 3 | xgboost_trainer uses raw DuckDB path, bypasses store | backend/app/modules/ml_engine/xgboost_trainer.py |

### Gaps (wired but incomplete)
| # | Item | Location |
|---|------|----------|
| 1 | KILL SWITCH and SwarmOverviewTab quick actions (Restart All, Stop All, etc.) no API | AgentCommandCenter.jsx, SwarmOverviewTab.jsx |
| 2 | Data Sources: Test Connection, Save, LIVE PING, Copy/Rotate, Connection Log | DataSourcesMonitor.jsx |
| 3 | Signal Intelligence: fallback signals array, Download/Upload/Share, Accept/Reject/Watch | SignalIntelligenceV3.jsx |
| 4 | BlackboardCommsTab HITL mock; SpawnScaleTab spawn/kill stubs | RemainingTabs.jsx, SpawnScaleTab.jsx |
| 5 | Backtest results/optimization/walk-forward/Monte Carlo return stubs | backtest_routes.py, Backtesting.jsx |
| 6 | Flywheel models/features endpoints empty; ML Brain "running" static | flywheel.py, MLBrainFlywheel.jsx |
| 7 | Live inference does not use model registry champion | ml_scorer.py, model_registry, jobs |
| 8 | Agent status filter and table field casing (Running vs running) | AgentRegistryTab.jsx, agents.py |

### Enhancement Ideas (prioritized by section)

**Dashboard**
- Real-time P&L with live Alpaca portfolio sync and WebSocket subscription to trades.
- One-click "Execute top signal" from dashboard table (if alignment passes).
- Weight sliders that persist to backend (council/agent weight API).

**Agent Command Center**
- Agent performance leaderboard (which agents generate best signals) from ELO/attribution API.
- Log viewer with WebSocket stream of agent logs (backend already has GET /logs; add WS channel optional).
- Emergency Kill / KILL SWITCH wired to risk-shield or orders emergency-stop.

**Sentiment**
- Sentiment heatmap by sector (aggregate by sector from existing sentiment API).
- Market Events from real feed with timestamps (replace static fallback).

**Data Sources**
- Real connection test and credential save endpoints; wire Test Connection / Save.
- Latency sparklines from API latency history.

**Signal Intelligence**
- One-click trade execution from signal row (already partially present; ensure Accept/Reject/Watch or Execute call real APIs).
- Live signal feed (WS or buffer of signal.generated) alongside LSTM/TurboScanner snapshot.
- Export to CSV/PDF for signals table.

**ML Brain**
- Flywheel status from scheduler/engine API; reduce or label fallback KPIs.
- Model registry and champion deployment: inference path uses champion from registry after promotion.
- Backtesting: implement results/optimization/walk-forward/Monte Carlo from BacktestEngine and persist results.

**Risk & Execution**
- Risk management panel: max drawdown, position sizing calculator (surface existing risk APIs).
- Audit log of all agent decisions and order executions (council_decisions + orders in one view).
- Keyboard shortcuts for power-user trading (e.g. Execute, Flatten, Emergency Stop).

**System-wide**
- Dark/light mode toggle (Aurora theme variants).
- Mobile-responsive layout for monitoring on phone during market hours.
- Anomaly detection alerts pushed to Slack/browser (flow-anomalies endpoint + notification).

---

## Priority Fix Queue — Top 10 (by impact on trading functionality)

| Rank | Priority | Finding | Impact | Files |
|------|----------|---------|--------|-------|
| 1 | 🔴 | **Flywheel data not synced from outcome_resolver** — KPIs/history empty or stale; ML feedback loop broken | High — learning loop ineffective | daily_outcome_update.py, flywheel.py, outcome_resolver.py |
| 2 | 🔴 | **Ingestion health returns 200 on error** — readiness probes cannot detect unhealthy state | High — orchestration/K8s | ingestion.py |
| 3 | 🟡 | **KILL SWITCH and Emergency Kill not wired** — user cannot emergency halt from UI | High — risk control | AgentCommandCenter.jsx, SwarmOverviewTab.jsx, risk_shield or orders API |
| 4 | 🟡 | **Live inference does not use model registry champion** — promoted models never used in production scoring | High — ML deployment | ml_scorer.py, model_registry, champion_challenger job |
| 5 | 🟡 | **xgboost_trainer raw DuckDB connection** — bypasses pool; wrong path risk | Medium — stability | xgboost_trainer.py |
| 6 | 🟡 | **Signal Intelligence fallback mock signals** — violates no-mock rule; misleading | Medium — trust | SignalIntelligenceV3.jsx |
| 7 | 🟡 | **Backtest results/optimization/walk-forward stubs** — Backtesting page shows non-real data | Medium — strategy validation | backtest_routes.py, Backtesting.jsx |
| 8 | 🟡 | **Data Sources Test Connection / Save not wired** — credentials and health check not usable from UI | Medium — ops | DataSourcesMonitor.jsx, backend settings/data-sources |
| 9 | 🟡 | **BlackboardCommsTab HITL mock** — HITL flow inconsistent across tabs | Medium — human-in-the-loop | RemainingTabs.jsx |
| 10 | 🟡 | **SwarmOverviewTab Restart All / Stop All / Spawn Team not wired** — bulk agent control missing | Medium — ops | SwarmOverviewTab.jsx, agents batch API |

---

## Appendix: Audit Method

- **Phase 1–2:** Frontend pages, Sidebar, WebSocket, hooks, api.js, services (parallel explore/code-explorer agents).
- **Phase 3:** Backend main.py, 44 routers, health endpoints, CORS, auth, DuckDB usage, scheduler, integrations (parallel explore agent).
- **Phase 4:** Agent Command Center buttons → API trace, agents.py routes, status/logs/HITL, council vs /agents (code-explorer agent).
- **Phase 5:** ML Brain flywheel loop, Signal Intelligence sources, signal→order trace, backtesting, model persistence (code-explorer agent).
- **Cross-check:** Grep for 501/NotImplementedError, ingestion health implementation, risk/config and sentiment/discover routes.

All findings use the format: **[PAGE/SERVICE]** | **[SEVERITY: 🔴/🟡/🟢]** | **[CATEGORY: Bug/Gap/Enhancement]** with Description, Root Cause, Fix, and Files Affected.
