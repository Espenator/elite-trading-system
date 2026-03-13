# Cursor Agent Prompt — Fix Signals, WebSocket, and API Security

> Copy everything below the line into Cursor as a single prompt.

---

Read these files first (in order): `CLAUDE.md`, `project_state.md`, `PLAN.md`, `PATH-STANDARD.md`

## Mission

You are fixing a cross-layer production blocker in Embodier Trader v5.0.0: signals are generated but not consistently reaching the frontend dashboard, WebSocket channel contracts are inconsistent across backend/frontend, and two API surfaces are missing standard auth enforcement.

Your goal is to complete all 9 fixes below in one session, validate end-to-end behavior, and leave the system in a consistent, test-passing state.

## System Context

- Repo: `elite-trading-system` (FastAPI backend + React 18/Vite frontend)
- Trade pipeline: `signal.generated` -> `CouncilGate` -> `council.verdict` -> `OrderExecutor` -> WebSocket -> frontend
- Current failure pattern:
  - Signal score gating mismatch causes under-triggering
  - WebSocket bridge publishes to wrong channel key
  - Channel registries drifted across 3 files
  - Some system/metrics endpoints bypass standard auth dependency

## Scope

Implement exactly these 9 fixes across 3 workstreams:

- Workstream 1 (Signal Pipeline): 4 fixes
- Workstream 2 (WebSocket): 3 fixes
- Workstream 3 (API Security & Reliability): 2 fixes

Do not add unrelated refactors.

## Files to Modify (Primary)

- `backend/app/services/signal_engine.py`
- `backend/app/council/runner.py`
- `backend/app/services/scouts/turbo_scanner.py` (or exact TurboScanner publish location if different)
- `backend/app/services/unusual_whales_service.py`
- `backend/app/main.py`
- `backend/app/websocket_manager.py`
- `frontend-v2/src/config/api.js`
- `backend/app/api/v1/system.py`
- `backend/app/api/v1/metrics_api.py`

## Workstream 1 - Signal Pipeline (4 fixes)

### 1) Lower hardcoded signal threshold to avoid pre-filtering profitable regimes

**Severity:** HIGH  
**Issue:** `SIGNAL_THRESHOLD` in signal engine is hardcoded at 65, while `CouncilGate` already applies regime-adaptive thresholds (55/65/75). This over-filters in BULLISH contexts.

**File:** `backend/app/services/signal_engine.py` (around line ~502)

**Before**

```python
SIGNAL_THRESHOLD = 65
```

**After**

```python
SIGNAL_THRESHOLD = 50
```

**Notes**

- Keep thresholding in signal engine permissive.
- Let `CouncilGate` remain the canonical regime-aware gate.

---

### 2) Ensure there is no active duplicate `council.verdict` publication in runner

**Severity:** HIGH  
**Issue:** Historical duplicate publish (Issue #46) caused double downstream execution/notification paths.

**File:** `backend/app/council/runner.py` (around line ~856)

**Action**

- Verify whether `runner.py` still contains an active `publish("council.verdict", ...)`.
- If active, remove or comment it out so only `CouncilGate` publishes the verdict event.

**Expected state**

- Exactly one canonical publication site for `council.verdict`.
- `runner.py` computes and returns verdict; `council_gate.py` handles publication.

---

### 3) Fix TurboScanner score scale mismatch (0.0-1.0 vs 0-100)

**Severity:** HIGH  
**Issue:** TurboScanner publishes normalized confidence (0-1), but downstream expects signal score in 0-100 range.

**File:** TurboScanner publish site (expected in `backend/app/services/scouts/turbo_scanner.py` or nearest signal publisher)

**Before (pattern)**

```python
payload = {
    "symbol": symbol,
    "score": score,  # 0.0-1.0
}
await message_bus.publish("signal.generated", payload)
```

**After**

```python
payload = {
    "symbol": symbol,
    "score": score * 100.0,  # convert to 0-100
}
await message_bus.publish("signal.generated", payload)
```

**Guardrails**

- If some publishers already emit 0-100, do not double-scale.
- Apply conversion only where score is truly normalized.

---

### 4) Wire UnusualWhales service outputs to MessageBus

**Severity:** MEDIUM  
**Issue:** UW options flow data exists but does not publish reliably to event bus (`Issue #47`), reducing signal enrichment.

**File:** `backend/app/services/unusual_whales_service.py`

**Action**

- Add publish calls for relevant data outputs (for example options flow snapshots/updates).
- Use existing topic conventions in the codebase (do not invent incompatible topic names).

**Suggested pattern**

```python
if self.message_bus and flow_items:
    await self.message_bus.publish(
        "data.options_flow",
        {
            "source": "unusual_whales",
            "count": len(flow_items),
            "items": flow_items,
        },
    )
```

**Requirements**

- Must fail gracefully if MessageBus unavailable.
- Must not break existing return values.

## Workstream 2 - WebSocket Contract Consistency (3 fixes)

### 5) Fix singular/plural bridge mismatch: `signal` -> `signals`

**Severity:** CRITICAL  
**Issue:** Backend bridge broadcasts to `signal` while frontend subscribes to `signals`. This drops live signal updates from dashboard.

**File:** `backend/app/main.py` (around line ~494)

**Before**

```python
await broadcast_ws("signal", payload)
```

**After**

```python
await broadcast_ws("signals", payload)
```

---

### 6) Unify WS channel registries across backend + frontend

**Severity:** HIGH  
**Issue:** Channel lists are out of sync across:

- `backend/app/websocket_manager.py` (`WS_ALLOWED_CHANNELS`)
- `backend/app/main.py` (`_VALID_WS_CHANNELS`)
- `frontend-v2/src/config/api.js` (`WS_CHANNELS`)

**Action**

1. Determine canonical frontend subscription set (`WS_CHANNELS` values).
2. Ensure `_VALID_WS_CHANNELS` in backend is a superset of frontend channels.
3. Ensure websocket manager allows all intended channels and does not reject valid frontend subscriptions.
4. Keep naming consistent across all three locations.

**Rule**

- `_VALID_WS_CHANNELS` must be superset of frontend `WS_CHANNELS` values.

---

### 7) Standardize `datasources` alias handling

**Severity:** LOW  
**Issue:** Inconsistent naming (`datasources` vs `data_sources`) causes brittle subscriptions.

**Target contract**

- Frontend key: `datasources`
- Wire value (transport/backend topic): `data_sources`
- Backend accepts both `datasources` and `data_sources` as valid input aliases

**Files**

- `frontend-v2/src/config/api.js`
- `backend/app/main.py`
- `backend/app/websocket_manager.py`

**Action**

- Preserve backwards compatibility while converging on canonical wire value.
- Add/keep a simple alias map in backend if needed.

## Workstream 3 - API Security & Reliability (2 fixes)

### 8) Protect DLQ replay/clear system endpoints with standard auth dependency

**Severity:** HIGH  
**Issue:** DLQ mutation endpoints are currently unauthenticated.

**File:** `backend/app/api/v1/system.py` (around lines ~272, ~285)

**Before (pattern)**

```python
@router.post("/dlq/replay")
async def replay_dlq(...):
    ...

@router.post("/dlq/clear")
async def clear_dlq(...):
    ...
```

**After**

```python
@router.post("/dlq/replay", dependencies=[Depends(require_auth)])
async def replay_dlq(...):
    ...

@router.post("/dlq/clear", dependencies=[Depends(require_auth)])
async def clear_dlq(...):
    ...
```

---

### 9) Replace custom metrics auth token logic with standard `require_auth`

**Severity:** MEDIUM  
**Issue:** `metrics_api.py` uses custom `TRADING_AUTH_TOKEN` handling, bypassing standard centralized auth policy.

**File:** `backend/app/api/v1/metrics_api.py` (around line ~283)

**Action**

- Remove endpoint-local custom token checks.
- Apply the standard `require_auth` dependency consistent with other protected routes.

**Before (pattern)**

```python
token = os.getenv("TRADING_AUTH_TOKEN")
if supplied != token:
    raise HTTPException(status_code=401, detail="Unauthorized")
```

**After (pattern)**

```python
@router.get("/...", dependencies=[Depends(require_auth)])
async def protected_metrics(...):
    ...
```

## Implementation Order (Required)

Execute in this order to reduce regressions:

1. Workstream 1 (signals/data publication)
2. Workstream 2 (WebSocket channel contract)
3. Workstream 3 (auth hardening)
4. Verification and tests

## Verification Checklist

Run all checks and include outputs/results in your final summary.

### A) Targeted code searches

1. Search for singular channel broadcast:

```bash
rg "broadcast_ws\\(\"signal\"" backend/app/main.py
```

Expected: no active singular usage for signal stream bridge.

2. Confirm plural channel usage exists:

```bash
rg "broadcast_ws\\(\"signals\"" backend/app/main.py
```

Expected: active bridge call found.

3. Confirm no active runner publication for `council.verdict`:

```bash
rg "council\\.verdict" backend/app/council/runner.py
```

Expected: no active publish call in runner (comments/documentation are okay).

4. Confirm threshold value:

```bash
rg "SIGNAL_THRESHOLD\\s*=\\s*" backend/app/services/signal_engine.py
```

Expected: value is 50.

5. Confirm auth on DLQ endpoints:

```bash
rg "dlq/(replay|clear)|require_auth|Depends" backend/app/api/v1/system.py
```

Expected: replay + clear endpoints include `dependencies=[Depends(require_auth)]`.

6. Confirm metrics auth standardization:

```bash
rg "TRADING_AUTH_TOKEN|require_auth|Depends" backend/app/api/v1/metrics_api.py
```

Expected: no custom token logic; standard `require_auth` dependency used.

### B) WebSocket contract checks

Validate channel alignment:

- Extract frontend `WS_CHANNELS` values from `frontend-v2/src/config/api.js`
- Extract backend `_VALID_WS_CHANNELS` from `backend/app/main.py`
- Confirm all frontend values are present in backend valid channels set
- Confirm websocket manager allow-list includes these channels

### C) Tests

Run backend tests:

```bash
cd backend
python -m pytest --tb=short -q
```

Expected: existing test suite passes.

## Completion Criteria (Definition of Done)

All are required:

1. All 9 fixes implemented.
2. Signals propagate to frontend via `signals` channel.
3. WebSocket channel naming is consistent and alias-safe (`datasources` -> `data_sources`).
4. DLQ replay/clear endpoints require auth.
5. Metrics endpoint auth uses `require_auth` standard path.
6. No active duplicate `council.verdict` publish in `runner.py`.
7. `SIGNAL_THRESHOLD` is 50 in signal engine.
8. Backend tests pass.
9. Final report lists exact files changed and concise rationale per file.

## Constraints

1. Do not modify council DAG stage order.
2. Do not remove passing tests.
3. Do not add mock data.
4. Do not add new secrets or hardcoded keys.
5. Keep changes minimal and surgical.
6. Preserve backward compatibility where aliases are already in use.

## Final Output Format

At the end, provide:

1. `Files changed` list
2. `Fixes completed (1-9)` checklist
3. `Verification results` (search checks + pytest result)
4. `Any residual risks` (if any)

