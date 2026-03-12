# Runbook — Embodier Trader Operations

Operational guide for starting/stopping the system, checking health, emergency procedures, and common errors.

**Last updated:** March 12, 2026 | **Version:** v5.0.0

---

## 1. Start / stop the system

### PC1 (ESPENMAIN) — backend + frontend

**Start (manual):**

```powershell
# From repo root
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal:

```powershell
cd frontend-v2
npm install
npm run dev
```

**One-click (Windows):**

```powershell
.\start-embodier.ps1
# or
.\start-embodier.bat
```

This script cleans stale processes, frees ports 8000 and 5173, clears DuckDB lock files, then starts backend and frontend and opens the browser.

**Stop:**

- **Manual:** `Ctrl+C` in each terminal (backend, then frontend).
- **One-click:** Same terminals; `Ctrl+C` stops the launcher and child processes.

### PC2 (ProfitTrader) — brain service (optional)

```powershell
cd brain_service
pip install -r requirements.txt
python server.py
```

Stop with `Ctrl+C`.

### Docker (full stack)

```bash
docker-compose up -d
# Stop
docker-compose down
```

---

## 2. Check system health

### Aggregated health (single endpoint)

```bash
curl -s http://localhost:8000/api/v1/health | jq
```

Returns: DuckDB status, Alpaca connectivity, Brain gRPC status, MessageBus queue depth, last council evaluation time, and (if available) data source summary.

### Programmatic sub-checks (for automation / K8s)

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Liveness (process alive) |
| `GET /readyz` | Readiness (DuckDB, Alpaca, MessageBus, optional Brain/Redis) — returns 503 if not ready |
| `GET /api/v1/health/readiness` | Same as readiness with structured checks (database, broker, brain, data_sources) |
| `GET /api/v1/health/broker` | Broker connectivity only |
| `GET /api/v1/health/brain` | Brain service only |
| `GET /api/v1/health/database` | DuckDB only |
| `GET /api/v1/health/data-sources` | Data provider freshness |

See **docs/PRODUCTION-DEPLOYMENT.md** for production env vars, paper vs live, and observability.

### Key URLs

| Check | URL |
|-------|-----|
| Health | http://localhost:8000/api/v1/health |
| Status | http://localhost:8000/api/v1/status |
| API docs | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |

### Health response (summary)

- **duckdb**: `connected: true` and `status: "healthy"` if DB is OK.
- **alpaca**: `connected: true` if broker API is reachable.
- **brain_grpc**: `connected: true` if brain_service (PC2) is reachable; `disabled` if not configured.
- **messagebus**: `queue_depth`, `queue_max`, `usage_pct` — high `usage_pct` may indicate backpressure.
- **last_council_evaluation**: Timestamp of last council run; stale if no signals recently.

### Alerts and incidents

```bash
curl -s http://localhost:8000/api/v1/health/alerts
curl -s http://localhost:8000/api/v1/health/incidents
```

---

## 3. Emergency flatten

Closes all open positions. **Requires Bearer auth.**

### Via API (recommended)

```bash
curl -X POST "http://localhost:8000/api/v1/metrics/emergency-flatten" \
  -H "Authorization: Bearer YOUR_API_AUTH_TOKEN"
```

Optional query param: `reason=manual` (or any string) for audit.

### Alternative endpoints

- **Flatten all (orders API):**  
  `POST /api/v1/orders/flatten-all` (auth required)
- **Emergency stop (cancel + close):**  
  `POST /api/v1/orders/emergency-stop` (auth required)
- **Risk emergency:**  
  `POST /api/v1/risk/emergency/flatten` (auth required)

### Behavior

- OrderExecutor uses a lock to prevent concurrent flatten runs.
- If Alpaca positions cannot be fetched, a background retry loop runs (e.g. up to 10 attempts).
- On success, an `emergency.flatten` event is published on the MessageBus; Slack may be notified if configured.
- Pending liquidations can be tracked in DuckDB (`pending_liquidations` table) for audit.

---

## 4. View council decisions and trade history

### Council

| What | Endpoint |
|------|----------|
| Latest decision | `GET /api/v1/council/latest` |
| Council status (agents, stages) | `GET /api/v1/council/status` |
| Agent weights | `GET /api/v1/council/weights` |
| Decision history | `GET /api/v1/council/history` |
| Decision by ID | `GET /api/v1/council/decision/{decision_id}` |
| Debates | `GET /api/v1/council/debates` |
| Calibration | `GET /api/v1/council/calibration` |

Example:

```bash
curl -s http://localhost:8000/api/v1/council/latest | jq
```

### Trade history

- **Orders:** `GET /api/v1/orders/` or `GET /api/v1/orders/recent`
- **Portfolio / positions:** `GET /api/v1/portfolio` or `GET /api/v1/alpaca/positions`
- **Performance:** `GET /api/v1/performance/*` (see API-REFERENCE.md)
- **Trades page (frontend):** Open http://localhost:5173/trades

---

## 5. Update API keys

- **Location:** `backend/.env` (gitignored). Do not commit secrets.
- **Template:** `backend/.env.example` lists variable names.

### Required for core trading

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL` (e.g. `https://paper-api.alpaca.markets` for paper)

### Optional (degrade gracefully if missing)

- `API_AUTH_TOKEN` — Bearer token for protected endpoints (generate a secure random string).
- Data sources: `FINVIZ_API_KEY`, `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `SEC_EDGAR_USER_AGENT`, etc.
- LLM: `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`; Brain/Ollama: `BRAIN_SERVICE_URL`, `OLLAMA_BASE_URL`.
- Notifications: `SLACK_BOT_TOKEN`, `RESEND_API_KEY`, `TELEGRAM_BOT_TOKEN`.

### After changing .env

- Restart the backend (uvicorn) so new values are loaded.
- For desktop/launcher flows that spawn the backend, restart the launcher.

---

## 6. Common error messages and fixes

| Symptom / message | Likely cause | Fix |
|-------------------|--------------|-----|
| Port 8000 already in use | Stale uvicorn or another app | Run `start-embodier.ps1` (it frees ports) or kill process using 8000; then restart backend. |
| Port 5173 already in use | Stale Vite or another app | Free 5173 or use another port (e.g. `npm run dev -- --port 5174`). |
| DuckDB "database is locked" / "file in use" | Another process or crashed backend holding lock | Stop all backend processes; remove lock files under `backend/data/` if documented/safe; restart. |
| 401 Unauthorized on POST /council/evaluate or /orders | Missing or invalid Bearer token | Set `API_AUTH_TOKEN` in `backend/.env` and send `Authorization: Bearer <token>` on requests. |
| Council evaluation timed out (120s) | Slow agents or network (e.g. brain gRPC) | Check brain_service on PC2; check network; reduce load or increase timeout if acceptable. |
| "Rate limit exceeded" on council evaluate | Too many evaluations per minute | Wait; default limit is 10/minute; avoid scripting rapid repeated evaluate calls. |
| Alpaca "connection" or "account" errors | Invalid keys or paper/live URL mismatch | Verify `ALPACA_*` in `.env` and `ALPACA_BASE_URL` (paper vs live). |
| Brain gRPC unhealthy / disabled | Brain service not running or unreachable | Start brain_service on PC2; check `BRAIN_SERVICE_URL` and firewall. |
| MessageBus queue 100% / backpressure | High event rate or slow consumers | Check for slow subscribers; consider scaling or tuning rate limits (see ARCHITECTURAL-REVIEW). |
| Import errors (e.g. app.council...) | Wrong cwd or missing deps | Run backend from `backend/` with venv activated; `pip install -r requirements.txt`. |
| Frontend "Failed to fetch" / blank dashboard | Backend not running or CORS | Ensure backend is up on 8000; check browser console and backend CORS (localhost:5173 allowed). |

---

## 7. Logs and debugging

- **Backend logs:** Stdout/stderr of uvicorn (or wherever the process logs). For structured logging, see `backend/app/core/logging_config.py`.
- **System logs API:** `GET /api/v1/logs` (if implemented) for in-memory ring buffer.
- **Metrics:** `GET /api/v1/metrics` and `GET /api/v1/metrics/pipeline` for throughput, council latency, queue depth.

---

## 8. Quick reference

| Task | Command or URL |
|------|-----------------|
| Start backend | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| Start frontend | `cd frontend-v2 && npm run dev` |
| One-click start | `.\start-embodier.ps1` |
| Health check | `GET /api/v1/health` |
| Emergency flatten | `POST /api/v1/metrics/emergency-flatten` (Bearer auth) |
| Council latest | `GET /api/v1/council/latest` |
| API keys | Edit `backend/.env`; restart backend after changes |

For full API details see [API-REFERENCE.md](API-REFERENCE.md). For architecture and council see [COUNCIL-ARCHITECTURE.md](COUNCIL-ARCHITECTURE.md).
