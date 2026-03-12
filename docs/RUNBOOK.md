# Runbook — Embodier Trader Operations

Operational guide for starting/stopping the system, checking health, emergency procedures, and common errors. Paths are repo-relative; see PATH-STANDARD.md and PATH-MAP.md for machine-specific paths.

---

## 1. Start / stop the system

### PC1 (ESPENMAIN) — primary (backend + frontend + trading)

**Start backend**
```bash
cd backend
# Optional: venv\Scripts\Activate.ps1  (Windows) or source venv/bin/activate (Linux/Mac)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start frontend**
```bash
cd frontend-v2
npm run dev
```
Frontend: http://localhost:5173. API: http://localhost:8000. Docs: http://localhost:8000/docs.

**One-click (Windows)**
```powershell
.\launch.bat
# or
.\start-embodier.ps1
```

**Stop**
- Backend: `Ctrl+C` in the terminal running uvicorn.
- Frontend: `Ctrl+C` in the terminal running `npm run dev`.
- Electron (if used): Exit from tray or app menu.

### PC2 (ProfitTrader) — brain_service (gRPC + Ollama)

**Start brain service**
```bash
cd brain_service
pip install -r requirements.txt   # first time only
python server.py
```
Listens on port 50051. Optional for council; required for hypothesis_agent LLM inference.

**Stop**
- `Ctrl+C` in the terminal running `python server.py`.

---

## 2. Check system health

| Check | How |
|-------|-----|
| **Liveness** | `GET http://localhost:8000/healthz` — returns 200 when process is up. |
| **Unified health** | `GET http://localhost:8000/health` — DuckDB, Alpaca, and service health. |
| **API docs** | http://localhost:8000/docs — Swagger UI; confirms routes are mounted. |
| **Council status** | `GET http://localhost:8000/api/v1/council/status` — 35 agents, 7 stages. |
| **Event pipeline** | `GET http://localhost:8000/api/v1/status` — MessageBus, CouncilGate, OrderExecutor. |
| **Data sources** | `GET http://localhost:8000/api/v1/data-sources/` — Alpaca, Finviz, FRED, etc. |
| **Risk** | `GET http://localhost:8000/api/v1/risk/risk-score` — current risk score. |
| **Metrics** | `GET http://localhost:8000/api/v1/metrics` (or path used by metrics_api) — council latency, queue depth, weight learner. |

**Interpretation**
- `healthz` 200 = process alive.
- `health` with `"status": "healthy"` and non-zero DuckDB tables = OK for trading.
- If council/status shows agents failing or pipeline components disabled, check logs and env (e.g. `COUNCIL_ENABLED`, `LLM_ENABLED`).

---

## 3. Emergency flatten (close all positions)

**Via API (recommended)**
```bash
curl -X POST "http://localhost:8000/api/v1/orders/flatten-all" \
  -H "Authorization: Bearer YOUR_API_AUTH_TOKEN"
```
Requires `API_AUTH_TOKEN` from `backend/.env`. Retries and DuckDB pending_liquidations are handled by the backend.

**Via API — emergency stop (no new orders)**
```bash
curl -X POST "http://localhost:8000/api/v1/orders/emergency-stop" \
  -H "Authorization: Bearer YOUR_API_AUTH_TOKEN"
```

**Risk shield — freeze new entries**
```bash
curl -X POST "http://localhost:8000/api/v1/risk-shield/emergency" \
  -H "Authorization: Bearer YOUR_API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "freeze_entries", "value": true}'
```
To unfreeze: `"value": false`.

**Manual (Alpaca)**  
Use Alpaca dashboard or Alpaca API to close positions if the app is unavailable.

---

## 4. View council decisions and trade history

| What | Where |
|------|--------|
| **Latest council decision** | `GET http://localhost:8000/api/v1/council/latest` — last DecisionPacket (cached). |
| **Run council on a symbol** | `POST http://localhost:8000/api/v1/council/evaluate` with body `{"symbol": "AAPL", "timeframe": "1d"}` (auth required). |
| **Council weights** | `GET http://localhost:8000/api/v1/council/weights` — current Bayesian-learned weights. |
| **Open orders** | `GET http://localhost:8000/api/v1/orders/` (auth). |
| **Recent orders** | `GET http://localhost:8000/api/v1/orders/recent` (auth). |
| **Positions** | `GET http://localhost:8000/api/v1/alpaca/positions` or `GET http://localhost:8000/api/v1/portfolio/positions`. |
| **Performance / trades** | `GET http://localhost:8000/api/v1/performance/trades` or performance dashboard. |

Frontend: Dashboard and Trade Execution pages show council latest and orders when wired to these endpoints.

---

## 5. Update API keys

- **Location**: `backend/.env` (gitignored). Copy from `backend/.env.example` if missing.
- **Required for trading**: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`. Optional: `ALPACA_BASE_URL` (paper vs live).
- **Optional (degrade gracefully if missing)**: `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `FINVIZ_API_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `RESEND_API_KEY`, Slack tokens, etc.

**Steps**
1. Edit `backend/.env` with new values.
2. Restart the backend (`Ctrl+C` then `uvicorn app.main:app ...`).
3. If using Electron/desktop app, update keys via Settings/API Keys if the app persists them.

**Security**: Never commit `.env` or expose keys. Use env vars or a secrets manager in production.

---

## 6. Common error messages and fixes

| Error / symptom | Cause | Fix |
|-----------------|--------|-----|
| **Council evaluation timed out (120s)** | Council or LLM (brain_service) slow/unreachable. | Check brain_service on PC2 (port 50051). Increase timeout only if necessary. Check network/firewall. |
| **Rate limit exceeded: max 10 evaluations per minute** | Too many `POST /api/v1/council/evaluate` calls. | Wait and retry; or adjust rate limit in `council.py` for dev. |
| **RiskGovernor unavailable (503)** | OpenClaw risk_governor not installed or import failed. | Optional. For RiskShield UI only. Install deps or ignore if not using OpenClaw. |
| **DuckDB lock / thread-safety** | Concurrent access or wrong connection usage. | Use `get_conn()` from `app.data.storage` only; do not open raw DuckDB connections elsewhere. |
| **Redis unavailable — MessageBus local-only** | REDIS_URL not set or Redis down. | Set `REDIS_URL` (e.g. `redis://localhost:6379`) for cross-PC MessageBus. Optional for single-PC. |
| **401 Unauthorized** on orders/council evaluate | Missing or invalid Bearer token. | Set `Authorization: Bearer <API_AUTH_TOKEN>`. Get token from `backend/.env` `API_AUTH_TOKEN`. |
| **Entries frozen** | Risk shield or emergency freeze enabled. | `POST /api/v1/risk-shield/emergency` with `{"action": "freeze_entries", "value": false}` (auth). |
| **WebSocket disconnect** | Token or network issue. | Frontend: ensure `?token=<API_AUTH_TOKEN>` in WebSocket URL. Check backend logs. |
| **No signals / council not running** | CouncilGate or signal engine disabled. | Set `COUNCIL_ENABLED=true`, `LLM_ENABLED=true` in `.env`. Check `GET /api/v1/status` for pipeline state. |
| **Scout crashes / discovery degraded** | Missing service methods or external API keys. | Check logs for scout name; add missing methods or disable scout in config. See Phase A scout fixes. |

---

## 7. Logs and debugging

- **Backend logs**: Stdout/stderr of uvicorn. For structured JSON logging, see `app.core.logging_config`.
- **Recent logs API**: `GET http://localhost:8000/api/v1/logs/` — ring buffer of recent log lines.
- **Pytest**: `cd backend && python -m pytest --tb=short -q` — run full test suite before/after changes.

---

## 8. Ports reference

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Brain (gRPC) | 50051 | localhost:50051 |
| Ollama | 11434 | http://localhost:11434 |
| Redis | 6379 | redis://localhost:6379 |

---

## 9. Two-PC summary

| PC | Hostname | Role | Start |
|----|----------|------|--------|
| PC1 | ESPENMAIN | Backend, frontend, DuckDB, OrderExecutor | uvicorn + npm run dev (or launch.bat) |
| PC2 | ProfitTrader | brain_service, Ollama, ML inference | python server.py in brain_service |

Both use the same repo (clone on each). PC1 connects to PC2’s brain_service via gRPC (host/port in config). For shared MessageBus across PCs, run Redis on PC1 and set `REDIS_URL` on both.
