# Embodier Trader - Setup & Quick Start Guide

## System Requirements
- Python 3.10+
- Node.js 18+
- Git
- Windows 10/11 (PowerShell 5.1+)

## Verified Paths (ESPENMAIN PC)
```
Repo:      C:\Users\Espen\elite-trading-system
Backend:   C:\Users\Espen\elite-trading-system\backend
Frontend:  C:\Users\Espen\elite-trading-system\frontend-v2
Desktop:   C:\Users\Espen\elite-trading-system\desktop
Python:    C:\Users\Espen\elite-trading-system\backend\.venv
```

## Verified Paths (ProfitTrader PC)
```
Repo:      C:\Users\ProfitTrader\elite-trading-system  (clone if missing)
```


## Network (Two-PC LAN)

| Machine | Hostname | LAN IP | Role |
|---------|----------|--------|------|
| PC1 | ESPENMAIN | 192.168.1.105 | Primary - backend, frontend, DB |
| PC2 | ProfitTrader | 192.168.1.116 | Secondary - GPU training, ML |

Both IPs are DHCP-reserved (fixed) on the AT&T BGW320-505 router (192.168.1.254).

> **Full details:** [docs/NETWORK_TWO_PC_SETUP.md](docs/NETWORK_TWO_PC_SETUP.md)
> **AI/Coding rules:** [docs/AI_TWO_PC_CODING_GUIDE.md](docs/AI_TWO_PC_CODING_GUIDE.md)
## Ports
| Service       | Port  | URL                          |
|--------------|-------|------------------------------|
| Backend API  | 8000  | http://localhost:8000        |
| API Docs     | 8000  | http://localhost:8000/docs   |
| Frontend     | 3000  | http://localhost:3000        |

## Quick Start (One Command)
```powershell
# Right-click > Run with PowerShell
cd C:\Users\Espen\elite-trading-system
.\start-embodier.ps1
```

## Manual Start (Step by Step)
```powershell
# 1. Backend
cd C:\Users\Espen\elite-trading-system\backend
.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (new terminal)
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm run dev
```

## Environment Files

### backend/.env (required)
```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
TRADING_MODE=paper
BACKEND_PORT=8000
```

### frontend-v2/.env (optional, defaults work)
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
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
cd backend; .venv\Scripts\Activate.ps1; pip install -r requirements.txt
cd ..\frontend-v2; npm install
cd ..; .\start-embodier.ps1
```

### Verify API is running
```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/signals
```

## Sync to ProfitTrader PC
```powershell
# On ProfitTrader:
cd C:\Users\ProfitTrader\elite-trading-system
git pull origin main
cd backend; .venv\Scripts\Activate.ps1; pip install -r requirements.txt
cd ..\frontend-v2; npm install
.\start-embodier.ps1
```

## Create Desktop Shortcut
```powershell
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Embodier Trader.lnk")
$s.TargetPath = "powershell.exe"
$s.Arguments = "-ExecutionPolicy Bypass -File `"C:\Users\Espen\elite-trading-system\start-embodier.ps1`""
$s.WorkingDirectory = "C:\Users\Espen\elite-trading-system"
$s.Save()
```
