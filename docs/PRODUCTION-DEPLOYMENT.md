# Production Deployment — Embodier Trader

Operational requirements and deployment notes for running the backend reliably in production.

**Last updated:** March 12, 2026 | **Version:** v5.0.0

---

## 1. Environment variables

### Required for all modes

| Variable | Purpose | Example (never commit real values) |
|----------|---------|-------------------------------------|
| `TRADING_MODE` | `paper` or `live` — controls broker URL and startup validation | `paper` |
| `ALPACA_API_KEY` | Alpaca Markets API key | (from Alpaca dashboard) |
| `ALPACA_SECRET_KEY` | Alpaca secret | (from Alpaca dashboard) |

- **Paper:** Use Alpaca paper keys and `ALPACA_BASE_URL=https://paper-api.alpaca.markets` (or leave default; backend forces paper URL when `TRADING_MODE=paper`).
- **Live:** Use live keys and `ALPACA_BASE_URL=https://api.alpaca.markets`. **Live mode additionally requires** `API_AUTH_TOKEN` (see below).

### Required for live trading

| Variable | Purpose |
|----------|---------|
| `API_AUTH_TOKEN` | Bearer token for all state-changing and execution endpoints. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |

If `TRADING_MODE=live` and `API_AUTH_TOKEN` is not set, the application **raises at startup** and will not run.

### Recommended for production

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | Set to `production` for JSON logging and stricter behavior. |
| `LOG_LEVEL` | `INFO` or `WARNING`. Avoid `DEBUG` in production (no secret leakage, but verbose). |
| `CORS_ORIGINS` | Comma-separated allowed origins (e.g. your dashboard URL). Localhost is always allowed. |
| `REDIS_URL` | If using cross-PC MessageBus (e.g. PC2 brain_service). |
| `BRAIN_HOST` / `BRAIN_PORT` | PC2 brain service host/port for LLM inference. |

### Optional (degrade gracefully if missing)

Data sources and LLM keys: `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `FINVIZ_API_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, etc. See `backend/.env.example`.

---

## 2. Secrets handling

- **Never** commit `.env` or any file containing API keys or tokens.
- **Never** log tokens, passwords, or API key values. Log only presence (e.g. "API_AUTH_TOKEN set").
- All sensitive config is loaded via `app.core.config.settings` from environment / `.env`.
- WebSocket auth: pass token as query param `?token=<API_AUTH_TOKEN>`; same token as REST Bearer.

---

## 3. Paper vs live execution

| Aspect | Paper | Live |
|--------|--------|------|
| Broker URL | `paper-api.alpaca.markets` | `api.alpaca.markets` |
| Startup | Runs without `API_AUTH_TOKEN` | **Requires** `API_AUTH_TOKEN`; fails otherwise |
| REST auth | Recommended; state-changing endpoints require Bearer if `API_AUTH_TOKEN` is set | **Required** on all protected routes |
| Execution | Orders sent to Alpaca paper account | Orders sent to live account |
| Guard | Backend forces paper URL when `TRADING_MODE=paper` | Backend validates Alpaca account type on startup when `AUTO_EXECUTE_TRADES=true` |

- **AUTO_EXECUTE_TRADES:** Set to `true` to let the OrderExecutor submit real orders (paper or live depending on `TRADING_MODE`). If `false`, the system runs in shadow mode (council and sizing run, but no orders submitted).
- **Defensive guard:** OrderExecutor and AlpacaService ensure URL and account type match `TRADING_MODE`; no live orders are sent when mode is paper.

---

## 4. Health and readiness endpoints

Use these for load balancers, Kubernetes probes, and monitoring.

| Endpoint | Purpose | Returns |
|----------|---------|--------|
| `GET /healthz` | Liveness — process alive, no dependencies | `{"status": "alive"}` |
| `GET /readyz` | Readiness — DuckDB, Alpaca config, MessageBus, optional Ollama/Redis/Brain | `{"status": "ready"|"not_ready", "checks": {...}}` — 503 if not ready |
| `GET /health` | Full health — ML engine, event pipeline, council gate, DuckDB, weights | Detailed JSON |
| `GET /api/v1/health` | Aggregated health — DuckDB, Alpaca, Brain gRPC, MessageBus, last council, data sources | JSON with per-component status |

### Programmatic sub-checks (for dashboards or automation)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Single call for DuckDB, broker, brain, data sources. |
| `GET /api/v1/council/health` | Last council evaluation + rolling 24h latency/health. |
| `GET /api/v1/data-sources/health` | Per–data source status. |

- **Kubernetes:** Set liveness probe to `GET /healthz` and readiness probe to `GET /readyz`.

---

## 5. Observability

### Metrics

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/metrics` | Full JSON: core counters/gauges, MessageBus, OrderExecutor, CouncilGate, pipeline summary, council latency percentiles, weight learner. |
| `GET /api/v1/metrics/prometheus` | Prometheus text exposition format. |
| `GET /api/v1/metrics/pipeline` | Pipeline-only: signals, council, execution, fill rate. |

### Key metrics

- **Council:** `council_latency_ms` (gauge, last run), percentiles from council health rolling window; stage timings in council health / pipeline metrics.
- **Execution:** `execution_attempt_total`, `execution_gate_denied_total`, `execution_viability_denied_total` (counters); OrderExecutor status (signals_received, signals_executed, signals_rejected).
- **Errors:** Counters by reason; check `GET /api/v1/metrics` and Prometheus scrape.

### Logging

- **Production:** Set `ENVIRONMENT=production` for JSON logs (ts, level, logger, msg, correlation_id, trace_id, eval_id).
- **Correlation:** Each request gets `X-Correlation-ID` or generated ID; council runs set `eval_id`/`trace_id` to `council_decision_id` for tracing signal → council → order.

---

## 6. Running the backend in production

### Single node (e.g. PC1)

```bash
cd backend
# Activate venv, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

- Use `--workers 1` if using in-memory state (MessageBus, CouncilGate, OrderExecutor). For multiple workers you would need shared state (e.g. Redis) and is out of scope here.

### With Docker

```bash
docker-compose up -d
# Health: curl http://localhost:8000/readyz
```

### Startup order

1. Load `.env`, validate config (live mode requires `API_AUTH_TOKEN` + Alpaca keys).
2. Init DB, MessageBus, services, council gate, order executor.
3. If `AUTO_EXECUTE_TRADES=true`, validate Alpaca account type vs `TRADING_MODE`; on mismatch, force shadow mode.
4. Serve HTTP; `/healthz` and `/readyz` available after app is up.

---

## 7. Protected endpoints

All state-changing and execution-related routes require `Authorization: Bearer <API_AUTH_TOKEN>` when `API_AUTH_TOKEN` is set (and are blocked when it is not set). Examples:

- `POST /api/v1/council/evaluate`
- `POST /api/v1/orders/*` (submit, close, flatten, emergency-stop)
- `POST /api/v1/risk/emergency/*`
- `POST /api/v1/metrics/emergency-flatten`
- `POST /api/v1/ingestion/backfill`
- Settings, data source credentials, agents, HITL, etc.

See `docs/API-REFERENCE.md` for the full list.

---

## 8. Checklist before going live

- [ ] `TRADING_MODE=live` only when intentionally trading with real money.
- [ ] `API_AUTH_TOKEN` set and stored securely; Bearer used by all clients that call protected endpoints.
- [ ] Alpaca **live** keys and `ALPACA_BASE_URL=https://api.alpaca.markets`.
- [ ] `ENVIRONMENT=production`, `LOG_LEVEL=INFO` or `WARNING`.
- [ ] Health/readiness monitored (e.g. `/readyz`); alerts on 503 or critical dependency down.
- [ ] Metrics scraped (e.g. `/api/v1/metrics/prometheus`) for council latency, execution counters, errors.
- [ ] No secrets in logs or in version control.
