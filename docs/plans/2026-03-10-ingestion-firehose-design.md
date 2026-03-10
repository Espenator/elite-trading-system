# Ingestion Firehose (CNS Sensory Layer) — Design

**Goal:** Build a production-grade, always-on, high-throughput ingestion layer that normalizes external world signals into a canonical `SensoryEvent` and publishes into the existing `MessageBus` topics, feeding HyperSwarm triage → Council → OrderExecutor.

**Architecture:** Add a `backend/app/services/channels/` “sensory layer” (agents + router + orchestrator) that wraps existing producers (Alpaca streaming, Discord, batch adapters, discovery engines) without breaking current flows. Bounded queues, retries/backoff, per-source circuit breakers, health/heartbeats, DLQ, optional raw publishing, optional two-PC awareness enrichment.

**Tech Stack:** Python 3.11+, asyncio, FastAPI, Pydantic v2, optional DuckDB persistence, Redis-bridged `MessageBus` for two-PC cluster.

---

## Canonical event model: `SensoryEvent`

`backend/app/services/channels/schemas.py`: event_id, ts (UTC), source, event_type, symbols, raw, normalized, confidence, priority, tags, embedding_ref, routing, provenance, data_quality. Helpers: `from_alpaca_bar()`, `from_discord_signal()`.

---

## Channel agents

`base_channel_agent.py`: bounded queue, retries + backoff, circuit breaker, heartbeats to `ingest.health`, DLQ to `ingest.dlq`, pause/resume.

**Initial agents:** AlpacaChannelAgent (subscribes to `market_data.bar`), DiscordChannelAgent (uses DiscordSwarmBridge with callback, no double-publish).

---

## Router

`router.py`: maps SensoryEvent to `market_data.bar`, `swarm.idea`, `ingest.raw`, `ingest.to_awareness`; bar anomaly heuristics; Discord → idea; optional HTTP awareness enrichment.

---

## Orchestrator

`orchestrator.py`: start/stop agents, aggregate status/metrics, pause/resume per agent. Wired in `main.py` under `FIREHOSE_ENABLED` (default true). Legacy DiscordSwarmBridge skipped when firehose enabled.

---

## Observability

- `GET /api/v1/ingestion/status`
- `GET /api/v1/ingestion/metrics`

---

## Safety

`data_quality` on every event; `alignment_preflight_required` on idea payloads.
