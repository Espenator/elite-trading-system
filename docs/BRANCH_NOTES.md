# Branch notes — Continuous Discovery & triage (March 2026)

Summary of work on this branch: triage/council/channels wiring, test fixes, and app startup fixes.

## Done

- **Triage (E3)**  
  - `IdeaTriageService`: scores `swarm.idea`, publishes `triage.escalated` / `triage.dropped`.  
  - `/api/v1/triage/status`: operator visibility (counters, drop reasons, audit trail).  
  - Contract tests: `test_triage_service_contract.py`, `test_idea_triage.py` (incl. `TriageResult` + `drop_reason`).

- **HyperSwarm**  
  - Consumes `triage.escalated`, runs micro-swarm triage, publishes `signal.generated` and `swarm.result`.  
  - Wiring test: `test_hyperswarm_wiring.py`.

- **Council invocation**  
  - Single path: `signal.generated` → CouncilGate (or safe fallback) → `council.verdict`.  
  - Tests: `test_council_invocation_single_path.py`.

- **Channels (firehose)**  
  - Package `app.services.channels`: `SensoryEvent`, `SensoryRouter`, `BaseChannelAgent`, `AlpacaChannelAgent`, `DiscordChannelAgent`, `ChannelsOrchestrator`.  
  - Normalize → `swarm.idea`, `market_data.*`, `ingest.*`.  
  - Exports in `channels/__init__.py`; ingestion API `/api/v1/ingestion/status`, `/api/v1/ingestion/metrics`.  
  - Tests: `test_channels_firehose.py`.

- **App startup**  
  - `main.py`: added missing `brain` and `blackboard_routes` imports so the app and test suite load.

- **Tests**  
  - Fixed `test_idea_triage.py`: `TriageResult` now includes required `drop_reason` in all three tests.  
  - Full unit suite (excluding e2e/integration): **867 passed**.

## Optional next steps

- Add more channel agents (e.g. news, screener) under `channels/`.  
- Wire channels orchestrator in lifespan if not already (already started when `CHANNELS_FIREHOSE_ENABLED`).  
- Open PR and merge to main after review.

## Suggested commit message

```
fix: triage + channels + app imports; 867 tests passing

- IdeaTriageService: TriageResult.drop_reason in tests
- channels: export SensoryEvent, SensoryRouter, agents, orchestrator from __init__
- main: add brain, blackboard_routes imports for app load
- All unit tests (excl. e2e/integration) passing
```
