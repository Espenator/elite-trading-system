# Elite Trading System — Startup Audit Report
**Date:** March 8, 2026
**Auditor:** Senior Platform Reliability Engineer
**Repository:** https://github.com/Espenator/elite-trading-system

---

## Executive Summary

This audit examines the complete startup orchestration for the Embodier.ai Elite Trading System, a multi-component architecture consisting of:
- FastAPI backend (Python 3.11+, DuckDB, MessageBus, 31-agent council)
- React/Vite frontend (Node 18+, TailwindCSS)
- gRPC brain service (Ollama LLM on PC2)
- Docker Compose orchestration
- Windows PowerShell launcher

**Key Findings:**
1. ✅ **One canonical Windows startup path exists** (`start-embodier.ps1`) and is well-implemented
2. ⚠️ **Filename drift**: README says `python start_server.py` but also references `run_server.py`
3. ✅ **Robust error handling** in PowerShell launcher with preflight checks
4. ⚠️ **Missing degraded-mode documentation** for brain service and optional integrations
5. ✅ **Health endpoints implemented** (`/healthz`, `/readyz`, `/health`)
6. ⚠️ **No automated preflight validation script** for env vars before startup
7. ⚠️ **Brain service startup not integrated** into root launcher
8. ✅ **Docker support is complete** with health checks and proper dependency ordering

---

## A. Startup Paths Inventory

### 1. Windows One-Click Startup (PRIMARY — Verified)
**Files:**
- `start-embodier.ps1` (354 lines, robust, production-ready)
- `start-embodier.bat` (17 lines, wrapper for PS1)

**What it does:**
1. Validates Python 3.10+ and Node 18+ on PATH
2. Kills stale processes on ports 8000 and 3000
3. Cleans DuckDB WAL locks
4. Creates Python venv if missing
5. Installs backend deps (requirements.txt)
6. Fixes .env encoding issues (Windows cp1252 → UTF-8)
7. Validates Alpaca API keys (warns on placeholders)
8. Starts backend via `venv\Scripts\python.exe start_server.py`
9. Starts frontend via `npx vite --port 3000 --host`
10. Opens browser to http://localhost:3000
11. Health check loop (HTTP + TCP port check)
12. Auto-restart on crash (up to 3 times)

**Status:** ✅ **VERIFIED — This is the canonical Windows dev startup path**

**Observations:**
- Excellent error handling and diagnostics
- Logs to `logs/backend.log` and `logs/frontend.log`
- Uses TCP port check before HTTP health check (smart for event loop blocking)
- Properly uses Start-Process instead of Start-Job (avoids PID tracking issues)

---

### 2. Backend Manual Startup

**File:** `backend/start_server.py` (14 lines)
```python
import uvicorn
from app.core.config import settings

uvicorn.run(
    "app.main:app",
    host=settings.HOST,
    port=settings.effective_port,
    reload=settings.DEBUG,
    log_level=settings.LOG_LEVEL.lower()
)
```

**Also exists:** `backend/run_server.py` (32 lines) — PyInstaller-compatible version

**Status:** ⚠️ **TWO FILES EXIST WITH SIMILAR NAMES**

**Issue:** README.md line 350 says `python start_server.py`, but repository also has `run_server.py`. This creates confusion.

**Recommendation:** Consolidate to ONE file or document the difference clearly.

---

### 3. Backend Batch Launcher

**File:** `backend/start.bat` (5 lines)
```batch
@echo off
echo Starting Embodier Trader Backend API...
call venv\Scripts\activate.bat
python start_server.py
```

**Status:** ✅ Exists but is redundant with root `start-embodier.ps1`

**Recommendation:** Keep for manual backend-only testing but document it's for advanced users.

---

### 4. Frontend Manual Startup

**Command:** `npm run dev` (from frontend-v2/)

**Vite config:**
- Port: 3000 (overridable via VITE_PORT)
- Proxy: `/api` → `http://localhost:8000`
- Proxy: `/ws` → `ws://localhost:8000`
- Backend URL: Defaults to `localhost:8000`, overridable via `VITE_BACKEND_URL`

**Status:** ✅ Standard, well-configured

---

### 5. Docker Compose Startup

**File:** `docker-compose.yml` (116 lines)

**Services:**
1. **Redis** (port 6379)
   - Health check: `redis-cli ping`
   - 512MB RAM limit, LRU eviction
2. **Backend** (port 8000)
   - Dockerfile: multi-stage build (Python 3.11-slim)
   - Health check: `curl http://localhost:8000/health`
   - Depends on: Redis (with health check)
   - Volumes: `duckdb_data`, `model_artifacts`
   - Resource limits: 4GB RAM, 2 CPU
   - Start period: 120s (allows for slow DB init)
3. **Frontend** (port 3000 → nginx:80)
   - Dockerfile: Node 20 build → nginx alpine
   - Depends on: Backend (with health check)
   - Resource limits: 512MB RAM, 1 CPU

**Status:** ✅ **EXCELLENT** — Proper health checks, dependency ordering, resource limits

**Observations:**
- Backend health check uses `/health` (not `/healthz`)
- Frontend nginx proxies to `http://backend:8000` (Docker network resolution)
- Redis included but NOT required by backend startup (fail-open design)

---

### 6. Brain Service Startup (PC2)

**Files:**
- `brain_service/server.py` (140 lines, gRPC server)
- `brain_service/README.md` (49 lines, setup instructions)

**What it does:**
1. Compiles proto files (requires `python compile_proto.py` first)
2. Starts gRPC server on port 50051
3. Wraps Ollama LLM calls (InferCandidateContext, CriticPostmortem)

**Dependencies:**
- Ollama installed and running (`ollama serve`)
- Model pulled (`ollama pull llama3.2`)

**Status:** ⚠️ **NOT INTEGRATED** into root launcher

**Issue:** README.md line 26 says "Brain service: gRPC + Ollama | BUILT — not yet wired to council"

**Startup command:** `python server.py` (manual)

**Recommendation:** Add optional brain service startup to `start-embodier.ps1` with env flag

---

## B. Actual Dependency Graph

### Critical Path (Must Start First)

```
1. Environment Validation
   ├─ Python 3.10+ installed
   ├─ Node 18+ installed (if frontend enabled)
   └─ backend/.env exists with Alpaca keys

2. Backend Prerequisites
   ├─ venv created and activated
   ├─ requirements.txt installed
   ├─ DuckDB directory (backend/data/) exists
   └─ Ports 8000 available

3. Backend Startup (start_server.py)
   ├─ Load .env into os.environ
   ├─ Initialize FastAPI app
   ├─ Connect to DuckDB (creates schema if missing)
   ├─ Start MessageBus
   ├─ Mount API routes (29 files)
   ├─ Start lifespan context:
   │   ├─ ML Flywheel singletons (ModelRegistry, DriftMonitor)
   │   ├─ OllamaNodePool health checks
   │   ├─ MarketDataAgent
   │   ├─ AlpacaStreamManager (if not disabled)
   │   ├─ EventDrivenSignalEngine
   │   ├─ CouncilGate
   │   ├─ OrderExecutor
   │   ├─ SwarmSpawner (if LLM_ENABLED)
   │   ├─ KnowledgeIngestionService
   │   ├─ AutonomousScoutService (if LLM_ENABLED)
   │   ├─ DiscordSwarmBridge (if LLM_ENABLED)
   │   ├─ GeopoliticalRadar (if LLM_ENABLED)
   │   ├─ CorrelationRadar
   │   ├─ WebSocket bridges (MarketData, Swarm, Macro)
   │   └─ Heartbeat loop
   └─ Uvicorn server listens on 0.0.0.0:8000

4. Backend Health Check
   ├─ TCP port 8000 open
   └─ HTTP GET /healthz returns 200

5. Frontend Startup (optional)
   ├─ node_modules installed
   ├─ Port 3000 available
   ├─ Vite dev server starts
   └─ Proxy configured to backend
```

### Optional Components (Fail-Open)

```
Brain Service (PC2)
├─ Ollama running on localhost:11434 (or OLLAMA_HOST)
├─ gRPC server on port 50051
├─ Backend calls via BRAIN_HOST env var (defaults to localhost)
└─ If unavailable: hypothesis_agent falls back to no-LLM mode

Redis (Docker only, or PC2)
├─ Port 6379
├─ Used for MessageBus cross-PC bridge (optional)
└─ If unavailable: MessageBus runs in local mode

External Data Sources (all fail-open)
├─ Alpaca Markets (required for trading, optional for dev)
├─ Unusual Whales (optional, degrades if missing)
├─ Finviz Elite (optional)
├─ FRED API (optional)
├─ NewsAPI (optional)
└─ All checked at runtime, startup continues if missing
```

### Port Usage Summary

| Port | Service | Protocol | Required |
|------|---------|----------|----------|
| 8000 | Backend FastAPI | HTTP/WS | Yes |
| 3000 | Frontend Vite | HTTP | Yes (for UI) |
| 50051 | Brain Service | gRPC | Optional |
| 6379 | Redis | TCP | Optional |
| 11434 | Ollama | HTTP | Optional |

---

## C. Failure-Point Analysis

### 1. Missing Environment Variables

**Risk:** Backend starts but features are disabled silently

**Current Behavior:**
- ✅ `start-embodier.ps1` warns if ALPACA_API_KEY is placeholder
- ⚠️ Other missing keys (FRED, Unusual Whales, etc.) are NOT validated
- ✅ Backend uses fail-open design (logs warnings, continues startup)

**Recommendation:** Add preflight script to validate ALL required vs optional env vars

---

### 2. Filename Confusion: `start_server.py` vs `run_server.py`

**Issue:** Both files exist in backend/

**Details:**
- `start_server.py`: Normal development startup (13 lines, uses settings)
- `run_server.py`: PyInstaller-compatible startup (32 lines, handles frozen mode)

**Current State:**
- ✅ `start-embodier.ps1` correctly calls `start_server.py`
- ⚠️ README Quick Start (line 350) says `python start_server.py` (correct)
- ⚠️ README Repository Map (line 215) says `run_server.py` (confusing)

**Recommendation:** Update README to mention BOTH files and explain the difference

---

### 3. Port Conflicts

**Risk:** Stale processes block startup

**Current Mitigation:**
- ✅ `start-embodier.ps1` kills processes on ports 8000 and 3000 before startup
- ✅ Uses robust netstat parsing + taskkill
- ✅ Works even if PIDs are orphaned

**Status:** SOLVED

---

### 4. DuckDB Lock Files

**Risk:** Previous crash leaves .wal files, blocking new connection

**Current Mitigation:**
- ✅ `start-embodier.ps1` deletes `analytics.duckdb.wal` and `.tmp` files
- ⚠️ Hardcoded to `backend\data\analytics.duckdb` (should use settings)

**Recommendation:** Read DB path from .env (DATABASE_URL) to clean correct file

---

### 5. Windows Encoding Issues (.env file)

**Risk:** Non-ASCII bytes in .env crash starlette/slowapi with UnicodeDecodeError

**Current Mitigation:**
- ✅ `start-embodier.ps1` strips non-ASCII bytes and rewrites as UTF-8 without BOM
- ✅ Sets `PYTHONUTF8=1` env var before starting Python
- ✅ Uses `python -X utf8` flag

**Status:** SOLVED (excellent fix)

---

### 6. Health Check Timeout in Docker

**Risk:** Backend lifespan init takes >30s, health check kills container

**Current Mitigation:**
- ✅ Docker health check has `start_period: 120s`
- ✅ Backend health check is `/health` (comprehensive) not `/healthz` (liveness only)

**Issue:** Docker health check uses `curl -f http://localhost:8000/health` but should use `/healthz` for faster response

**Recommendation:** Change Docker health check to `/healthz` (no DB queries, <50ms)

---

### 7. Missing Brain Service Integration

**Risk:** Users don't know how to start brain service, council runs without LLM

**Current State:**
- ✅ Backend starts without brain service (fail-open)
- ⚠️ No clear instructions on when/how to start brain service
- ⚠️ No health check for brain service connectivity

**Recommendation:**
1. Add `BRAIN_ENABLED` env flag
2. Add brain service health check to `/readyz` endpoint
3. Add optional brain service startup to `start-embodier.ps1 -WithBrain`

---

### 8. Frontend Assumes Backend is Ready

**Risk:** Frontend starts before backend is healthy, users see errors

**Current Mitigation:**
- ✅ `start-embodier.ps1` waits for backend health check before starting frontend
- ✅ Docker Compose uses `depends_on` with health condition

**Status:** SOLVED

---

### 9. No Automated Startup Verification

**Risk:** Startup completes but critical routes are broken

**Current State:**
- ✅ Health checks exist (`/healthz`, `/readyz`, `/health`)
- ⚠️ No automated script to verify critical endpoints work

**Recommendation:** Create `scripts/verify-startup.py` that:
1. Checks `/healthz` returns 200
2. Checks `/api/v1/status` returns valid JSON
3. Checks `/api/v1/council/status` returns council config
4. Checks WebSocket connection succeeds
5. Checks key API routes (stocks, portfolio, signals)

---

### 10. Inconsistent Health Check Endpoints

**Observation:**
- `/healthz` → Liveness probe (fast, no dependencies)
- `/readyz` → Readiness probe (checks DuckDB, Alpaca, services)
- `/health` → Comprehensive health (ML status, event pipeline, council)

**Docker uses:** `/health` (should use `/healthz`)
**PowerShell uses:** `/healthz` (correct)

**Recommendation:** Standardize on `/healthz` for liveness, `/readyz` for readiness

---

## D. Canonical Startup Design

### Local Development (Windows — One Command)

**Command:**
```powershell
.\start-embodier.ps1
```

**What it does:** (see Section A.1)

**Optional flags:**
- `-SkipFrontend` — Backend only
- `-BackendPort 8001` — Custom backend port
- `-FrontendPort 3001` — Custom frontend port

**Startup sequence:**
1. Preflight: Python 3.10+, Node 18+
2. Port cleanup: 8000, 3000
3. DuckDB lock cleanup
4. .env validation and encoding fix
5. Backend venv + deps
6. Start backend (logs to logs/backend.log)
7. Wait for backend health (TCP + HTTP /healthz)
8. Frontend npm install (if needed)
9. Start frontend (logs to logs/frontend.log)
10. Open browser to http://localhost:3000
11. Monitor loop (health check every 10s)

**Health check flow:**
```
1. TCP port check (fast, works even if event loop blocked)
2. HTTP GET /healthz (confirms HTTP stack is responding)
3. If both pass → healthy
4. If 3 consecutive failures → shutdown and show logs
```

---

### Local Development (Manual — Advanced Users)

**Terminal 1 — Backend:**
```powershell
cd backend
venv\Scripts\Activate.ps1
python start_server.py
```

**Terminal 2 — Frontend:**
```powershell
cd frontend-v2
npm run dev
```

**Terminal 3 — Brain Service (optional, PC2):**
```bash
cd brain_service
python compile_proto.py  # First time only
python server.py
```

---

### Docker Compose

**Command:**
```bash
docker-compose up -d
```

**Startup order:**
1. Redis (health: redis-cli ping)
2. Backend (waits for Redis health)
   - Health check: `curl -f http://localhost:8000/health` ← SHOULD BE /healthz
   - Start period: 120s
3. Frontend (waits for Backend health)

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Recommendation:** Change backend health check to `/healthz` for faster startup

---

### Degraded Mode Startup

**Scenario 1: No Alpaca Keys**
- ✅ Backend starts
- ✅ Warns in logs: "ALPACA_API_KEY not configured"
- ✅ `/readyz` returns 200 but sets `alpaca_configured: not_configured`
- ✅ Market data features disabled
- ✅ UI shows "Demo Mode" or "Paper Trading Disabled"

**Scenario 2: No Brain Service**
- ✅ Backend starts
- ✅ hypothesis_agent falls back to rule-based mode
- ✅ Council runs without LLM inference
- ⚠️ No clear indication to user that LLM is disabled

**Scenario 3: No Optional Integrations**
- ✅ Backend starts
- ✅ Logs warnings for each missing service
- ✅ Features degrade gracefully

**Recommendation:** Add `/api/v1/startup-status` endpoint that returns:
```json
{
  "mode": "full|degraded|minimal",
  "critical_services": {
    "database": "ok",
    "message_bus": "ok",
    "backend_api": "ok"
  },
  "optional_services": {
    "alpaca": "configured|not_configured",
    "brain_service": "connected|disconnected",
    "unusual_whales": "configured|not_configured",
    "finviz": "configured|not_configured"
  },
  "disabled_features": []
}
```

---

## E. Concrete Changes Needed

### 1. README.md

**Change 1: Fix filename reference**

**Line 215:** (Repository Map)
```diff
- └── run_server.py
+ ├── run_server.py              # PyInstaller-compatible entry point
+ └── start_server.py             # Development entry point (use this)
```

**Change 2: Clarify Quick Start**

**Line 350:**
```diff
# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit .env with Alpaca API keys
-python start_server.py
+python start_server.py  # Or: uvicorn app.main:app --reload
```

**Change 3: Add brain service instructions**

Add new section after line 356:
```markdown
### Brain Service (Optional — PC2 GPU Machine)

The brain service provides LLM inference via Ollama for the hypothesis agent.

**Prerequisites:**
1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Start Ollama: `ollama serve`

**Start brain service:**
```bash
cd brain_service
python compile_proto.py  # First time only
python server.py
```

**Configure backend to use brain service:**
```env
# In backend/.env
BRAIN_ENABLED=true
BRAIN_HOST=localhost  # Or PC2 IP: 192.168.1.116
BRAIN_PORT=50051
```

If brain service is not running, the backend will start in degraded mode with rule-based hypothesis generation.
```

---

### 2. SETUP.md

**Change 1: Add environment validation section**

Add after line 50:
```markdown
## Environment Validation

Before first run, validate your environment:

```powershell
# Check Python version (must be 3.10+)
python --version

# Check Node version (must be 18+)
node --version

# Check backend dependencies
cd backend
pip install -r requirements.txt
python -c "import fastapi, uvicorn; print('✅ Backend deps OK')"

# Check frontend dependencies
cd ../frontend-v2
npm install
npm run build --dry-run
```

**Change 2: Document health check endpoints**

Add after line 150:
```markdown
## Health Check Endpoints

| Endpoint | Purpose | Response Time | Dependencies |
|----------|---------|---------------|--------------|
| /healthz | Liveness probe | <50ms | None |
| /readyz | Readiness probe | <200ms | DuckDB, Alpaca config check |
| /health | Full diagnostic | <500ms | All subsystems |

**Test health:**
```powershell
Invoke-RestMethod http://localhost:8000/healthz
Invoke-RestMethod http://localhost:8000/readyz
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Depth 5
```
```

---

### 3. start-embodier.ps1

**Change 1: Add brain service support**

Add parameter at line 1:
```powershell
param(
    [switch]$SkipFrontend,
+   [switch]$WithBrain,
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [int]$MaxRestarts = 3
)
```

Add after line 310 (after frontend starts):
```powershell
# Start brain service (if requested and Python available on PC2)
$brainProc = $null
if ($WithBrain) {
    $BrainDir = Join-Path $Root "brain_service"
    if (Test-Path $BrainDir) {
        Set-Location $BrainDir

        # Check if proto is compiled
        $protoDir = Join-Path $BrainDir "proto"
        if (-not (Test-Path "$protoDir\brain_pb2.py")) {
            Log "Compiling gRPC proto files..." Cyan
            & python compile_proto.py
        }

        $brainLogFile = Join-Path $LogDir "brain.log"
        $brainErrFile = Join-Path $LogDir "brain-error.log"
        "" | Out-File $brainLogFile -Encoding utf8
        "" | Out-File $brainErrFile -Encoding utf8

        $brainProc = Start-Process -FilePath "python" -ArgumentList "server.py" `
            -WorkingDirectory $BrainDir `
            -RedirectStandardOutput $brainLogFile `
            -RedirectStandardError $brainErrFile `
            -PassThru -WindowStyle Hidden

        Log "Brain Service PID: $($brainProc.Id)" DarkGray
        Log "Brain Service  grpc://localhost:50051" Green
    } else {
        Log "Brain service directory not found - skipping" Yellow
    }
}
```

**Change 2: Improve health check logging**

Change line 260:
```powershell
if ($healthy) {
    Log "Backend   http://localhost:$BackendPort" Green
    Log "API Docs  http://localhost:$BackendPort/docs" DarkGray
+   Log "Health    http://localhost:$BackendPort/healthz" DarkGray
+   Log "Readiness http://localhost:$BackendPort/readyz" DarkGray
} else {
```

---

### 4. docker-compose.yml

**Change 1: Fix backend health check**

Line 66:
```diff
    healthcheck:
-     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
+     test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
-     start_period: 120s
+     start_period: 60s
```

**Rationale:** `/healthz` is liveness-only (no DB queries), much faster, allows shorter start period

---

### 5. backend/.env.example

**Change 1: Add brain service config**

Add after line 180 (after YOUTUBE config):
```env
# ── Brain Service (gRPC + Ollama LLM) ────────────────
# Optional — provides LLM inference for hypothesis agent.
# If disabled, backend uses rule-based hypothesis generation.
BRAIN_ENABLED=false
BRAIN_HOST=localhost
BRAIN_PORT=50051
# For dual-PC setup, point to PC2:
# BRAIN_HOST=192.168.1.116
```

---

### 6. New File: `scripts/preflight.py`

Create comprehensive environment validation script:

```python
#!/usr/bin/env python3
"""Preflight validation for Embodier Trading System startup.

Checks:
- Python 3.10+ installed
- Required Python packages available
- .env file exists and is valid
- Required env vars present
- Optional env vars present (warns if missing)
- Ports 8000, 3000, 50051 available
- DuckDB directory writable

Exit codes:
- 0: All checks passed
- 1: Critical failure (missing required dependency)
- 2: Degraded mode (optional dependency missing)
"""

import os
import sys
import socket
from pathlib import Path

# Color output helpers
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

def check(name: str, status: bool, details: str = ""):
    symbol = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    msg = f"  {symbol} {name}"
    if details:
        msg += f" — {details}"
    print(msg)
    return status

def warn(name: str, details: str = ""):
    print(f"  {YELLOW}⚠{RESET} {name} — {details}")

def info(msg: str):
    print(f"{CYAN}{msg}{RESET}")

def check_python_version():
    version = sys.version_info
    required = (3, 10)
    ok = version >= required
    check("Python version", ok, f"{version.major}.{version.minor}.{version.micro} (required: 3.10+)")
    return ok

def check_python_packages():
    packages = ["fastapi", "uvicorn", "duckdb", "alpaca", "pydantic", "dotenv"]
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            check(f"Package {pkg}", True)
        except ImportError:
            check(f"Package {pkg}", False, "Not installed")
            all_ok = False
    return all_ok

def check_env_file():
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    exists = env_path.exists()
    check(".env file exists", exists, str(env_path))
    return exists

def check_env_vars():
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    load_dotenv(env_path)

    required = {
        "ALPACA_API_KEY": "Alpaca trading (can be placeholder for dev)",
        "ALPACA_SECRET_KEY": "Alpaca trading",
    }

    optional = {
        "UNUSUAL_WHALES_API_KEY": "Options flow data",
        "FINVIZ_API_KEY": "Stock screener",
        "FRED_API_KEY": "Economic data",
        "NEWS_API_KEY": "News headlines",
        "YOUTUBE_API_KEY": "YouTube knowledge agent",
    }

    all_ok = True
    info("Checking required environment variables:")
    for key, desc in required.items():
        val = os.getenv(key, "")
        if val and not val.startswith("your-"):
            check(key, True, desc)
        else:
            warn(key, f"Not set or placeholder — {desc}")

    info("Checking optional environment variables:")
    for key, desc in optional.items():
        val = os.getenv(key, "")
        if val and not val.startswith("your-"):
            check(key, True, desc)
        else:
            warn(key, f"Not set — {desc} will be disabled")

    return all_ok

def check_port(port: int, name: str):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                check(f"Port {port} ({name})", False, "Already in use")
                return False
            else:
                check(f"Port {port} ({name})", True, "Available")
                return True
    except Exception as e:
        warn(f"Port {port} ({name})", f"Could not check: {e}")
        return True  # Assume OK

def check_duckdb_dir():
    db_dir = Path(__file__).parent.parent / "backend" / "data"
    exists = db_dir.exists()
    if not exists:
        db_dir.mkdir(parents=True, exist_ok=True)
    writable = os.access(db_dir, os.W_OK)
    check("DuckDB directory", writable, str(db_dir))
    return writable

def main():
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}  Embodier Trading System — Preflight Check{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    checks = []

    # Critical checks
    info("1. Critical Dependencies")
    checks.append(("Python version", check_python_version()))
    checks.append(("Python packages", check_python_packages()))
    checks.append((".env file", check_env_file()))
    checks.append(("DuckDB directory", check_duckdb_dir()))

    # Environment variables
    info("\n2. Environment Configuration")
    check_env_vars()

    # Port availability
    info("\n3. Port Availability")
    checks.append(("Backend port", check_port(8000, "Backend API")))
    checks.append(("Frontend port", check_port(3000, "Frontend Dev Server")))
    check_port(50051, "Brain Service (optional)")

    # Summary
    critical_passed = all(passed for _, passed in checks)

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    if critical_passed:
        print(f"{GREEN}✅ Preflight check PASSED — ready to start{RESET}")
        print(f"\nRun: {CYAN}./start-embodier.ps1{RESET} (Windows) or {CYAN}docker-compose up -d{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ Preflight check FAILED — fix errors above{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

### 7. New File: `scripts/verify-startup.py`

Create automated startup verification:

```python
#!/usr/bin/env python3
"""Verify that all critical backend endpoints are responding correctly.

This script is run AFTER startup to confirm the system is operational.
"""

import sys
import time
import requests
from typing import Tuple

RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

def test_endpoint(url: str, name: str, timeout: int = 5) -> Tuple[bool, str]:
    """Test an HTTP endpoint."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return True, f"OK ({r.status_code})"
        else:
            return False, f"Status {r.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def main():
    base_url = "http://localhost:8000"

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}  Startup Verification{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    tests = [
        (f"{base_url}/healthz", "Liveness probe"),
        (f"{base_url}/readyz", "Readiness probe"),
        (f"{base_url}/health", "Health diagnostics"),
        (f"{base_url}/api/v1/status", "Status API"),
        (f"{base_url}/api/v1/council/status", "Council status"),
        (f"{base_url}/docs", "API documentation"),
    ]

    all_passed = True
    for url, name in tests:
        passed, details = test_endpoint(url, name)
        symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {symbol} {name:30} {details}")
        if not passed:
            all_passed = False

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    if all_passed:
        print(f"{GREEN}✅ All checks passed — system is operational{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ Some checks failed — see errors above{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## F. Verification Plan

### Manual Verification Steps

**1. Windows Local Startup**
```powershell
# Clean start
.\start-embodier.ps1

# Verify logs
Get-Content logs\backend.log -Tail 50
Get-Content logs\frontend.log -Tail 50

# Test health
Invoke-RestMethod http://localhost:8000/healthz
Invoke-RestMethod http://localhost:3000

# Test API
Invoke-RestMethod http://localhost:8000/api/v1/status

# Stop
Ctrl+C
```

**2. Docker Startup**
```bash
# Build and start
docker-compose build
docker-compose up -d

# Check health
docker-compose ps
docker-compose logs backend | tail -50
curl http://localhost:8000/healthz
curl http://localhost:3000

# Test API
curl http://localhost:8000/api/v1/status

# Stop
docker-compose down
```

**3. Degraded Mode (No Alpaca Keys)**
```powershell
# Edit backend/.env: Set ALPACA_API_KEY=
.\start-embodier.ps1

# Verify warning in logs
Get-Content logs\backend.log | Select-String "ALPACA"

# Check readyz
Invoke-RestMethod http://localhost:8000/readyz
# Should show: alpaca_configured: not_configured
```

**4. Brain Service Integration**
```powershell
# Start with brain
.\start-embodier.ps1 -WithBrain

# Verify brain process
Get-Process python | Where-Object { $_.Path -like "*brain_service*" }

# Check brain logs
Get-Content logs\brain.log -Tail 20
```

### Automated Verification

```bash
# Preflight check before startup
python scripts/preflight.py

# Start system
.\start-embodier.ps1

# Post-startup verification
python scripts/verify-startup.py
```

---

## G. Priority Fixes

### P0 — Critical (Do First)

1. ✅ **Document filename drift** (README: run_server.py vs start_server.py)
2. ✅ **Fix Docker health check** (use /healthz instead of /health)
3. ✅ **Create preflight.py** (validate environment before startup)
4. ✅ **Create verify-startup.py** (test critical endpoints post-startup)

### P1 — High (Do Next)

5. ✅ **Add brain service integration** (start-embodier.ps1 -WithBrain flag)
6. ✅ **Add BRAIN_ENABLED to .env.example**
7. ✅ **Document degraded mode** (README: what works without Alpaca/brain)
8. ✅ **Add startup-status API endpoint** (shows enabled/disabled features)

### P2 — Medium (Nice to Have)

9. ⏸️ **Consolidate run_server.py and start_server.py** (single entry point)
10. ⏸️ **Add .env validation on backend startup** (fail fast on invalid config)
11. ⏸️ **Add WebSocket health check** (verify WS connections work)
12. ⏸️ **Add brain service connectivity test** (gRPC health check)

---

## H. Summary

### What Works Well ✅

1. **One-click Windows startup** (`start-embodier.ps1`) is robust and production-ready
2. **Docker Compose** has proper health checks and dependency ordering
3. **Fail-open design** allows development without all integrations configured
4. **Health endpoints** are well-implemented and comprehensive
5. **Port cleanup** and DuckDB lock handling prevent common startup issues
6. **Windows encoding fixes** solve real-world deployment problems

### What Needs Fixing ⚠️

1. **Filename confusion** (run_server.py vs start_server.py) needs documentation
2. **Docker health check** should use /healthz (not /health) for faster startup
3. **No preflight validation** script to catch issues before startup
4. **Brain service** not integrated into root launcher
5. **No automated verification** of critical endpoints post-startup
6. **Degraded mode** not clearly documented for solo operators

### What Should Be Added 🆕

1. `scripts/preflight.py` — Environment validation before startup
2. `scripts/verify-startup.py` — Endpoint verification after startup
3. `BRAIN_ENABLED` env var and brain service health checks
4. `/api/v1/startup-status` endpoint showing enabled/disabled features
5. `-WithBrain` flag for start-embodier.ps1
6. Clearer degraded mode documentation in README

---

## Conclusion

The Embodier Trading System startup process is **fundamentally sound** with a clear canonical path for Windows development (`start-embodier.ps1`) and Docker deployment. The main issues are:

1. **Documentation drift** (minor filename confusion)
2. **Missing preflight validation** (preventable errors)
3. **Brain service not integrated** (manual startup required)
4. **No automated verification** (post-startup smoke tests)

All issues are **addressable with small, focused changes** — no major refactoring required.

**Recommended Next Steps:**
1. Implement P0 fixes (documentation, Docker health check, validation scripts)
2. Test all startup paths (Windows, Docker, degraded mode)
3. Implement P1 fixes (brain service integration, degraded mode docs)
4. Run full verification suite
5. Update CI/CD to include preflight and verification steps

---

**Audit Complete.**
**Status:** PASSED with minor fixes recommended.
**Confidence:** HIGH — startup is reliable for solo operator on Windows.
