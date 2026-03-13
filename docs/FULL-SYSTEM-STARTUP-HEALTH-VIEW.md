# Full System Startup & Health — View

**7 phases:** environment check → backend startup → router verification → API smoke tests → signal pipeline → frontend wiring → background loops.

## Where to see it

- **UI:** System → **Startup Health** (`/startup-health`). Shows live 7-phase result and common failure patterns table.
- **Report file:** `reports/STARTUP-HEALTH-REPORT.md` — written when you run the script below.

## How to run the check

### From the UI

Open **Startup Health** and click **Run check**. The backend runs the 7 phases in-process and returns the same structure the script uses.

### From the command line (writes report)

From repo root:

```bash
python scripts/startup_health_check.py
```

Options:

- `--base-url http://localhost:8000` — Backend URL (default: `http://localhost:8000` or `EMBODIER_BACKEND_URL`).
- `--frontend-url http://localhost:5173` — Frontend URL for phase 6 (optional).
- `--no-write` — Do not write `reports/STARTUP-HEALTH-REPORT.md`.

Exit code: 0 if all phases pass, 1 otherwise.

## 7 phases

| Phase | Description |
|-------|-------------|
| 1. Environment check | Python 3.10+, `backend/.env` exists, Alpaca key set |
| 2. Backend startup | `GET /healthz` returns 200 |
| 3. Router verification | `GET /openapi.json` returns routes |
| 4. API smoke tests | `GET /api/v1/health`, `/api/v1/status`, `/api/v1/signals/` return 200 |
| 5. Signal pipeline | MessageBus and council (last eval) present in `/api/v1/health` |
| 6. Frontend wiring | Optional: frontend URL reachable (script only; API skips) |
| 7. Background loops | `/readyz` and `/api/v1/status` indicate services and background state |

## Common failure patterns table

The report and the **Startup Health** view both include a table of common failure patterns: **Symptom** → **Cause** → **Remediation**. Use it when a phase fails to find likely cause and fix. The table is defined in:

- `scripts/startup_health_check.py` (script + report)
- `backend/app/api/v1/health.py` (API + view)

## API

- **GET /api/v1/health/startup-check** — Returns `{ phases, overall_ok, failure_patterns, timestamp }`. No auth required. Used by the Startup Health page.

## Files

| File | Purpose |
|------|---------|
| `scripts/startup_health_check.py` | CLI runner; 7 phases via HTTP; writes `reports/STARTUP-HEALTH-REPORT.md` |
| `backend/app/api/v1/health.py` | `GET /api/v1/health/startup-check`; in-process 7-phase check + failure patterns |
| `frontend-v2/src/pages/StartupHealth.jsx` | View: phases + failure table + “Run check” |
| `reports/STARTUP-HEALTH-REPORT.md` | Generated report (after running script) |
