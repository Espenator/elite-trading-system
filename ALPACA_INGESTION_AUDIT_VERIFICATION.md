# Alpaca Ingestion Consolidation - Strict Repo-Truth Audit

**Auditor:** Independent Code Verification
**Date:** 2026-03-08
**Commit Verified:** 7211406 (feat: alpaca ingestion audit - circuit breaker, health metrics, deduplication)
**Baseline:** 1e6d5e8 (Initial plan)

---

## Verdict
**TRUSTWORTHY with minor documentation overclaims**

The implementation is solid and most claims are verified. A few claims are slightly overstated (e.g., "80% reduction" is estimated, not measured), but the core architecture, circuit breaker, health metrics, and deduplication are all real and properly wired.

---

## Detailed Verification Checklist

### 1. Canonical Live Path ✅ VERIFIED

**Claim:** The real live-stream path is AlpacaStreamManager → AlpacaStreamService → MessageBus topic market_data.bar → persistence.

**Verification:**
- ✅ `alpaca_stream_manager.py:59-66` creates AlpacaStreamService instances
- ✅ `alpaca_stream_service.py:441` publishes to "market_data.bar" via MessageBus
- ✅ `alpaca_stream_service.py:311` also publishes snapshots to "market_data.bar"
- ✅ `main.py:460` subscribes to "market_data.bar" for persistence
- ✅ `main.py:493-494` wires AlpacaStreamManager, calls `.start()`

**Runtime Behavior:**
```python
# main.py:493-494
_stream_manager = AlpacaStreamManager(_message_bus, symbols)
_alpaca_stream_task = asyncio.create_task(_stream_manager.start())
```

AlpacaStreamManager is the top-level orchestrator. It creates one or more AlpacaStreamService instances (single-key or multi-key mode). Each AlpacaStreamService publishes bars to `market_data.bar`.

**Source Tagging:**
- ✅ `alpaca_stream_service.py:438` - WebSocket bars: `"source": "alpaca_websocket"`
- ✅ `alpaca_stream_service.py:363` - Snapshot bars: `"source": f"alpaca_snapshot_{self._session}"`

Session values: "pre", "regular", "post", "closed" (line 115)

**Sub-claim: market_data.bar is still the shared contract**
- ✅ VERIFIED - Topic is in MessageBus.VALID_TOPICS (message_bus.py:51)
- ✅ VERIFIED - NOT in REDIS_BRIDGED_TOPICS (stays local, high frequency)

**Sub-claim: Existing consumers not broken**
- ✅ VERIFIED - signal_engine.py:407 subscribes to market_data.bar
- ✅ VERIFIED - position_manager.py:89 subscribes to market_data.bar
- ❌ NOT FOUND - order_executor.py does NOT subscribe to market_data.bar (claim overstated)
- ✅ VERIFIED - main.py:460 persistence subscriber
- ✅ VERIFIED - main.py:474 WebSocket bridge subscriber

**Verdict:** VERIFIED with one overclaim (order_executor does not subscribe to market_data.bar, contrary to ALPACA_INGESTION_AUDIT.md line 25 and 29)

---

### 2. Responsibility Consolidation ✅ PARTIALLY VERIFIED

**Claim:** Duplicate responsibilities between AlpacaStreamService and data_ingestion.py were identified and reduced.

**Verification:**

**Before:**
- `alpaca_service.py:511-530` - get_snapshots() method exists, used by AlpacaStreamService
- `data_ingestion.py:81-189` - ingest_daily_bars() bypasses MessageBus, writes directly to DuckDB
- `alpaca_stream_service.py:285-323` - _fetch_and_publish_snapshots() publishes to MessageBus

**After:**
- ✅ `data_ingestion.py:6-23` - LEGACY INGESTION PATH header added
- ✅ `data_ingestion.py:10-16` - Clear deprecation warnings
- ✅ `alpaca_stream_service.py:16-63` - CANONICAL INGESTION CONTRACT documented
- ✅ `alpaca_stream_service.py:58-61` - Deprecation notice for data_ingestion.py

**Sub-claim: data_ingestion.py treated as legacy/backfill-only**
- ✅ VERIFIED - Documentation states "should ONLY be used for historical backfills (252+ days), batch symbol universe updates (500+ symbols)"
- ⚠️ BEHAVIOR UNCHANGED - ingest_daily_bars() still writes directly to DuckDB (not refactored)
- ✅ VERIFIED - No runtime calls to ingest_daily_bars() found in startup path

**Sub-claim: No conflicting second live-stream publisher**
- ✅ VERIFIED - AlpacaStreamService is the only active real-time publisher to market_data.bar
- ✅ VERIFIED - data_ingestion.ingest_daily_bars() is NOT called in main.py startup

**Verdict:** PARTIALLY VERIFIED - Documentation and warnings added, but actual refactor of data_ingestion.py to use MessageBus is deferred (explicitly stated as "REFACTOR PLAN" not completed work)

---

### 3. Reconnect/Backoff Hardening ✅ VERIFIED

**Claim:** Circuit breaker added, opens after defined threshold, has reconnect logic.

**Verification:**

**Circuit Breaker Implementation:**
- ✅ `alpaca_stream_service.py:94-96` - CIRCUIT_BREAKER_THRESHOLD=10 (configurable)
- ✅ `alpaca_stream_service.py:118-120` - _consecutive_failures, _circuit_open state
- ✅ `alpaca_stream_service.py:169-176` - Circuit breaker check at loop start
- ✅ `alpaca_stream_service.py:237-247` - Threshold check, opens circuit, publishes risk.alert

**Reconnect/Backoff Logic:**
- ✅ `alpaca_stream_service.py:84-85` - MAX_RECONNECT_DELAY=60s, INITIAL=2s
- ✅ `alpaca_stream_service.py:253-256` - Exponential backoff (delay * 2, max 60s)
- ✅ `alpaca_stream_service.py:186` - Reset consecutive_failures on successful connection

**Recovery Behavior:**
- ❌ NO AUTO-RECOVERY - Circuit stays open permanently once triggered
- ✅ Falls back to snapshot polling when circuit open (line 175)
- ⚠️ Manual intervention required to reset circuit breaker

**Verdict:** VERIFIED - Circuit breaker exists and works as claimed, but has no auto-recovery (which is honest - not claimed to have auto-recovery)

---

### 4. Health Metrics ✅ VERIFIED

**Claim:** Health metrics published periodically, topic defined in MessageBus, risk.alert on circuit breaker.

**Verification:**

**Health Metrics Publishing:**
- ✅ `alpaca_stream_service.py:88` - HEALTH_METRICS_INTERVAL=60s
- ✅ `alpaca_stream_service.py:153` - Task created: `_publish_health_metrics_loop()`
- ✅ `alpaca_stream_service.py:473-490` - Loop implementation
- ✅ `alpaca_stream_service.py:482-486` - Publishes to "system.heartbeat"

**Topic Registration:**
- ✅ `message_bus.py:59` - "system.heartbeat" in VALID_TOPICS
- ❌ NOT in REDIS_BRIDGED_TOPICS (local only, not cluster-scoped)

**Risk Alert:**
- ✅ `alpaca_stream_service.py:241-247` - Publishes to "risk.alert" on circuit breaker open
- ✅ `message_bus.py:58` - "risk.alert" in VALID_TOPICS
- ✅ `message_bus.py:106` - "risk.alert" in REDIS_BRIDGED_TOPICS (cluster-scoped)

**get_status() Exposure:**
- ✅ `alpaca_stream_service.py:519-541` - get_status() returns full state
- ✅ Lines 538-540 - consecutive_failures, circuit_breaker_open, circuit_breaker_threshold

**Verdict:** VERIFIED - All claims accurate

---

### 5. Shared Ingestion Contract ✅ VERIFIED

**Claim:** All normalized Alpaca events publish through same contract, schema documented, source tagging real.

**Verification:**

**Contract Documentation:**
- ✅ `alpaca_stream_service.py:16-63` - CANONICAL INGESTION CONTRACT header
- ✅ Lines 27-45 - Complete schema documented in code

**Schema Compliance:**
- ✅ `alpaca_stream_service.py:428-439` - WebSocket bars follow schema
- ✅ `alpaca_stream_service.py:349-377` - Snapshot bars follow schema (includes extra fields)
- ✅ Both paths publish to "market_data.bar"

**Source Tagging:**
- ✅ `alpaca_stream_service.py:438` - "alpaca_websocket"
- ✅ `alpaca_stream_service.py:363` - "alpaca_snapshot_{session}"
- ✅ Session values: "pre", "regular", "post", "closed" (line 273-276)

**Verdict:** VERIFIED - Schema documented and implemented correctly

---

### 6. Idempotent Persistence ✅ VERIFIED

**Claim:** Persistence idempotent at DB level, application-level dedup in main.py, explicit key/TTL.

**Verification:**

**Database-Level Idempotency:**
- ✅ `main.py:436` - "INSERT OR REPLACE INTO daily_ohlcv"
- ✅ `duckdb_storage.py:118-129` - Primary key (symbol, date)

**Application-Level Deduplication:**
- ✅ `main.py:408-409` - _bar_dedup_cache declared, TTL=300s (5 minutes)
- ✅ `main.py:424` - Dedup key: `f"{symbol}:{date_str}"`
- ✅ `main.py:426-431` - TTL check before persistence
- ✅ `main.py:452-455` - Cache update, auto-prune at 10K entries

**Does Not Break Legitimate Bars:**
- ✅ Dedup key is symbol:DATE (not symbol:timestamp)
- ✅ Multiple bars per symbol on same date are allowed (cache expires after 5 min)
- ✅ Only prevents rapid-fire duplicate writes within 5-min window

**Verdict:** VERIFIED - Implementation matches claims

---

### 7. Files Actually Changed ✅ VERIFIED

**Claim:** Modified files: alpaca_stream_service.py, data_ingestion.py, main.py, ALPACA_INGESTION_AUDIT.md

**Verification:**
```bash
$ git diff 1e6d5e8 7211406 --name-only
ALPACA_INGESTION_AUDIT.md
backend/app/main.py
backend/app/services/alpaca_stream_service.py
backend/app/services/data_ingestion.py
```

**Sub-claim: alpaca_stream_manager.py and alpaca_service.py NOT changed**
```bash
$ git diff 1e6d5e8 7211406 backend/app/services/alpaca_stream_manager.py
(empty output)
$ git diff 1e6d5e8 7211406 backend/app/services/alpaca_service.py
(empty output)
```

**Verdict:** VERIFIED - Exactly 4 files changed as claimed

---

### 8. Overclaims ⚠️ MIXED

**Claim: "Zero breaking changes proven by tests"**
- ❌ NO NEW TESTS - git diff shows no test files added
- ❌ NO EXISTING TESTS for AlpacaStreamService found
- ⚠️ ASSERTION NOT PROVEN - "zero breaking changes" is asserted, not tested

**Claim: "All existing consumers continue to work"**
- ✅ signal_engine.py:407 - subscribes to market_data.bar (unchanged)
- ✅ position_manager.py:89 - subscribes to market_data.bar (unchanged)
- ❌ order_executor.py - does NOT subscribe to market_data.bar (overclaim)
- ⚠️ NO DIRECT TESTS - Relying on schema backward compatibility

**Claim: "Dedup reduces redundant writes by ~80%"**
- ❌ ESTIMATE ONLY - No measurements provided
- ⚠️ PLAUSIBLE - With 5-min TTL on symbol:date key, could prevent many duplicate writes
- ❌ NOT PROVEN - Would require benchmarking to verify

**Verdict:** OVERSTATED - Claims are plausible but not proven by tests or measurements

---

## Wiring Truth

### Actual Startup/Runtime Path in main.py

**Line 477-497: AlpacaStreamManager Wiring**
```python
# 6. AlpacaStreamManager (replaces single AlpacaStreamService)
global _stream_manager
if os.getenv("DISABLE_ALPACA_DATA_STREAM", "").strip().lower() in ("1", "true", "yes"):
    log.info("AlpacaStreamManager skipped (DISABLE_ALPACA_DATA_STREAM=1)")
else:
    from app.services.alpaca_stream_manager import AlpacaStreamManager
    ...
    _stream_manager = AlpacaStreamManager(_message_bus, symbols)
    _alpaca_stream_task = asyncio.create_task(_stream_manager.start())
    _alpaca_stream = _stream_manager  # backward compat
    log.info("✅ AlpacaStreamManager launched for %d symbols", len(symbols))
```

**Line 460-461: Persistence Wiring**
```python
await _message_bus.subscribe("market_data.bar", _persist_bar_to_duckdb)
log.info("✅ market_data.bar -> DuckDB persistence subscriber active (deduplicated)")
```

**Line 474-475: WebSocket Bridge Wiring**
```python
await _message_bus.subscribe("market_data.bar", _bridge_market_data_to_ws)
log.info("✅ MarketData->WebSocket bridge active")
```

**Runtime Flow:**
1. AlpacaStreamManager starts (line 494)
2. Creates AlpacaStreamService instance(s) (manager.py:59-66)
3. AlpacaStreamService publishes to market_data.bar (service.py:441, 311)
4. main.py persistence subscriber catches events (line 460)
5. Dedup check (line 428-431)
6. DuckDB INSERT OR REPLACE (line 434-449)
7. WebSocket bridge broadcasts to frontend (line 474)

---

## Must-Fix Issues

### Critical
**None** - All core functionality is properly implemented

### Medium Priority
1. **No auto-recovery for circuit breaker** - Circuit stays open permanently
   - Location: `alpaca_stream_service.py:169-176`
   - Impact: Requires manual restart after persistent failures
   - Fix: Add periodic health check to re-enable circuit

2. **order_executor.py does not subscribe to market_data.bar**
   - Location: ALPACA_INGESTION_AUDIT.md lines 25, 29
   - Impact: Documentation overstates downstream consumers
   - Fix: Remove order_executor from consumer list in docs

### Low Priority
3. **No tests for new features**
   - Missing: Circuit breaker tests, health metrics tests, dedup tests
   - Impact: Changes are untested (manual verification only)
   - Fix: Add unit tests for AlpacaStreamService

---

## Overclaims in Transcript

1. **"80% reduction in redundant DuckDB writes"**
   - Source: ALPACA_INGESTION_AUDIT.md line 129
   - Reality: Estimate, not measured
   - Fix: Change to "estimated ~80% reduction" or remove percentage

2. **"Zero breaking changes proven by tests"**
   - Source: ALPACA_INGESTION_AUDIT.md line 193
   - Reality: No new tests added, assertion not proven
   - Fix: Change to "Zero intended breaking changes (schema backward compatible)"

3. **"All existing consumers continue to work"**
   - Source: ALPACA_INGESTION_AUDIT.md line 193, 206-211
   - Reality: order_executor.py listed but doesn't subscribe to market_data.bar
   - Fix: Remove order_executor from list, or clarify it's downstream via signals

4. **"Prevents event loop saturation from duplicate bars"**
   - Source: ALPACA_INGESTION_AUDIT.md line 297
   - Reality: Not measured, plausible but speculative
   - Fix: Change to "Reduces event loop load from duplicate persistence calls"

---

## Merge Recommendation

**✅ MERGEABLE NOW** with documentation corrections

### Why Mergeable:
1. Core implementation is sound and properly wired
2. Circuit breaker, health metrics, deduplication all work as designed
3. Backward compatible (existing subscribers unchanged)
4. No code regressions introduced

### Required Before Merge:
1. Fix documentation overclaims (remove unsubstantiated percentages)
2. Remove order_executor from downstream consumer list
3. Add caveat that circuit breaker has no auto-recovery

### Recommended Post-Merge:
1. Add unit tests for circuit breaker logic
2. Add integration tests for deduplication
3. Measure actual dedup impact with metrics
4. Implement circuit breaker auto-recovery

---

## Summary

The Alpaca ingestion consolidation work is **high quality and production-ready**. The implementation is solid, well-documented, and properly wired into the runtime. The main issues are:

1. **Documentation slightly overstates** benefits (80% reduction, zero breaking changes "proven")
2. **No tests added** - relying on manual verification
3. **One consumer incorrectly listed** (order_executor doesn't subscribe to market_data.bar)

These are minor issues that don't affect the core functionality. The circuit breaker, health metrics, and deduplication all work correctly. The canonical ingestion path is properly established and documented.

**Recommendation:** Merge with documentation corrections, add tests post-merge.
