# API Reference — Embodier Trader

All REST endpoints under `backend/app/api/v1/`. Base URL: `http://localhost:8000` (or your backend host). **Auth:** Bearer token in header `Authorization: Bearer <API_AUTH_TOKEN>`; required where noted.

**Last updated:** March 12, 2026 | **Version:** v5.0.0 | **Route files:** 43

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Aggregated health: DuckDB, Alpaca, Brain gRPC, MessageBus, last council |
| GET | `/api/v1/health/alerts` | No | Slack alerter status and config |
| GET | `/api/v1/health/incidents` | No | Recent health incidents |

**Source:** `backend/app/api/v1/health.py`

---

## Trading

### Orders (`/api/v1/orders`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/orders/` | No | List orders (filtered by query params) |
| GET | `/api/v1/orders/recent` | No | Recent orders |
| POST | `/api/v1/orders/advanced` | Yes | Submit advanced order (bracket, OCO, etc.) |
| PATCH | `/api/v1/orders/{order_id}` | Yes | Modify order |
| DELETE | `/api/v1/orders/{order_id}` | Yes | Cancel order |
| DELETE | `/api/v1/orders/` | Yes | Cancel all orders |
| POST | `/api/v1/orders/close` | Yes | Close position |
| POST | `/api/v1/orders/adjust` | Yes | Adjust position |
| POST | `/api/v1/orders/flatten-all` | Yes | Flatten all positions |
| POST | `/api/v1/orders/emergency-stop` | Yes | Emergency stop |

**Source:** `backend/app/api/v1/orders.py`

### Signals (`/api/v1/signals`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/signals/` | No | List signals (LSTM + TurboScanner + event-driven) |
| POST | `/api/v1/signals/` | Yes | Trigger signal scan |
| GET | `/api/v1/signals/{symbol}/technicals` | No | Technicals for symbol |
| GET | `/api/v1/signals/active/{symbol}` | No | Active signal for symbol |
| GET | `/api/v1/signals/heatmap` | No | Signal heatmap |
| GET | `/api/v1/signals/kelly-ranked` | No | Kelly-ranked signals |

**Source:** `backend/app/api/v1/signals.py`

### Portfolio (`/api/v1/portfolio`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/portfolio` | No | Portfolio positions and P&L |
| GET | `/api/v1/portfolio/sync-status` | No | Position sync status with Alpaca |

**Source:** `backend/app/api/v1/portfolio.py`

### Alpaca proxy (`/api/v1/alpaca`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/alpaca` | No | Alpaca connection status |
| GET | `/api/v1/alpaca/account` | No | Account info |
| GET | `/api/v1/alpaca/positions` | No | Positions |
| GET | `/api/v1/alpaca/orders` | No | Orders |
| GET | `/api/v1/alpaca/activities` | No | Activities |
| GET | `/api/v1/alpaca/clock` | No | Market clock |
| GET | `/api/v1/alpaca/snapshots` | No | Snapshots |
| GET | `/api/v1/alpaca/latest-trades` | No | Latest trades |
| GET | `/api/v1/alpaca/latest-quotes` | No | Latest quotes |
| DELETE | `/api/v1/alpaca/positions/{symbol}` | Yes | Close position by symbol |
| DELETE | `/api/v1/alpaca/positions` | Yes | Close all positions |

**Source:** `backend/app/api/v1/alpaca.py`

### Backtest (`/api/v1/backtest`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/backtest/` | No | Backtest runs overview |
| GET | `/api/v1/backtest/runs` | No | List backtest runs |
| POST | `/api/v1/backtest/` | Yes | Create backtest run |
| POST | `/api/v1/backtest/compare-kelly` | Yes | Compare Kelly strategies |
| GET | `/api/v1/backtest/results` | No | Backtest results |
| GET | `/api/v1/backtest/optimization` | No | Optimization results |
| GET | `/api/v1/backtest/walkforward` | No | Walk-forward results |
| GET | `/api/v1/backtest/montecarlo` | No | Monte Carlo results |
| GET | `/api/v1/backtest/correlation` | No | Correlation analysis |
| GET | `/api/v1/backtest/sector-exposure` | No | Sector exposure |
| GET | `/api/v1/backtest/drawdown-analysis` | No | Drawdown analysis |
| GET | `/api/v1/backtest/rolling-sharpe` | No | Rolling Sharpe |
| GET | `/api/v1/backtest/trade-distribution` | No | Trade distribution |
| GET | `/api/v1/backtest/kelly-comparison` | No | Kelly comparison |
| GET | `/api/v1/backtest/regime` | No | Regime analysis |

**Source:** `backend/app/api/v1/backtest_routes.py`

---

## Council

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/council/evaluate` | Yes | Run 35-agent council on symbol; returns DecisionPacket |
| GET | `/api/v1/council/latest` | No | Most recent council decision |
| GET | `/api/v1/council/status` | No | Council config (35 agents, 7 stages) |
| GET | `/api/v1/council/weights` | No | Current agent weights (Bayesian-updated) |
| POST | `/api/v1/council/weights/reset` | Yes | Reset weights to defaults |
| GET | `/api/v1/council/history` | No | Council decision history |
| GET | `/api/v1/council/decision/{decision_id}` | No | Decision by ID |
| GET | `/api/v1/council/debates` | No | Debate history |
| GET | `/api/v1/council/calibration` | No | Calibration (Brier) stats |

**Request (POST /evaluate):** `{ "symbol": string, "timeframe": "1d", "features": object?, "context": object? }`

On completion (or timeout/error), a compact verdict is broadcast on WebSocket channel **council_verdict**. See `docs/COUNCIL-VERDICT-WEBSOCKET.md` for payload shape and subscription.

**Source:** `backend/app/api/v1/council.py`

---

## Market data

### Quotes (`/api/v1/quotes`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/quotes/` | No | Quotes overview |
| GET | `/api/v1/quotes/{ticker}` | No | Quote for ticker |
| GET | `/api/v1/quotes/{ticker}/candles` | No | Candles (OHLCV) |
| GET | `/api/v1/quotes/{ticker}/book` | No | Order book |
| GET | `/api/v1/quotes/{ticker}/options-chain` | No | Options chain |

**Source:** `backend/app/api/v1/quotes.py`

### Market (`/api/v1/market`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/market/*` | No | Market data, regime, indices (see route file) |

**Source:** `backend/app/api/v1/market.py`

### Stocks (`/api/v1/stocks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/stocks/*` | No | Finviz screener proxy |

**Source:** `backend/app/api/v1/stocks.py`

### Data sources (`/api/v1/data-sources`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/data-sources/` | No | List data sources and health |
| GET | `/api/v1/data-sources/{source_id}` | No | Get source by ID |
| POST | `/api/v1/data-sources/` | Yes | Create data source |
| PUT | `/api/v1/data-sources/{source_id}` | Yes | Update source |
| DELETE | `/api/v1/data-sources/{source_id}` | Yes | Delete source |
| PUT | `/api/v1/data-sources/{source_id}/credentials` | Yes | Update credentials |
| GET | `/api/v1/data-sources/{source_id}/credentials` | No | Get credentials (masked) |
| POST | `/api/v1/data-sources/{source_id}/test` | Yes | Test connection |
| POST | `/api/v1/data-sources/ai-detect` | Yes | AI-detect data source |
| GET | `/api/v1/data-sources/off-hours/status` | No | Off-hours status |
| GET | `/api/v1/data-sources/off-hours/gaps` | No | Data gaps |

**Source:** `backend/app/api/v1/data_sources.py`

### Patterns (`/api/v1/patterns`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/patterns` | No | List patterns |
| POST | `/api/v1/patterns` | Yes | Create pattern |
| DELETE | `/api/v1/patterns/{pattern_id}` | Yes | Delete pattern |
| DELETE | `/api/v1/patterns` | Yes | Delete all patterns |

**Source:** `backend/app/api/v1/patterns.py`

---

## Risk

### Risk (`/api/v1/risk`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/risk` | No | Risk overview |
| GET | `/api/v1/risk/proposal/{symbol}` | No | Risk proposal for symbol |
| GET | `/api/v1/risk/history` | No | Risk history |
| PUT | `/api/v1/risk` | Yes | Update risk config |
| GET | `/api/v1/risk/kelly-sizer` | No | Kelly sizer state |
| POST | `/api/v1/risk/kelly-sizer` | Yes | Update Kelly sizer |
| GET | `/api/v1/risk/position-sizing` | No | Position sizing |
| POST | `/api/v1/risk/position-sizing` | Yes | Update position sizing |
| POST | `/api/v1/risk/drawdown-check` | Yes | Drawdown check |
| POST | `/api/v1/risk/dynamic-stop-loss` | Yes | Dynamic stop loss |
| GET | `/api/v1/risk/risk-score` | No | Risk score |
| GET | `/api/v1/risk/var-analysis` | No | VaR analysis |
| GET | `/api/v1/risk/drawdown-check` | No | Drawdown check (read) |
| GET | `/api/v1/risk/risk-gauges` | No | Risk gauges |
| GET | `/api/v1/risk/circuit-breakers` | No | Circuit breaker status |
| GET | `/api/v1/risk/stress-test` | No | Stress test |
| GET | `/api/v1/risk/monte-carlo` | No | Monte Carlo |
| GET | `/api/v1/risk/position-var` | No | Position VaR |
| GET | `/api/v1/risk/shield` | No | Risk shield status |
| GET | `/api/v1/risk/equity-curve` | No | Equity curve |
| GET | `/api/v1/risk/correlation-matrix` | No | Correlation matrix |
| GET | `/api/v1/risk/var-histogram` | No | VaR histogram |
| GET | `/api/v1/risk/drawdown-episodes` | No | Drawdown episodes |
| POST | `/api/v1/risk/emergency/{action}` | Yes | Emergency action (e.g. flatten) |
| GET | `/api/v1/risk/config` | No | Risk config |
| PUT | `/api/v1/risk/config` | Yes | Update risk config |

**Source:** `backend/app/api/v1/risk.py`

### Risk shield (`/api/v1/risk-shield`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/risk-shield` | No | Risk shield overview (entries frozen, governor status) |
| POST | `/api/v1/risk-shield/*` | Yes | Emergency actions (kill_switch, hedge_all, reduce_50, freeze_entries) |

**Source:** `backend/app/api/v1/risk_shield_api.py`

---

## Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/settings` | No | All settings |
| GET | `/api/v1/settings/categories` | No | Setting categories |
| GET | `/api/v1/settings/audit-log` | No | Settings change log |
| GET | `/api/v1/settings/{category}` | No | Settings by category |
| PUT | `/api/v1/settings` | Yes | Bulk update settings |
| PUT | `/api/v1/settings/{category}` | Yes | Update category |
| POST | `/api/v1/settings/reset/{category}` | Yes | Reset category to defaults |
| POST | `/api/v1/settings/validate` | Yes | Validate API key |
| POST | `/api/v1/settings/test-connection` | Yes | Test data-source connection |
| GET | `/api/v1/settings/export` | No | Export settings as JSON |
| POST | `/api/v1/settings/import` | Yes | Import settings from JSON |

**Source:** `backend/app/api/v1/settings_routes.py`

---

## Additional domains

### Status & system

- **Status** (`/api/v1/status`): GET `/`, GET `/data` — system status. **Source:** `status.py`
- **System** (`/api/v1/system`): GET `/`, `/status`, `/event-bus/status`, `/gpu`, `/rate-limits`, `/circuit-breakers`, `/backfill/status`, `/dlq`, POST `/dlq/replay`, DELETE `/dlq`, `/session-scanner`, `/device`. **Source:** `system.py`
- **Metrics** (no prefix; tags `metrics`): GET `/metrics`, GET `/metrics/prometheus`, GET `/metrics/pipeline`, POST `/metrics/emergency-flatten` (auth), POST `/metrics/ws-circuit-breaker/reset` (auth). **Source:** `metrics_api.py`

### Agents & council UX

- **Agents** (`/api/v1/agents`): Agent Command Center — list agents, start/stop/pause/restart, swarm topology, conference, consensus, teams, drift, alerts, HITL buffer/approve/reject/defer, config, batch ops, attribution, ELO leaderboard, flow anomalies. **Source:** `agents.py`
- **CNS** (`/api/v1/cns`): Homeostasis, circuit breaker, agents health/history/override, blackboard, postmortems, directives, profit-brain, last-verdict. **Source:** `cns.py`
- **Blackboard** (`/api/v1/blackboard`): GET `` (current), GET `/{symbol}`. **Source:** `blackboard_routes.py`
- **Swarm** (`/api/v1/swarm`): Swarm intelligence and scout data. **Source:** `swarm.py`
- **Awareness** (prefix `/api/v1`): POST `/enrich` (auth). **Source:** `awareness.py`

### ML & intelligence

- **Brain** (`/api/v1/brain`): Brain gRPC proxy / LLM. **Source:** `brain.py`
- **ML Brain** (`/api/v1/ml-brain`): Registry, performance, signals/staged, flywheel logs, conference, drift, LSTM predict, status. **Source:** `ml_brain.py`
- **Flywheel** (`/api/v1/flywheel`): Flywheel overview, logs, KPIs, performance, models, features, record (auth), engine, registry, drift, feature-pipeline-status, kelly-feedback (auth), scheduler. **Source:** `flywheel.py`
- **Training** (`/api/v1/training`): Runs, datasets, active progress, start/stop/retrain, config, deploy, models/compare. **Source:** `training.py`
- **Features** (`/api/v1/features`): Feature aggregator endpoints. **Source:** `features.py`
- **LLM Health** (`/api/v1/llm/health`): LLM health monitor. **Source:** `llm_health.py`

### Strategy & performance

- **Strategy** (`/api/v1/strategy`): Regime-based strategies. **Source:** `strategy.py`
- **Performance** (`/api/v1/performance`): Performance analytics. **Source:** `performance.py`
- **Sentiment** (`/api/v1/sentiment`): Sentiment aggregation, summary, history, discover, source-health. **Source:** `sentiment.py`

### Alerts, logs, webhooks

- **Alerts** (`/api/v1/alerts`): Drawdown alerts, system alerts. **Source:** `alerts.py`
- **Logs** (`/api/v1/logs`): System logs (ring buffer). **Source:** `logs.py`
- **Webhooks** (`/api/v1/webhooks`): POST `/tradingview`, POST `/signal`. **Source:** `webhooks.py`

### Other

- **OpenClaw** (`/api/v1/openclaw`): Bridge summary, consensus, signals, scan, regime, top, health, whale-flow, FOM, LLM, sectors, refresh, memory, macro, swarm-status, agents, candidates, spawn-team, nlp-spawn, health-matrix, regime/transitions. **Source:** `openclaw.py`
- **Alignment** (`/api/v1/alignment`): Alignment/consensus. **Source:** `alignment.py`
- **Cognitive** (`/api/v1/cognitive`): Cognitive dashboard. **Source:** `cognitive.py`
- **Cluster** (`/api/v1/cluster`): Dual-PC cluster. **Source:** `cluster.py`
- **Triage** (`/api/v1/triage`): Idea triage. **Source:** `triage.py`
- **Mobile** (`/api/v1/mobile`): Mobile API. **Source:** `mobile_api.py`
- **YouTube** (`/api/v1/youtube-knowledge`): YouTube research. **Source:** `youtube_knowledge.py`
- **Ingestion firehose** (no prefix): GET `/status`, GET `/metrics`. **Source:** `ingestion_firehose.py`

---

## Auth summary

- **Required (Bearer token):** All order submission/cancel, council evaluate, weights reset, settings write, risk config write, emergency flatten, data source write/test, backtest create, pattern write, agent control (start/stop/HITL), flywheel record, training control, and similar mutating or sensitive operations.
- **Optional / no auth:** Health, status, council latest/status/weights/history, signals read, portfolio read, market data, risk read, settings read, metrics read, and most GETs.

Use header: `Authorization: Bearer <API_AUTH_TOKEN>`. Token from `backend/.env` (`API_AUTH_TOKEN`).

---

## OpenAPI (Swagger)

Interactive docs: **http://localhost:8000/docs** (Swagger UI). ReDoc: **http://localhost:8000/redoc**.
