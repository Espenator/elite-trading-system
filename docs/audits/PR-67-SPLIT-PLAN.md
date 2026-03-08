# PR #67 Split Plan — Streaming Discovery Engine, 12 Scouts, Idea Triage

> **Original PR #67** added 3 238 lines across 25 files in a single commit.
> This document defines how to split that work into five focused, independently
> mergeable PRs **without redoing any code**. Each PR builds on the previous one
> so that `main` always stays green.

---

## Dependency graph

```
PR A (message-bus topics)
  └─► PR B (BaseScout + ScoutRegistry)
        └─► PR C (12 individual scouts)
PR A
  └─► PR D (StreamingDiscoveryEngine + IdeaTriageService + HyperSwarm wiring)
        depends on PR B & C being merged first (scouts publish to swarm.idea)
PR E (tests + docs) — depends on A–D, can be opened in parallel with A but
                      must not be merged until A–D are merged
```

---

## PR A — Minimum Safe Core

**Branch**: `split/pr67-a-core`  
**Target**: `main`  
**Purpose**: Register all new MessageBus topics so they are available before any
service that uses them is merged. Zero runtime behaviour change.

### Files

| File | Change |
|------|--------|
| `backend/app/core/message_bus.py` | Add `scout.heartbeat`, `triage.escalated`, `triage.dropped`, `hyper_swarm.escalated` to `VALID_TOPICS` and the WebSocket-bridge set |

### Dependency ordering

No dependencies — this is the root. Must be merged **first**.

### Notes

- All four new topics are additive; existing subscribers are unaffected.
- `hyper_swarm.escalated` is required by PR D (Fix 1 — breaks HyperSwarm
  circular loop).

---

## PR B — Scout Framework

**Branch**: `split/pr67-b-scout-framework`  
**Target**: `split/pr67-a-core` → then retargeted to `main` after PR A merges  
**Purpose**: Introduce `BaseScout`, `DiscoveryPayload`, and `ScoutRegistry`
without any concrete scouts. The registry `start()` method already imports
the 12 scouts lazily, so it will fail gracefully if PR C has not merged yet.

### Files

| File | Change |
|------|--------|
| `backend/app/services/scouts/__init__.py` | New — package init, re-exports |
| `backend/app/services/scouts/base.py` | New — `BaseScout` ABC + `DiscoveryPayload` dataclass |
| `backend/app/services/scouts/registry.py` | New — `ScoutRegistry` lifecycle manager |

### Dependency ordering

Depends on **PR A** (uses `scout.heartbeat` and `swarm.idea` topics).

### Notes

- `ScoutRegistry.start()` uses deferred imports for all 12 scouts, so the
  package is importable before PR C lands.
- No `main.py` wiring yet — that comes in PR D.

---

## PR C — Individual Scout Agents

**Branch**: `split/pr67-c-scouts`  
**Target**: `split/pr67-b-scout-framework` → then retargeted to `main` after PR B merges  
**Purpose**: Ship all 12 concrete scout implementations. Each scout is
independently testable and does not require the others.

### Files

| File | Change |
|------|--------|
| `backend/app/services/scouts/flow_hunter.py` | New — Unusual Whales flow events |
| `backend/app/services/scouts/insider.py` | New — SEC Form 4 filings |
| `backend/app/services/scouts/congress.py` | New — Congressional trading disclosures |
| `backend/app/services/scouts/gamma.py` | New — options gamma exposure |
| `backend/app/services/scouts/news.py` | New — Alpaca news stream **(Fix 2 applied: `get_news()` not `get_latest()`; `_pending` capped at 500 items)** |
| `backend/app/services/scouts/sentiment.py` | New — social sentiment aggregation |
| `backend/app/services/scouts/macro.py` | New — FRED macro indicators |
| `backend/app/services/scouts/earnings.py` | New — upcoming earnings calendar |
| `backend/app/services/scouts/sector_rotation.py` | New — sector ETF relative strength |
| `backend/app/services/scouts/short_squeeze.py` | New — short interest + borrow rate |
| `backend/app/services/scouts/ipo.py` | New — IPO / lockup expiry calendar |
| `backend/app/services/scouts/correlation_break.py` | New — inter-asset correlation breaks |

### Dependency ordering

Depends on **PR B** (all scouts inherit from `BaseScout`).

### Bug fix included (Fix 2 + Fix 6)

`NewsScout.scout()` previously called `agg.get_latest()` which does not exist
on `NewsAggregator`; corrected to `agg.get_news()`. `NewsScout._pending` now
has a hard 500-item cap (`MAX_PENDING`) to prevent unbounded growth between
poll intervals.

---

## PR D — Triage Routing & HyperSwarm Integration

**Branch**: `split/pr67-d-triage`  
**Target**: `split/pr67-c-scouts` → then retargeted to `main` after PR C merges  
**Purpose**: Wire `StreamingDiscoveryEngine` (E1), `ScoutRegistry` (E2), and
`IdeaTriageService` (E3) into `main.py`. Fix the HyperSwarm feedback loop and
expose module-level globals for health-endpoint inspection.

### Files

| File | Change |
|------|--------|
| `backend/app/services/streaming_discovery.py` | New — 5-detector, 3-gate bar anomaly engine |
| `backend/app/services/idea_triage.py` | New — dedup + priority scoring + adaptive threshold **(Fix 5 + Fix 7 applied)** |
| `backend/app/services/hyper_swarm.py` | Modified — `_escalate()` publishes to `hyper_swarm.escalated` **(Fix 1)** |
| `backend/app/services/swarm_spawner.py` | Modified — subscribes to `triage.escalated` + `hyper_swarm.escalated` instead of raw `swarm.idea` **(Fix 4)** |
| `backend/app/main.py` | Modified — module-level globals `_streaming_discovery`, `_idea_triage`, `_scout_registry` added; startup/shutdown wiring for E1/E2/E3 **(Fix 3)** |
| `backend/app/modules/ml_engine/artifacts/drift/drift_log.json` | Modified — updated drift log (auto-generated, no logic change) |
| `backend/app/modules/ml_engine/artifacts/drift/reference_stats.json` | Modified — updated reference stats (auto-generated, no logic change) |

### Dependency ordering

Depends on **PR A** (needs `triage.escalated`, `hyper_swarm.escalated` topics)
and **PR B + PR C** (ScoutRegistry imports the 12 scouts).

### Bug fixes included

| Fix | Description |
|-----|-------------|
| Fix 1 | `HyperSwarm._escalate()` now publishes to `hyper_swarm.escalated` instead of `swarm.idea`, breaking the circular loop where `IdeaTriageService` would re-score and re-escalate back to HyperSwarm |
| Fix 3 | `_streaming_discovery`, `_idea_triage`, and `_scout_registry` are now declared in the module-level globals block of `main.py` and listed in all `global` statements, making them inspectable from health endpoints |
| Fix 4 | `SwarmSpawner` subscribes to `triage.escalated` and `hyper_swarm.escalated` rather than raw `swarm.idea`; all ideas now pass through the triage quality gate before reaching the spawner |
| Fix 5 | `IdeaTriageService._recent_arrivals` has a hard cap of 2 000 entries (`MAX_ARRIVALS_WINDOW`) so it cannot grow unboundedly during event storms |
| Fix 7 | Unused `defaultdict` import removed from `idea_triage.py` |

---

## PR E — Tests & Docs Cleanup

**Branch**: `split/pr67-e-tests`  
**Target**: `main` (open early, merge last)  
**Purpose**: Consolidate all test files and documentation. Can be opened in
parallel with PR A (tests will fail CI until A–D are merged) but should only be
merged **after** PR D lands.

### Files

| File | Change |
|------|--------|
| `backend/tests/test_streaming_discovery.py` | New — 48 tests for `StreamingDiscoveryEngine` |
| `backend/tests/test_scout_agents.py` | New — 50 tests for all 12 scout agents + `BaseScout` |
| `backend/tests/test_idea_triage.py` | New — 45 tests for `IdeaTriageService` (scoring, dedup, adaptive threshold) |

### Dependency ordering

Must be merged **after PR D** (test imports require the production modules).
Can be opened as a draft immediately so reviewers can see the test coverage.

---

## How to create the branches without redoing work

Because all code already exists on `copilot/issue-38-streaming-discovery-engine`
(or on this branch after the bug fixes were applied), use `git checkout` to
compose each branch without re-writing files:

```bash
# Start from the fixed branch (this PR)
FIXED_SHA=$(git rev-parse HEAD)

# PR A — message_bus.py only
git checkout -b split/pr67-a-core main
git checkout $FIXED_SHA -- backend/app/core/message_bus.py
git commit -m "feat(E1-E3): register scout, triage, hyper_swarm topics in MessageBus"

# PR B — scout framework
git checkout -b split/pr67-b-scout-framework split/pr67-a-core
git checkout $FIXED_SHA -- \
    backend/app/services/scouts/__init__.py \
    backend/app/services/scouts/base.py \
    backend/app/services/scouts/registry.py
git commit -m "feat(E2): BaseScout ABC, DiscoveryPayload, ScoutRegistry"

# PR C — 12 individual scouts
git checkout -b split/pr67-c-scouts split/pr67-b-scout-framework
git checkout $FIXED_SHA -- \
    backend/app/services/scouts/congress.py \
    backend/app/services/scouts/correlation_break.py \
    backend/app/services/scouts/earnings.py \
    backend/app/services/scouts/flow_hunter.py \
    backend/app/services/scouts/gamma.py \
    backend/app/services/scouts/insider.py \
    backend/app/services/scouts/ipo.py \
    backend/app/services/scouts/macro.py \
    backend/app/services/scouts/news.py \
    backend/app/services/scouts/sector_rotation.py \
    backend/app/services/scouts/sentiment.py \
    backend/app/services/scouts/short_squeeze.py
git commit -m "feat(E2): 12 scout agents (flow_hunter, insider, congress, gamma, news, sentiment, macro, earnings, sector_rotation, short_squeeze, ipo, correlation_break)"

# PR D — triage + HyperSwarm wiring + main.py
git checkout -b split/pr67-d-triage split/pr67-c-scouts
git checkout $FIXED_SHA -- \
    backend/app/services/streaming_discovery.py \
    backend/app/services/idea_triage.py \
    backend/app/services/hyper_swarm.py \
    backend/app/services/swarm_spawner.py \
    backend/app/main.py \
    backend/app/modules/ml_engine/artifacts/drift/drift_log.json \
    backend/app/modules/ml_engine/artifacts/drift/reference_stats.json
git commit -m "feat(E1/E3): StreamingDiscoveryEngine, IdeaTriageService, HyperSwarm fix, main.py wiring"

# PR E — tests
git checkout -b split/pr67-e-tests split/pr67-d-triage
git checkout $FIXED_SHA -- \
    backend/tests/test_streaming_discovery.py \
    backend/tests/test_scout_agents.py \
    backend/tests/test_idea_triage.py
git commit -m "test(E1/E2/E3): 134 tests for streaming discovery, scouts, and idea triage"
```

---

## Merge order summary

| Step | PR | Merges into | Prerequisite |
|------|----|-------------|--------------|
| 1 | PR A | `main` | none |
| 2 | PR B | `main` | PR A merged |
| 3 | PR C | `main` | PR B merged |
| 4 | PR D | `main` | PR C merged |
| 5 | PR E | `main` | PR D merged |

---

## Bug fix checklist (all applied on this branch)

- [x] **Fix 1** — `HyperSwarm._escalate()` → `hyper_swarm.escalated` topic (breaks circular loop)
- [x] **Fix 2** — `NewsScout.scout()` → `agg.get_news()` not `agg.get_latest()`
- [x] **Fix 3** — `_streaming_discovery`, `_idea_triage`, `_scout_registry` declared in `main.py` module-level globals
- [x] **Fix 4** — `SwarmSpawner` subscribes to `triage.escalated` + `hyper_swarm.escalated` (not raw `swarm.idea`)
- [x] **Fix 5** — `IdeaTriageService._recent_arrivals` capped at `MAX_ARRIVALS_WINDOW = 2000`
- [x] **Fix 6** — `NewsScout._pending` capped at `MAX_PENDING = 500`
- [x] **Fix 7** — Unused `defaultdict` import removed from `idea_triage.py`
