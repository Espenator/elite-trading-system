# ESPENMAIN (PC1) — Operations Runbook

**Hostname**: ESPENMAIN  
**LAN IP**: 192.168.1.105  
**Role**: Primary — backend API, frontend, DuckDB, trading execution, Electron desktop.

## PC1 Responsibilities

| Component | Responsibility | Port / URL |
|-----------|----------------|------------|
| Backend API | FastAPI, 35-agent council, MessageBus, OrderExecutor, Alpaca (Key 1) | 8000 |
| Frontend | React/Vite dashboard, 14 pages, WebSocket to backend | 5173 |
| DuckDB | analytics.duckdb, checkpoints.duckdb, trading_orders.db | — |
| Trading execution | Council verdict → OrderExecutor → Alpaca (paper/live per TRADING_MODE) | — |
| Electron desktop | Embodier Trader app window; uses backend + frontend already running | — |

## Keep Code Up to Date

```powershell
cd C:\Users\Espen\Dev\elite-trading-system
git fetch origin
git status -sb
# If safe to merge: git pull origin main --no-edit
# Resolve any conflicts (e.g. .env.example, untracked files) before pull.
```

## Start Full Stack 24/7 (recommended)

From repo root:

```powershell
.\scripts\run_full_stack_24_7.ps1 -CleanPorts
```

- **Backend**: New window; auto-restart on crash or 3× failed `/health` (every 30s).
- **Frontend**: New window; auto-restart when Vite exits.
- **Electron**: New window; auto-restart when app exits.
- Ports: 8000 (backend), 5173 (frontend). If busy, use `-CleanPorts` to free or use next in range (8001–8010, 5174–5183). Chosen ports saved to `.embodier-ports.json`.

Alternative (backend + frontend only, no Electron):

```powershell
.\scripts\run_full_stack_24_7.ps1 -CleanPorts -NoElectron
```

Or use the main launcher with watch mode (backend + frontend, no Electron):

```powershell
.\start-embodier.ps1 -Watch
```

Or full stack via main launcher:

```powershell
.\start-embodier.ps1 -FullStack
```

## Start Only Electron (backend + frontend already running)

```powershell
.\desktop\scripts\run_electron_autorestart.ps1
```

Electron will connect to backend/frontend using `.embodier-ports.json` or defaults (8000, 5173).

## Health Checks

| Check | URL / Command |
|-------|----------------|
| Backend health | `http://localhost:8000/health` (or port from `.embodier-ports.json`) |
| API docs | `http://localhost:8000/docs` |
| Dashboard | `http://localhost:5173/dashboard` (or frontend port) |

Backend autorestart script pings `/health` every 30s; after 3 consecutive failures (and after 45s startup grace), it kills and restarts the backend.

## If Something Drops

1. **Backend dies or hangs**  
   The backend window’s watchdog restarts uvicorn. Check backend window for “[Run #N] Starting uvicorn…”. Restart log: `logs/backend_autorestart.log` (if present).

2. **Frontend dies**  
   The frontend window restarts `npm run dev` after 2s. Reload the browser.

3. **Electron closes**  
   The Electron window restarts the app after 5s.

4. **Ports stuck (e.g. TIME_WAIT)**  
   Run with port cleanup:
   - `.\scripts\run_full_stack_24_7.ps1 -CleanPorts`  
   - or `.\start-embodier.ps1 -Watch`

## Environment

- **Python**: `backend\venv` (Python 3.11+).
- **Node**: For frontend and Electron (npm in PATH).
- **Secrets**: `backend\.env` (Alpaca keys, API keys). Never commit. Copy from `backend\.env.example` if missing.

## Alpaca on PC1

ESPENMAIN uses **Key 1** (portfolio trading). Set in `backend\.env`:

- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` (e.g. paper-api.alpaca.markets for paper).

## Quick Checklist (daily / after reboot)

- [ ] Git pull when safe (`git pull origin main --no-edit`).
- [ ] Start stack: `.\scripts\run_full_stack_24_7.ps1 -CleanPorts` (or `-NoElectron` if not using desktop).
- [ ] Confirm backend: open `http://localhost:8000/health` (or chosen port).
- [ ] Confirm dashboard: open `http://localhost:5173/dashboard`.
- [ ] If using Electron: start `.\desktop\scripts\run_electron_autorestart.ps1` or use full-stack launcher with Electron.
