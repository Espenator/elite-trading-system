# Strict Repo-Truth Verification — 2026-03-08

This document records a code-first verification of UI/backend truth-alignment claims.

## Scope checked
- Agent Command Center and tabs
- Shared layout/footer
- Dashboard
- Sentiment Intelligence
- Data Sources Monitor
- Signal Intelligence V3
- Relevant backend routes (`agents`, `orders`, `system`, `status`, `council`, `ml_brain`, `logs`)
- Existing alignment docs and validation evidence

## High-level verdict
- **Mixed / overstated**

## What is verified
- `AgentCommandCenter.jsx` now parses the real `/api/v1/agents` payload shape (`{ agents, logs }`).
- Agent Command Center emergency stop calls the real backend endpoint `/api/v1/orders/emergency-stop`.
- Blackboard topics in `RemainingTabs.jsx` now come from `/api/v1/system/event-bus/status`.
- HITL buffer in `RemainingTabs.jsx` now comes from `/api/v1/agents/hitl/buffer`, with real approve/reject POST routes.
- Shared `Layout.jsx` and `StatusFooter.jsx` no longer inject fake ticker defaults; they use real market/status/regime inputs or an explicit empty state.
- Swarm Overview ELO leaderboard now reads the backend `{ leaderboard }` shape.

## What is only partially true
- Agent Command Center uses real backend/system data in several places, but some backend sources feeding it are themselves fallback-heavy or stub-like:
  - `backend/app/api/v1/agents.py:/alerts` always appends `"Bridge latency normalized — 23ms avg"`.
  - `backend/app/api/v1/agents.py:/drift` returns mock-structure metrics when no live drift monitor is available.
  - `backend/app/api/v1/logs.py` still returns a fixed sample log list.
- RemainingTabs degrades more truthfully than before, but Logs/ML/Conference truth is constrained by those backend payloads.

## What remains misleading
- `frontend-v2/src/pages/SentimentIntelligence.jsx`
  - hardcoded `HEATMAP_SYMBOLS`
  - hardcoded `SCANNER_SYMBOLS`
  - these are still user-visible fallbacks
- `frontend-v2/src/pages/DataSourcesMonitor.jsx`
  - hardcoded `SOURCE_DEFS` with latency/uptime/status/data-rate values
  - decorative `WS Connected` / `API Healthy` badges
  - hardcoded ingestion/openclaw/websocket metrics in top bar
- `frontend-v2/src/pages/SignalIntelligenceV3.jsx`
  - hardcoded scanners/modules/data-source lists
  - hardcoded ML model defaults
  - fake seeded signals if the API returns no signals
- `frontend-v2/src/pages/agent-tabs/AgentRegistryTab.jsx`
  - inspector panel still contains hardcoded config, metrics, logs, donut gauge, and lifecycle chrome around real table rows

## Docs reality
- The following requested files were **not present** at verification time:
  - `docs/ui-backend-alignment/README.md`
  - `docs/ui-backend-alignment/page-truth-matrix.md`
  - `docs/ui-backend-alignment/implementation-plan.md`
  - `docs/ui-backend-alignment/acceptance-checklist.md`
- Existing docs use different names:
  - `UI_BACKEND_GAP_AUDIT.md`
  - `UI_BACKEND_TRUTH_MATRIX.md`
  - `UI_IMPLEMENTATION_PLAN.md`
  - `UI_ACCEPTANCE_CRITERIA.md`
- These existing docs are useful, but they should not be treated as proof that the repo is fully truth-aligned.

## Validation reality
- `frontend-v2/package.json` confirms `npm run build` is a valid build command.
- `backend/tests/` and `backend/pytest.ini` confirm backend pytest structure exists.
- A local run of `python -m pytest tests/ -q` can produce `666 passed`, but that claim is not proven by static repo contents alone.
- No repository-native evidence proves local manual verification beyond external transcript/assertion.
- No repository-native evidence proves a successful CodeQL run; treat that as external-session evidence unless persisted elsewhere.

## Recommendation
- Treat current state as a **partial truthful pass**, not a complete truth-alignment.
- Safe to continue iterative cleanup, but not safe to claim “zero fake UI” or “fully backend-accurate” across the app.
