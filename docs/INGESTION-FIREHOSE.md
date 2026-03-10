# Firehose and CNS Enhancements for Elite Trading System

## Overview
This document outlines the implementation of Firehose and CNS enhancements in the Elite Trading System as detailed in `cursor_agent_prompts_firehose_and_cns.md`.

## Enhancements Overview

### 1. Score Standardization and CouncilGate Fix
- Standardized `signal.generated.score` range to 0-100 across all producers and consumers.
- Default threshold set to `65.0` in CouncilGate with updated documentation and comments.
- Fixed fallback gating in `backend/app/main.py` for `signal->verdict` -> ensured confidence mapping (score/100) and preserved direction mapping (buy/sell/hold) and price field.
- Added tests for score invariants and gate behavior.

### 2. New Backend App Services
- Created `backend/app/services/firehose/` package that includes:
  - `schemas.py`: SensoryEvent Pydantic model.
  - `router.py`: Topic routing to MessageBus.
  - `base_agent.py`: Bounded queue, retries/backoff, circuit breaker, and start/stop functionalities.
  - `orchestrator.py`: Agent registry, status/metrics, pause/resume functionalities.
  - `metrics.py`: Metrics collections for counters.
  - `persistence.py`: Optional raw append-only store using DuckDB or SQLite.

### 3. Ingestion Agents
- Implemented ingestion agents in `firehose/agents/`:
  - `alpaca_streaming_agent.py`: Publishes `market_data.bar` with consistent schema + anomalies to `swarm.idea`.
  - `discord_ingest_agent.py`: Converts actionable messages to `SensoryEvent` and publishes to `swarm.idea/perception.world_intel`.
  - `unusual_whales_agent.py`: Publishes to `unusual_whales.flow/darkpool/congress + swarm.idea`.
  - `finviz_screener_agent.py`: Publishes to `perception.finviz.screener + swarm.idea`.

### 4. Triage Service
- Implemented `triage_service.py` subscribing to `swarm.idea` and publishing `triage.escalated/triage.dropped` with deduplication, priority threshold, and per-symbol cooldown functionality.
- Optional enrichment via `Awareness Worker` if `AWARENESS_WORKER_URL` environment variable is set; with audit publishing.

### 5. PC2 Awareness Worker Service
- **Endpoint:** `POST /awareness/enrich` — accepts `{"events": [ ... ]}` (SensoryEvent payloads), returns `{"enriched": [...], "results": [...], "count": N}` with stub fields `embedding_ref`, `novelty_score`, `tags` (stub implementation; replace with GPU/embedding pipeline on PC2).
- **In main app:** The awareness router is mounted in `app.main`, so the same process can serve `/awareness/enrich` (e.g. single-node or when this instance is the PC2 brain). See `backend/app/api/v1/awareness.py`.
- **Standalone PC2:** Run only the awareness worker: from `backend/`, `python -m uvicorn awareness_main:app --host 0.0.0.0 --port 8001`. Then set on PC1: `AWARENESS_URL=http://<pc2>:8001` or `PC2_BRAIN_URL=http://<pc2>:8001`, and `AWARENESS_MODE=http`.
- **Client:** `backend/app/services/awareness_worker.py` — `enrich_events(events, timeout)` and `is_awareness_worker_configured()`; fails gracefully when PC2 is down or `AWARENESS_WORKER_URL` is unset.

### 6. BlackboardState Implementation
- Created `backend/app/services/blackboard_state.py` with a per-symbol TTL store and an API route `GET /api/v1/blackboard/{symbol}`. Connected perception events to write facts, and council agents to read.

### 7. New API Routes
- Added API routes:
  - `GET /api/v1/ingestion/firehose/health` — firehose health check
  - `GET /api/v1/brain/health` — ideas/sec, signals/sec, council pass/veto/hold ratios, order submitted/filled/rejected, queue depths, dropped counts, last event timestamps
  - `GET /api/v1/blackboard` — list symbols with blackboard state
  - `GET /api/v1/blackboard/{symbol}` — working memory (facts) for symbol; perception writes, council reads
  - `POST /awareness/enrich` — PC2 batch enrichment (tags, novelty_score, embedding_ref); client in `app.services.awareness_worker.enrich_events()` fails gracefully if PC2 down
- Registered routers in `backend/app/main.py`.

### 8. Two-PC Support
- Ensured no hardcoded `localhost` references; employed environment variables for PC2 URLs and bound to `0.0.0.0`.

### 9. Documentation Updates
- Added `docs/INGESTION-FIREHOSE.md` and updated any environment templates accordingly.

### 10. Testing
- Introduced at least 5 meaningful tests covering schema validation, routing, triage deduplication, score invariants, and awareness worker client fallback functionality.

## Profit Brain Policies (2026-03-10)

The following policies ensure learning integrity, execution safety, and real-time operator awareness.

### Censored outcomes policy

- **Purpose**: Avoid corrupting win/loss stats and weight learning when shadow positions time out or data is missing.
- **Behaviour**:
  - Shadow timeouts are resolved per `OUTCOME_TIMEOUT_POLICY` (env):
    - **`timeout_censored`** (default): Do not count toward win/loss/Kelly/weights; `close_reason=timeout_censored`, `is_censored=True`.
    - **`mark_to_market`**: Resolve at last known price when available; otherwise treat as censored.
  - Resolved outcome payloads include `close_reason` and `is_censored`.
  - WeightLearner and Kelly sizing ignore censored outcomes; no weight update and no addition to `resolved_history`.

### Degraded mode policy

- **Purpose**: Prevent auto-trading when critical data is stale or unavailable (real-time truth for the operator).
- **Behaviour**:
  - `GET /api/v1/brain/degraded` returns `degraded: bool`, `reasons` (e.g. `market_data_stale`, `risk_stale`, `llm_unavailable`, `ws_disconnected`), and `details` with ages/timestamps.
  - OrderExecutor refuses AUTO execution when degraded unless `DEGRADED_MODE_OVERRIDE=true` (use with caution).
  - UI can show a global DEGRADED banner using this endpoint.

### Sizing gate policy

- **Purpose**: Ensure no live trade executes without passing a single canonical sizing step.
- **Behaviour**:
  - The canonical SizingGate runs inside OrderExecutor: Kelly (or deterministic sizing) must return `final_pct > 0` and `action != HOLD` before any order is submitted.
  - If sizing returns HOLD or zero size, execution is blocked (no order submitted).
  - Sizing metadata (`sizing_gate_passed`, `sizing_metadata` with edge, raw_kelly, stats_source) is attached to `order.submitted` and optionally reflected on `council.verdict` via `sizing_deferred_to_executor`.

## Conclusion
The implementation of the Firehose and CNS enhancements has been completed and thoroughly documented. Further testing will ensure robustness and functionality of the new integrations and changes in the system.