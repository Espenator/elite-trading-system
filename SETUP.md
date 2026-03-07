# Embodier Trader — Setup & Quick Start

## Requirements
- Python 3.10+ (with pip)
- Node.js 18+ (with npm)
- Git
- Windows 10/11 (PowerShell 5.1+)

## Paths

### ESPENMAIN (PC1 — Primary)
```
Repo:      C:\Users\Espen\elite-trading-system
Backend:   C:\Users\Espen\elite-trading-system\backend
Frontend:  C:\Users\Espen\elite-trading-system\frontend-v2
Python:    C:\Users\Espen\elite-trading-system\backend\venv
```

### ProfitTrader (PC2 — Secondary)
```
Repo:      C:\Users\ProfitTrader\elite-trading-system
```

## Network (Two-PC LAN)

| Machine | Hostname | LAN IP | Role |
|---------|----------|--------|------|
| PC1 | ESPENMAIN | 192.168.1.105 | Primary — backend, frontend, DB |
| PC2 | ProfitTrader | 192.168.1.116 | Secondary — GPU training, ML |

Both IPs are DHCP-reserved on the AT&T BGW320-505 router (192.168.1.254).

> See also: [docs/NETWORK_TWO_PC_SETUP.md](docs/NETWORK_TWO_PC_SETUP.md) and [docs/AI_TWO_PC_CODING_GUIDE.md](docs/AI_TWO_PC_CODING_GUIDE.md)

## Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend | 3000 | http://localhost:3000 |

## Quick Start (One Click)

Double-click `start-embodier.bat` or run:
```powershell
cd C:\Users\Espen\elite-trading-system
.\start-embodier.ps1
```

This will:
1. Create a Python venv and install deps (first run only)
2. Start the FastAPI backend on port 8000
3. Install npm packages and start Vite on port 3000 (first run only)
4. Open http://localhost:3000 in your browser
5. Auto-restart if either service crashes (up to 3 times)

### Backend only (no frontend)
```powershell
.\start-embodier.ps1 -SkipFrontend
```

## Manual Start (Step by Step)

```powershell
# Terminal 1 — Backend
cd C:\Users\Espen\elite-trading-system\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm run dev
```

## Environment Files

### backend/.env (required)
Copy `backend/.env.example` to `backend/.env` and fill in your API keys.

The minimum to get started:
```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
TRADING_MODE=paper
PORT=8000
```

### frontend-v2/.env (optional)
The frontend proxy is configured in `vite.config.js` to forward `/api` requests
to `http://localhost:8000` automatically. No `.env` needed for local dev.

Set these only for production builds:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Docker (Alternative)

```bash
# Copy and configure .env
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Troubleshooting

### Kill stale processes
```powershell
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Reset and restart
```powershell
cd C:\Users\Espen\elite-trading-system
git stash; git pull origin main; git stash drop
cd backend; venv\Scripts\Activate.ps1; pip install -r requirements.txt
cd ..\frontend-v2; npm install
cd ..; .\start-embodier.ps1
```

### Check if the API is running
```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/status
```

### Check logs
```
logs\backend.log
logs\frontend.log
```

### Common issues

| Symptom | Fix |
|---------|-----|
| "python not found" | Install Python 3.10+ and add to PATH |
| "npm not found" | Install Node.js 18+ from nodejs.org |
| Backend won't start | Check `backend/.env` exists with valid Alpaca keys |
| Frontend blank page | Make sure backend is running on port 8000 |
| CORS errors | Backend auto-allows localhost origins — should work out of the box |
| Port in use | The launcher auto-kills stale processes on ports 8000/3000 |

## Sync to ProfitTrader PC
```powershell
# On ProfitTrader:
cd C:\Users\ProfitTrader\elite-trading-system
git pull origin main
cd backend; venv\Scripts\Activate.ps1; pip install -r requirements.txt
cd ..\frontend-v2; npm install
cd ..; .\start-embodier.ps1
```

## Desktop Shortcut
```powershell
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Embodier Trader.lnk")
$s.TargetPath = "powershell.exe"
$s.Arguments = "-ExecutionPolicy Bypass -File `"C:\Users\Espen\elite-trading-system\start-embodier.ps1`""
$s.WorkingDirectory = "C:\Users\Espen\elite-trading-system"
$s.Save()
```
