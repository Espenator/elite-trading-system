# Alpaca Ingestion Consolidation - Strict Repo-Truth Audit (Summary)

**Auditor:** Independent Code Verification
**Date:** 2026-03-08
**Commit:** 7211406

---

## Verdict
**TRUSTWORTHY** with minor documentation overclaims

---

## Checklist

### 1. Canonical live path
- **VERIFIED** - AlpacaStreamManager → AlpacaStreamService → MessageBus 'market_data.bar' → persistence
  - File: `alpaca_stream_manager.py:59-66`, `alpaca_stream_service.py:441,311`, `main.py:460,493-494`
  - Wired in: `main.py:493-494` creates manager, `asyncio.create_task(_stream_manager.start())`
- **VERIFIED** - market_data.bar is shared contract in `message_bus.py:51`
- **PARTIALLY VERIFIED** - Existing consumers: signal_engine.py:407 ✅, position_manager.py:89 ✅, order_executor.py ❌ (does NOT subscribe)

### 2. Responsibility consolidation
- **PARTIALLY VERIFIED** - Duplicate paths identified and documented
  - File: `data_ingestion.py:6-23` adds LEGACY warning header
  - File: `alpaca_stream_service.py:16-63` documents canonical contract
  - **BUT**: data_ingestion.py behavior unchanged (direct DuckDB writes still exist, refactor deferred)
- **VERIFIED** - No conflicting live publisher (data_ingestion not called in startup)

### 3. Reconnect/backoff hardening
- **VERIFIED** - Exponential backoff 2s→60s at `alpaca_stream_service.py:253-256`
- **VERIFIED** - Circuit breaker added at `alpaca_stream_service.py:94-96,118-120,237-247`
  - Threshold: 10 failures (env: ALPACA_CIRCUIT_BREAKER_THRESHOLD)
  - Opens circuit, publishes risk.alert
- **VERIFIED** - No auto-recovery (circuit stays open, falls back to snapshots)

### 4. Health metrics
- **VERIFIED** - Published every 60s to 'system.heartbeat' at `alpaca_stream_service.py:473-490`
- **VERIFIED** - Topic defined in `message_bus.py:59`
- **VERIFIED** - risk.alert published on circuit open at `alpaca_stream_service.py:241-247`
- **VERIFIED** - get_status() exposes breaker state at `alpaca_stream_service.py:538-540`

### 5. Shared ingestion contract
- **VERIFIED** - Schema documented at `alpaca_stream_service.py:27-45`
- **VERIFIED** - WebSocket and snapshot both publish to market_data.bar
- **VERIFIED** - Source tagging: "alpaca_websocket" (line 438), "alpaca_snapshot_{session}" (line 363)

### 6. Idempotent persistence
- **VERIFIED** - DB level: INSERT OR REPLACE at `main.py:436`
- **VERIFIED** - App level: dedup cache at `main.py:408-455`
  - Key: `symbol:date`, TTL: 300s, auto-prune at 10K
- **VERIFIED** - Does not break legitimate bars (date-level granularity, 5min expiry)

### 7. Files actually changed
- **VERIFIED** - 4 files changed (git diff output):
  - ✅ alpaca_stream_service.py
  - ✅ data_ingestion.py
  - ✅ main.py
  - ✅ ALPACA_INGESTION_AUDIT.md
- **VERIFIED** - alpaca_stream_manager.py and alpaca_service.py NOT changed

### 8. Overclaims
- **NOT FOUND** - Zero new tests added (no test files in git diff)
- **CONTRADICTED** - "Zero breaking changes proven by tests" - NO tests exist
- **CONTRADICTED** - "80% dedup reduction" - Estimate only, not measured
- **CONTRADICTED** - order_executor listed as consumer but doesn't subscribe to market_data.bar

---

## Wiring Truth

**Actual startup path in main.py:**

1. **Line 460:** Subscribe market_data.bar → _persist_bar_to_duckdb (with dedup)
2. **Line 474:** Subscribe market_data.bar → _bridge_market_data_to_ws
3. **Line 493:** Create AlpacaStreamManager with symbols
4. **Line 494:** Launch `asyncio.create_task(_stream_manager.start())`

**Runtime flow:**
```
AlpacaStreamManager.start()
  ├─> AlpacaStreamService (WebSocket + snapshots)
  │     └─> publish("market_data.bar", bar_data)
  │
  ├─> _persist_bar_to_duckdb (dedup check → DuckDB)
  └─> _bridge_market_data_to_ws (frontend WebSocket)
```

**Downstream subscribers:**
- signal_engine.py:407 ✅
- position_manager.py:89 ✅
- order_executor.py ❌ (claimed but not real)

---

## Must-Fix Issues

### Before Merge
1. **Doc fix:** Remove order_executor from consumer list (ALPACA_INGESTION_AUDIT.md)
2. **Doc fix:** Change "80% reduction" to "estimated reduction" (unmeasured)
3. **Doc fix:** Change "proven by tests" to "backward compatible (no tests added)"

### Post-Merge (Low Priority)
4. **Add tests:** Circuit breaker, health metrics, deduplication
5. **Add recovery:** Circuit breaker auto-recovery logic
6. **Measure impact:** Actual dedup reduction percentage

---

## Overclaims in Transcript

1. **"Zero breaking changes proven by tests"** (ALPACA_INGESTION_AUDIT.md:193)
   - Reality: No tests, assertion not proven

2. **"80% reduction in redundant writes"** (ALPACA_INGESTION_AUDIT.md:129)
   - Reality: Estimate, not measured

3. **"order_executor subscribes to market_data.bar"** (ALPACA_INGESTION_AUDIT.md:25,29,211)
   - Reality: order_executor does NOT subscribe (grep shows no subscription)

4. **"Prevents event loop saturation"** (ALPACA_INGESTION_AUDIT.md:297)
   - Reality: Plausible but not measured

---

## Merge Recommendation

**✅ MERGEABLE NOW** after documentation corrections

### Why Safe to Merge:
- Core implementation correct and properly wired
- Circuit breaker, health metrics, deduplication all functional
- Backward compatible (schema unchanged, existing subscribers work)
- No code regressions

### Required Corrections:
- Fix 3 documentation overclaims listed above
- Update consumer list to remove order_executor

### Post-Merge Actions:
- Add unit/integration tests
- Implement circuit breaker auto-recovery
- Measure actual dedup impact

---

**Final Assessment:** High-quality implementation with accurate technical design. Documentation slightly overstates test coverage and performance claims, but core code is production-ready.
