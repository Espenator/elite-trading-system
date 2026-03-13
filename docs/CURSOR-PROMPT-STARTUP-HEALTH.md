# Cursor prompt: Startup health

**Use this prompt in Cursor** to diagnose startup failure, fix import errors, and get the stack running.

---

## Paste this into Cursor

```
Open docs/CURSOR-PROMPT-STARTUP-HEALTH.md in Cursor and paste it — Cursor will diagnose the startup failure, fix any import errors, and get it running.
```

Or, for a longer instruction:

```
Act as the startup-health prompt:

1. Read project_state.md and CLAUDE.md for context.
2. Diagnose startup failure:
   - Test backend import: `cd backend && python -c "from app.main import app; print('Import OK')"`
   - If that fails, fix any missing or broken imports in backend/app/main.py and related API routers.
   - Start the backend with uvicorn and capture any lifespan/startup errors (DuckDB lock, missing .env, etc.).
3. Run the 7-phase startup health check: `python scripts/startup_health_check.py --no-write`
   - If phase 2 (backend startup) fails: ensure no other process holds DuckDB; start backend on port 8000.
   - If phase 5 (signal pipeline) fails: ensure /api/v1/health returns message_bus and council; fix phase 5 logic if it wrongly fails when no council eval has run yet.
4. Fix any import or runtime errors so that:
   - Backend starts without exiting (watch for DuckDB "file in use" — only one backend per data dir).
   - All 7 phases pass or report clear, expected warnings (e.g. PC2 unreachable, Alpaca key missing).
5. Optionally create or update docs/CURSOR-PROMPT-STARTUP-HEALTH.md with this prompt so it can be reused.
```

---

## What Cursor will do

| Step | Action |
|------|--------|
| 1 | Test `from app.main import app` and fix any ImportError (missing deps, wrong imports in `main.py` or `api/v1`). |
| 2 | Run uvicorn and check lifespan: DuckDB init, MessageBus, council gate. If the process exits with "DuckDB file in use", that means another backend instance is running — only one per data directory. |
| 3 | Run `scripts/startup_health_check.py` and fix causes of failed phases (e.g. relax phase 5 when council is wired but no eval has run yet). |
| 4 | Ensure backend stays up and 7-phase check passes (or documents expected warnings). |

---

## Restart backend (one instance only)

You need **exactly one backend** so DuckDB isn’t locked (the app exits with “file in use” if a second instance starts). Stop any other backend first, then start once:

- **Stop other backends** (optional): In PowerShell, stop Python processes running uvicorn/start_server:
  ```powershell
  Get-Process python -ErrorAction SilentlyContinue | Where-Object {(Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -match "uvicorn|start_server"} | Stop-Process -Force
  ```
- **Start backend + frontend once**: From repo root run `.\start-embodier.ps1` (cleans up, picks ports, starts both). Or manually: `cd backend` → activate venv → `$env:PORT = "8000"` → `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`. Set `VITE_BACKEND_URL=http://localhost:8000` for the frontend so the WebSocket points at the correct backend.

---

## References

- **7-phase check**: `docs/FULL-SYSTEM-STARTUP-HEALTH-VIEW.md`
- **Script**: `scripts/startup_health_check.py`
- **API**: `GET /api/v1/health/startup-check` (same 7 phases in-process)
- **UI**: System → Startup Health (`/startup-health`)
