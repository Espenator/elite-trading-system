# UI Implementation Plan

## Batch 1 — Remove fake / misleading UI
- Remove hardcoded market tickers, optimistic health badges, toast-only destructive actions, fake topic lists, fake HITL rows, fake conference history, fake log rows.
- Replace `FALLBACK_*` values that look like live operator data with explicit empty/error/unavailable states.
- Audit every badge labeled Connected / Healthy / Active / Running / Ready / Synced / Live / Profitable and require a backend source.
- Completed in this branch for:
  - shared footer fake ticker strip
  - Agent Command Center header/footer/status chrome
  - Blackboard & Comms fake topics/HITL entries
  - Swarm Overview fake ELO fallback
  - RemainingTabs fake conference/model/log fallbacks

## Batch 2 — Wire real data and statuses
- Normalize all frontend payload parsing so object-vs-array mismatches do not silently trigger demo fallbacks.
- Add shared helpers for payload normalization, freshness labels, and empty/error/disconnected badges.
- Priority order:
  1. Dashboard
  2. Data Sources Monitor
  3. Signal Intelligence V3
  4. Performance Analytics
  5. ML Brain & Flywheel
  6. Market Regime

## Batch 3 — Expose missing operator controls
- Expose admin-gated emergency controls (`orders/emergency-stop`, `flatten-all`) in the correct pages with explicit auth/error messaging.
- Surface existing backend configuration/tuning endpoints where the frontend is currently read-only.
- Add drilldowns for alerts, conference status, model registry, drift, and risk diagnostics.
- Do not invent controls for backend-missing features; document blockers instead.

## Batch 4 — Visual fidelity / pixel pass
- Re-compare each page against:
  - `docs/UI-DESIGN-SYSTEM.md`
  - `docs/mockups-v3/FULL-MOCKUP-SPEC.md`
  - matching image in `docs/mockups-v3/images/`
- Tune spacing, card density, hierarchy, typography, and status-color semantics only after data/control truth is resolved.
- Preserve dense operator visibility; do not simplify away high-information panels.

## Batch 5 — Edge states and responsiveness
- For every page/panel verify:
  - loading
  - empty
  - stale
  - error
  - disconnected
  - partial-data
  - auth-limited/admin-only
- Validate layout at the repo’s intended desktop density and ensure tablet/mobile behavior is at least non-broken where supported.

## Batch 6 — Validation and regression checks
- Local validation:
  - `cd frontend-v2 && npm run build`
  - `cd backend && python -m pytest tests/ -q`
- Manual validation per page:
  - verify backend route exists
  - verify payload shape matches frontend usage
  - verify visible action performs a real request or a clearly blocked flow
  - verify no fake rows/charts/badges remain
- CI follow-up:
  - fix workflow configuration so Actions exposes real jobs/logs again

## Recommended execution order by subsystem
1. Shared layout chrome ✅ partial
2. Agent Command Center ✅ first truth pass done
3. Dashboard
4. Data Sources Monitor
5. Signal Intelligence V3
6. Risk + Trade Execution + Trades
7. Performance + ML Brain + Market Regime + Backtesting
8. Settings
