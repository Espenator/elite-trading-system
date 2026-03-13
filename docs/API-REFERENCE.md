# API Reference — Embodier Trader v5.0.0

All REST endpoints live under `/api/v1/`. Base URL: `http://localhost:8000` (or your backend host).  
**Auth**: Live trading and mutation endpoints require `Authorization: Bearer <API_AUTH_TOKEN>` (fail-closed).  
**Docs**: Interactive Swagger at `http://localhost:8000/docs`.

---

## 1. Trading

### Orders — `/api/v1/orders`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | Yes | List open orders (Alpaca) |
| GET | `/recent` | Yes | Recent orders from local DB |
| POST | `/advanced` | Yes | Create order (bracket/OCO/OTO/trailing/notional). Body: `AdvancedOrderRequest` (symbol, side, type, qty/notional, limit_price, stop_loss, take_profit, etc.) |
| PATCH | `/{order_id}` | Yes | Replace/amend open order |
| DELETE | `/{order_id}` | Yes | Cancel single order |
| DELETE | `/` | Yes | Cancel all open orders |
| POST | `/close` | Yes | Close position (symbol in body) |
| POST | `/adjust` | Yes | Adjust order (e.g. trailing stop) |
| POST | `/flatten-all` | Yes | Emergency flatten all positions |
| POST | `/emergency-stop` | Yes | Emergency stop trading |

**Request (POST /advanced)**: `{ "symbol": "AAPL", "side": "buy", "type": "market", "qty": "10", "time_in_force": "day", "take_profit": {...}, "stop_loss": {...} }`  
**Response**: Alpaca order object or local order record.

### Alpaca — `/api/v1/alpaca`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Alpaca connection status |
| GET | `/account` | No | Account info |
| GET | `/positions` | No | Current positions |
| GET | `/orders` | No | Orders from Alpaca |
| GET | `/activities` | No | Account activities |
| GET | `/clock` | No | Market clock |
| GET | `/snapshots` | No | Snapshots (symbols query) |
| GET | `/latest-trades` | No | Latest trades |
| GET | `/latest-quotes` | No | Latest quotes |
| DELETE | `/positions/{symbol}` | Yes | Close single position |
| DELETE | `/positions` | Yes | Close all positions |

### Signals — `/api/v1/signals`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | List/cursor signals (query params) |
| GET | `/heatmap` | No | Signals heatmap data |
| GET | `/kelly-ranked` | No | Kelly-ranked signals |

### Portfolio — `/api/v1/portfolio`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Portfolio summary, positions, P&L |
| GET | `/positions` | No | Positions list |
| GET | `/sync-status` | No | Position manager sync status with Alpaca |

---

## 2. Council

### Council — `/api/v1/council`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/evaluate` | Yes | Run 35-agent council on a symbol. Body: `{ "symbol": "AAPL", "timeframe": "1d", "features": null, "context": {} }`. Returns `DecisionPacket` (votes, final_direction, final_confidence, vetoed, etc.) |
| GET | `/latest` | No | Most recent council decision (cached) |
| GET | `/status` | No | Council config (35 agents, 7 stages) |
| GET | `/weights` | No | Current agent weights (Bayesian-updated) |
| POST | `/weights/reset` | Yes | Reset weights to defaults |

**Response (evaluate/latest)**: `{ "symbol", "final_direction", "final_confidence", "execution_ready", "vetoed", "votes": [ AgentVote... ], "council_reasoning", "cognitive_meta", ... }`

### Brain — `/api/v1/brain`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/infer` | No | gRPC proxy to brain_service (Ollama) |
| GET | `/health` | No | Brain service health |

### Blackboard — `/api/v1/blackboard`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/current` | No | Current blackboard state (shared council context) |

### CNS — `/api/v1/cns`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/blackboard/current` | No | Blackboard state (alias) |
| GET | `/status` | No | CNS architecture status |

### Swarm — `/api/v1/swarm`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ideas` | No | Scout/swarm ideas from MessageBus |
| GET | `/topology` | No | Swarm topology |

### Triage — `/api/v1/triage`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/status` | No | Idea triage service status |

---

## 3. Market data

### Market — `/api/v1/market`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Market summary |
| GET | `/indices` | No | Index data |
| GET | `/order-book` | No | Order book data |
| GET | `/regime` | No | Current regime (OpenClaw/bayesian) |

### Quotes — `/api/v1/quotes`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Quotes list (symbols query) |
| GET | `/{ticker}` | No | Single ticker quote |
| GET | `/{ticker}/candles` | No | OHLCV candles |
| GET | `/{ticker}/book` | No | Order book for ticker |
| GET | `/{ticker}/options-chain` | No | Options chain |

### Stocks — `/api/v1/stocks`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Finviz screener / stock list |

### Data sources — `/api/v1/data-sources`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Data source health (Alpaca, Finviz, FRED, etc.) |

---

## 4. Risk

### Risk — `/api/v1/risk`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Risk overview |
| GET | `/risk-score` | No | Current risk score |
| GET | `/kelly-sizer` | No | Kelly sizer params/results |
| POST | `/kelly-sizer` | Yes | Run Kelly sizer |
| GET | `/position-sizing` | No | Position sizing info |
| POST | `/position-sizing` | Yes | Compute position size |
| GET | `/drawdown-check` | No | Drawdown check status |
| POST | `/drawdown-check` | Yes | Run drawdown check |
| POST | `/dynamic-stop-loss` | Yes | Dynamic stop loss |
| GET | `/risk-gauges` | No | Risk gauges (heat, exposure) |
| GET | `/circuit-breakers` | No | Circuit breaker status |
| GET | `/config` | No | Risk config |
| PUT | `/config` | Yes | Update risk config |
| GET | `/proposal/{symbol}` | No | Risk proposal for symbol |
| GET | `/var-analysis` | No | VaR analysis |
| GET | `/stress-test` | No | Stress test results |
| GET | `/monte-carlo` | No | Monte Carlo simulation |
| POST | `/emergency/{action}` | Yes | Emergency action (e.g. flatten) |

### Risk shield — `/api/v1/risk-shield`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | No | RiskShield overview (governor_available, entries_frozen) |
| GET | `/status` | No | Full status (9 safety checks) |
| POST | `/emergency` | Yes | Emergency action (kill_switch, hedge_all, reduce_50, freeze_entries). Body: `{ "action": "freeze_entries", "value": true }` |

---

## 5. Settings & system

### Settings — `/api/v1/settings`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | All settings |
| GET | `/{key}` | No | Single setting |
| PUT | `/{key}` | Yes | Update setting |

### Status — `/api/v1/status`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | System status (event bus, pipeline, council) |

### System — `/api/v1/system`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | System config |
| GET | `/event-bus/status` | No | MessageBus status |
| GET | `/gpu` | No | GPU telemetry (if available) |

### Logs — `/api/v1/logs`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Recent logs (ring buffer) |

### Alerts — `/api/v1/alerts`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Active alerts (drawdown, system) |

### Agents (ACC) — `/api/v1/agents`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Agent Command Center status (5 template agents) |
| POST | `/{agent_id}/start` | Yes | Start agent |
| POST | `/{agent_id}/stop` | Yes | Stop agent |
| GET | `/swarm-topology` | No | Swarm topology |
| GET | `/consensus` | No | Agent consensus |
| GET | `/conference` | No | Conference view |
| GET | `/teams` | No | Teams view |
| GET | `/drift` | No | Drift metrics |
| GET | `/alerts` | No | Agent alerts |
| GET | `/resources` | No | Agent resources |

---

## 6. Health & metrics

### Health — `/health` (mounted at app root when available)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Unified health (DuckDB, Alpaca, services) |
| GET | `/healthz` | No | Liveness/readiness (used by k8s/Docker) |

### Metrics — `/api/v1` (metrics_api, no prefix)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/metrics` | No | Prometheus-style or JSON metrics (council latency, queue depth, weight learner stats) |

### LLM health — `/api/v1/llm/health`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | LLM health (Ollama, Perplexity, Claude) |

---

## 7. Other domains

### Strategy — `/api/v1/strategy`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Strategy list / status |
| GET | `/regime-params` | No | Regime parameters |
| GET | `/pre-trade-check/{ticker}` | No | Pre-trade check for symbol |

### Performance — `/api/v1/performance`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Performance summary |
| GET | `/equity` | No | Equity curve |
| GET | `/trades` | No | Trade history |

### Backtest — `/api/v1/backtest`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Backtest runs list |
| GET | `/runs` | No | Backtest runs |
| POST | `/` | Yes | Run backtest |
| GET | `/results` | No | Backtest results |
| GET | `/optimization` | No | Optimization results |
| GET | `/walkforward` | No | Walk-forward results |
| GET | `/montecarlo` | No | Monte Carlo backtest |
| POST | `/compare-kelly` | Yes | Compare Kelly strategies |

### Features — `/api/v1/features`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/{symbol}` | No | Aggregated feature vector for symbol |
| GET | `/` | No | Feature summary |

### Patterns — `/api/v1/patterns`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Pattern/screener data (DB-backed) |

### Sentiment — `/api/v1/sentiment`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | No | Sentiment summary |
| GET | `/summary` | No | Sentiment summary |
| GET | `/history` | No | Sentiment history |
| POST | `` | Yes | Ingest sentiment |
| POST | `/discover` | Yes | Discover sentiment sources |

### ML brain — `/api/v1/ml-brain`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | ML brain status |
| GET | `/performance` | No | ML performance |
| GET | `/signals/staged` | No | Staged signals |
| GET | `/flywheel-logs` | No | Flywheel logs |
| POST | `/conference/{symbol}` | Yes | Run conference for symbol |
| GET | `/registry/status` | No | Model registry status |
| GET | `/drift/status` | No | Drift detector status |
| GET | `/lstm/predict/{symbol}` | No | LSTM prediction |
| GET | `/status` | No | Status |

### Flywheel — `/api/v1/flywheel`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Flywheel metrics |

### Training — `/api/v1/training`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/` | Yes | Trigger training job |
| GET | `/status` | No | Training status |

### OpenClaw — `/api/v1/openclaw`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/regime` | No | Regime from OpenClaw |
| GET | `/swarm-status` | No | Swarm status |
| GET | `/candidates` | No | Candidate symbols |
| GET | `/health` | No | OpenClaw health |

### Alignment — `/api/v1/alignment`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Alignment/consensus state |
| POST | `/verdict` | Yes | Submit verdict (audit) |

### Awareness — `/api/v1`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/awareness/...` | No | Awareness endpoints (varies by module) |

### Cognitive — `/api/v1/cognitive`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Cognitive dashboard (memory, heuristics) |

### Cluster — `/api/v1/cluster`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Cluster / node status (dual-PC) |

### YouTube knowledge — `/api/v1/youtube-knowledge`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | YouTube research extraction |

### Ingestion — `/ingestion` (no /api/v1 prefix; see main.py)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/...` | No | Ingestion endpoints (firehose) |

### Ingestion firehose — (mounted by ingestion_firehose.router)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/ingestion/...` | No | Real-time ingestion (varies) |

### Webhooks — `/api/v1/webhooks`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/tradingview` | No | TradingView webhook |
| POST | `/slack` | No | Slack webhook |

### Mobile — `/api/v1/mobile`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Mobile API entry |

---

## Auth

- **Header**: `Authorization: Bearer <API_AUTH_TOKEN>`  
- **Env**: `API_AUTH_TOKEN` in `backend/.env`.  
- **Live trading**: All order/position mutations and council evaluate require auth (fail-closed).  
- **WebSocket**: Pass token as query param `?token=<API_AUTH_TOKEN>`.

---

## Response schemas (representative)

- **DecisionPacket** (council): `symbol`, `final_direction` (buy/sell/hold), `final_confidence` (0–1), `execution_ready`, `vetoed`, `votes` (list of AgentVote), `council_reasoning`, `cognitive_meta`, `timestamp`.
- **AgentVote**: `agent_name`, `direction`, `confidence`, `reasoning`, `veto`, `veto_reason`, `weight`, `metadata`.
- **Order**: Alpaca v2 order shape: `id`, `symbol`, `side`, `qty`, `type`, `status`, `filled_avg_price`, `created_at`, etc.

For full request/response shapes, use **Swagger** at `http://localhost:8000/docs`.
