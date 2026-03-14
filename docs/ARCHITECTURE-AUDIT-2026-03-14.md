# Embodier Trader v5.0.0 — Architecture Audit Report

**Date:** March 14, 2026  
**Scope:** backend/, frontend-v2/, brain_service/, council/, services/  
**Focus:** Execution paths, architecture layers, dependencies, data flow, anti-patterns

---

## 1. Main Trade Pipeline — Execution Path Map

### 1.1 Primary Path (Event-Driven, <1s Latency)

```
AlpacaStreamService (alpaca_stream_service.py:286,423)
  │ publishes market_data.bar
  ▼
MessageBus (core/message_bus.py)
  │ topic: market_data.bar
  ├─► EventDrivenSignalEngine (signal_engine.py:541) — _on_new_bar()
  │     • Rolling bar history per symbol (max 50 bars)
  │     • _compute_composite_score() + _compute_short_composite_score()
  │     • OpenClaw 5-pillar blend (if available)
  │     • ML XGBoost blend (if ml_scorer loaded)
  │     • Regime-adaptive threshold (SIGNAL_THRESHOLD=65, overridden by regime)
  │     publishes signal.generated (score >= threshold)
  │
  ├─► DuckDB bar persistence (main.py:485-534) — batched every 5s
  ├─► WebSocket "market" channel bridge (main.py:541-550)
  └─► (other subscribers)
  │
  ▼ signal.generated
  │
CouncilGate (council_gate.py:183) — _on_signal()
  │ Gates: mock guard, regime-adaptive threshold, per-symbol+direction cooldown, concurrency
  │ _evaluate_with_council() → run_council()
  ▼
Council Runner (council/runner.py:326)
  │ BlackboardState created, sensory_store merged into features
  │ Stages 1→2→3→4→5→5.5→6→7 (35 agents)
  │ arbiter() → DecisionPacket
  ▼
CouncilGate publishes council.verdict
  │
  ▼
OrderExecutor (order_executor.py:208) — _on_council_verdict()
  │ Gates 0-9: TTL 30s, council approval, mock guard, regime, circuit breaker,
  │   drawdown, degraded, kill switch, daily limit, cooldown, Kelly sizing,
  │   portfolio heat, viability, risk governor
  │ KellyPositionSizer, TradeStatsService, AlpacaService
  ▼
order.submitted → Alpaca API
  │
  ├─► WebSocket bridges (signal, order, council)
  ├─► Slack notification bridges
  └─► OutcomeTracker (position.closed → outcome.resolved → WeightLearner)
```

### 1.2 Alternate Signal Sources (Parallel to Alpaca Bars)

| Source | Publisher | Topic | Consumer |
|--------|-----------|-------|----------|
| DiscoverySignalBridge | triage.escalated | signal.generated | CouncilGate |
| TurboScanner | turbo_scanner.py:845 | signal.generated | CouncilGate |
| MarketWideSweep | market_wide_sweep.py:638 | signal.generated | CouncilGate |
| NewsAggregator | news_aggregator.py:513 | signal.generated | CouncilGate |
| MLSignalPublisher | ml_signal_publisher.py:123 | signal.generated | CouncilGate |

### 1.3 Council Bypass Path (COUNCIL_GATE_ENABLED=false)

When council is disabled, `main.py:426-454` registers `_signal_to_verdict_fallback` which converts `signal.generated` directly to `council.verdict` format (score >= 65). OrderExecutor receives verdicts without council evaluation.

---

## 2. Architecture Layers and Interactions

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION                                                                 │
│  FastAPI (main.py) • 43 route files • WebSocket (25 channels) • React SPA   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVENT BUS (MessageBus)                                                        │
│  core/message_bus.py — async pub/sub, Redis bridge, DLQ, rate limits        │
│  ~54 VALID_TOPICS, 22 REDIS_BRIDGED_TOPICS                                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ SENSORY      │    │ COUNCIL      │    │ EXECUTION    │    │ FEEDBACK     │
│ • Alpaca WS  │    │ • 35-agent   │    │ • OrderExec  │    │ • Outcome    │
│ • UW, Finviz │    │   DAG        │    │ • Kelly      │    │   Tracker    │
│ • FRED, EDGAR│    │ • Blackboard │    │ • Alpaca API │    │ • Weight     │
│ • SqueezeM   │    │ • Arbiter    │    │ • Position   │    │   Learner    │
└──────────────┘    └──────────────┘    │   Manager    │    └──────────────┘
         │                    │         └──────────────┘             │
         ▼                    ▼                    │                 │
┌─────────────────────────────────────────────────────────────────────────────┐
│ SENSORY STORE (core/sensory_store.py)                                        │
│  Last-value cache for perception.*, macro.fred — merged into council features│
│  Updated by main.py lifespan subscribers (12 topics)                         │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                                   │
│  DuckDB (analytics.duckdb) — OHLCV, indicators, features, outcomes         │
│  SQLite (trading_orders.db) — orders, config, db_service                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 MessageBus ↔ Blackboard Flow

- **Blackboard** (`council/blackboard.py`): Per-council-run shared state. Created in `run_council()`, passed to all 35 agents. Holds perceptions, hypothesis, strategy, risk_assessment, execution_plan, debate, etc.
- **Sensory Store** (`core/sensory_store.py`): Global last-value cache. Main.py subscribes to 12+ perception/macro topics and calls `sensory_update(topic, payload)`. Council runner merges `get_snapshot()` into `features["features"]["sensory"]` before creating BlackboardState.
- **Data flow**: Data sources (UW, Finviz, FRED, SEC EDGAR, SqueezeMetrics, Benzinga, Capitol Trades) publish to perception.* / macro.fred → sensory store → council features → agents read via `features.get("features",{}).get("sensory",{})`.

### 2.3 Council Stage Dependencies

| Stage | Agents | Depends On |
|-------|--------|------------|
| 1 | 13 (perception + academic edge) | raw_features, sensory |
| 2 | 8 (technical + enrichment) | S1 perceptions |
| 3 | 2 (hypothesis, memory) | S1+S2 |
| 4 | 1 (strategy) | S1-S3 |
| 5 | 3 (risk, execution, portfolio) | S1-S4 |
| 5.5 | 3 (debate) | S1-S5 |
| 6 | 1 (critic) | S1-S5.5 |
| 7 | Arbiter | All votes |

---

## 3. Circular Dependencies, Dead Code, Orphaned Modules

### 3.1 Circular Dependencies

**No hard circular import cycles detected** in the sampled import graph. The codebase uses lazy imports and dependency injection (e.g., `message_bus` passed into constructors) to avoid cycles. Notable patterns:

- `order_executor.py` imports `ExecutionDecision` from `execution_decision`; `execution_decision` does not import order_executor.
- `council/runner.py` imports `BlackboardState`, `TaskSpawner`, `arbitrate` — all council-internal; no back-references from council to services for core flow.
- `main.py` is the central orchestrator; it imports routers and services but defers many imports to lifespan/startup.

**Potential tension:** `order_executor.py` imports `REGIME_PARAMS` from `app.api.v1.strategy` (line 320) — business logic in API layer. Consider moving `REGIME_PARAMS` to `core/config` or `council/` to avoid API→service coupling.

### 3.2 Dead / Orphaned Code

| Item | Location | Status |
|------|----------|--------|
| **OpenClaw module** | `modules/openclaw/` | **Partially orphaned.** 6 files (risk_governor, hmm_regime, trading_conference). Used by: openclaw_bridge_service, signal_engine (_get_openclaw_context), ingestion adapters, strategy, risk_shield_api. Regime detection defaults to RED when OpenClaw offline. |
| **Agent Command Center (5 agents)** | `api/v1/agents.py` | **Legacy.** project_state.md: "NOT real agents. No daemon lifecycle." Market Data Agent tick still runs via main.py `_market_data_tick_loop` for symbols not on WebSocket. |
| **blackboard_service.py** | `services/blackboard_service.py` | Uses `bb.publish(Topic.ML_PREDICTIONS)` — different blackboard (Rx-style) than council BlackboardState. Verify if still used. |
| **duckdb_service** | Referenced by layered_memory_agent | `query_recent_trades`, `query_sector_patterns`, etc. — ensure `duckdb_service` exists (grep found `duckdb_storage`, not `duckdb_service`). |
| **database.py / db_service** | `services/database.py` | **Heavy coupling.** 30+ modules use `db_service.get_config`/`set_config` for SQLite-backed key-value store. Single point of failure; consider splitting by domain. |

### 3.3 Orphaned / Low-Wiring Topics

MessageBus audit (message_bus.py:52-80) documents **PUBLISH_ONLY** topics with no subscribers. As of main.py lifespan wiring (lines 1643-1682), these are now subscribed:

- `hitl.approval_needed` → WebSocket + alert.health
- `position.closed` → feedback_loop.record_outcome
- `position.partial_exit` → sensory store
- `symbol.prep.ready` → sensory store
- `alert.health` → sensory + WebSocket

**Still potentially orphaned:** `signal.unified`, `scout.heartbeat`, `triage.dropped`, `swarm.spawned`, `knowledge.ingested` — publishers exist; confirm subscribers in main.py or elsewhere.

---

## 4. Data Flow: Sources → Order Execution

### 4.1 Data Source → MessageBus Mapping

| Source | Service | Topics Published | Consumer |
|--------|---------|------------------|----------|
| Alpaca | AlpacaStreamService | market_data.bar | EventDrivenSignalEngine, DuckDB persist, WebSocket |
| Unusual Whales | unusual_whales_service | perception.unusualwhales, unusual_whales.flow, .congress, .insider, .darkpool, perception.gex | Sensory store, ChannelsOrchestrator |
| Finviz | finviz_service | perception.finviz.screener | Sensory store |
| FRED | fred_service | macro.fred | Sensory store |
| SEC EDGAR | sec_edgar_service, market_data_agent | perception.insider, perception.edgar | Sensory store |
| SqueezeMetrics | squeezemetrics_service | perception.squeezemetrics | Sensory store |
| Benzinga | benzinga_service | perception.earnings | Sensory store |
| Capitol Trades | capitol_trades_service | perception.congressional | Sensory store |
| Data Swarm | data_swarm collectors | data.price.*, data.flow.*, data.futures, etc. | Optional; DATA_SWARM_ENABLED |

### 4.2 Perception → Council Path

1. Data source fetches data (polling, WebSocket, or scheduled).
2. Service publishes to `perception.<source>` or `macro.fred`.
3. Main.py lifespan handler calls `sensory_update(topic, payload)`.
4. Council runner calls `get_snapshot()` and merges into `features["features"]["sensory"]`.
5. Agents read via `features.get("features",{}).get("sensory",{}).get("perception.xyz",{})`.

**Gap:** Data swarm collectors publish to `data.*` topics (e.g., `data.price.finviz`, `data.flow.options`). These are **not** the same as `perception.*`. Verify if any agent or feature_aggregator consumes `data.*` or if they are display-only.

### 4.3 Feature Aggregator

`features/feature_aggregator.py` — `aggregate(symbol, timeframe)` pulls from DuckDB (OHLCV, indicators), computes price/volume/volatility/regime/flow/indicator/intermarket/cycle features. Used when council is invoked without pre-computed features (runner.py:356). Does **not** directly read sensory store; sensory is merged in runner after aggregate.

---

## 5. Architectural Inconsistencies and Anti-Patterns

### 5.1 High Impact

| Issue | Location | Description |
|-------|----------|-------------|
| **Regime params in API layer** | order_executor.py:320, api/v1/strategy.py | `REGIME_PARAMS` lives in strategy API route. OrderExecutor (service) imports from API. Inverts dependency direction. |
| **Dual storage systems** | DuckDB + SQLite + db_service | DuckDB for analytics, SQLite for orders/config. `db_service` (database.py) is a catch-all key-value store. Unclear ownership; risk of schema drift. |
| **layered_memory_agent → duckdb_service** | council/agents/layered_memory_agent.py:131 | Imports `query_recent_trades` from `app.services.duckdb_service`. Module does not exist. Agent has try/except fallback to in-memory store — no crash, but DuckDB path is dead code. |
| **EventDrivenSignalEngine regime** | signal_engine.py:567 | Uses `SIGNAL_THRESHOLD = 65` as class constant. CouncilGate has regime-adaptive thresholds. Signal engine uses `self.SIGNAL_THRESHOLD` for both long and short; regime-adaptive logic is in CouncilGate, not here. Inconsistent. |
| **OpenClaw default RED** | signal_engine.py:379 | When OpenClaw unavailable, regime defaults to RED. Conservative but may over-restrict. Document and consider configurable fallback. |

### 5.2 Medium Impact

| Issue | Location | Description |
|-------|----------|-------------|
| **Multiple signal publishers** | 5+ services | signal.generated has many publishers (EventDrivenSignalEngine, DiscoverySignalBridge, TurboScanner, MarketWideSweep, NewsAggregator, MLSignalPublisher). No deduplication by symbol+score+timestamp. Risk of duplicate council invocations. |
| **Sensory store threading** | sensory_store.py | Uses `threading.Lock`. Async code calls `get_snapshot()` from council runner. Generally safe but consider asyncio.Lock if all callers are async. |
| **main.py size** | main.py | ~1700 lines. Lifespan does too much: pipeline startup, bridges, deferred services, sensory wiring, health. Consider extracting `EventPipelineBootstrap` or similar. |
| **Council timeout** | council_gate.py:318 | `COUNCIL_GLOBAL_TIMEOUT=90` — long. Individual agents have 30s. Document and consider tiered timeouts. |

### 5.3 Low Impact

| Issue | Location | Description |
|-------|----------|-------------|
| **ProcessPoolExecutor for agents** | runner.py:49 | `_COUNCIL_PROCESS_POOL` uses `spawn` context. Agent modules must be picklable. Some agents may not be. |
| **Hardcoded default symbols** | main.py:548 | `["AAPL","MSFT",...]` when `get_tracked_symbols()` fails. Consider config. |
| **outcome.resolved subscriber** | main.py:801 | `_on_outcome_resolved` is `pass` — placeholder. OutcomeTracker updates WeightLearner directly. Redundant subscriber. |

---

## 6. Findings Prioritized by Impact

### P0 — Critical (Fix Immediately)

1. **layered_memory_agent imports non-existent duckdb_service** — Module does not exist. Agent catches ImportError and falls back to in-memory store; DuckDB memory layer never used. Create `duckdb_service` with query helpers or wire to `duckdb_storage`.
2. **OrderExecutor imports REGIME_PARAMS from API** — Breaks layering. Move to `core/config` or `council/regime/`.

### P1 — High (Next Sprint)

3. **Multiple signal.generated publishers, no dedup** — Add idempotency key (symbol, direction, score_bucket, window) to avoid duplicate council runs.
4. **main.py monolithic lifespan** — Extract pipeline bootstrap into `app/bootstrap/` or `app/core/event_pipeline.py`.
5. **db_service as god object** — 30+ modules depend on it. Plan to split by domain (risk_config, agent_status, etc.).

### P2 — Medium (Backlog)

6. **OpenClaw module status** — Document clearly: required vs optional. Consider extracting only regime + risk_governor if rest is dead.
7. **Data swarm data.* topics** — Confirm consumers. If none, document as future-use or remove.
8. **EventDrivenSignalEngine threshold** — Align with CouncilGate regime-adaptive thresholds or document why they differ.

### P3 — Low (Tech Debt)

9. **Agent Command Center** — Decide: retire or refactor to real agent lifecycle.
10. **blackboard_service vs BlackboardState** — Two different "blackboard" concepts. Rename or document to avoid confusion.
11. **outcome.resolved empty subscriber** — Remove or add real side effects.

---

## 7. Essential Files for Understanding

| Topic | Files |
|-------|-------|
| Trade pipeline | `main.py` (lifespan), `signal_engine.py`, `council_gate.py`, `council/runner.py`, `order_executor.py` |
| MessageBus | `core/message_bus.py` |
| Council | `council/runner.py`, `council/arbiter.py`, `council/schemas.py`, `council/blackboard.py` |
| Data flow | `core/sensory_store.py`, `features/feature_aggregator.py`, `services/alpaca_stream_service.py` |
| Data sources | `unusual_whales_service.py`, `finviz_service.py`, `fred_service.py`, `sec_edgar_service.py` |
| Execution | `order_executor.py`, `kelly_position_sizer.py`, `alpaca_service.py` |
| Config | `core/config.py`, `api/v1/strategy.py` (REGIME_PARAMS) |

---

## 8. Summary

The Embodier Trader v5.0.0 architecture is **well-structured** for an event-driven trading system. The main trade pipeline (Alpaca → SignalEngine → CouncilGate → Council → OrderExecutor) is clear, with proper gate enforcement and council control. MessageBus and sensory store provide clean decoupling. Key risks:

- **Import error** in layered_memory_agent (duckdb_service)
- **Layering violation** (OrderExecutor → API)
- **Monolithic main.py** and **db_service** coupling

Recommend addressing P0 items before production deployment.
