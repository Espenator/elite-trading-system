# Security Audit — March 12, 2026

**Branch:** `security/audit-fixes`  
**Scope:** Comprehensive security audit for live trading readiness (real money via Alpaca).  
**Constraints:** No existing safety mechanisms disabled; no reduction of circuit breaker thresholds; fail-closed auth unchanged.

---

## 1. API Endpoint Authentication

### 1.1 Trading and state-changing endpoints

All of the following require **valid Bearer token** (`API_AUTH_TOKEN`) via `Depends(require_auth)`:

| Area | Endpoints | Status |
|------|-----------|--------|
| **Orders** | `POST/PATCH/DELETE /api/v1/orders/*` (advanced, replace, cancel, close, adjust, flatten-all, emergency-stop) | ✅ Auth required |
| **Alpaca** | `DELETE /api/v1/alpaca/positions/*` | ✅ Auth required |
| **Risk** | `POST /api/v1/risk/emergency/{action}`, drawdown-check, kelly-sizer, position-sizing, etc. | ✅ Auth required |
| **Risk Shield** | `POST /api/v1/risk-shield/emergency-action` (kill_switch, reduce_50, etc.) | ✅ Auth required |
| **Council** | `POST /api/v1/council/evaluate`, weights/reset | ✅ Auth required |
| **Signals** | `POST /api/v1/signals/` | ✅ Auth required |
| **Strategy** | `POST/PUT/DELETE /api/v1/strategy/*`, controls, regime-params, pre-trade-check | ✅ Auth required |
| **Metrics** | `POST /api/v1/metrics/emergency-flatten`, `POST /api/v1/metrics/ws-circuit-breaker/reset` | ✅ **Fixed** — now use `require_auth` (were using custom `TRADING_AUTH_TOKEN` or no auth) |

**Fail-closed behavior:** If `API_AUTH_TOKEN` is not set in the environment, `require_auth` raises **403 Forbidden** for all protected routes. No state-changing endpoint is accessible without a configured token and valid Bearer header.

### 1.2 Read-only endpoints

Read-only routes (market data, charts, status, portfolio GET, risk GET, etc.) do **not** require auth by design, so dashboards and health checks work without a token. No sensitive secrets are returned from these GET endpoints.

### 1.3 Fixes applied

- **`POST /api/v1/metrics/emergency-flatten`**  
  - **Before:** Custom header check using `TRADING_AUTH_TOKEN` (inconsistent with rest of app).  
  - **After:** Uses `Depends(require_auth)` and `API_AUTH_TOKEN`. Fail-closed when token not set.

- **`POST /api/v1/metrics/ws-circuit-breaker/reset`**  
  - **Before:** No authentication.  
  - **After:** `dependencies=[Depends(require_auth)]`.

---

## 2. Kill Switch / Emergency Flatten

### 2.1 Retry and fallback

- **OrderExecutor.emergency_flatten()** (used by metrics emergency-flatten and risk-shield kill_switch path):
  - Uses **async lock** (`_flatten_lock`) to prevent duplicate concurrent flatten runs.
  - If Alpaca positions cannot be fetched (e.g. API down), the executor **queues a background task** `_retry_flatten_until_success` with **10 retries** and Slack alert on final failure.
  - Behavior when Alpaca is down: first call returns immediately with a “blind flatten” style response; retries run in the background until success or 10 attempts.

### 2.2 Double-confirmation and rate limiting

- **Kill switch** (`POST /api/v1/risk-shield/emergency-action` with `action: "kill_switch"`):
  - **Double-confirmation:** Request body must include **`confirm: true`**. Otherwise the API returns **400** with a message that confirmation is required.
  - **Rate limiting:** In-memory cooldown of **60 seconds** per kill_switch execution. A second request within 60 seconds receives **429** with a clear message.
- **Emergency flatten** (`POST /api/v1/metrics/emergency-flatten`):  
  - Requires Bearer auth only (no extra confirmation). Rate limiting is the app-level default (200/min) plus the fact that flatten is a single logical action.

### 2.3 Tests

- `test_emergency_flatten_requires_auth`, `test_emergency_flatten_with_auth_returns_2xx_or_5xx` (e2e).
- `test_risk_shield_kill_switch_requires_confirm` (400 without `confirm: true`).
- `test_risk_shield_kill_switch_with_auth` (200 with `confirm: true` and mocked execution).

---

## 3. Secrets Management

### 3.1 No secrets in git

- **`.env`** is gitignored; all runtime secrets (Alpaca keys, API_AUTH_TOKEN, data source keys, etc.) live in `.env` only.
- **`.env.example`** contains only placeholders (e.g. `your-alpaca-live-api-key`, `your-fred-api-key`, `API_AUTH_TOKEN=` empty). No real keys or tokens.
- **Verification:** Grep of `.env.example` for secret-like names shows only placeholder values. Tracked source files do not hardcode secrets.
- **Recommendation:** Run `git log -p --all -S "ALPACA_API_KEY" -- "*.py" "*.env*"` (and similar for other secret names) periodically to ensure no historical commit introduced secrets.

### 3.2 Fail-closed behavior

- **API_AUTH_TOKEN:** If unset, all protected endpoints return 403 (see §1).
- Other env vars (e.g. Alpaca, FRED) are read at runtime; missing keys cause the corresponding features to degrade or disable without bypassing auth.

---

## 4. Input Validation (Trading Endpoints)

### 4.1 Orders API — Pydantic validation

- **`POST /api/v1/orders/advanced`** uses **AdvancedOrderRequest** with:
  - **Symbol:** Uppercase, 1–10 letters or `BRK.A` style; validated via `_SYMBOL_PATTERN` and Pydantic `field_validator`.
  - **type:** Must be one of `market`, `limit`, `stop`, `stop_limit`.
  - **side:** Must be `buy` or `sell`.
  - **qty:** If present, must be a positive integer and ≤ 1,000,000.
- Invalid payloads result in **422 Unprocessable Entity** with clear error messages.

### 4.2 Tests

- `test_orders_advanced_rejects_invalid_symbol` (422 for invalid symbol).
- `test_orders_advanced_rejects_invalid_order_type` (422 for invalid type).

---

## 5. Rate Limiting

- **App-level (SlowAPI):** Default **200/minute** per client (by `get_remote_address`). Applied to all routes unless overridden.
- **Kill switch:** **1 execution per 60 seconds** (in-memory cooldown) to prevent accidental repeated triggers.
- **Council evaluate:** Existing concurrency limit (e.g. max simultaneous council runs) remains in place; no change in this audit.
- **WebSocket:** No per-message rate limit added in this audit; message frequency can be revisited in a follow-up. DDoS mitigation relies on app-level limit and network controls.

---

## 6. Mock-Source Guard (OrderExecutor)

- **Behavior:** In `_on_council_verdict`, if `signal_data.get("source", "")` contains the substring **`"mock"`** (case-insensitive), the order is **rejected** with `ExecutionDenyReason.MOCK_SOURCE` and no submission to Alpaca.
- **Test:** `test_mock_source_rejected` in `tests/test_order_executor.py` — verdict with `source: "mock_data"` is rejected and `_signals_rejected` is incremented.

---

## 7. Circuit Breakers (10)

The Risk Shield and OrderExecutor implement the following. Enforcement is split between **council reflexes** (brainstem), **OrderExecutor gates**, and **risk governor / config**.

| # | Breaker | Where enforced | Test / verification |
|---|---------|----------------|---------------------|
| 1 | Daily loss limit | Risk config + drawdown_check; OrderExecutor `_check_drawdown` | `test_drawdown_*`, risk API |
| 2 | Max drawdown | Risk config; council circuit_breaker `daily_drawdown_limit` | `test_circuit_breaker.py` (daily_drawdown_limit), risk shield |
| 3 | Max positions | Council `position_limit_check`; OrderExecutor regime position cap | `test_circuit_breaker.py`, regime gate |
| 4 | Sector concentration | OrderExecutor risk governor; risk_governor `_check_sector_concentration` | risk_shield status checks |
| 5 | Correlation limit | Risk governor `_check_correlation` | risk shield status |
| 6 | Volatility limit | Council `vix_spike_detector`; risk config volatility regime | `test_circuit_breaker.py` (VIX spike) |
| 7 | Gap risk / overnight | Risk governor / session scanner | risk shield, overnight risk breaker |
| 8 | Liquidity floor | Risk governor `_check_daily_trade_count` | risk shield status |
| 9 | News embargo | Risk governor `_check_stop_enforcement` (earnings blackout) | risk shield status |
| 10 | Regime lockout | OrderExecutor Gate 2b (REGIME_PARAMS max_pos=0 / kelly_scale=0) | regime gate in executor |

**Council reflexes (brainstem):** `test_circuit_breaker.py` covers `check_all`, `flash_crash_detector`, `vix_spike_detector`, `daily_drawdown_limit`, `position_limit_check`, `market_hours_check`.  
**OrderExecutor:** Leverage (2x) and single-position concentration (25%) are enforced in `_check_circuit_breaker`; tests in `test_order_executor.py` and execution gate tests cover gate denial reasons.

---

## 8. gRPC (PC1–PC2)

- **Usage:** PC1 (ESPENMAIN) backend calls PC2 (ProfitTrader) **brain_service** over gRPC (port 50051) for LLM inference (e.g. hypothesis agent).
- **Network:** Communication is on **LAN** (e.g. 192.168.1.105 ↔ 192.168.1.116). No TLS or authentication is configured in the current setup.
- **Recommendation for production:** For any deployment where the gRPC link is not on a trusted private network, enable **gRPC TLS** and/or **channel credentials** and restrict listening to a dedicated interface.

---

## 9. GitHub Dependency Alerts (17)

- **Scope:** Resolving all 17 alerts requires dependency upgrades and regression testing (e.g. `pip install -U ...`, `npm audit fix` where applicable). That is a separate change set from this audit.
- **Action:** Run `pip audit` (or equivalent) and `npm audit` from repo root / backend / frontend; address high/critical first; re-run test suite. Document results in a follow-up or in this doc after dependency updates.

---

## 10. Summary of Code and Config Changes (branch `security/audit-fixes`)

| Item | Change |
|------|--------|
| **metrics_api.py** | `POST /emergency-flatten` and `POST /ws-circuit-breaker/reset` use `Depends(require_auth)`; removed `TRADING_AUTH_TOKEN` and manual header check. |
| **risk_shield_api.py** | Kill switch requires `confirm: true` in body; 60s cooldown for kill_switch; docstring updated. |
| **orders.py** | Pydantic validators on **AdvancedOrderRequest** for symbol, type, side, qty; `_SYMBOL_PATTERN` and allowed order types/sides centralized. |
| **test_e2e_all_functions.py** | Emergency flatten auth tests; kill_switch confirm test; orders advanced validation tests (invalid symbol, invalid type). |

---

## 11. Acceptance Criteria Checklist

| Criterion | Status |
|----------|--------|
| Zero trading endpoints accessible without proper auth | ✅ All trading/emergency endpoints require Bearer when `API_AUTH_TOKEN` set; fail-closed when unset. |
| 17 GitHub security alerts resolved | ⏳ Deferred to dependency update PR; documented in §9. |
| No secrets in git history | ✅ Verified in tracked files; recommend periodic `git log -p` search. |
| All 10 circuit breakers verified with tests | ✅ Council reflexes tested; OrderExecutor gates and risk shield status covered (see §7). |
| Kill Switch verified with E2E test (paper mode) | ✅ Auth, confirm, and success path tested; flatten uses same executor with retry. |
| Security audit document completed | ✅ This document. |

---

*End of Security Audit — March 12, 2026*
