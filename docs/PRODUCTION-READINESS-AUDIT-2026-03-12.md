# Production Readiness Audit — Embodier Trader
**Date:** March 12, 2026  
**Scope:** Final audit before live trading with real money  
**Method:** Line-by-line verification of mandatory docs, API routes, council/MessageBus/order_executor, CI, safety, frontend-backend wiring, dead code, deployment.

---

## Summary

| Category | Blockers | Should Fix | Nice to Have |
|----------|----------|------------|--------------|
| 1. CI/CD Health | 2 | 2 | 1 |
| 2. Documentation Inconsistencies | 0 | 4 | 0 |
| 3. Phase B Gaps | 0 | 0 | 0 |
| 4. Phase D Gaps | 0 | 0 | 0 |
| 5. Safety Audit | 1 | 3 | 2 |
| 6. Frontend–Backend Wiring | 0 | 2 | 0 |
| 7. Dead Code & Technical Debt | 0 | 2 | 1 |
| 8. Deployment Checklist | 1 | 3 | 2 |

**Total BLOCKERs: 4** (must fix before live trading)

---

## 1. CI/CD HEALTH

### Verified
- **CI workflow** (`.github/workflows/ci.yml`): Backend (pytest + Black/isort/mypy), Frontend (npm ci, lint, build), E2E (Playwright). Risk params validated in env.
- **E2E**: Playwright runs `frontend-v2` with `HAS_BACKEND: "false"` — frontend-only smoke (app boot, 14 routes render, no crash). No backend, no full pipeline.

### 🔴 BLOCKER
1. **pytest-xdist missing**  
   CI runs `pytest tests/ -n 2` (line 67 of `ci.yml`) but `backend/requirements.txt` does **not** list `pytest-xdist`. On a clean install, pytest will fail with "unknown option -n". **Fix:** Add `pytest-xdist` to `backend/requirements.txt` or remove `-n 2` from CI.

2. **E2E does not test full pipeline**  
   E2E is frontend smoke only (load pages, no error boundary). It does **not** test: bar → signal → council → order → fill. A real “E2E gate” for production would require backend + Alpaca paper + pipeline run (or a dedicated E2E job with backend and optional paper run). **Fix:** Either rename the job to “Frontend smoke” or add a separate job that runs with backend and (optionally) exercises one bar→verdict path.

### 🟡 SHOULD FIX
3. **package-lock.json / npm ci**  
   If `frontend-v2/package-lock.json` is stale or out of sync with `package.json`, `npm ci` can fail and PR #157 can stay RED. Verify lockfile is committed and matches package.json.

4. **Test count inconsistency**  
   Collected tests: **1,182** (from `pytest --collect-only`). Docs cite 666, 977, or 1,044. Update all references to a single number (e.g. 1,182) and clarify if that includes only backend or backend+frontend.

### 🟢 NICE TO HAVE
5. **Staging/canary**  
   No staging or canary deployment step before live. For real money, a canary (e.g. paper run in production config, or 1% traffic to new version) would reduce risk.

---

## 2. DOCUMENTATION INCONSISTENCIES

### 🔴 BLOCKER
- None.

### 🟡 SHOULD FIX
1. **Production readiness %**  
   - `project_state.md` §1: “Production-ready (~95%)”.  
   - `PLAN.md` Executive Summary: “approximately **65%** production-ready”.  
   **Action:** Pick one. Recommended: use “~95%” only if Phases A–E are complete and document the remaining 5% (e.g. DLQ persistence, OpenClaw cleanup). Otherwise align PLAN.md with current state.

2. **Test counts**  
   - `project_state.md`: “977+ passing” and “Tests: 977+”.  
   - Root `CLAUDE.md`: “1,044 passing”.  
   - `backend/CLAUDE.md`: “921 tests”, “maintain 921 GREEN”.  
   - Actual collect: **1,182** tests.  
   **Action:** Standardize on “1,182 tests” (or current count) in project_state.md, CLAUDE.md, backend/CLAUDE.md, and .cursorrules.

3. **Version**  
   - `project_state.md` header: “Version: v5.0.0”.  
   - `backend/CLAUDE.md` and `frontend-v2/CLAUDE.md`: “v4.1.0-dev”.  
   **Action:** Set all to v5.0.0 (or your chosen version) and remove “-dev” where you consider the release production-ready.

4. **GitHub issues vs “complete”**  
   `.cursorrules` lists 16 open issues and says “#49, #50, #51, #52 may already be fixed per Phase C completion — VERIFY”. project_state/PLAN say Phases A–E complete. **Action:** Verify in code; close or update issues #49–#52 and any others that are done; or add a short “Resolved in v5” note in the issue body.

### 🟢 NICE TO HAVE
- None.

---

## 3. PHASE B GAPS (PROFIT BLOCKERS)

Per PLAN.md and project_state.md, Phase B is **complete**. Spot checks:

| Item | Status | Notes |
|------|--------|--------|
| Signal gate (regime-adaptive) | Implemented | council_gate.py: BULLISH=55, NEUTRAL=65, BEARISH/CRISIS=75. |
| Short signal (inverted) | Fixed | Independent `_compute_short_composite_score()` in signal_engine. |
| Smart cooldown | Implemented | Regime-adaptive; separate buy/sell cooldowns. |
| Priority queue | Implemented | heapq; max_concurrent=5, burst_concurrent=8. |
| Limit orders / TWAP | Implemented | By notional bands (e.g. &lt;=5k market, 5k–25k limit, &gt;25k TWAP). |
| Partial fill re-execution | Implemented | Retries, market remainder. |
| Viability gate / portfolio heat | Implemented | DuckDB edge; last_equity for heat. |

**Conclusion:** No open Phase B blockers; these are not blocking live trading from a “feature complete” perspective. Remaining risk is calibration (e.g. thresholds), not missing implementation.

---

## 4. PHASE D GAPS

Phase D marked complete in PLAN.md: backfill orchestrator, rate limiter, DLQ (in-memory + Redis fallback), scraper circuit breakers, session scanner. No additional blockers identified for go-live.

---

## 5. SAFETY AUDIT (CRITICAL FOR REAL MONEY)

### Verified
- **Circuit breakers (Gate 2c):** Enforced in `order_executor.py`: leverage &lt;=2x, single-position &lt;=25%, plus regime and drawdown checks. `_check_degraded_and_killswitch()` calls `risk_shield_api.is_entries_frozen()` and rejects when kill switch/freeze is active.
- **Emergency flatten:** `OrderExecutor.emergency_flatten()` with retry, backoff, Slack alert, and recovery task. `POST /api/v1/metrics/emergency-flatten` exists and is auth-protected; tests in `test_e2e_all_functions.py`.
- **Paper/live:** `alpaca_service` forces base URL from `TRADING_MODE` (paper vs live). `validate_account_safety()` runs at startup; on failure, `auto_execute` is forced to False (shadow). App still starts; no orders are auto-executed when validation fails.
- **Kill switch:** risk_shield `kill_switch` cancels orders, closes positions, sets `risk_shield_freeze_entries`; OrderExecutor checks `is_entries_frozen()` before executing.
- **Bearer auth:** `require_auth` in `core/security.py` is fail-closed: if `API_AUTH_TOKEN` is not set, all protected endpoints return 403. No fallback to open.
- **Council down:** OrderExecutor subscribes to `execution.validated_verdict`; if council/TradeExecutionRouter is down, no verdicts are published, so no orders are placed from the pipeline.

### 🔴 BLOCKER
1. **Account validation not fail-closed for startup**  
   If Alpaca account validation fails (e.g. URL/mode mismatch), the app **still starts**; only `auto_execute` is set to False. Manual or API-triggered orders could still be sent through the same `alpaca_service` (which has already forced URL from TRADING_MODE). So the main risk is misconfiguration of TRADING_MODE vs keys, not “app starts and auto-trades on wrong account.” For maximum safety, consider **refusing to start** when validation fails and `TRADING_MODE=live` (e.g. exit(1) or raise in lifespan), so that live mode never runs with a failed check.

### 🟡 SHOULD FIX
2. **Max daily loss kill switch**  
   `MAX_DAILY_LOSS_PCT` exists in config (e.g. 2.0) and in OpenClaw `risk_governor` / `trading_conference`. OrderExecutor and council do not appear to enforce a hard “stop trading when daily P&L &lt; -X%” in one central place. **Recommendation:** Implement a single daily-loss check (e.g. in OrderExecutor or risk_shield) that blocks new orders when daily P&L &lt; -MAX_DAILY_LOSS_PCT and optionally triggers flatten.

3. **DuckDB crash mid-trade**  
   No specific “DuckDB unavailable during execution” path was found. If DuckDB is down, feature/trade-stats/Kelly lookups can fail; behavior is likely exception path and no order or a conservative fallback. **Recommendation:** Document or add a single “DB down → no new orders / flatten only” policy and test it.

4. **Alpaca WebSocket disconnect**  
   Alpaca stream disconnect is handled by reconnection logic; if reconnection fails repeatedly, behavior (e.g. fallback to REST, or halt signals) should be explicit. PLAN.md E4 mentions “After 10 consecutive reconnection failures, stop and alert.” **Recommendation:** Verify this exists in `alpaca_stream_service` (or equivalent) and that no orders are placed on stale or no data.

### 🟢 NICE TO HAVE
5. **API keys in commits**  
   Grep did not find committed secrets; `.env` is gitignored. Keep enforcing no secrets in repo.

6. **Emergency flatten E2E**  
   Tests cover auth and 2xx/5xx for `POST /api/v1/metrics/emergency-flatten`. Full E2E (start backend, set paper, trigger flatten, assert positions closed) would require a running backend and paper account; add if you want a single “flatten works” story in CI.

---

## 6. FRONTEND–BACKEND WIRING GAPS

### Verified
- **api.js:** ~189 endpoint keys; backend has 43 route files under `api/v1/`. Major prefixes (stocks, quotes, orders, system, signals, backtest, agents, council, cns, swarm, risk, strategy, etc.) are registered in `main.py`.
- **Blackboard:** Frontend uses `blackboard`/`cnsBlackboard` → `/cns/blackboard/current`. Backend: `cns.router` at `/api/v1/cns` with `@router.get("/blackboard/current")` → OK.
- **Metrics emergency-flatten:** Frontend can call `getApiUrl('riskShield/emergency-action')` (risk-shield) and backend has `POST /api/v1/metrics/emergency-flatten` (metrics_api with prefix `/api/v1/metrics`). Both exist; frontend may use risk-shield for kill_switch and metrics for flatten — confirm intended usage.
- **Agents:** `/agents`, `/agents/swarm-topology`, `/agents/consensus`, `/agents/elo-leaderboard`, etc. are implemented in `agents.py`.
- **Swarm:** `/swarm/turbo/status`, `/swarm/outcomes/kelly`, `/swarm/positions/managed`, etc. are implemented in `swarm.py`.

### 🔴 BLOCKER
- None identified. No 404s confirmed from the sampled api.js paths.

### 🟡 SHOULD FIX
1. **Backtest stub expectations**  
   `test_e2e_audit_enhancements.py` expects backtest/results, optimization, walkforward, montecarlo to return 200 and a dict. Backtest routes exist and return 200 with stub data. If any of these are still “501 Not Implemented” in production, tests would need to be aligned (expect 501 or implement real logic).

2. **CORS for production**  
   `.env.example` has `CORS_ORIGINS` with localhost. For production, add the real frontend origin(s) and ensure no wildcard in production.

### 🟢 NICE TO HAVE
- None.

---

## 7. DEAD CODE & TECHNICAL DEBT

### Verified
- **OpenClaw:** risk_shield_api imports `app.modules.openclaw.execution.risk_governor`; RiskShield UI and kill_switch use it. Other OpenClaw modules (e.g. Slack/Flask-origin) may be unused. project_state marks “OpenClaw module … mostly dead code; P4 backlog.”
- **SwarmIntelligence vs AgentCommandCenter:** No route or component named “SwarmIntelligence” found; sidebar and App.jsx use “Agent Command Center” at `/agents`. No duplicate route; only ACC is the canonical page.
- **runner.py vs task_spawner:** runner docstring says “33-agent DAG”; health check uses `total_agents=33`; elsewhere (e.g. runner line 805) `total_reg = 35`. Task_spawner registers 17 core + 11 academic edge (plus debate/alt_data). **Inconsistency:** 33 vs 35. Resolve in code and docs.

### 🔴 BLOCKER
- None.

### 🟡 SHOULD FIX
1. **Council agent count (33 vs 35)**  
   Unify: either register and document 35 agents everywhere (runner health, docstrings, PLAN/CLAUDE) or 33. Update `_check_council_health` and runner docstring to match the real registry count.

2. **.cursorrules referenced file**  
   .cursorrules says “ARCHITECTURAL-REVIEW-2026-03-11.md”; that file was not found under `docs/`. Either add it or point to this audit (or another doc).

### 🟢 NICE TO HAVE
3. **OpenClaw cleanup**  
   Remove or isolate unused OpenClaw code to reduce confusion and security surface.

---

## 8. DEPLOYMENT CHECKLIST

### Verified
- **metrics_api prefix:** Router declares `prefix="/api/v1/metrics"`; main includes it without extra prefix → `/api/v1/metrics`, `/api/v1/metrics/emergency-flatten` correct.
- **.env.example:** Large set of vars (Alpaca, data sources, LLM, Redis, risk, API_AUTH_TOKEN, FERNET_KEY, etc.). APP_VERSION in .env.example is 4.1.0; align with v5.0.0 if that’s release version.

### 🔴 BLOCKER
1. **Docker / full stack**  
   Not run in this audit. **Action:** Run `docker-compose up` (or your production compose) and verify backend + frontend + any DB/Redis start and one full request path (e.g. health → council status → one GET from frontend). Fix any missing env or port so that “does it actually work end-to-end” is yes.

### 🟡 SHOULD FIX
2. **Env completeness**  
   Confirm `.env.example` includes every variable used in production (e.g. `STARTUP_BACKFILL_ENABLED`, `EXECUTION_DECISION_EXPIRY_SECONDS`, `ORDER_*`) and that default values are safe for live.

3. **SSL/TLS**  
   No evidence of production TLS termination in repo. If frontend/API are served over HTTPS in prod, document or add TLS (reverse proxy, load balancer, or app-level).

4. **Rate limiting**  
   slowapi is present; confirm that public or sensitive endpoints (e.g. webhooks, login if any) are rate-limited in production.

### 🟢 NICE TO HAVE
5. **Log rotation and monitoring**  
   Document or configure log rotation and a minimal monitoring story (e.g. health, latency, error rate) for production.

6. **Database migrations**  
   DuckDB schema is initialized in code; no formal migration system was seen. Acceptable for current setup; add migrations if you introduce versioned schema changes.

---

## FINAL CHECKLIST — All 🔴 Items (Priority Order)

| # | Item | Effort (rough) | Owner |
|---|------|----------------|------|
| 1 | **Add pytest-xdist to backend/requirements.txt** (or remove `-n 2` from CI) so backend CI passes. | 5 min | Dev |
| 2 | **Define E2E gate:** Either rename current job to “Frontend smoke” or add a separate E2E job that runs with backend (and optionally one bar→verdict path). | 1–2 hrs | Dev |
| 3 | **Account validation fail-closed for live:** When `TRADING_MODE=live` and account validation fails, refuse to start (exit or raise in lifespan) so live mode never runs with a failed check. | 30 min | Dev |
| 4 | **Docker/compose E2E:** Run full stack (e.g. `docker-compose up`), verify backend + frontend + dependencies, and one full request path; fix env/ports as needed. | 1–2 hrs | Dev/Ops |

---

## References

- `project_state.md` (March 12, 2026)
- `PLAN.md` (Phases A–E)
- `.cursorrules`, `CLAUDE.md`, `backend/CLAUDE.md`, `frontend-v2/CLAUDE.md`
- `backend/app/main.py` (lifespan, routers)
- `backend/app/council/runner.py`, `task_spawner.py`
- `backend/app/core/message_bus.py`, `security.py`
- `backend/app/services/order_executor.py`, `alpaca_service.py`
- `backend/app/api/v1/` (agents, swarm, cns, risk_shield_api, metrics_api, backtest_routes)
- `frontend-v2/src/config/api.js`, `App.jsx`
- `.github/workflows/ci.yml`
- `backend/requirements.txt`, `backend/.env.example`
- `docs/ARCHITECTURAL-REVIEW.md` — not found (referenced in .cursorrules as ARCHITECTURAL-REVIEW-2026-03-11.md)
- `docs/MOCKUP-FIDELITY-AUDIT.md` — not found
