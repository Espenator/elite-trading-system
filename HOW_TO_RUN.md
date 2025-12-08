# 🚀 How to Run Elite Trading System

## Quick Start (Easiest Method)

### Option 1: Use the Batch File (Windows)
```bash
.\LAUNCH_ELITE_TRADER.bat
```
This will automatically start both backend and frontend in separate windows.

### Option 2: Use the PowerShell Script
```powershell
powershell -ExecutionPolicy Bypass -File .\LAUNCH_ELITE_TRADER.ps1
```

---

## Manual Start (Step-by-Step)

### Step 1: Start the Backend API Server

Open a **PowerShell** or **Command Prompt** window and run:

```powershell
cd F:\Workspace\2025_12_Espen\elite-trading-system
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**What this does:**
- Starts the FastAPI backend server
- Runs on `http://localhost:8000`
- `--reload` enables auto-reload on code changes
- Keep this window open while the server is running

**You should see:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Elite Trading System Starting...
✅ FastAPI server initialized
INFO:     Application startup complete.
```

### Step 2: Start the Frontend UI

Open a **NEW** PowerShell or Command Prompt window and run:

```powershell
cd F:\Workspace\2025_12_Espen\elite-trading-system\elite-trader-ui
npm run dev
```

**What this does:**
- Starts the Next.js frontend development server
- Runs on `http://localhost:3000`
- Auto-reloads on code changes
- Keep this window open while the server is running

**You should see:**
```
▲ Next.js 15.x.x
- Local:        http://localhost:3000
- Ready in X seconds
```

---

## Access the Application

Once both servers are running:

1. **Frontend UI**: Open your browser and go to:
   - http://localhost:3000

2. **Backend API Documentation**: 
   - http://localhost:8000/docs
   - Interactive API documentation (Swagger UI)

3. **Backend Health Check**:
   - http://localhost:8000/api/health

---

## Stopping the Servers

To stop the servers:
1. Go to each terminal window
2. Press `Ctrl + C`
3. Confirm if prompted

---

## Troubleshooting

### Port Already in Use
If you get an error that port 8000 or 3000 is already in use:

**Windows PowerShell:**
```powershell
# Kill process on port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force

# Kill process on port 3000
Get-NetTCPConnection -LocalPort 3000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force
```

### Missing Dependencies
If you get import errors, install dependencies:
```powershell
pip install -r requirements.txt
cd elite-trader-ui
npm install
```

### Backend Not Starting
Check that all Python dependencies are installed:
```powershell
python -c "import fastapi, uvicorn, sqlalchemy, loguru, yfinance; print('All dependencies OK')"
```

---

## System Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Frontend UI   │  ──────> │   Backend API   │
│  (Next.js)      │  HTTP   │  (FastAPI)      │
│  Port: 3000     │          │  Port: 8000      │
└─────────────────┘         └─────────────────┘
                                      │
                                      │
                              ┌───────▼───────┐
                              │   Database   │
                              │   (SQLite)   │
                              └──────────────┘
```

---

## Development Tips

1. **Auto-reload**: Both servers support auto-reload. Just save your files and changes will be reflected automatically.

2. **Logs**: Check the terminal windows for server logs and any errors.

3. **API Testing**: Use the Swagger UI at http://localhost:8000/docs to test API endpoints interactively.

4. **WebSocket**: The backend also provides WebSocket support at `ws://localhost:8000/ws` for real-time updates.

---

## Next Steps

Once the servers are running:
- Visit http://localhost:3000 to see the Elite Trader UI
- Visit http://localhost:8000/docs to explore the API
- Check http://localhost:8000/api/health to verify backend status

Happy Trading! 📈

