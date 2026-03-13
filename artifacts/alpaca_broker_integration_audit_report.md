# Alpaca Broker Integration — Order Lifecycle & Reconciliation Audit Report

**Prompt 18** | March 2026 | Embodier Trader v5.0.0

---

## 1. Order Lifecycle (Traced)

```
council.verdict (MessageBus)
  → OrderExecutor._on_council_verdict()
  → Gates 0–9 (TTL, council, mock, regime, circuit breaker, daily limit, cooldown,
     drawdown, degraded/kill, regime position count, Kelly, heat, viability, risk governor)
  → ExecutionDecision built
  → _execute_order() or _shadow_execute()
  → AlpacaService.create_order() [REST POST /v2/orders]
  → Alpaca API
  → order.submitted (MessageBus) + _poll_for_fill() for fill/partial handling
```

- **Council verdict** is the only path into execution; no direct broker path without `ExecutionDecision`.
- **AlpacaService** is the single facade for trading API; key pool is used only when `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` are unset (fallback to pool’s `trading` key).

---

## 2. 429 Rate Limit Handling

| Finding | Status |
|--------|--------|
| 429 distinguished from other HTTP errors | **Yes** — `_request()` treats 429 and 503 as retriable; others are not. |
| Retry with backoff | **Yes** — 3 retries, wait `2^attempt` seconds (1s, 2s, 4s). |
| Reported to key pool | **No** — `AlpacaService._request()` does not call `AlpacaKeyPool.report_rate_limit(role)`. Key pool has `report_rate_limit()` and `rate_limit_hits` but nothing in the Alpaca HTTP path calls it. |

**Recommendation:** After exhausting retries on 429 (or on each 429 if you want to count), call `get_alpaca_key_pool().report_rate_limit("trading")` so health/observability can track rate limit pressure and optionally back off or rotate.

---

## 3. Partial Fill Retry Logic

| Finding | Status |
|--------|--------|
| Partial fill remainder re-executed | **Yes** — `_poll_for_fill()` detects filled vs remainder and calls `_re_execute_remainder()`. |
| Max retries | **Yes** — `MAX_PARTIAL_FILL_RETRIES = 3`. |
| Exponential backoff before remainder order | **No** — remainder is sent as a market order immediately; no delay or backoff between retries. |

**Recommendation:** Add a short delay before each remainder submission (e.g. `2 ** retry` seconds) to avoid hammering the API and to allow partial liquidity; optionally use limit order for remainder on retries 2–3.

---

## 4. Position Reconciliation

| Finding | Status |
|--------|--------|
| Periodic sync of Alpaca positions vs internal state | **No** — no scheduled job. |
| Startup sync | **Yes** — `PositionManager._sync_from_alpaca()` on start; syncs open positions into `ManagedPosition` for trailing stops. |
| Drift detection | **Not implemented** — no comparison of OrderExecutor/PositionManager state vs `GET /v2/positions` on a schedule. |

**Recommendation:** Add a periodic reconciliation job (e.g. every 5–15 minutes during market hours) that (1) fetches `AlpacaService.get_positions()`, (2) compares to PositionManager and/or OrderExecutor’s view of open positions, (3) logs discrepancies and optionally publishes `position.reconciliation_drift` with symbol, internal qty, broker qty, and (4) updates internal state from broker as source of truth so drift does not accumulate.

---

## 5. Key Pool — Account 1 vs Account 2 Isolation

| Finding | Status |
|--------|--------|
| PC1 (primary) uses Key 1 for trading | **Yes** — `ALPACA_KEY_1`/`ALPACA_SECRET_1` → role `trading`; optional Key 2 as `discovery_rest` (REST only, no WS). |
| PC2 (secondary) uses Key 2 for discovery | **Yes** — `PC_ROLE=secondary` loads only Key 2 as `discovery`. |
| Isolation | **Correct** — each PC uses one key for WebSocket; trading orders use trading key only. |
| Key rotation/refresh | **No** — keys loaded at init; no rotation or refresh mechanism. |

**Recommendation:** Document that key rotation requires process restart (or add a refresh method that reloads from settings and optionally closes/reopens HTTP/WS clients). For 429 hardening, consider reporting rate limit by role so a future multi-key rotation could back off the affected key.

---

## 6. WebSocket Reconnection (AlpacaStreamService)

| Finding | Status |
|--------|--------|
| Reconnect loop | **Yes** — main loop catches exceptions and reconnects with exponential backoff (`_reconnect_delay` up to `MAX_RECONNECT_DELAY` 60s). |
| Sustained outage | After `WS_CIRCUIT_BREAKER_THRESHOLD` (default 10) consecutive failures, circuit opens and service falls back to **permanent** REST snapshot polling; no further WS reconnect attempts until manual reset. |
| Snapshot fallback | **Yes** — when market closed or WS fallback active, `_run_snapshot_poll_loop()` runs every `SNAPSHOT_POLL_INTERVAL` (30s). |

**Recommendation:** Expose an API or admin action to reset the WS circuit breaker so operators can re-enable WebSocket after Alpaca recovery without restarting the process. Consider a scheduled “probe” (e.g. once per hour) that tries one WS connect and resets the circuit on success.

---

## 7. Paper vs Live Mode Safety

| Finding | Status |
|--------|--------|
| URL forced by TRADING_MODE | **Yes** — in `AlpacaService.__init__`: if `TRADING_MODE=live` and URL contains "paper", base_url is forced to `https://api.alpaca.markets`; if `TRADING_MODE=paper` and URL does not contain "paper", base_url is forced to `https://paper-api.alpaca.markets`. |
| PAPER config hitting LIVE | **Prevented** — paper mode cannot use live URL; init enforces paper URL when mode is paper. |
| validate_account_safety | **Present** — startup validation checks account vs mode and logs CRITICAL on mismatch. |

No change required for paper/live safety; behavior is correct.

---

## 8. Order Executor Gates — Verification Summary

| # | Gate | Verified | Notes |
|---|------|----------|--------|
| 1 | Regime gate | ✅ | RED/CRISIS (max_pos=0, kelly_scale=0) block; regime position count enforced. |
| 2 | Circuit breaker | ✅ | Leverage >2x or concentration >25% blocks. |
| 3 | Kelly sizing | ✅ | HOLD or REJECT from sizer blocks; qty &lt; 1 rejected. |
| 4 | Portfolio heat | ✅ | New position % vs remaining heat; uses last_equity (B8). |
| 5 | Viability | ✅ | Expected cost vs edge (B7); configurable via ENABLE_EXECUTION_VIABILITY_GATE. |
| 6 | HITL | ⚠️ | Not in OrderExecutor; assumed upstream (council_gate/hitl_gate). ExecutionDecision is required for submit. |
| 7 | Duplicate check | ✅ | Verdict dedup by hash within 60s window. |
| 8 | Market hours | ⚠️ | No explicit gate in OrderExecutor; Alpaca rejects outside hours unless extended_hours. |
| 9 | Notional limit | ✅ | _select_order_type: ≤$5K market, $5K–$25K limit, &gt;$25K TWAP. |

---

## 9. Deliverables Completed

- **Tests added:** `backend/tests/test_alpaca_order_lifecycle_audit.py`
  - Gate 1: Regime (red blocks, position cap).
  - Gate 2: Circuit breaker (high leverage blocks).
  - Gate 3: Kelly (HOLD blocks).
  - Gate 4: Portfolio heat (exceeded blocks).
  - Gate 5: Viability (denied blocks).
  - Gate 6: HITL (ExecutionDecision required).
  - Gate 7: Duplicate verdict suppressed.
  - Gate 8: Order type selection by notional.
  - Gate 9: Notional threshold constants and selection.
  - 429: AlpacaService retries on 429; key pool has report_rate_limit.
  - Position reconciliation: drift detection logic test; PositionManager sync-on-start only.
  - Paper vs live: paper URL when paper mode; force paper URL when mode paper but URL live.
- **Single-symbol quote helper:** `AlpacaService.get_latest_quote(symbol)` added so `order_executor._get_fresh_price` and outcome_tracker have a consistent API (wraps `get_latest_quotes([symbol])`).

---

## 10. Recommended Hardening (Prioritized)

1. **Periodic position reconciliation job**  
   Schedule (e.g. APScheduler/cron) every 5–15 min: fetch Alpaca positions, compare to PositionManager/OrderExecutor, log and publish drift, update internal state from broker.

2. **Report 429 to key pool**  
   In `AlpacaService._request()`, when `resp.status_code == 429` (and optionally when retries exhausted), call `get_alpaca_key_pool().report_rate_limit("trading")` (and use trading key role if using pool).

3. **Adaptive backoff for partial fill remainder**  
   In `_re_execute_remainder()`, before submitting the remainder order, `await asyncio.sleep(2 ** retry)` (e.g. 1s, 2s, 4s) and optionally use a limit order for retries 2–3.

4. **WebSocket circuit breaker reset**  
   Expose an endpoint or admin action to reset `AlpacaStreamService` WS circuit breaker so WebSocket can be re-enabled after Alpaca recovery; optional periodic probe to auto-reset.

5. **Optional: key pool rotation**  
   Document key rotation (restart or config reload); if multiple keys are used for trading, consider using `report_rate_limit` and health to temporarily prefer another key when one is rate-limited.

---

## 11. Files Touched

| File | Change |
|------|--------|
| `backend/app/services/alpaca_service.py` | Added `get_latest_quote(symbol)` wrapper. |
| `backend/tests/test_alpaca_order_lifecycle_audit.py` | New test module (17 tests). |
| `artifacts/alpaca_broker_integration_audit_report.md` | This report. |

All new tests pass: `pytest tests/test_alpaca_order_lifecycle_audit.py -v`.
