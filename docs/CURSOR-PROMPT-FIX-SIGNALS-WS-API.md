# Cursor Agent Prompt — Fix Signals, WebSocket & API Pipeline

> Copy everything below the line into Cursor as a single prompt.

---

Read these files first (in order): `CLAUDE.md`, `project_state.md`, `PLAN.md`

## Mission

You are a **senior backend engineer** performing targeted fixes to three interconnected subsystems in the Embodier Trader pipeline: **Signal generation**, **WebSocket delivery**, and **API security**. These bugs prevent the trading pipeline from working end-to-end — signals are generated but never reach the frontend, and API endpoints have security gaps.

**Output**: Working code changes across 5-7 files. Every change includes a before/after diff. Run tests after each workstream.

## System Context

- **Repo**: `elite-trading-system` — Python 3.11 FastAPI backend, React 18/Vite frontend
- **Pipeline**: `AlpacaStream → SignalEngine → CouncilGate → 35-agent council → OrderExecutor → WebSocket → Frontend`
- **The problem**: Signals score ≥65 but the WebSocket bridge broadcasts to `"signal"` (singular) while the frontend subscribes to `"signals"` (plural). Signals silently vanish. Additionally, the SignalEngine filters signals at 65 before CouncilGate can apply its regime-adaptive thresholds (55 in BULLISH), and API endpoints lack auth.

## Pre-Flight Checks

Before making any changes, verify these issues still exist:

```bash
# 1. Confirm signal→signals mismatch (should find "signal" singular in broadcast)
grep -n 'broadcast_ws("signal"' backend/app/main.py

# 2. Confirm SIGNAL_THRESHOLD is still 65
grep -n 'SIGNAL_THRESHOLD' backend/app/services/signal_engine.py

# 3. Confirm DLQ endpoints lack auth
grep -n 'require_auth\|Depends' backend/app/api/v1/system.py | grep -i dlq

# 4. Confirm channel registry mismatch
grep -n '_VALID_WS_CHANNELS' backend/app/main.py
grep -n 'WS_ALLOWED_CHANNELS' backend/app/websocket_manager.py
```

---

## WORKSTREAM 1: Signal Pipeline (2 fixes)

### FIX 1.1 — Lower SignalEngine threshold to let CouncilGate do regime filtering

**Severity**: HIGH — Filters 20-40% of profitable signals in BULLISH regimes

**Problem**: `EventDrivenSignalEngine` has `SIGNAL_THRESHOLD = 65` hardcoded. But `CouncilGate` already applies regime-adaptive thresholds:

```python
# council_gate.py lines 30-41 — the REAL filtering
_REGIME_GATE_THRESHOLDS = {
    "BULLISH": 55.0,   # ← Signals 55-65 never reach here because engine blocks them
    "RISK_ON": 58.0,
    "NEUTRAL": 65.0,
    "RISK_OFF": 70.0,
    "BEARISH": 75.0,
    "CRISIS": 75.0,
}
```

**File**: `backend/app/services/signal_engine.py`

**Line 502 — BEFORE:**
```python
SIGNAL_THRESHOLD = 65  # Minimum score to publish a signal
```

**Line 502 — AFTER:**
```python
SIGNAL_THRESHOLD = 50  # Pre-filter; real regime-adaptive filtering in CouncilGate (55-75)
```

**Why 50 (not lower)**: Scores below 50 are noise (base score starts at 50.0 with zero indicators). Anything above 50 means at least one indicator fired. CouncilGate then applies the real regime-adaptive threshold (55/58/65/70/75).

**Verification**: `grep -n SIGNAL_THRESHOLD backend/app/services/signal_engine.py` should show `50`.

---

### FIX 1.2 — Wire UnusualWhales MessageBus events to council agents

**Severity**: MEDIUM — Options flow data published but zero subscribers (GitHub Issue #47)

**Problem**: `unusual_whales_service.py` publishes to 4 MessageBus topics (`unusual_whales.flow`, `unusual_whales.congress`, `unusual_whales.insider`, `unusual_whales.darkpool`) but NO agents subscribe to them. The council agents (dark_pool_agent, insider_agent, congressional_agent, flow_perception_agent) fetch data directly from the service instead of listening to MessageBus events.

**File**: `backend/app/main.py` — Add subscriptions in the lifespan startup, after the existing WebSocket bridges (around line 730).

**AFTER the existing bridge registrations (around line 730), ADD:**

```python
    # 5b. Wire UnusualWhales MessageBus → council agent caches (Issue #47)
    # Agents still do direct queries, but this enables real-time cache warming
    # so council evaluations have fresh data without blocking on API calls.
    try:
        from app.services.unusual_whales_service import UnusualWhalesService
        _uw_svc = UnusualWhalesService()

        async def _cache_uw_flow(data):
            """Cache options flow alerts for flow_perception + dark_pool agents."""
            try:
                _uw_svc._last_flow_cache = data.get("alerts", [])
                _uw_svc._last_flow_ts = time.time()
            except Exception:
                pass

        async def _cache_uw_congress(data):
            """Cache congressional trades for congressional_agent."""
            try:
                _uw_svc._last_congress_cache = data.get("trades", [])
                _uw_svc._last_congress_ts = time.time()
            except Exception:
                pass

        await _message_bus.subscribe("unusual_whales.flow", _cache_uw_flow)
        await _message_bus.subscribe("unusual_whales.congress", _cache_uw_congress)
        log.info("✅ UnusualWhales→Cache bridge active (Issue #47)")
    except Exception as e:
        log.warning("UnusualWhales cache bridge skipped: %s", e)
```

**Then update the agents** (`flow_perception_agent.py`, `congressional_agent.py`) to check the cache before making API calls:

```python
# In evaluate(), before the API call:
uw_svc = UnusualWhalesService()
cached = getattr(uw_svc, '_last_flow_cache', None)
cache_age = time.time() - getattr(uw_svc, '_last_flow_ts', 0)
if cached and cache_age < 60:  # Use cache if fresh (<60s)
    flow_data = cached
else:
    flow_data = await uw_svc.get_flow_alerts(...)  # Existing API call
```

**NOTE**: This is a cache-warming pattern, not a full rewrite. The agents still work without the cache; they just make fewer API calls when data is fresh.

---

### ALREADY FIXED (verify, do not re-fix)

- **Issue #45 (TurboScanner scale)**: Already fixed — `turbo_scanner.py:844` multiplies `signal.score * 100`
- **Issue #46 (Double council.verdict)**: Already fixed — `runner.py:856-858` has the duplicate publish commented out with a NOTE explaining council_gate.py is the canonical publisher

---

## WORKSTREAM 2: WebSocket Pipeline (2 fixes)

### FIX 2.1 — Fix signal channel name: "signal" → "signals"

**Severity**: CRITICAL — Signals never reach the frontend dashboard

**Problem**: The WebSocket bridge in `main.py` broadcasts to channel `"signal"` (singular), but the frontend subscribes to `"signals"` (plural) via `WS_CHANNELS.signals`. Result: signals are generated, scored, council-evaluated, but the frontend never receives them.

**File**: `backend/app/main.py`

**Line 494 — BEFORE:**
```python
            await broadcast_ws("signal", {"type": "new_signal", "signal": signal_data})
```

**Line 494 — AFTER:**
```python
            await broadcast_ws("signals", {"type": "new_signal", "signal": signal_data})
```

**Verification**: `grep -rn 'broadcast_ws("signal"' backend/app/main.py` should return ZERO results (only `"signals"` plural).

---

### FIX 2.2 — Unify WebSocket channel registries across 3 files

**Severity**: HIGH — Channel mismatches cause silent subscription failures

**Problem**: Three files define allowed WebSocket channels, but they disagree:

| File | Location | Count | Missing vs Frontend |
|------|----------|-------|-------------------|
| `websocket_manager.py:18` | `WS_ALLOWED_CHANNELS` | 25 | Has extras: `health`, `market_data`, `outcomes`, `system` |
| `main.py:1776` | `_VALID_WS_CHANNELS` | 21 | Missing: `health`, `market_data`, `outcomes`, `system`, `datasources` |
| `api.js:268` | `WS_CHANNELS` | 16 | Source of truth for frontend needs |

The `_VALID_WS_CHANNELS` in `main.py` must be a **superset** of both `WS_ALLOWED_CHANNELS` and frontend `WS_CHANNELS` values.

**File**: `backend/app/main.py`

**Lines 1776-1781 — BEFORE:**
```python
_VALID_WS_CHANNELS = frozenset({
    "signal", "signals", "order", "council", "council_verdict",
    "risk", "swarm", "kelly", "market", "macro", "blackboard",
    "alerts", "performance", "agents", "data_sources", "trades",
    "logs", "sentiment", "alignment", "homeostasis", "circuit_breaker",
})
```

**Lines 1776-1783 — AFTER:**
```python
_VALID_WS_CHANNELS = frozenset({
    # Frontend channels (must match WS_CHANNELS values in frontend-v2/src/config/api.js)
    "signals", "order", "council", "council_verdict", "risk", "swarm",
    "kelly", "market", "macro", "agents", "data_sources", "trades",
    "logs", "sentiment", "alignment", "homeostasis", "circuit_breaker",
    # Backend-only channels (server-side publishing, no frontend subscriber yet)
    "health", "market_data", "outcomes", "system", "blackboard",
    "performance", "alerts", "datasources",
})
```

**Changes**:
- Removed `"signal"` (singular) — only `"signals"` is correct
- Added `"health"`, `"market_data"`, `"outcomes"`, `"system"`, `"datasources"` from `WS_ALLOWED_CHANNELS`
- Organized with comments for maintainability

**Also update `websocket_manager.py`** to keep them in sync:

**File**: `backend/app/websocket_manager.py`

**Lines 18-26 — BEFORE:**
```python
WS_ALLOWED_CHANNELS: Set[str] = {
    # Core trading channels
    "order", "risk", "kelly", "signals", "council", "health",
    "market_data", "alerts", "outcomes", "system",
    # Frontend dashboard channels (must match frontend WS_CHANNELS in config/api.js)
    "agents", "data_sources", "datasources", "trades", "logs",
    "sentiment", "alignment", "council_verdict",
    "homeostasis", "circuit_breaker", "swarm", "macro", "market",
}
```

**Lines 18-28 — AFTER:**
```python
WS_ALLOWED_CHANNELS: Set[str] = {
    # Frontend channels (match WS_CHANNELS values in frontend-v2/src/config/api.js)
    "signals", "order", "council", "council_verdict", "risk", "swarm",
    "kelly", "market", "macro", "agents", "data_sources", "trades",
    "logs", "sentiment", "alignment", "homeostasis", "circuit_breaker",
    # Backend-only channels (server-side publishing)
    "health", "market_data", "outcomes", "system", "blackboard",
    "performance", "alerts", "datasources",
}
```

**Verification**: The union of both sets should be identical. Run:
```bash
python3 -c "
fe = {'signals','order','council','council_verdict','risk','swarm','kelly','market','macro','agents','data_sources','trades','logs','sentiment','alignment','homeostasis','circuit_breaker'}
be = {'health','market_data','outcomes','system','blackboard','performance','alerts','datasources'}
print('Frontend channels:', len(fe))
print('Backend-only channels:', len(be))
print('Total:', len(fe | be))
"
```

---

## WORKSTREAM 3: API Security (2 fixes)

### FIX 3.1 — Add auth to DLQ replay/clear endpoints

**Severity**: HIGH (SECURITY) — Unauthenticated endpoints allow message replay and queue clearing

**Problem**: `POST /api/v1/system/dlq/replay` and `DELETE /api/v1/system/dlq` have no `require_auth` dependency. An attacker could replay malicious signals or destroy the audit trail.

**File**: `backend/app/api/v1/system.py`

**Line 272 — BEFORE:**
```python
@router.post("/dlq/replay")
async def dlq_replay(topic: str = None, limit: int = 50):
```

**Line 272 — AFTER:**
```python
@router.post("/dlq/replay", dependencies=[Depends(require_auth)])
async def dlq_replay(topic: str = None, limit: int = 50):
```

**Line 285 — BEFORE:**
```python
@router.delete("/dlq")
async def dlq_clear():
```

**Line 285 — AFTER:**
```python
@router.delete("/dlq", dependencies=[Depends(require_auth)])
async def dlq_clear():
```

**Also ensure the import exists** at the top of the file:
```python
from fastapi import Depends
from app.core.security import require_auth
```

**Verification**: `grep -A1 'dlq/replay\|/dlq"' backend/app/api/v1/system.py` should show `require_auth` on both endpoints.

---

### FIX 3.2 — Standardize auth on metrics WS circuit breaker reset

**Severity**: MEDIUM — Uses non-standard auth mechanism

**Problem**: `POST /api/v1/metrics/ws-circuit-breaker/reset` in `metrics_api.py` has no `require_auth` dependency. It's a state-changing endpoint that resets WebSocket circuit breakers.

**File**: `backend/app/api/v1/metrics_api.py`

**Line 283 — BEFORE:**
```python
@router.post("/ws-circuit-breaker/reset")
def reset_ws_circuit_breaker():
```

**Line 283 — AFTER:**
```python
@router.post("/ws-circuit-breaker/reset", dependencies=[Depends(require_auth)])
def reset_ws_circuit_breaker():
```

**Ensure the import exists** at the top of the file:
```python
from fastapi import Depends
from app.core.security import require_auth
```

**Verification**: `grep -B1 'ws-circuit-breaker' backend/app/api/v1/metrics_api.py` should show `require_auth`.

---

## Verification Checklist

After all fixes, run these checks:

```bash
# 1. Run tests — must all pass
cd backend && python -m pytest --tb=short -q

# 2. Verify signal channel fix
grep -rn 'broadcast_ws("signal"' backend/app/main.py
# Expected: NO results (only "signals" plural should exist)

# 3. Verify threshold change
grep -n 'SIGNAL_THRESHOLD' backend/app/services/signal_engine.py
# Expected: SIGNAL_THRESHOLD = 50

# 4. Verify channel registries match
grep -A10 '_VALID_WS_CHANNELS' backend/app/main.py
grep -A10 'WS_ALLOWED_CHANNELS' backend/app/websocket_manager.py
# Expected: Both contain same channels, "signal" (singular) removed

# 5. Verify auth on DLQ endpoints
grep -B1 'dlq_replay\|dlq_clear' backend/app/api/v1/system.py
# Expected: Both have require_auth

# 6. Verify auth on metrics endpoint
grep -B1 'ws-circuit-breaker' backend/app/api/v1/metrics_api.py
# Expected: Has require_auth

# 7. Quick smoke test (if backend is running)
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

## Summary of Changes

| # | File | Change | Lines |
|---|------|--------|-------|
| 1.1 | `services/signal_engine.py` | SIGNAL_THRESHOLD 65→50 | 502 |
| 1.2 | `main.py` + 2 agent files | Wire UW cache bridge + agent cache check | ~730 (new) |
| 2.1 | `main.py` | broadcast_ws `"signal"` → `"signals"` | 494 |
| 2.2 | `main.py` + `websocket_manager.py` | Unify channel registries, remove `"signal"` singular | 1776, 18 |
| 3.1 | `api/v1/system.py` | Add `require_auth` to DLQ endpoints | 272, 285 |
| 3.2 | `api/v1/metrics_api.py` | Add `require_auth` to WS circuit breaker reset | 283 |
| 4.1 | `main.py` | Fix gate_threshold default `"0.65"` → `"65.0"` | 422 |
| 4.2 | `main.py` | Fix fallback direction `"label"` → `"direction"` | 441 |

**Total files modified**: 5-7
**Risk**: Low — all changes are additive (lowering threshold, adding auth, fixing channel names)
**Rollback**: Git revert on single commit

## BONUS FIXES (Quick Wins Found During Investigation)

### FIX 4.1 — CouncilGate threshold env var uses 0-1 scale (noisy warning on every startup)

**File**: `backend/app/main.py`

**Line 422 — BEFORE:**
```python
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "0.65")),
```

**Line 422 — AFTER:**
```python
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "65.0")),
```

**Why**: `coerce_gate_threshold_0_100()` in `core/score_semantics.py` detects 0-1 values and auto-scales to 0-100, but logs a warning every startup. Using `65.0` directly avoids the noisy warning.

### FIX 4.2 — Fallback verdict uses `label` as direction (wrong field)

**File**: `backend/app/main.py`

**Line 441 — BEFORE:**
```python
                "final_direction": signal_data.get("label", "long"),
```

**Line 441 — AFTER:**
```python
                "final_direction": signal_data.get("direction", "buy"),
```

**Why**: When CouncilGate is disabled, the fallback converts signals to verdicts. But `signal_data["label"]` contains strings like `"Bull candle"` or `"scanner_momentum"`, not `"buy"`/`"sell"`. The `direction` field is what contains the actual trade direction. Using `"label"` would cause OrderExecutor to receive nonsensical directions.

---

## Already Fixed (Do Not Re-Fix)

These GitHub issues were found to be already resolved during investigation:

- **Issue #45 (TurboScanner scale mismatch)**: Fixed at `turbo_scanner.py:844` — `signal.score * 100`
- **Issue #46 (Double council.verdict)**: Fixed at `runner.py:856-858` — duplicate publish commented out, `council_gate.py` is canonical publisher
