# CLAUDE.md — Embodier Trader Backend
# Python 3.11 + FastAPI + uvicorn + DuckDB + pydantic-settings
# Last updated: March 12, 2026 — v4.1.0-dev

## Stack

- **Runtime**: Python 3.11+, FastAPI, uvicorn
- **Database**: DuckDB (WAL mode, connection pooling, thread-safe async lock)
- **Config**: pydantic-settings (`core/config.py`)
- **Auth**: Bearer token (`API_AUTH_TOKEN`), fail-closed for live trading
- **Events**: MessageBus pub/sub (`core/message_bus.py`)

## API Route Files (43 in api/v1/)

| File | Purpose |
|------|---------|
| agents.py | Agent Command Center (5 template agents) |
| alerts.py | Drawdown alerts, system alerts |
| alignment.py | Alignment/consensus endpoints |
| alpaca.py | Alpaca API proxy for frontend |
| awareness.py | System awareness endpoints |
| backtest_routes.py | Strategy backtesting |
| blackboard_routes.py | Blackboard shared state |
| brain.py | Brain gRPC proxy / LLM endpoints |
| cluster.py | Dual-PC cluster management |
| cns.py | CNS architecture endpoints |
| cognitive.py | Cognitive dashboard (memory, heuristics) |
| council.py | Council evaluate, status, weights |
| data_sources.py | Data source health monitoring |
| features.py | Feature aggregator endpoints |
| flywheel.py | ML flywheel metrics |
| health.py | Health check endpoints |
| ingestion_firehose.py | Real-time data ingestion |
| llm_health.py | LLM health monitor |
| logs.py | System logs (real ring buffer) |
| market.py | Market data, regime, indices |
| metrics_api.py | System metrics |
| ml_brain.py | ML model management |
| mobile_api.py | Mobile API endpoints |
| openclaw.py | OpenClaw bridge |
| orders.py | Alpaca order CRUD |
| patterns.py | Pattern/screener (DB-backed) |
| performance.py | Performance analytics |
| portfolio.py | Portfolio positions, P&L |
| quotes.py | Price/chart data |
| risk.py | Risk metrics, Monte Carlo |
| risk_shield_api.py | Emergency controls |
| sentiment.py | Sentiment aggregation |
| settings_routes.py | Settings CRUD |
| signals.py | Trading signals |
| status.py | System health status |
| stocks.py | Finviz screener proxy |
| strategy.py | Regime-based strategies |
| swarm.py | Swarm intelligence / scout data |
| system.py | System config, GPU telemetry |
| training.py | ML training jobs |
| triage.py | Idea triage / prioritization |
| webhooks.py | TradingView + Slack webhooks |
| youtube_knowledge.py | YouTube research extraction |

## Service Directory (72+ modules)

### Top-Level Services (key files)

| Service | Purpose |
|---------|---------|
| signal_engine.py | EventDrivenSignalEngine — core signal generation |
| order_executor.py | Trade execution with Gate 2b/2c enforcement |
| alpaca_service.py | Broker integration (2 accounts) |
| alpaca_stream_service.py | 24/7 WebSocket + snapshot fallback |
| kelly_position_sizer.py | Position sizing (half-Kelly + vol targeting) |
| data_ingestion.py | Auto-backfill with daily_ohlcv verification |
| ml_training.py | XGBoost + LightGBM + walk-forward |
| llm_router.py | 3-tier LLM dispatch |
| brain_client.py | gRPC client to brain_service (PC2) |
| position_manager.py | Position tracking + trailing stops |
| unusual_whales_service.py | Options flow, dark pool, congressional |
| finviz_service.py | Screener, fundamentals |
| fred_service.py | Macro indicators, yield curves |
| sec_edgar_service.py | Insider transactions, 13F filings |
| slack_alerter.py | Slack notifications |
| health_registry.py | Service health monitoring |

### Service Subdirectories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `scouts/` | 12 scouts + base + registry | Continuous discovery (flow, gamma, insider, macro, news, etc.) |
| `llm_clients/` | ollama, perplexity, claude | LLM provider clients |
| `channel_agents/` | 6 agents + orchestrator + router | Channel-specific data agents |
| `firehose_agents/` | 4 agents + orchestrator | Real-time data ingest |
| `integrations/` | 6 adapters + registry | Data source adapters |
| `intelligence/` | cache + orchestrator | Intelligence layer |

## Council Directory (15 orchestration + 32 agent files)

See `backend/app/council/CLAUDE.md` for full details.

Key files: `runner.py` (DAG orchestrator), `arbiter.py` (weighted verdict), `schemas.py` (AgentVote), `council_gate.py` (signal bridge), `weight_learner.py` (Bayesian learning).

## Agent Registration Pattern

```python
# Every agent file in council/agents/ follows this pattern:
NAME = "my_agent"
WEIGHT = 0.8

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    f = features.get("features", features)
    # ... analysis logic ...
    return AgentVote(
        agent_name=NAME,
        direction="buy",      # "buy" | "sell" | "hold"
        confidence=0.75,       # 0.0 – 1.0
        reasoning="...",
        veto=False,            # Only risk + execution can set True
        veto_reason="",
        weight=WEIGHT,
        metadata={}
    )
```

## DuckDB Connection Pattern

```python
# ALWAYS use connection pooling — never raw connections
from app.data.storage import get_conn

conn = get_conn()
result = conn.execute("SELECT * FROM signals WHERE score > ?", [70]).fetchall()

# Thread-safe async lock (double-checked locking) — Phase A6 fix
# Never open raw DuckDB connections elsewhere
```

## MessageBus Pattern

```python
from app.core.message_bus import MessageBus

bus = MessageBus.get_instance()

# Publish
bus.publish("signal.generated", {"symbol": "AAPL", "score": 78})

# Subscribe
bus.subscribe("council.verdict", my_handler)

# Core topics: market_data.bar, signal.generated, council.verdict,
# order.submitted, order.filled, order.cancelled, model.updated,
# risk.alert, system.heartbeat, swarm.idea
```

## Background Jobs

| Job | Location | Schedule |
|-----|----------|----------|
| scheduler.py | `jobs/scheduler.py` | Orchestrates all background jobs |
| daily_outcome_update | `jobs/daily_outcome_update.py` | Daily: trade outcome → WeightLearner |
| champion_challenger_eval | `jobs/champion_challenger_eval.py` | Periodic: model comparison |
| weekly_walkforward_train | `jobs/weekly_walkforward_train.py` | Weekly: ML model retraining |
| _supervised_loop() | `main.py` | Wrapper: crash recovery (3 retries + Slack) |

## Authentication

- **Bearer token**: `API_AUTH_TOKEN` env var
- **Fail-closed**: Live trading endpoints require valid token
- **WebSocket**: `?token=<API_AUTH_TOKEN>` query param
- **CORS**: localhost:5173, 3000, 8501, 3002

## Event Pipeline

```
AlpacaStreamService → market_data.bar (MessageBus)
  → EventDrivenSignalEngine → signal.generated (score >= 65)
  → CouncilGate → run_council() (35 agents, 7 stages)
  → council.verdict (BUY/SELL/HOLD + confidence)
  → OrderExecutor (Gate 2b regime → Gate 2c breakers → Alpaca bracket order)
  → order.submitted → WebSocket bridges → Frontend
```

## Testing

```bash
cd backend
python -m pytest --tb=short -q          # All 666+ tests
python -m pytest tests/test_api.py -v   # Specific file
python -m pytest -k "test_signals"      # By name pattern
```

- **conftest.py** monkey-patches DuckDB → in-memory (test isolation)
- **CI**: GitHub Actions runs pytest + frontend build

## Environment Variables

All in `backend/.env` (gitignored). See `backend/.env.example` for full template.

**Required**: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`
**Recommended**: `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`
**Optional**: All others degrade gracefully

## Startup

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# 6-phase lifespan startup: DB init → service singletons → ML models →
# background loops → event pipeline → WebSocket bridges
```

## Rules

1. **4-space Python indentation** — never tabs
2. **DuckDB via `get_conn()` only** — never raw connections
3. **MessageBus for events** — no direct service-to-service calls for event data
4. **Bearer auth on live endpoints** — fail-closed
5. **AgentVote schema required** — all agents must return it
6. **No yfinance** — use Alpaca/FinViz/UW
7. **No mock data** — all endpoints return real data
8. **Run tests before/after changes** — maintain 666+ GREEN
