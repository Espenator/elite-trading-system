# Embodier Trader — Setup & Quick Start

## Requirements
- Python 3.10+ (with pip) — [python.org/downloads](https://www.python.org/downloads/)
- Node.js 18+ (with npm) — [nodejs.org](https://nodejs.org/)
- Git

## One-Click Launch

### Windows (ESPENMAIN / ProfitTrader)

**First time only:**
```powershell
# 1. Clone the repo
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system

# 2. Create desktop shortcut
powershell -File create-shortcut.ps1

# 3. Double-click "Embodier Trader" on your Desktop
```

**Or launch directly:**
```
launch.bat
```

### Linux / macOS
```bash
./launch.sh
```

## What Happens on Launch

The Electron app handles everything automatically:

1. **First run:** Shows setup wizard to collect device name, API keys, and trading mode
2. **Auto-update:** Checks git for updates and pulls if behind (`git fetch` + `git pull --ff-only`)
3. **Python setup:** Creates `backend/venv` and installs `requirements.txt` (only when deps change)
4. **Frontend build:** Runs `npm install` + `npm run build` in `frontend-v2/` (only when source changes)
5. **Backend start:** Launches FastAPI on port 8000 with health monitoring
6. **Dashboard:** Opens the React frontend in the Electron window
7. **System tray:** Minimizes to tray, shows backend status

Every subsequent launch auto-updates from git — just like Spotify, Discord, or VS Code.

## Network (Two-PC LAN)

| Machine | Hostname | LAN IP | Role |
|---------|----------|--------|------|
| PC1 | ESPENMAIN | 192.168.1.105 | Primary — backend, frontend, DB |
| PC2 | ProfitTrader | 192.168.1.116 | Secondary — GPU training, ML |

Both IPs are DHCP-reserved on the AT&T BGW320-505 router (192.168.1.254).

### Alpaca Accounts (Paper Trading)

| Label | Machine | Purpose | Env Key |
|-------|---------|---------|---------|
| ESPENMAIN | PC1 | Trading (portfolio execution) | `ALPACA_KEY_1` |
| Profit Trader | PC2 | Discovery scanning | `ALPACA_KEY_2` |

Both use `https://paper-api.alpaca.markets/v2`. Keys are in `backend/.env` (gitignored).

### Slack Bots (Embodier Trader Workspace)

| Bot | App ID | Purpose |
|-----|--------|---------|
| OpenClaw | A0AF9HSCQ6S | Multi-agent swarm notifications |
| TradingView Alerts | A0AFQ89RVEV | Inbound TradingView webhook alerts |

Slack workspace tokens expire every 12h. Refresh at https://api.slack.com/apps

> See also: [docs/NETWORK_TWO_PC_SETUP.md](docs/NETWORK_TWO_PC_SETUP.md) and [docs/AI_TWO_PC_CODING_GUIDE.md](docs/AI_TWO_PC_CODING_GUIDE.md)

## Ports

| Service | Port | Access |
|---------|------|--------|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend (Vite dev) | 5173 | http://localhost:5173 |
| Frontend (Electron) | -- | Served by Electron (no separate port) |
| Mobile PWA | 8765 | http://192.168.1.105:8765 (iPhone) |

## Environment / API Keys

API keys are stored in Electron's config store (managed via the setup wizard).
A `backend/.env` file is auto-generated from the wizard settings.

To edit keys later: **Embodier Trader menu > Settings > API Keys**

For manual launch, this will:
1. Create a Python venv and install deps (first run only)
2. Start the FastAPI backend on port 8000
3. Install npm packages and start Vite on port 5173 (first run only)
4. Open http://localhost:5173 in your browser
5. Auto-restart if either service crashes (up to 3 times)

### Required for Live Trading
- `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` (from [alpaca.markets](https://alpaca.markets))
- `API_AUTH_TOKEN` (auto-generated on first setup)

### Optional Data Sources
- Finviz Elite, FRED, Unusual Whales, NewsAPI, StockGeist
- Discord, X/Twitter, YouTube (social sentiment)
- Perplexity AI, Anthropic Claude (LLM council)

## Backend local startup (developers)

**Entrypoint:** `backend/app/main.py` — FastAPI app is `app.main:app`.

**Exact commands (from repo root):**

```powershell
# 1. Backend (Terminal 1)
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Env:** `backend/.env` is optional. If missing, the app still starts; set at least for live/data features:

- **Minimal (API starts):** `TRADING_MODE=paper`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` (use placeholders like `test`/`test` for health checks only).
- **Copy template:** `copy backend\.env.example backend\.env` then edit. Never commit `.env`.

**Health check after start:**

```powershell
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/v1/health
```

Optional integrations (Brain, Redis, data sources) degrade gracefully if unset or unreachable. See [docs/RUNBOOK.md](docs/RUNBOOK.md) for full start/stop and troubleshooting.

## Pre-commit Hooks (optional)

Format and lint before every commit:

```powershell
# One-time install (requires Python 3.11+)
pip install pre-commit
pre-commit install

# Backend: Black + isort (run from repo root)
cd backend && black app tests && isort app tests

# Frontend: ESLint + Prettier
cd frontend-v2 && npm run lint
```

Pre-commit runs automatically on `git commit`. Config: [.pre-commit-config.yaml](.pre-commit-config.yaml). Backend style: [backend/pyproject.toml](backend/pyproject.toml).

## Automated Deployment

### PC1 (ESPENMAIN)

From repo root (e.g. `C:\Users\Espen\elite-trading-system`):

```powershell
.\scripts\deploy-pc1.ps1
```

This: pulls `main`, installs backend deps, stops backend/frontend on 8000/5173, starts backend and frontend in new windows, runs a health check. Rollback: `.\scripts\deploy-pc1.ps1 -Rollback`.

### PC2 (ProfitTrader)

From repo root on PC2:

```powershell
.\scripts\deploy-pc2.ps1
```

This: pulls `main`, installs backend + brain_service deps, restarts brain_service (gRPC :50051), checks port. Rollback: `.\scripts\deploy-pc2.ps1 -Rollback`.

### Rollback to a specific ref

```powershell
.\scripts\rollback.ps1           # revert to HEAD~1
.\scripts\rollback.ps1 v5.0.0   # revert to tag
```

### Post-deploy smoke tests

```powershell
.\scripts\smoke-test.ps1
# Or against another host:
.\scripts\smoke-test.ps1 -BaseUrl http://192.168.1.105:8000
```

Verifies: `/health`, `/api/v1/health`, `/api/v1/council/status`, `/readyz`.

## Docker (full stack)

From repo root:

```bash
docker-compose up -d
```

Starts: **backend** (:8000), **brain** (:50051), **redis** (:6379). Backend uses `BRAIN_HOST=brain` and `REDIS_URL=redis://redis:6379`. Health checks are defined for all three services. To verify:

```bash
docker-compose ps
curl http://localhost:8000/healthz
```

## CI and release tagging

- **CI** (`.github/workflows/ci.yml`): runs on push to `main`, pull requests, and manual trigger. Backend: Black, isort, mypy (council + trading), pytest on Python 3.11 and 3.12. Frontend: lint, build. E2E: Playwright. Target: &lt; 10 minutes.
- **Release tag**: In GitHub Actions, run workflow **Release Tag**, enter version (e.g. `v5.0.1`). Creates and pushes the tag. Use when `main` is green.

## Troubleshooting

### Embodier Trader won't start
```powershell
# Check Python is installed
python --version     # Should be 3.10+

# Check Node.js is installed
node --version       # Should be 18+

# Manual start (for debugging)
cd desktop
npm install
npm start
```

### Backend won't start
Check the Electron log:
- **Windows:** `%APPDATA%\embodier-trader\logs\main.log`
- **macOS:** `~/Library/Logs/embodier-trader/main.log`
- **Linux:** `~/.config/embodier-trader/logs/main.log`

### Check if the API is running
```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/status
```

### Reset everything
```powershell
cd elite-trading-system
cd backend && rmdir /s /q venv
cd ..\frontend-v2 && rmdir /s /q node_modules dist
cd ..\desktop && rmdir /s /q node_modules
# Then re-launch — everything rebuilds automatically
```

### Common issues

| Symptom | Fix |
|---------|-----|
| "python not found" | Install Python 3.10+ and add to PATH |
| "npm not found" | Install Node.js 18+ from nodejs.org |
| Backend won't start | Check API keys in Settings |
| Port 8000 in use | Electron auto-kills stale processes — if stuck, restart your PC |
| Frontend blank | Backend may still be starting — wait for splash to finish |

## Check for Updates

**Menu > Embodier Trader > Check for Updates**

Or from command line:
```bash
cd elite-trading-system
git pull origin main
```

## Sync to ProfitTrader PC
```powershell
# On ProfitTrader — same process:
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system
launch.bat
# Setup wizard auto-detects ProfitTrader as secondary node
```

## Desktop Shortcut (Manual)
```powershell
powershell -File create-shortcut.ps1
```
