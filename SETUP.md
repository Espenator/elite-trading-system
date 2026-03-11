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
