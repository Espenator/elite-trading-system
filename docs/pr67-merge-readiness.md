# PR #67 — Merge-Readiness Checklist

Self-review of `feat(E1/E2/E3): Streaming Discovery Engine, 12 Scout Agents, Idea Triage
Service` against the actual diff only (25 files, +3238/−4 lines, 2 commits).

---

## 📁 Changed files grouped by purpose

| Group | Files |
|---|---|
| **Infrastructure** | `core/message_bus.py` (+3 topics, +1 Redis bridge), `main.py` (startup + shutdown wiring) |
| **E1 — StreamingDiscoveryEngine** | `services/streaming_discovery.py` (409 lines new) |
| **E2 — Scout agents** | `services/scouts/__init__.py`, `base.py`, `registry.py`, 12 concrete scouts (746 lines total) |
| **E3 — IdeaTriageService** | `services/idea_triage.py` (389 lines new) |
| **Modified consumer** | `services/hyper_swarm.py` (topic: `swarm.idea` → `triage.escalated`, 3-line change) |
| **Tests** | `test_streaming_discovery.py` (41), `test_idea_triage.py` (45), `test_scout_agents.py` (48) — 134 total |
| **Stale artifacts** ⚠️ | `ml_engine/artifacts/drift/drift_log.json`, `reference_stats.json` — timestamp-only diff, completely unrelated to this feature |

---

## 🔀 Duplicate / split event paths

### Path 1: swarm.idea → two independent consumers

```
swarm.idea ─┬─ IdeaTriageService  →  triage.escalated  →  HyperSwarm
            └─ SwarmSpawner  (raw, unfiltered, bypasses E3 entirely)
```

`swarm_spawner.py:132` still subscribes to `swarm.idea` directly.  SwarmSpawner
was **not migrated** to `triage.escalated`.  This is a deliberate split (SwarmSpawner
and HyperSwarm are separate consumers), but it means:

- SwarmSpawner processes **every** raw idea including noise that E3 would drop.
- HyperSwarm only sees the pre-screened subset.
- The two consumers now have different quality floors — document this explicitly or
  migrate SwarmSpawner to `triage.escalated` as well.

### Path 2: HyperSwarm → swarm.idea feedback loop

`hyper_swarm.py:417` publishes to `swarm.idea` when escalating micro-swarm results
to SwarmSpawner (enhanced context path).  IdeaTriageService subscribes to `swarm.idea`,
so those re-emitted events re-enter E3.  The loop does **not** recurse to infinity
(`source: "hyper_swarm:…"` gets `source_bonus=0`; base_score=50 still passes
threshold=40), but the triage metadata will be re-stamped on an already-processed event.

---

## ↔️ Services subscribed to both old and new topics

None.  The migration from `swarm.idea` to `triage.escalated` is clean for HyperSwarm.
No service subscribes to both simultaneously.

---

## ⏱️ Startup/shutdown ordering risks

### Startup

| Step | Service | Risk |
|------|---------|------|
| 2b | StreamingDiscoveryEngine (E1) | Starts publishing to `swarm.idea` immediately. |
| 2c | IdeaTriageService (E3) | Subscribes to `swarm.idea` here — any bars before this step are not triaged. *(Window is tiny; the MessageBus queue buffers events.)* |
| **10b** | **ScoutRegistry (E2)** | **Starts 8 steps after E3 and after SwarmSpawner (8).  The E1→E2→E3 pipeline described in the PR is started in the order E1, E3, [many others], E2.** |

**Fix applied (this review branch):** ScoutRegistry moved to step 2d, immediately
after IdeaTriageService.  All three discovery-pipeline stages (E1/E2/E3) are live
before SwarmSpawner or HyperSwarm.

### Shutdown

Original order: `ScoutRegistry` → `IdeaTriageService` → `StreamingDiscoveryEngine`

Risk: IdeaTriageService was stopped **before** StreamingDiscoveryEngine.  E1 could
still emit to `swarm.idea` after E3's maintenance loop was cancelled.

**Fix applied (this review branch):** Stop publishers first (E2 ScoutRegistry, then
E1 StreamingDiscoveryEngine), then stop the processor (E3 IdeaTriageService).

---

## 📦 Unbounded in-memory buffers, caches, or dedupe windows

| Buffer | Default bound | Risk without cap | Fix applied |
|--------|--------------|-----------------|-------------|
| `IdeaTriageService._recent_arrivals` | Originally `List[float]`, `MAX_QUEUE_SIZE=5000` constant **declared but never enforced** | Under a message storm the list grows without bound between the 60-second maintenance prune | ✅ Changed to `deque(maxlen=MAX_QUEUE_SIZE)` — O(1) automatic eviction |
| `IdeaTriageService._seen` dedup dict | Pruned by 60-second maintenance loop only, **no hard cap** | A symbol storm (e.g., market-wide circuit-breaker open, thousands of tickers spiking) could grow it to millions of keys before the next prune cycle | ✅ Added `MAX_SEEN_SIZE=10_000`; FIFO eviction on every `_check_and_record` write |
| `StreamingDiscoveryEngine._states` | One `BarState` per new symbol, **never evicted** | Delisted / one-off symbols accumulate forever; each `BarState` holds 5 deques × 20 floats | ✅ Added `MAX_TRACKED_SYMBOLS=2000`; FIFO eviction when limit exceeded |
| `BaseScout._stats` per scout | Plain dict, counters only | Bounded by integer overflow (~2^63); no growth risk | None needed |

---

## 🧪 Tests that are unit-only and not representative of runtime behavior

All 134 original tests use `FakeBus` — an in-memory stub that delivers events
synchronously with no queue depth, no Redis, and no backpressure.  Six specific gaps:

1. **No multi-service pipeline test.**  E1→E3→HyperSwarm was never exercised as a
   connected system.  *(1 integration test added in this review branch.)*

2. **No SwarmSpawner + triage concurrency test.**  Both subscribe to `swarm.idea`
   simultaneously in production.  Their interaction (double-processing of ideas) is
   not tested.

3. **No Redis bridge test.**  `triage.escalated` is in `REDIS_BRIDGED_TOPICS` for
   cross-PC cluster transport.  No test verifies that an escalated idea actually
   arrives on a second process via Redis pub/sub.

4. **No backpressure test.**  The adaptive threshold logic is validated by manually
   injecting `_recent_arrivals` values — not by flooding the service through the bus.
   The queue-depth-based clamping (HIGH_WATER=200) has never been tested at actual
   200+ msg/min arrival rate.

5. **Scout detection logic is untested.**  Each of the 12 concrete scouts has exactly
   one test: `test_X_returns_empty_on_service_error`.  None verify positive detection
   or data parsing from real-shaped API payloads.

6. **`ScoutRegistry` restart is untested.**  `stop()` clears `_scouts` and resets
   `_started=False`.  A second `start()` call would re-create all scouts on top of an
   empty list — correct.  But there is no test for this restart path, and if `stop()`
   is called before any scout finishes its first cycle, `asyncio.Task.cancel()` races
   with task completion are not validated.

---

## 🔧 5 smallest code changes that de-risk this PR the most

These are applied in branch `copilot/review-pr-67-checklist` and tested (804 tests pass).

### Fix 1 — `_recent_arrivals` deque cap (`idea_triage.py`, ~5 lines)

```python
# Before: self._recent_arrivals: List[float] = []
# After:
self._recent_arrivals: Deque[float] = deque(maxlen=MAX_QUEUE_SIZE)
```

`MAX_QUEUE_SIZE=5000` was declared at the top of the file but never applied.
Switching to `deque(maxlen=…)` enforces the cap with O(1) amortised cost.

---

### Fix 2 — `_states` symbol cap (`streaming_discovery.py`, ~6 lines)

```python
MAX_TRACKED_SYMBOLS = 2000   # new constant

# Inside _on_bar(), after setdefault():
if len(self._states) > MAX_TRACKED_SYMBOLS:
    oldest = next(iter(self._states))
    del self._states[oldest]
```

Python 3.7+ dicts are insertion-ordered; `next(iter(…))` is the first-inserted
(oldest) symbol — correct FIFO eviction for delisted / one-off tickers.

---

### Fix 3 — `_seen` dict cap (`idea_triage.py`, ~8 lines)

```python
MAX_SEEN_SIZE = 10_000   # new constant

# Inside _check_and_record(), after updating the key:
if len(self._seen) > MAX_SEEN_SIZE:
    oldest_key = next(iter(self._seen))
    del self._seen[oldest_key]
```

Same insertion-order FIFO rationale as Fix 2.  Protects the dedup dict in the 60-second
gap between maintenance-loop prune cycles.

---

### Fix 4 — Move ScoutRegistry to step 2d (`main.py`, ~8 lines moved)

Remove the step 10b block and re-insert it at step 2d (after `IdeaTriageService`).
This ensures all three discovery-pipeline stages (E1/E2/E3) are active before any
downstream consumer starts, matching the architecture diagram in the PR description.

---

### Fix 5 — Correct shutdown ordering (`main.py`, ~4 lines reordered)

Reorder the `_stop_event_driven_pipeline` try-blocks so that:

```
ScoutRegistry.stop()          # E2 publisher first
StreamingDiscoveryEngine.stop() # E1 publisher second
IdeaTriageService.stop()      # E3 processor last
```

This ensures no in-flight `swarm.idea` events from E1/E2 can be dispatched to an
already-stopped triage service during the shutdown window.

---

## ✅ Merge-readiness summary

| Area | Status | Notes |
|---|---|---|
| Core logic (E1/E2/E3) | ✅ Merge-ready | Clean architecture, correct 3-gate emit, correct scoring |
| Topic routing | ⚠️ Document or fix | SwarmSpawner bypasses triage; HyperSwarm feedback loop is benign but undocumented |
| Memory safety | ✅ Fixed | Three buffer caps applied (Fixes 1–3 above) |
| Startup/shutdown ordering | ✅ Fixed | E2 co-located with E1/E3; publishers stop before processor |
| Stale artifact files | ⚠️ Cosmetic | `drift_log.json` + `reference_stats.json` should be gitignored — unrelated timestamp diff |
| Test coverage | ⚠️ Acceptable for draft | Add Redis bridge test and SwarmSpawner concurrency test before promoting to ready |
| Security (CodeQL) | ✅ Clean | 0 alerts |

> All five de-risking fixes are available in `copilot/review-pr-67-checklist` as a
> single commit for cherry-pick into `copilot/issue-38-streaming-discovery-engine`.
