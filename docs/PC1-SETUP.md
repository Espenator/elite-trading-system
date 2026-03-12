# PC1 (ESPENMAIN) Setup — 192.168.1.105

Primary machine: FastAPI backend (primary), Vite frontend (:5173), DuckDB, Alpaca Key 1 trade execution, council gate, order executor, WebSocket manager, real-time signal engine.

## Role Summary

| Item | Value |
|------|--------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary — backend API, frontend, DuckDB, Alpaca Key 1, council gate, order executor, WebSocket |
| Repo path | `C:\Users\Espen\elite-trading-system` or `C:\Users\Espen\Dev\elite-trading-system` |

## Development Priorities (PC1)

1. **Uvicorn multi-worker** — `start_server.py` uses `--workers 4` when `DEBUG=False` (matches 4 P-cores). Override with `UVICORN_WORKERS` in `.env`. With `DEBUG=True` (reload), runs single-worker only.
2. **Ollama on PC1** — Light models only: `llama3.2` and `mistral:7b` for regime classification, signal scoring, quick hypothesis, feature summary. Do **not** run `deepseek-r1:14b` on PC1 (that is PC2’s job). Set `MODEL_PIN_PC1=llama3.2,mistral:7b` in `backend/.env`.
3. **Council gate on PC1** — The 35-agent council runs here. CouncilGate subscribes to `signal.generated`, runs the DAG, publishes `council.verdict`. Hypothesis and critic agents already route LLM calls to PC2 via `brain_client` (gRPC). Strategy and regime agents are rule-based (no LLM in agent).
4. **DuckDB** — PC1 owns DuckDB. Bar flush batch (5s) is in `main.py`. DuckDB connection sets `threads = 8` on init for analytical queries.
5. **Redis on PC1** — Required for dual-PC. Set `REDIS_URL=redis://localhost:6379`. PC2 connects to `192.168.1.105:6379`. `main.py` lifespan runs a Redis startup health check; set `REDIS_REQUIRED=true` to fail startup if Redis is down.
6. **Frontend in production** — For production, build with `vite build --mode production` and serve via FastAPI static mount or nginx. The Vite dev server adds latency (~200ms per request). Development: `npm run dev` on port 5173 is fine.

## PC1-Specific .env (backend/.env)

Verify or set in `backend/.env`:

```env
# Point to PC2 brain_service (gRPC)
BRAIN_SERVICE_URL=192.168.1.116:50051
OLLAMA_BASE_URL=http://localhost:11434
CLUSTER_PC2_HOST=192.168.1.116

# Redis — required for dual-PC; PC2 uses 192.168.1.105:6379
REDIS_URL=redis://localhost:6379

# Optional: fail startup if Redis down
# REDIS_REQUIRED=true

LLM_ENABLED=true
COUNCIL_GATE_ENABLED=true
AUTO_EXECUTE_TRADES=false

# PC1 light Ollama models only
MODEL_PIN_PC1=llama3.2,mistral:7b
OLLAMA_SMALL_MODEL=mistral:7b
```

## Workload Division (PC1 vs PC2)

| Workload | PC1 ESPENMAIN | PC2 ProfitTrader |
|----------|----------------|------------------|
| FastAPI backend (primary) | ✅ Port 8000 | 🔵 Port 8000 (discovery only) |
| Frontend (Vite) | ✅ Port 5173 | ❌ Not needed |
| DuckDB storage | ✅ Owner | ❌ No |
| Order execution | ✅ Alpaca Key 1 | ❌ Never |
| Discovery scanning | ❌ | ✅ Alpaca Key 2 |
| Council gate (35 agents) | ✅ Runs here | ❌ |
| LLM inference (light) | ✅ llama3.2, mistral:7b | ❌ |
| LLM inference (heavy) | 🔵 gRPC calls only | ✅ deepseek-r1:14b, mixtral |
| Brain service gRPC | ❌ Client | ✅ Server :50051 |
| LSTM/PyTorch inference | ❌ No torch | ✅ RTX 4080 CUDA |
| XGBoost training | ❌ | ✅ GPU backend |
| 12 Scout agents | 🔴 Should move off | ✅ Move here |
| Ollama serving | 🔵 Light models | ✅ Heavy models |
| GPU telemetry broadcast | ❌ Consumer | ✅ Producer :8001 |
| Redis | ✅ Host (localhost:6379) | 🔵 Client (192.168.1.105:6379) |
| WebSocket manager | ✅ All channels | ❌ |

## Quick Start (PC1)

```powershell
# From repo root
.\start-embodier.ps1
```

This starts backend (uvicorn via `start_server.py`, 4 workers when not DEBUG) and frontend (Vite dev server). For production frontend, build and serve static:

```powershell
cd frontend-v2
npm run build -- --mode production
# Then serve dist/ via FastAPI static mount or nginx
```

## Fresh Code

```powershell
cd C:\Users\Espen\Dev\elite-trading-system
git pull origin main
```

Then ensure `backend/.env` has the PC1 keys above and Redis is running locally.

## Run & Verify (ESPENMAIN install debug)

Use this after a fresh clone or when debugging the PC1 install.

### 1. One-time: create venv and install deps

If `backend\venv` does not exist:

```powershell
cd C:\Users\Espen\Dev\elite-trading-system\backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Start backend (manual)

Ensure nothing else is using port 8000. From repo root or backend:

```powershell
cd C:\Users\Espen\Dev\elite-trading-system\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Wait until you see: `Embodier Trader v4.1.0 ONLINE` and `Application startup complete`. Then in another terminal:

### 3. Verify health and Alpaca

```powershell
# Health (no auth)
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
# Expect: status = healthy, version = 4.1.0

# Alpaca account (uses API_AUTH_TOKEN from backend/.env if set)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/alpaca/account" -Headers @{ Authorization = "Bearer $env:API_AUTH_TOKEN" }
# Expect: status = ACTIVE, account_number = PA...
```

### 4. Optional: use launcher

From repo root:

```powershell
.\start-embodier.ps1
```

This cleans stale processes, frees ports 8000/5173, then starts backend + frontend. Ensure `backend\.env` exists (copy from `backend\.env.example` and fill keys).

### Common issues

| Issue | Fix |
|-------|-----|
| Port 8000 in use | Run `start-embodier.ps1` (it kills stale Python) or: `Get-NetTCPConnection -LocalPort 8000 \| % { Stop-Process -Id $_.OwningProcess -Force }` |
| `.\venv\Scripts\python.exe` not found | Create venv: `cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt` |
| PC2 gRPC unreachable | Expected if PC2 is off; council runs in degraded mode (local Ollama only). |
| FERNET_KEY not set | Optional; credentials won’t persist across restarts. Set in `.env` for persistence. |
| Redis connection refused | Install/start Redis; PC1 needs `redis://localhost:6379` for MessageBus. |
| **DuckDB "file already open"** | Only one backend can use DuckDB. Close other Embodier/Python instances, then restart. |
| **Alpaca "connection limit exceeded"** | One data WebSocket per account. Close other instances; app falls back to snapshot polling. |

### Desktop shortcut

Run once: `.\scripts\create-shortcut.ps1` to create "Embodier Trader" on Desktop and Start Menu. Double-click runs the launcher; you get one backend terminal and one frontend window; browser opens to the dashboard after ~10s. **Run only one instance** to avoid DuckDB lock or Alpaca connection limit.
