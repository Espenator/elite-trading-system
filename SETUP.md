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

### PC1 (ESPENMAIN)
| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend | 3000 | http://localhost:3000 |

### PC2 (ProfitTrader) - Optional
| Service | Port | URL (from PC1) |
|---------|------|----------------|
| Ollama API | 11434 | http://192.168.1.116:11434 |
| Brain gRPC | 50051 | 192.168.1.116:50051 |

## Quick Start (One Click)

### Single-PC Mode (PC1 Only)

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

#### Backend only (no frontend)
```powershell
.\start-embodier.ps1 -SkipFrontend
```

### Dual-PC Mode (PC1 + PC2)

For maximum performance with GPU-accelerated Brain Service and Ollama on PC2:

**First-time setup (run once on PC2):**
```powershell
# On PC2 (ProfitTrader) - run as Administrator
cd C:\Users\ProfitTrader\elite-trading-system
.\setup-pc2.ps1
```

This configures PowerShell remoting and firewall rules.

**Daily use (run from PC1):**
```powershell
# On PC1 (ESPENMAIN)
cd C:\Users\Espen\elite-trading-system
.\start-dual-pc.ps1
```

This will:
1. Test connectivity to PC2
2. Start Brain Service (gRPC) and Ollama on PC2 via remote PowerShell
3. Start Backend + Frontend on PC1
4. Validate cross-PC connectivity
5. Graceful fallback to single-PC mode if PC2 is unavailable

**Alternative - Manual PC2 Start:**

If PowerShell remoting is not configured, start PC2 services manually:
```powershell
# On PC2 (ProfitTrader)
cd C:\Users\ProfitTrader\elite-trading-system
.\start-pc2.ps1

# Then on PC1 (ESPENMAIN)
cd C:\Users\Espen\elite-trading-system
.\start-dual-pc.ps1 -NoRemoting
```

**Force single-PC mode:**
```powershell
.\start-dual-pc.ps1 -SinglePCMode
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

### Dual-PC Mode Troubleshooting

| Symptom | Fix |
|---------|-----|
| "PC2 is not reachable" | Ensure PC2 is powered on and both PCs are on same LAN. Check `CLUSTER_PC2_HOST` in `backend/.env` |
| "PowerShell Remoting FAILED" | On PC2, run as Admin: `.\setup-pc2.ps1` or use `-NoRemoting` flag |
| "Ollama NOT READY YET" | Wait 30-60 seconds for Ollama to start. Check `logs\ollama.log` on PC2 |
| "Brain Service unresponsive" | Check `logs\brain_service.log` on PC2. Ensure Python 3.10+ installed |
| Dual-PC starts in single-PC mode | Check network connectivity with `ping 192.168.1.116` from PC1 |
| PC2 services won't stop | Manually run on PC2: `Get-Process ollama,python | Stop-Process -Force` |

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
