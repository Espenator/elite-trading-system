# UI / Backend Gap Audit

## Scope
- Frontend audited from `frontend-v2/src/App.jsx`, routed page files in `frontend-v2/src/pages/`, Agent Command Center tab files in `frontend-v2/src/pages/agent-tabs/`, and shared layout chrome in `frontend-v2/src/components/layout/`.
- Backend truth audited from `backend/app/api/v1/*.py`, websocket wiring, and `frontend-v2/src/config/api.js`.
- Visual target audited from `docs/UI-DESIGN-SYSTEM.md`, `docs/mockups-v3/FULL-MOCKUP-SPEC.md`, and `docs/mockups-v3/images/*`.

## Method
1. Enumerate routes from `App.jsx`.
2. Map `useApi(...)`, direct fetches, and websocket subscriptions to backend routes.
3. Search for `FALLBACK_*`, hardcoded arrays, toast-only actions, and decorative status text.
4. Compare current behavior to backend truth and mockup intent.
5. Implement a first P0/P1 truth pass where scope was safe and localized.

## Severity
- **P0** fake or misleading UI, dead controls, dangerous trust break
- **P1** missing control/visibility for existing backend capability, wrong mapping, stale labels
- **P2** incomplete loading/empty/error/stale/disconnect handling
- **P3** polish / visual fidelity only

## Cross-cutting findings

| Severity | Finding | Source | Truth source | Recommended fix |
|---|---|---|---|---|
| P0 | Shared footer shipped with hardcoded market values and default regime text. | `frontend-v2/src/components/layout/StatusFooter.jsx` | `/api/v1/market/indices`, `/api/v1/openclaw/regime` | **Implemented:** remove fake defaults; show real data or explicit zero-state. |
| P0 | Multiple pages still show optimistic connection labels or destructive controls without backend verification. | `AgentCommandCenter.jsx`, `Dashboard.jsx`, `DataSourcesMonitor.jsx`, `Settings.jsx` | `/api/v1/status`, websocket client state, `/api/v1/orders/emergency-stop` | Wire or remove each control/badge. |
| P0 | Several pages still rely on static arrays/fallback objects that look like live operator data. | `RemainingTabs.jsx`, `PerformanceAnalytics.jsx`, `MLBrainFlywheel.jsx`, `SignalIntelligenceV3.jsx`, `DataSourcesMonitor.jsx`, `TradeExecution.jsx` | Mixed backend routes; some backend endpoints are themselves still stub-like | Replace fake content with real data or explicit unavailable states. |
| P1 | Some components mis-parse backend payloads and silently fall back to demo rows. | `AgentCommandCenter.jsx`, `SwarmOverviewTab.jsx`, `RemainingTabs.jsx` | `/api/v1/agents`, `/api/v1/agents/elo-leaderboard`, `/api/v1/system/event-bus/status` | **Implemented for Agent Command Center:** normalize actual response shapes first. |
| P1 | Freshness / stale-state / source attribution are inconsistent across the app. | most routed pages | `useApi` already exposes `lastUpdated` and `isStale` | Add consistent freshness UI before further fidelity polish. |
| P2 | Recent GitHub Actions workflow runs end in `action_required` with zero jobs exposed. | repo workflow `CI - Lint & Test` | Actions API inspection | Treat as workflow-side blocker; rely on local validation until workflow config is fixed. |

---

## Page-by-page audit

### 1. Dashboard (`/dashboard`)
- **Owner:** `frontend-v2/src/pages/Dashboard.jsx`
- **Visual refs:** `docs/mockups-v3/images/02-intelligence-dashboard.png`, `docs/UI-DESIGN-SYSTEM.md`
- **Backend sources:** `market.py`, `portfolio.py`, `performance.py`, `signals.py`, `risk.py`, `agents.py`, `sentiment.py`, `openclaw.py`, websocket service

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Emergency stop control | Decorative / toast-style control instead of real broker stop request. | Reuse truthful stop flow now added in Agent Command Center. |
| P0 | Connection / health chrome | Still has dashboard-specific status text instead of consistent truth-driven footer/header state. | Replace with the same backend-driven pattern used in shared layout chrome. |
| P1 | Operator drilldowns | Backend alerts, cognitive data, and data-source health exist but are not surfaced strongly. | Add drilldowns/hotlinks from KPI cards. |
| P2 | Edge states | Several panels collapse to blank or minimal UI on empty/error. | Add loading / empty / stale / error states with timestamps. |

### 2. Agent Command Center (`/agents`)
- **Owner:** `frontend-v2/src/pages/AgentCommandCenter.jsx`, `frontend-v2/src/pages/agent-tabs/*.jsx`
- **Visual refs:** `01-agent-command-center-final.png`, `05-agent-command-center.png`, `05b-agent-command-center-spawn.png`, `05c-agent-registry.png`
- **Backend sources:** `agents.py`, `system.py`, `council.py`, `ml_brain.py`, `orders.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Header metrics | Frontend previously misread `/api/v1/agents` and invented fleet metrics. | **Implemented:** normalize `{ agents }` payload and remove fake fallbacks. |
| P0 | Emergency stop button | Previously toast-only. | **Implemented:** wire to `POST /api/v1/orders/emergency-stop`. |
| P0 | Footer strip | Previously hardcoded websocket/API/topic/load values. | **Implemented:** use real websocket state, API health, topic count, alerts, mode, refresh time. |
| P0 | Blackboard & Comms topic table / HITL queue | Previously static topic rows and fake approval items. | **Implemented:** use `/api/v1/system/event-bus/status` and `/api/v1/agents/hitl/buffer`. |
| P1 | ELO leaderboard | Payload shape mismatch caused fallback leaderboard rows. | **Implemented:** parse `{ leaderboard }` and show real empty state. |
| P1 | Conference history | Backend exposes latest conference and DAG config, not the rich multi-row history shown before. | Keep latest conference only until backend history exists. |
| P1 | ML Ops | Training and drift cards previously used fake rows. | **Implemented:** show real registry/drift data or explicit empty state. |
| P2 | Remaining tab controls | Live Wiring / Spawn / Registry still need per-control truth review. | Audit every interactive control before leaving it enabled. |

### 3. Sentiment Intelligence (`/sentiment`)
- **Owner:** `frontend-v2/src/pages/SentimentIntelligence.jsx`, `frontend-v2/src/hooks/useSentiment.js`
- **Backend source:** `backend/app/api/v1/sentiment.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Symbol/source grids | Static visual lists still shape the page even when backend summary differs. | Make all grids derive only from `summary.heatmap`, `summary.sourceHealth`, and `summary.signals`. |
| P1 | Source attribution | Backend exposes source health and divergences, but page hides freshness/source context in places. | Add last-updated and source labels per card. |
| P2 | Trend chart states | Blank chart does not distinguish no history vs fetch failure. | Add explicit no-history/error state. |

### 4. Data Sources Monitor (`/data-sources`)
- **Owner:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`
- **Backend source:** `backend/app/api/v1/data_sources.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Source inventory and metrics | Page still contains hardcoded source definitions and performance values. | Render only backend-reported sources and fields. |
| P1 | Health / latency visibility | Mockup expects freshness, latency, limits, and config detail, but truth surface needs verification first. | Keep only truthful fields; document backend blockers instead of faking more charts. |
| P2 | Decorative websocket badge | Badge implies per-source stream health without a clear backend contract. | Bind it to real state or remove it. |

### 5. Signal Intelligence V3 (`/signal-intelligence-v3`)
- **Owner:** `frontend-v2/src/pages/SignalIntelligenceV3.jsx`
- **Backend sources:** `signals.py`, `agents.py`, `openclaw.py`, `data_sources.py`, `sentiment.py`, `training.py`, `ml_brain.py`, `patterns.py`, `risk.py`, `alerts.py`, `status.py`, `performance.py`, `market.py`, `portfolio.py`, `strategy.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Scanner/module states | Page still uses hardcoded scanners, all-green state, zeroed metrics, and default websocket latency. | Replace every static state array with backend-driven or clearly blocked UI. |
| P1 | Endpoint registry panel | Decorative endpoint list is not a real health monitor. | Replace with actual health results or remove it. |
| P1 | Agent lists | Silent empty fallbacks hide backend failure or empty state. | Show explicit diagnostics when agents cannot be loaded. |

### 6. ML Brain & Flywheel (`/ml-brain`)
- **Owner:** `frontend-v2/src/pages/MLBrainFlywheel.jsx`
- **Backend sources:** `backend/app/api/v1/flywheel.py`, `backend/app/api/v1/ml_brain.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P1 | KPI/model/log fallbacks | Page merges empty fallback structures into real payloads. | Show truthful empty states rather than operator-looking default values. |
| P1 | Registry/drift visibility | Real registry and drift info exists but is not surfaced strongly on this page. | Promote champion/challenger, latest runs, and drift state. |
| P2 | Decorative sparklines | Sparkline structure remains even when no real series exists. | Hide sparkline visuals when the series is empty. |

### 7. Screener & Patterns (`/patterns`)
- **Owner:** `frontend-v2/src/pages/Patterns.jsx`
- **Backend sources:** `backend/app/api/v1/patterns.py`, `signals.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P1 | Zero-state semantics | Page prefers silent empty arrays when there are no patterns/signals/feed messages. | Add explicit no-pattern, no-feed, and backend-error states. |
| P1 | Missing controls | If backend supports scan filters/config, page should expose them. | Audit request params in `patterns.py` and surface them. |

### 8. Backtesting Lab (`/backtest`)
- **Owner:** `frontend-v2/src/pages/Backtesting.jsx`
- **Backend source:** `backend/app/api/v1/backtest_routes.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Run history truth | Backtesting is operator-critical; any static run/strategy examples on either side are unacceptable. | Audit `backtest_routes.py` and remove any static run history before claiming parity. |
| P1 | Strategy/symbol controls | Frontend should not ship hardcoded strategy universes if backend owns them. | Fetch registries from backend or mark unsupported selectors as unavailable. |
| P2 | Chart states | Charts degrade to empty arrays with minimal explanation. | Add dataset-empty and run-selection context. |

### 9. Performance Analytics (`/performance`)
- **Owner:** `frontend-v2/src/pages/PerformanceAnalytics.jsx`
- **Backend sources:** `backend/app/api/v1/performance.py`, `agents.py`, `risk.py`, `flywheel.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P1 | KPI/trade/leaderboard fallbacks | Large fallback objects/arrays hide whether the backend actually has history. | Remove fallback values and show no-history state with source attribution. |
| P1 | Attribution depth | Agent/conference context exists but is not explained with freshness/source. | Add timestamps and source labels. |

### 10. Market Regime (`/market-regime`)
- **Owner:** `frontend-v2/src/pages/MarketRegime.jsx`
- **Backend sources:** `backend/app/api/v1/openclaw.py`, `strategy.py`, `risk.py`, `market.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P1 | Default regime parameters | Page still keeps default regime parameter objects. | Render unavailable/config-missing state instead of defaults. |
| P1 | Missing diagnostics | Bridge health, transitions, whale flow, and memory intelligence need clearer freshness/error handling. | Add source/freshness treatment to each panel. |

### 11. Active Trades (`/trades`)
- **Owner:** `frontend-v2/src/pages/Trades.jsx`
- **Backend sources:** `backend/app/api/v1/alpaca.py`, `portfolio.py`, `orders.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P1 | Refresh model | Real broker data is poll-driven but freshness/disconnect treatment is weak. | Add timestamps and websocket-backed updates where possible. |
| P1 | Operator controls | Backend supports flatten/emergency actions that should be reachable here. | Surface admin-gated controls with clear error/auth messaging. |

### 12. Risk Intelligence (`/risk`)
- **Owner:** `frontend-v2/src/pages/RiskIntelligence.jsx`
- **Backend sources:** `backend/app/api/v1/risk.py`, `risk_shield_api.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Safety check defaults | PASS-style defaults are misleading on a risk page. | Render unknown/unavailable until backend supplies a real assessment. |
| P1 | Existing backend controls | Risk/risk-shield exposes meaningful controls and emergency actions. | Audit every destructive action for real wiring and visibility. |

### 13. Trade Execution (`/trade-execution`)
- **Owner:** `frontend-v2/src/pages/TradeExecution.jsx`
- **Backend sources:** `backend/app/api/v1/orders.py`, `alpaca.py`, `quotes.py`, `alignment.py`, `council.py`, `stocks.py`

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Strategy/options/news chrome | Any hardcoded strategy or news framing is misleading in order entry. | Remove static lists; fetch real strategy/context sources or mark unavailable. |
| P1 | Missing visibility | Alignment verdicts, council rationale, and broker/account state need stronger source/timestamp treatment. | Add source attribution, auth-aware failures, and freshness near submit flow. |

### 14. Settings (`/settings`)
- **Owner:** `frontend-v2/src/pages/Settings.jsx`
- **Backend sources:** `backend/app/api/v1/settings_routes.py`, `system.py`, `device` endpoint, auth helpers

| Severity | Component / element | Finding | Recommended fix |
|---|---|---|---|
| P0 | Connection badges | Several badges imply live connectivity without direct validation. | Bind every badge to a real validation call or restyle as neutral config state. |
| P1 | Persistence / audit visibility | Settings should reflect real persisted config, reset semantics, and audit log coverage. | Audit every tab against `settings_routes.py`; remove unsupported toggles and expose real flows. |

---

## First implementation pass completed in this branch
- `frontend-v2/src/pages/AgentCommandCenter.jsx`
  - real `/agents` payload parsing
  - real emergency-stop wiring
  - real header/footer status values
- `frontend-v2/src/pages/agent-tabs/RemainingTabs.jsx`
  - real MessageBus topics
  - real HITL buffer + approve/reject requests
  - real council/latest registry/drift/logs parsing with empty states
- `frontend-v2/src/pages/agent-tabs/SwarmOverviewTab.jsx`
  - real ELO leaderboard parsing
- `frontend-v2/src/components/layout/Layout.jsx`
  - shared footer now fed from real market/status/regime endpoints
- `frontend-v2/src/components/layout/StatusFooter.jsx`
  - fake ticker/regime defaults removed
- `frontend-v2/src/config/api.js`
  - explicit mapping for `orders/emergency-stop`

## Validation performed
- `cd frontend-v2 && npm run build` ✅
- `cd backend && python -m pytest tests/ -q` ✅ (`666 passed`)
- GitHub Actions inspection: recent `CI - Lint & Test` workflow runs expose `action_required` with zero jobs/logs through the API, so local validation is currently the trustworthy signal.
