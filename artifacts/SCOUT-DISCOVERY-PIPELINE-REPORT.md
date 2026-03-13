# Scout Discovery Pipeline Audit Report

**Date**: March 13, 2026  
**Scope**: Wire orphaned scout discovery consumer; swarm.idea → council/execution path.

---

## 1. Current State Summary

### 1.1 swarm.idea — Publishers vs Subscribers

| Role | Component | Location |
|------|-----------|----------|
| **Publishers** | 12 scouts (FlowHunter, Insider, Congress, Gamma, News, Sentiment, Macro, Earnings, SectorRotation, ShortSqueeze, IPO, CorrelationBreak) | `backend/app/services/scouts/base.py` → `_publish()` → `bus.publish("swarm.idea", payload.to_swarm_idea())` |
| **Publishers** | StreamingDiscoveryEngine, firehose agents (Alpaca, UW, Finviz, Discord), TurboScanner, ML Signal Publisher, Knowledge Ingest, News Aggregator, etc. | Multiple services |
| **Subscribers** | IdeaTriageService | `backend/app/services/idea_triage.py` L183: `await self._bus.subscribe("swarm.idea", self._on_idea)` |
| **Subscribers** | WebSocket bridge | `backend/app/main.py` L747: `_bridge_swarm_idea_to_ws` |

**Finding**: swarm.idea **does** have consumers (IdeaTriageService + WS). The “orphan” is **downstream**: triage.escalated has no path to **signal.generated** that works without Ollama.

### 1.2 triage.escalated → Council/Execution Gap

| Consumer | What it does | Reaches council? | Reaches OrderExecutor? |
|----------|--------------|-------------------|-------------------------|
| **SwarmSpawner** | Subscribes to triage.escalated, runs symbol prep → **run_council()** internally → publishes **swarm.result** only | Council run in-process | **No** — does not publish council.verdict |
| **HyperSwarm** | Subscribes to triage.escalated, runs micro-swarm (Ollama), if score ≥ 65 publishes **signal.generated** → CouncilGate | Yes (via CouncilGate) | Yes |
| **DiscoverySignalBridge** (new) | Subscribes to triage.escalated, publishes **signal.generated** with synthetic score | Yes (via CouncilGate) | Yes |

**Finding**: Scout discoveries reach council only when **HyperSwarm** is enabled (LLM_ENABLED) and micro-swarm score ≥ 65. When HyperSwarm is off or Ollama is down, escalated ideas never become signals; SwarmSpawner runs council but never publishes council.verdict, so OrderExecutor never sees them.

### 1.3 scout.discovery Topic

| Role | Component | Location |
|------|-----------|----------|
| **Publishers** | SessionScanner (gap alerts), GeopoliticalRadar | `session_scanner.py` L238, `geopolitical_radar.py` L555/L573 |
| **Subscribers** | WebSocket bridge only | `main.py` L756: `_bridge_macro_to_ws` |

**Finding**: scout.discovery has **no triage/signal path** — WS broadcast only. SessionScanner doc says “scout.discovery → IdeaTriage → SwarmSpawner” but IdeaTriage subscribes to **swarm.idea**, not scout.discovery. So scout.discovery events are not triaged unless another service republishes them to swarm.idea.

### 1.4 DiscoveryPayload Schema (base.py)

```python
@dataclass
class DiscoveryPayload:
    source: str           # e.g. "flow_hunter_scout"
    symbols: List[str]    # symbols of interest
    direction: str        # bullish | bearish | neutral
    reasoning: str       # human-readable explanation
    priority: int = 5     # 1 (highest) – 5 (lowest)
    metadata: Dict[str, Any]
    discovered_at: str   # ISO timestamp
```

**Verified**: symbols, direction, priority, reasoning are all present. `to_swarm_idea()` emits dict with source, symbols, direction, reasoning, priority, metadata (incl. discovered_at).

### 1.5 Auto-backfill for Discovered Symbols

- **Startup auto-backfill** (`main.py` ~L1415): Runs when DuckDB has 0 OHLCV/indicator rows; uses `get_tracked_symbols()[:20]` — **not** driven by swarm.idea or scout discoveries.
- **SymbolPrepService**: SwarmSpawner requests prep via `symbol.prep.requested`; SymbolPrepService runs data_ingestion (bars + indicators) and publishes `symbol.prep.ready`. So **discovered symbols get backfill only when SwarmSpawner processes a triage.escalated idea** and requests prep.
- **Gap**: No dedicated “on discovery, auto_backfill_symbol(s)” before council. If a symbol is not in tracked universe, prep may still run on demand via SymbolPrepService.

### 1.6 TODO/FIXME / Orphan Comments

- `main.py` L405: “downstream consumers (SwarmSpawner, HyperSwarm)” — no explicit “wire discovery” TODO.
- `main.py` L1570: “Sensory store — wire orphan perception/macro/signal topics” — perception/macro, not swarm.idea.
- No explicit “wire swarm.idea consumer” or “scout discovery orphan” FIXME found.

---

## 2. Publish-Only MessageBus Topics (Need Subscribers)

From `message_bus.py` audit block (L62–67), **16 publish-only topics**:

| Topic | Publisher(s) | Suggested consumer |
|-------|--------------|--------------------|
| signal.unified | — | CouncilGate or unified scoring |
| **scout.heartbeat** | All 12 scouts (base.py _heartbeat_loop) | Health/monitoring dashboard |
| triage.dropped | IdeaTriageService | Audit / metrics |
| swarm.spawned | SwarmSpawner | UI / analytics |
| knowledge.ingested | Knowledge ingest | Council context |
| hitl.approval_needed | HITL gate | Human approval UI |
| perception.finviz.screener | Channels | Sensory store / council |
| finviz.screener | — | Sensory store |
| perception.macro | Macro agents | Sensory store |
| perception.edgar | EDGAR agents | Sensory store |
| perception.gex | GEX agents | Sensory store |
| signal.external | External webhooks | CouncilGate or triage |
| alert.health | Health registry | Slack / dashboard |
| position.partial_exit | OrderExecutor | Sensory / UI |
| position.closed | OrderExecutor | Sensory / UI |
| symbol.prep.ready | SymbolPrepService | SwarmSpawner (already used via request_id Future) |

---

## 3. Proposed Wiring

### 3.1 swarm.idea → Council Path (Implemented)

```
swarm.idea
  → IdeaTriageService (dedup, priority, threshold)
  → triage.escalated
  → [NEW] DiscoverySignalBridge: publish signal.generated (score = max(triage_score, 55))
  → CouncilGate → run_council() → council.verdict → OrderExecutor
```

- **DiscoverySignalBridge**: Subscribes to `triage.escalated`. For each payload, build `signal.generated` with symbol, score (from triage score or priority map), direction, source, metadata. Ensures scout-origin ideas reach CouncilGate even when HyperSwarm is disabled.
- **Dedup**: Already done by IdeaTriageService (5-min window, per-symbol cooldown).
- **Priority**: Triage already scores by source + priority; bridge uses that score (capped to pass gate).

### 3.2 Optional: SwarmSpawner → council.verdict

When SwarmSpawner’s internal `_run_council()` returns a verdict with `execution_ready=True`, publish that verdict to `council.verdict` so OrderExecutor can execute. This gives a second path: triage.escalated → SwarmSpawner → council.verdict (without going through CouncilGate again). Implement only if product wants swarm results to auto-execute; otherwise keep current “swarm.result only” for UI/audit.

### 3.3 scout.discovery → swarm.idea (Optional)

If SessionScanner / GeopoliticalRadar should go through IdeaTriage, add a small adapter that subscribes to `scout.discovery` and republishes to `swarm.idea` with the same schema (source, symbols, direction, reasoning, priority). Then existing triage + bridge path applies.

---

## 4. Code Locations Reference

| Item | File:Line or path |
|------|-------------------|
| Scout publish swarm.idea | `backend/app/services/scouts/base.py` L207–218 (`_publish`) |
| IdeaTriage subscribe swarm.idea | `backend/app/services/idea_triage.py` L183 |
| IdeaTriage publish triage.escalated | `backend/app/services/idea_triage.py` L453–455 |
| SwarmSpawner subscribe triage.escalated | `backend/app/services/swarm_spawner.py` L132 |
| SwarmSpawner _run_council | `backend/app/services/swarm_spawner.py` L280–303 |
| SwarmSpawner publish swarm.result | `backend/app/services/swarm_spawner.py` L246 |
| HyperSwarm subscribe triage.escalated | `backend/app/services/hyper_swarm.py` L124 |
| HyperSwarm _escalate → signal.generated | `backend/app/services/hyper_swarm.py` L442–478 |
| CouncilGate subscribe signal.generated | `backend/app/council/council_gate.py` L122 |
| OrderExecutor subscribe council.verdict | `backend/app/services/order_executor.py` L186 |
| Scout heartbeat publish | `backend/app/services/scouts/base.py` L172–178 |
| DiscoveryPayload schema | `backend/app/services/scouts/base.py` L26–50 |
| MessageBus VALID_TOPICS / PUBLISH_ONLY | `backend/app/core/message_bus.py` L49–79, L102–118 |

---

## 5. Test: DiscoveryPayload → swarm.idea → Council Path

- **Test**: Publish a mock DiscoveryPayload (as swarm.idea dict) → IdeaTriageService escalates (mock or ensure score ≥ threshold) → DiscoverySignalBridge publishes signal.generated → assert one signal.generated and (with CouncilGate stubbed) one council invocation or council.verdict.
- **Location**: `backend/tests/test_scout_discovery_pipeline.py` (new) or extend `test_e2e_pipeline.py`.

---

## 6. Deliverables Checklist

- [x] Report on scout→council gap with code locations
- [x] Proposed wiring: swarm.idea → dedup (IdeaTriage) → priority (IdeaTriage) → DiscoverySignalBridge → signal.generated → CouncilGate
- [x] List of 16 publish-only MessageBus topics
- [x] Test: mock DiscoveryPayload → swarm.idea → verify reaches council (`tests/test_scout_discovery_pipeline.py`)
