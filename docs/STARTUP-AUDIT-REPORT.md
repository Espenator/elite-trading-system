# Full Startup Audit Report — Post-Pull 20a5206 → 7733d28

**Date:** March 13, 2026  
**Scope:** Static analysis (no app start). Repo: primary `C:\Users\Espen\elite-trading-system` (commands); fixes applied in workspace.

---

## Phase 1 Results Summary

| Check | Result | Notes |
|-------|--------|--------|
| 1a MessageBus vs VALID_TOPICS | 4 topics published but not in VALID_TOPICS; 1 call missing await | See below |
| 1b Backend `import app.main` | **PASS** | CORS warning only (non-blocking) |
| 1c DuckDB schema | **ENV** | DB locked by another process (PID 25624); cannot verify tables |
| 1d Frontend build | **FAIL** | api.js:40 — `??` and `||` without parentheses (esbuild) |
| 1e Settings/.env | **PASS** | Config loaded OK |
| 1f Ports 8000, 5173 | **PASS** | No conflicts |

---

## STARTUP BLOCKERS FOUND

### CRITICAL (prevents startup or build)

1. **[CRITICAL] Frontend build fails — `??` and `||` without parentheses**  
   **File:** `frontend-v2/src/config/api.js:40`  
   **What’s wrong:** `WS_URL: import.meta.env.VITE_WS_URL ?? _deriveWsFromBackend(...) || _DEFAULT_WS` — esbuild/vite transform rejects mixing `??` and `||` without parentheses.  
   **Fix:** Use parentheses so the `??` expression is evaluated first:  
   `WS_URL: (import.meta.env.VITE_WS_URL ?? _deriveWsFromBackend(import.meta.env.VITE_BACKEND_URL ?? "")) || _DEFAULT_WS`

2. **[CRITICAL] TradeExecution.jsx — esbuild parse error on `#` in JSX className**  
   **File:** `frontend-v2/src/pages/TradeExecution.jsx` (around line 300, Daily P/L span)  
   **What’s wrong:** `className={(...)? "text-[#00e676]" : "text-red-400"}` — esbuild reported "Expected '>' but found '\"'" when parsing the attribute (likely the `#` in the Tailwind arbitrary value).  
   **Fix:** Use a standard Tailwind class instead of an arbitrary value, e.g. `text-emerald-400` instead of `text-[#00e676]`. Applied via PowerShell replace on primary; workspace copy fixed in editor.

3. **[CRITICAL] DuckDB file locked by another process (runtime)**  
   **Context:** `get_connection()` raised: `IOException: File is already open in C:\Python313\python.exe (PID 25624)`.  
   **What’s wrong:** Another Python process holds the DuckDB file; backend startup or health checks that touch DuckDB will fail until the lock is released.  
   **Fix:** Stop the other process using the DB (or use a different DB path for dev). Not a code bug — environment/process cleanup.

### WARNING (app may start but features broken or logs noisy)

4. **[WARNING] MessageBus topics published but not in VALID_TOPICS**  
   **File:** `backend/app/core/message_bus.py` (VALID_TOPICS set)  
   **Topics used in code but not in VALID_TOPICS:**  
   - `emergency.flatten` — `order_executor.py:1650`  
   - `briefing.generated` — `briefing_service.py:307`  
   - `signal.overnight_gap` — `off_hours_monitor.py:128`  
   - `data.staleness_alert` — `off_hours_monitor.py:161`  
   **What’s wrong:** `publish()` drops events for unregistered topics and logs ERROR.  
   **Fix:** Add these four topics to `VALID_TOPICS` in `message_bus.py`.

5. **[WARNING] briefing_service calls MessageBus.publish without await**  
   **File:** `backend/app/services/briefing_service.py:307`  
   **What’s wrong:** `bus.publish("briefing.generated", {...})` — `publish()` is async; calling it without `await` leaves a coroutine unscheduled and can cause subtle failures.  
   **Fix:** Use `await bus.publish(...)`. Caller must be in an async context (it is — `generate_briefing` is async).

6. **[WARNING] CORS_ORIGINS empty in production**  
   **File:** `app.core.config` (Settings)  
   **What’s wrong:** Config logs: "CORS_ORIGINS is empty in production. Only localhost and null (Electron file://) origins are allowed."  
   **Fix:** Set `CORS_ORIGINS` in `.env` when deploying to non-localhost (optional for local dev).

---

## DuckDB Expected Tables (from init_schema)

If the DB is not locked, `_init_schema_internal` in `duckdb_storage.py` creates these 33 tables:

daily_ohlcv, symbol_registry, technical_indicators, options_flow, macro_data, trade_outcomes, ml_features_cache, features, daily_features, daily_predictions, model_evals, postmortems, ingestion_events, pending_liquidations, job_state, swarm_prices, flow_signals, screener_signals, futures_prices, llm_calls, adaptive_routing, debate_logs, red_team_logs, agent_memories, heuristics, knowledge_edges, agent_calibration, debate_history, council_decisions, circuit_breaker_events, llm_predictions, llm_calibration

No schema mismatch was found in code; the only issue observed was the file lock.

---

## Phase 3–4 Fixes Applied

- **CRITICAL #1:** `frontend-v2/src/config/api.js` line 40 — added parentheses so `??` is evaluated before `||` (primary repo fixed).
- **CRITICAL #2:** `frontend-v2/src/pages/TradeExecution.jsx` — replaced `text-[#00e676]` with `text-emerald-400` in Daily P/L span (and elsewhere in file on primary) to fix esbuild parse error; workspace copy fixed in editor.
- **WARNING #4:** Added `emergency.flatten`, `briefing.generated`, `signal.overnight_gap`, `data.staleness_alert` to `VALID_TOPICS` in `backend/app/core/message_bus.py` (primary + workspace).
- **WARNING #5:** In `backend/app/services/briefing_service.py`, changed to `await bus.publish(...)` (primary + workspace).

---

## Phase 5 Verification (Primary Repo)

- **Ports:** Killed 8000 (PID 25624), 5173 (PID 53908); DuckDB lock released.
- **Backend:** Started successfully; `startup-audit.log` shows 6-phase lifespan completed with no application ERROR in first ~10s. DuckDB initialized (9 tables, 929412 rows). MessageBus, Council, scouts, and pipeline started.
- **Endpoints:** `GET /api/v1/status` and `GET /api/v1/council/latest` returned 200 OK; `/api/v1/signals` and `/api/v1/portfolio` timed out at 5s (slow first-hit; not a startup blocker).
- **Frontend build:** `npm run build` succeeded after TradeExecution.jsx and api.js fixes.
- **Note:** Alpaca WebSocket later logged "connection limit exceeded" (external API limit); does not block app startup.

## Summary

- **Critical fixes:** api.js `??`/`||` parentheses; TradeExecution.jsx `#` in className (use text-emerald-400); DuckDB lock resolved by stopping other process.
- **Warning fixes:** 4 MessageBus topics added; briefing_service `await bus.publish`.
- **Root cause:** Post-pull 20a5206→7733d28: api.js operator precedence, new topics not in VALID_TOPICS, async publish without await, and esbuild/JSX issue with `#` in Tailwind arbitrary value.
