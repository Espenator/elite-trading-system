# Channel & Firehose Agents — Data Spine Integrity Audit

**Date:** 2026-03-13  
**Scope:** 6 channel agents + 4 firehose agents (sensory data spine), MessageBus, DLQ, circuit breakers, backpressure, metrics.

---

## 1. Data Flow Summary

| Step | Component | Topic / Action |
|------|-----------|----------------|
| 1 | AlpacaStreamService (or other publishers) | Publishes `market_data.bar` |
| 2 | AlpacaChannelAgent (channel) | Subscribes to `market_data.bar` → builds SensoryEvent → enqueue → worker drains batch |
| 3 | SensoryRouter (channel) | `route_and_publish()` → `market_data.bar`, `ingest.raw`, `swarm.idea` (if attention-worthy) |
| 4 | MessageBus | Delivers to all subscribers of those topics |
| 5 | EventDrivenSignalEngine | Subscribes to `market_data.bar` → score → `signal.generated` (if ≥ threshold) |
| 6 | CouncilGate → council → OrderExecutor | Signal → verdict → order |

**Firehose path (separate):** Firehose agents (e.g. `AlpacaStreamingAgent`) also subscribe to `market_data.bar`, enqueue to their own queue, and publish to `swarm.idea` for anomalies. So the same bar can be consumed by both channel and firehose; channel re-publishes `market_data.bar` (potential duplication — see §5).

---

## 2. DLQ Flow — Verified

**Question:** Do failed channel events actually reach `ingest.dlq`?

**Answer: Yes.**

- **Channel agents** (`base_channel_agent.py`): On router failure after retries, `_publish_dlq(ev, error)` is called and publishes to `self._dlq_topic` (`ingest.dlq`) with payload `{ "agent", "error", "event", "ts" }`. No subscriber is required; the bus accepts the publish.
- **Firehose agents** (`firehose/base_agent.py`): Do **not** publish to `ingest.dlq` on failure. They only increment `_failures` and open the circuit; failed events are dropped (not sent to DLQ).

**Tests added:**  
- `test_dlq_flow_channel_agent_failure_reaches_ingest_dlq` — asserts failed channel event results in exactly one `ingest.dlq` publish with correct shape (`agent`, `error`, `event`, `ts`).

---

## 3. Circuit Breaker Integration

**Channel agents** (`base_channel_agent.py`):

- `CircuitBreaker(failure_threshold=10, reset_timeout_s=30.0)` (default).
- After 10 consecutive failures, circuit opens; events are sent to DLQ with reason `"circuit_open"` until `reset_timeout_s` has passed.

**Firehose agents** (`firehose/base_agent.py`):

- `circuit_failures = 5`, `circuit_reset_sec = 60.0`.
- After 5 consecutive publish failures, `_circuit_open_until = time.monotonic() + 60`; loop then `await asyncio.sleep(1.0)` and re-checks until time has passed, then processes again.

**Test added:**  
- `test_firehose_circuit_breaker_five_failures_then_reset` — 5 failures → circuit open; after reset window, 6th event is published successfully.

---

## 4. Backpressure — MessageBus Queue Full

**Question:** What happens when MessageBus queue hits capacity?

**Current behavior:**

- `MessageBus.publish()` uses `put_nowait()`. If the queue is full, the event is passed to `_add_to_dlq(event, reason="queue_full")` and not delivered to subscribers. No feedback is sent back to channel/firehose agents; they do not pause.
- Channel agents have their own internal queue (`max_queue_size` 2000–5000). If that queue is full, `enqueue()` drops the event and increments `events_dropped_queue_full` (no DLQ at channel level for that).

**Conclusion:** There is **no backpressure feedback** from MessageBus to channel agents. Producers are not paused when the bus is full; overflow is handled by the bus DLQ only.

**Test added:**  
- `test_backpressure_message_bus_queue_full_event_to_dlq` — when the bus queue is full (small queue + slow handler), a publish results in an event in the bus DLQ with `reason="queue_full"`.

---

## 5. Channel vs Firehose Metrics — Different Formats

| Source | Location | Shape |
|--------|----------|--------|
| Channel orchestrator | `ChannelsOrchestrator.get_metrics()` | `{ "router": {...}, "agents": { name: { events_in, events_out, events_dropped_queue_full, events_failed, events_dlq, batches_processed, max_batch_seen } }, "bus": bus.get_metrics() }` |
| Firehose | `firehose/metrics.get_metrics()` | `{ "agent_id": { "count", "last_ts", "queue_depth", "last_latency" }, "agent_id:topic": { "count", "last_ts" } }` (keyed by agent_id and agent_id:topic) |

So today there are **two different metric namespaces**: channel (per-agent counters + router) vs firehose (per-agent latency/queue/count). They are not aggregated in one place.

---

## 6. Data Duplication Risk

- **Same bar, two paths:** `market_data.bar` is published by the data source (e.g. Alpaca stream). Both:
  - **AlpacaChannelAgent** (channel) subscribes, normalizes to channel `SensoryEvent`, and via SensoryRouter publishes again to `market_data.bar` (and `ingest.raw`, and optionally `swarm.idea`).
  - **AlpacaStreamingAgent** (firehose) subscribes and, for anomaly bars, publishes to `swarm.idea`.
- So the same bar can generate **duplicate** `market_data.bar` (once from source, once from channel router) and, for anomaly bars, **two** `swarm.idea` messages (channel router + firehose). No deduplication by `event_id` or bar key was observed at the bus or router level.

---

## 7. Agent Startup in main.py

| Orchestrator | Agents | Started in main.py? |
|--------------|--------|----------------------|
| **ChannelsOrchestrator** | 5: alpaca_firehose, discord, uw_firehose, finviz_firehose, news_firehose | Yes (step 24d, when `CHANNELS_FIREHOSE_ENABLED=true`) |
| **FirehoseOrchestrator** | 4: AlpacaStreamingAgent, DiscordIngestAgent, UnusualWhalesAgent, FinvizScreenerAgent | **No** — `ensure_orchestrator_started()` for the firehose orchestrator is never called from `main.py`. |

So only the **5 channel agents** are started at application startup. The **4 firehose spine agents** (in `firehose/orchestrator.py`) are only started if some other code path calls `ensure_orchestrator_started(message_bus)` from `app.services.firehose.orchestrator`; that call was not found in the main lifespan.

---

## 8. Other Findings

- **Channel retry:** Uses exponential backoff with jitter (`base_delay_s * 2^attempt + jitter_s`), not fixed backoff.
- **Rate limiting:** MessageBus has per-topic rate limits (e.g. `swarm.idea`, `scout.heartbeat`); channel/firehose agents do not have their own per-channel rate limiting (risk of upstream 429s if they push too fast).
- **Firehose polling:** `poll_interval_sec` is fixed per agent; no adaptive polling by market hours.

---

## 9. Unified Metrics Proposal — Single `/metrics` for All 10 Agents

**Goal:** One place to see all sensory spine agents (5 channel + 4 firehose) and the bus.

### 9.1 Recommended schema for `/api/v1/metrics` (or `/api/v1/ingestion/metrics`)

```json
{
  "spine": {
    "channels": {
      "running": true,
      "agents": {
        "alpaca_firehose": {
          "events_in": 0,
          "events_out": 0,
          "events_dropped_queue_full": 0,
          "events_failed": 0,
          "events_dlq": 0,
          "batches_processed": 0,
          "max_batch_seen": 0,
          "queue_depth": 0,
          "queue_max": 5000,
          "circuit_open": false,
          "paused": false
        }
      },
      "router": { "events_routed": 0, "events_failed": 0, "events_to_awareness": 0 }
    },
    "firehose": {
      "running": true,
      "agents": {
        "alpaca_streaming": {
          "queue_depth": 0,
          "last_latency_sec": null,
          "published_by_topic": { "swarm.idea": 0 },
          "circuit_open": false,
          "failures": 0
        }
      }
    }
  },
  "message_bus": {
    "queue_depth": 0,
    "queue_max": 10000,
    "queue_usage_pct": 0,
    "events_by_topic": {},
    "dlq": { "size": 0, "max": 500 },
    "rate_limited": {}
  }
}
```

### 9.2 Implementation steps

1. **Unified ingestion metrics endpoint**  
   - Add or extend an endpoint (e.g. `GET /api/v1/metrics` or `GET /api/v1/ingestion/metrics`) that:
     - Calls `ChannelsOrchestrator.get_metrics()` and normalizes under `spine.channels`.
     - If the firehose orchestrator is started, call `FirehoseOrchestrator.get_status()` (or a new `get_metrics()`) and normalize under `spine.firehose` using the same field names where possible (e.g. `queue_depth`, `circuit_open`).
     - Includes `message_bus.get_metrics()` under `message_bus`.
2. **Normalize firehose metrics**  
   - In `firehose/metrics.py` or the firehose orchestrator, expose per-agent metrics in a shape that matches the schema above (e.g. `queue_depth`, `last_latency_sec`, `published_by_topic`, `circuit_open`, `failures`).
3. **Start firehose orchestrator in main**  
   - In the same lifespan step as ChannelsOrchestrator (or immediately after), call `ensure_orchestrator_started(message_bus)` from `app.services.firehose.orchestrator` so all 9 agents (5 channel + 4 firehose) run and appear in the unified metrics.
4. **Optional: Prometheus export**  
   - Add a single Prometheus scrape target that reads this unified payload and exposes counters/gauges with labels `agent`, `topic`, `layer=channel|firehose`.

This gives a single dashboard for queue depth, circuit state, DLQ, and throughput for the entire data spine.

---

## 10. Deliverables Checklist

| Deliverable | Status |
|-------------|--------|
| Test: DLQ flow (channel agent failure → ingest.dlq) | Done — `test_dlq_flow_channel_agent_failure_reaches_ingest_dlq` |
| Test: Circuit breaker (5 failures → agent disabled → reset after 60s) | Done — `test_firehose_circuit_breaker_five_failures_then_reset` (reset window 0.6s in test) |
| Test: Backpressure (queue full → event to DLQ) | Done — `test_backpressure_message_bus_queue_full_event_to_dlq` |
| Report: Unified metrics proposal | Done — §9 above |

---

## 11. File References

- Channel lifecycle: `backend/app/services/channels/orchestrator.py`
- Channel base (batch-drain, DLQ): `backend/app/services/channels/base_channel_agent.py`
- Channel Alpaca/UW: `backend/app/services/channels/alpaca_channel_agent.py`, `uw_channel_agent.py`
- Firehose lifecycle: `backend/app/services/firehose/orchestrator.py`
- Firehose base (circuit breaker 5/60s): `backend/app/services/firehose/base_agent.py`
- Firehose Alpaca: `backend/app/services/firehose/agents/alpaca_streaming_agent.py`
- Firehose metrics: `backend/app/services/firehose/metrics.py`
- Event routing: `backend/app/core/message_bus.py`
- Tests: `backend/tests/test_channels_firehose.py`
