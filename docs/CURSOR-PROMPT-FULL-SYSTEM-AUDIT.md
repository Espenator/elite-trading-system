# Cursor Agent Prompt — Full System Audit (Codebase + UI)

> Copy everything below the line into Cursor as a single prompt. Spawn multiple agents to run audits in parallel.

---

Read these files first (in order): `CLAUDE.md`, `project_state.md`, `PLAN.md`

## Mission

You are a **senior engineering auditor** performing a comprehensive deficiency, gap, and shortcoming analysis of the entire Embodier Trader codebase — backend, frontend, council, ML pipeline, infrastructure, and UI. This system trades real money. Every gap you miss is a potential loss. Be ruthless, specific, and actionable.

**Output**: A single structured report (`docs/FULL-SYSTEM-AUDIT-REPORT-2026-03.md`) with every finding categorized by severity, location, and fix effort. No hand-waving. Every finding must reference specific file paths and line numbers where possible.

## System Context

- **Repo**: `elite-trading-system` — Python 3.11 FastAPI backend, React 18/Vite frontend, 35-agent council DAG, DuckDB, Alpaca broker
- **Scale**: 44 API route files (364+ endpoints), 135 service files, 33 council agents, 19 frontend pages, 56 test files (981+ tests)
- **Status**: v5.0.0, Phases A-E complete, Phase F (TradingView integration) in progress
- **Architecture**: Event-driven pipeline — AlpacaStream → SignalEngine → CouncilGate → 35-agent council → OrderExecutor → Alpaca
- **Infra**: Two-PC LAN (ESPENMAIN + ProfitTrader), brain_service gRPC on PC2, Docker-ready
- **New**: TradersPost webhook bridge (paper trading), morning briefing scheduled task, dual-webhook safety pattern

## Audit Scope — 12 Parallel Workstreams

Spawn agents for each workstream. Each agent should produce findings in this format:

```markdown
### [SEVERITY] Finding Title
- **Location**: `path/to/file.py` (lines X-Y)
- **Issue**: What's wrong
- **Impact**: What breaks or what risk this creates
- **Fix**: Specific remediation (code-level, not vague)
- **Effort**: S/M/L (hours estimate)
```

Severity levels: `🔴 CRITICAL` (blocks trading or loses money), `🟠 HIGH` (significant risk or data loss), `🟡 MEDIUM` (degraded functionality), `🔵 LOW` (code quality, tech debt)

---

### WORKSTREAM 1: Backend API Integrity

**Scope**: All 44 files in `backend/app/api/v1/` + `backend/app/api/ingestion.py`

Audit for:
1. **Endpoint correctness**: Do all route handlers call real service methods, or do any return hardcoded/stub data?
2. **Error handling**: Are exceptions caught properly? Do any endpoints swallow errors silently? Are HTTP status codes correct?
3. **Auth enforcement**: Every state-changing endpoint (POST/PUT/DELETE) must require `Bearer` token via `API_AUTH_TOKEN`. Check all of them. Which ones are unprotected?
4. **Input validation**: Are request bodies validated with Pydantic models? Any raw dict access without validation?
5. **Response shape consistency**: Do similar endpoints return consistent shapes? Are there endpoints that return different structures for success vs error?
6. **Dead endpoints**: Any endpoints registered in `main.py` but with no actual implementation? Any that import services that don't exist?
7. **Missing endpoints**: Based on frontend `api.js` config, are there API calls the frontend makes that have no backend endpoint?
8. **Rate limiting**: Which endpoints have rate limits? Which should but don't?

**Key files to cross-reference**: `frontend-v2/src/config/api.js` (189 endpoint definitions), `backend/app/main.py` (router registrations)

---

### WORKSTREAM 2: Service Layer Health

**Scope**: All 135 files in `backend/app/services/` (including subdirs: `scouts/`, `llm_clients/`, `channel_agents/`, `firehose_agents/`, `integrations/`)

Audit for:
1. **Dead code**: Services that are imported nowhere, or have methods never called
2. **Error propagation**: Services that catch exceptions and return `None` or empty dict instead of raising — causing silent failures downstream
3. **Missing graceful degradation**: Services that crash the entire backend if an external API is down (Alpaca, UW, FRED, etc.) vs. those that degrade gracefully
4. **Singleton patterns**: Are services using proper singleton/factory patterns, or creating new instances on every call? Watch for DuckDB connection leaks
5. **Async correctness**: Any blocking calls (`requests.get`, `time.sleep`) inside async functions? These would block the event loop
6. **Configuration**: Services with hardcoded values that should come from env vars or settings
7. **MessageBus integration**: Which services publish events and which should but don't? Cross-reference with `message_bus.py` topic registry
8. **Circular imports**: Any circular dependency chains between services?
9. **External API error handling**: For each data source (Alpaca, UW, Finviz, FRED, EDGAR, NewsAPI, Benzinga, SqueezeMetrics), does the service handle: rate limits, auth expiry, timeouts, malformed responses, empty data?

---

### WORKSTREAM 3: Council Pipeline Integrity

**Scope**: `backend/app/council/` — 15 orchestration files + `agents/` (33 agent files)

Audit for:
1. **Agent completeness**: Do all 35 registered agents have real `evaluate()` implementations? Any that just return `HOLD` with hardcoded confidence?
2. **AgentVote schema compliance**: Every agent must return `AgentVote(agent_name, direction, confidence, reasoning, veto, veto_reason, weight, metadata)`. Check all 33 agent files
3. **Runner DAG correctness** (`runner.py`): Are all 7 stages properly defined? Are agents assigned to correct stages? Are stage dependencies correct?
4. **Arbiter logic** (`arbiter.py`): Is Bayesian weighting mathematically correct? Does it properly handle edge cases (all HOLD, all VETO, empty votes, NaN weights)?
5. **Weight learner** (`weight_learner.py`): Is the Bayesian Beta(α,β) update correct? Does regime-stratified learning work? Is the confidence floor at 0.20 as intended?
6. **CouncilGate** (`council_gate.py`): Does the signal→council→order pipeline handle: concurrent signals, stale signals (>30s), queue overflow, council timeout?
7. **Circuit breakers** (`reflexes/circuit_breaker.py`): Are all 10 breakers enforced (not just advisory)? Do they actually block trades?
8. **Blackboard state** (`blackboard.py`): Is shared state thread-safe? Can concurrent council runs corrupt blackboard data?
9. **HITL gate** (`hitl_gate.py`): Does human-in-the-loop properly pause execution and wait? What happens if the human never responds?
10. **Debate engine**: Do bull/bear debaters and red_team actually influence the final verdict, or is their output ignored?
11. **Data quality** (`data_quality.py`): What happens when data quality is LOW? Does the council still trade, or properly abstain?

---

### WORKSTREAM 4: Order Execution & Risk Management

**Scope**: `backend/app/services/order_executor.py`, `services/kelly_position_sizer.py`, `services/position_manager.py`, `services/alpaca_service.py`, `council/reflexes/circuit_breaker.py`

Audit for:
1. **Order flow correctness**: Trace the full path from `council.verdict` → position sizing → viability check → order submission → fill tracking → outcome recording. Any gaps?
2. **Kelly sizing edge cases**: What happens with negative edge? Zero trades? Win rate of 100% or 0%? Division by zero?
3. **Market/limit/TWAP logic**: Is the notional-based routing correct ($5K/$25K thresholds)? Does TWAP properly handle partial fills across slices?
4. **Partial fill handling**: Does the 3-retry mechanism work? What if Alpaca rejects the remainder order?
5. **Regime gating (Gate 2b)**: Does RED/CRISIS regime actually block new entries? Can this be bypassed?
6. **Circuit breaker gating (Gate 2c)**: Are leverage (2x) and concentration (25%) properly enforced? What's the race condition window?
7. **Portfolio heat**: Is `last_equity` properly updated daily? What happens on the first day when there's no historical equity?
8. **Stop/take-profit**: Are bracket orders (OCO) properly placed with ATR-based levels? What happens if ATR data is missing?
9. **Position tracking**: Does `position_manager.py` properly sync with Alpaca on startup? Are trailing stops initialized for pre-existing positions?
10. **Emergency flatten**: Does it actually work under Alpaca outage? Test the retry + exponential backoff + DuckDB pending_liquidations queue
11. **Paper vs live safety**: Is the `TRADING_MODE` check enforced at startup? Can it be changed at runtime?

---

### WORKSTREAM 5: Frontend UI Completeness

**Scope**: All 19 files in `frontend-v2/src/pages/`, plus `components/`, `hooks/`, `config/api.js`

Audit for:
1. **Data fetching**: Every page should use `useApi()` hook — never raw `fetch()` or hardcoded data. Check all 19 page files
2. **Loading states**: Does every page handle `loading=true` properly? Are there skeleton loaders or just blank screens?
3. **Error states**: When API returns error, does the page show a useful message or silently show nothing?
4. **Empty states**: When API returns empty data (no trades, no signals, no positions), does the page show a helpful empty state?
5. **WebSocket integration**: Which pages consume WebSocket data? Which should but don't? Check `services/websocket.js` consumer list
6. **Responsive design**: Any pages that break at standard breakpoints (1280px, 1024px, 768px)?
7. **Stale data**: Are polling intervals appropriate? Any pages that poll too aggressively (< 5s) or too infrequently (> 60s)?
8. **Action buttons**: For every button that triggers a POST/PUT/DELETE, verify: (a) it calls the right endpoint, (b) it shows loading state, (c) it handles errors, (d) it refreshes data after success
9. **Navigation**: Are all sidebar links correct? Any dead routes? Any pages accessible only via direct URL (no sidebar entry)?
10. **Console errors**: Are there any obvious issues that would produce console errors (missing keys, invalid refs, memory leaks from uncleared intervals)?

---

### WORKSTREAM 6: UI Mockup Fidelity

**Scope**: All 23 mockup images in `docs/mockups-v3/images/` compared against all frontend page files

Audit for:
1. **Layout structure**: Does each page match its mockup's panel layout, grid structure, and visual hierarchy?
2. **Component inventory**: For each mockup panel, is there a corresponding frontend component? List missing panels
3. **Color/typography**: Are colors from `docs/UI-DESIGN-SYSTEM.md`? Is JetBrains Mono loaded? Are card headers ALL CAPS text-xs slate-400?
4. **Chart types**: Do chart components match the visualization type shown in mockups (line vs bar vs area vs heatmap)?
5. **Data density**: Mockups show dense data displays — are frontend components actually rendering that level of detail or showing simplified versions?
6. **Interactive elements**: Buttons, toggles, dropdowns, tabs shown in mockups — are they all implemented and functional?
7. **Priority pages with known gaps** (from previous audit):
   - ACC Swarm Overview: mockup shows 12+ dense panels, code has simple card grid
   - ACC Node Control: missing HITL detail table, Override History, Analytics charts
   - Sentiment: heatmap density, scanner matrix dots, emergency alerts
   - Performance Analytics: Trading Grade badge, Returns Heatmap
   - Trade Execution: order type visualization
   - Risk Intelligence: correlation matrix, VaR charts

---

### WORKSTREAM 7: Test Coverage & Quality

**Scope**: All 56 files in `backend/tests/`

Audit for:
1. **Coverage gaps**: List every service and route file that has NO corresponding test file
2. **Test quality**: Are tests testing real behavior or just that functions don't throw? Look for tests that assert `True` or `is not None` without checking actual values
3. **Mock correctness**: Does `conftest.py` properly mock DuckDB, Alpaca, external APIs? Are mocks realistic?
4. **Edge case coverage**: For critical paths (order execution, Kelly sizing, council verdict, circuit breakers), are edge cases tested? (Zero values, negative values, None, empty lists, concurrent access)
5. **Integration tests**: Any tests that test the full pipeline (signal → council → order)? If not, which integration tests are missing?
6. **Flaky tests**: Any tests that depend on timing, network, or external state? These need mocking
7. **CI configuration**: Does `.github/workflows/` properly run all tests? Are there tests excluded from CI?
8. **Frontend tests**: Are there ANY frontend tests? (Likely not — this is a gap to document)

---

### WORKSTREAM 8: Security & Auth

**Scope**: `backend/app/core/security.py`, auth middleware, `.env.example`, all endpoint auth decorators

Audit for:
1. **Auth enforcement**: Which endpoints require auth? Which should but don't? Especially: order placement, position modification, settings changes, emergency flatten
2. **Token validation**: Is `API_AUTH_TOKEN` properly validated? Can it be bypassed with empty string, None, or malformed header?
3. **CORS policy**: Is CORS properly restrictive or wide-open (`*`)? What origins are allowed?
4. **Secret exposure**: Scan all Python and JS files for hardcoded API keys, tokens, passwords, or connection strings. Check git history too
5. **WebSocket auth**: Does the `/ws` WebSocket endpoint require token authentication? Can unauthenticated clients connect?
6. **Rate limiting**: Is `slowapi` properly configured? Which endpoints are rate-limited?
7. **Input sanitization**: Any SQL injection vectors (unlikely with DuckDB but check)? Any path traversal in file-serving endpoints?
8. **Dependency vulnerabilities**: Run `pip audit` or check `requirements.txt` for known CVEs
9. **HTTPS/TLS**: Is there any TLS configuration, or is everything plain HTTP? (Acceptable for LAN-only, but document the assumption)

---

### WORKSTREAM 9: Data Integrity & Database

**Scope**: `backend/app/data/storage.py`, `data/init_schema.py`, all DuckDB queries across the codebase

Audit for:
1. **Schema completeness**: Is `init_schema.py` creating all tables the codebase expects? Any queries referencing tables that don't exist?
2. **Connection pooling**: Is `get_conn()` properly pooled? Any files that create raw DuckDB connections outside the pool?
3. **Write safety**: DuckDB doesn't support concurrent writers — are all writes serialized? Any race conditions?
4. **Data retention**: Is old data ever cleaned up? Will the DuckDB file grow unbounded? What's the projected size after 1 year of trading?
5. **Backup**: Is there any backup mechanism for the DuckDB file? What happens if it corrupts?
6. **Schema migrations**: How are schema changes handled? Is there a migration mechanism, or does `init_schema.py` just `CREATE TABLE IF NOT EXISTS`?
7. **Query performance**: Any obviously slow queries (full table scans, missing indexes, N+1 patterns)?
8. **Trade audit trail**: Is every trade decision, fill, and outcome recorded with enough detail for postmortem? Can we reconstruct WHY any given trade happened?

---

### WORKSTREAM 10: Infrastructure & Deployment

**Scope**: `docker-compose.yml`, `.github/workflows/`, `desktop/`, `scripts/`, `start-embodier.ps1`, `launch.bat`

Audit for:
1. **Docker**: Does `docker-compose.yml` correctly define all services? Are ports, volumes, env vars correct? Can the full stack start with `docker-compose up`?
2. **CI/CD pipeline**: What does the GitHub Actions workflow test? Does it test backend + frontend + E2E? What's missing?
3. **Desktop app** (`desktop/`): Is the Electron app properly configured? Does it correctly spawn the backend and serve the frontend?
4. **Startup scripts**: Do `start-embodier.ps1` and `launch.bat` handle errors (venv not found, port already in use, DuckDB locked)?
5. **Two-PC sync**: How is code synced between ESPENMAIN and ProfitTrader? Is there a deployment script for PC2?
6. **Environment consistency**: Is `backend/.env.example` complete? Any env vars referenced in code but missing from the example?
7. **Log management**: Where do logs go? Are they rotated? What happens when disk fills up?
8. **Health checks**: Are `/healthz` and `/readyz` comprehensive? Do they check all critical dependencies (DuckDB, Alpaca connection, MessageBus)?
9. **Monitoring**: Is there any monitoring/alerting beyond Slack notifications? Any metrics export (Prometheus, StatsD)?
10. **Recovery**: After a crash, can the system fully recover automatically? What manual steps are required?

---

### WORKSTREAM 11: ML Pipeline & Intelligence

**Scope**: `backend/app/modules/ml_engine/`, `services/signal_engine.py`, `features/feature_aggregator.py`, `council/weight_learner.py`, `council/calibration.py`

Audit for:
1. **Model staleness**: How often are XGBoost models retrained? Is `ML_RETRAIN_INTERVAL_HOURS=168` (weekly) appropriate? What happens if retraining fails?
2. **Feature drift**: Does `drift_detector.py` actually catch meaningful drift, or just statistical noise? What action is taken on drift detection?
3. **Feature sync**: Are features computed identically in `signal_engine.py` (inference) and `ml_training.py` (training)? Feature skew is a common silent killer
4. **Signal scoring**: Is the blended signal score (momentum, MACD, RSI, volume, etc.) well-calibrated? Are the weights (momentum +-25, MACD +-5) ever validated?
5. **Regime detection**: Is the HMM/Bayesian regime detection producing meaningful regimes, or are transitions too frequent/infrequent?
6. **Overfitting guard** (`overfitting_guard.py`): Does it actually prevent deploying overfit models? What metrics does it check?
7. **Walk-forward validation**: Is it implemented correctly? Are train/test splits time-respecting (no future data leakage)?
8. **Weight learner feedback loop**: Is the Brier calibration working? Are poorly-calibrated agents actually being penalized?
9. **Data quality impact**: When `feature_aggregator.py` returns empty or partial data, how does the signal engine handle it? Does it produce garbage signals?

---

### WORKSTREAM 12: TradingView Integration (Phase F)

**Scope**: `docs/TRADING-ASSISTANT-PLAN.md`, `docs/CURSOR-PROMPT-TRADING-ASSISTANT.md`, `docs/TRADING-ASSISTANT-RESEARCH.md`, and any existing implementation files

Audit for:
1. **Implementation status**: Which of the 7 planned files (briefing_service, tradingview_bridge, 2 API routes, frontend page, tests) actually exist vs. are still planned?
2. **Webhook security**: Is the TradersPost webhook URL stored securely? Can the monitoring webhook (webhook.site) leak trade signals to the public?
3. **Safety gate**: Is `execute=False` truly the default everywhere? Can it be accidentally set to `True` through any code path?
4. **Payload format**: Does the TradersPost payload format match their actual API spec? Test with: `{"ticker": "AAPL", "action": "buy", "sentiment": "bullish", "price": 178.50, "time": "2026-03-12T09:00:00Z"}`
5. **Scheduled task**: Is the `morning-trade-briefing` cron job (9 AM ET weekdays) properly configured? What timezone is it using?
6. **Failure modes**: What happens if: webhook.site is down? TradersPost is down? Alpaca rejects the order? Signal data is stale?
7. **Dual-system conflicts**: Can Embodier Trader and TradingView submit conflicting orders simultaneously? Is there a coordination mechanism?

---

## Output Format

Produce a single markdown report `docs/FULL-SYSTEM-AUDIT-REPORT-2026-03.md` with this structure:

```markdown
# Full System Audit Report — Embodier Trader v5.0.0
# Date: March 2026
# Auditor: Cursor Agent Swarm

## Executive Summary
- Total findings: X
- 🔴 CRITICAL: X findings
- 🟠 HIGH: X findings
- 🟡 MEDIUM: X findings
- 🔵 LOW: X findings
- Top 5 findings that should be fixed before live trading

## Findings by Workstream

### 1. Backend API Integrity
[findings...]

### 2. Service Layer Health
[findings...]

[...continue for all 12 workstreams...]

## Recommended Fix Order
1. All 🔴 CRITICAL findings (in priority order)
2. All 🟠 HIGH findings grouped by component
3. Estimated total effort for CRITICAL + HIGH fixes

## Appendix: Files Audited
[List every file that was read during the audit]
```

## Rules

1. **Be specific**: "auth is missing on some endpoints" is useless. "`POST /api/v1/orders` at `orders.py:47` has no auth decorator" is useful.
2. **No false positives**: Only report actual issues. If something looks suspicious but works correctly, note it as `🔵 LOW` with explanation.
3. **Cross-reference**: When a frontend page calls an API that's broken, report it once under the more relevant workstream but note the cross-impact.
4. **Read the code**: Don't just grep for patterns — understand the logic. A service that returns `{}` on failure might be intentional graceful degradation or a silent bug. Check the callers.
5. **Respect what works**: The system has 981+ passing tests and has gone through 5 phases of hardening. Not everything is broken. Acknowledge what's solid.
6. **Trading context**: This is a trading system. Issues that could cause: wrong order size, missed stop-loss, stale data trading, or unintended live execution are automatically `🔴 CRITICAL`.
7. **Never use yfinance**: If you find any yfinance imports or references, flag as `🔴 CRITICAL`.
8. **Never add mock data**: If you find hardcoded/mock data in production paths, flag as `🟠 HIGH`.
