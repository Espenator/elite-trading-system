# Production Readiness Audit — March 12, 2026

**Scope:** Final audit before live trading.  
**Deliverables in this PR:** CI fix (pytest-xdist), live-mode fail-closed startup, E2E renamed to frontend-smoke, doc consistency (v5.0.0, test count 1,182+).

## Checklist implemented

| # | Item | Status |
|---|------|--------|
| 1 | Add pytest-xdist to backend/requirements.txt (CI parallel) | Done |
| 2 | E2E job renamed to "Frontend smoke"; npm ci; HAS_BACKEND=false documented | Done |
| 3 | Live mode fail-closed: when TRADING_MODE=live and account validation fails, refuse to start (RuntimeError in lifespan) | Done |
| 4 | Docs: backend/CLAUDE.md and frontend-v2/CLAUDE.md → v5.0.0; test count 1,182+ in project_state and CI comment | Done |

## Safety change (main.py)

- When Alpaca is configured, account validation runs at startup.
- If **TRADING_MODE=live** and `validate_account_safety()` returns `valid=False`, the app **raises RuntimeError** and does not start (fail-closed).
- If TRADING_MODE=paper, behavior unchanged: force shadow mode on validation failure.

## CI

- Job name: `frontend-smoke` (was e2e-gate). Comment clarifies that full pipeline E2E would require backend.
- Frontend job uses `npm ci` for reproducible installs.
- Backend test count comment updated to 1,182+.

## Docker / full-stack E2E

Not run in this audit. Recommend running `docker-compose up` once and verifying one full request path before production.
