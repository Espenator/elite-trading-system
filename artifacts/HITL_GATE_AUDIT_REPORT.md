# HITL Gate & Approval Flow — Audit Report (Prompt 20)

**Date:** March 13, 2026  
**Scope:** Human-in-the-loop gate, approval timeout, bulk approval, learning period, overflow, bypass.

---

## 1. Verification of All 6 Gates

| Gate | Config / Condition | Behavior | Test |
|------|--------------------|----------|------|
| **1. Trade size** | `max_trade_value_usd=5000` | Estimated trade value > $5000 → requires approval | `test_gate_1_trade_size_*` |
| **2. Confidence** | `min_confidence_for_auto=0.60` | `final_confidence` < 60% → requires approval | `test_gate_2_confidence_*` |
| **3. Learning period** | `learning_period_days=30`, `learning_start_timestamp` set | Days since start < 30 → requires approval | `test_gate_3_learning_period_*` |
| **4. Novel regime** | `known_regimes` = bullish, bearish, sideways, volatile | `metadata.regime` not in list → requires approval | `test_gate_4_novel_regime_*` |
| **5. Consecutive losses** | `max_consecutive_losses=5` | `_consecutive_losses` ≥ 5 → requires approval | `test_gate_5_consecutive_losses_*` |
| **6. Sector concentration** | `max_sector_concentration=0.40` | Any sector in `portfolio_context.sector_allocation` > 40% → requires approval | `test_gate_6_sector_concentration_*` |

**Finding:** All six gates are implemented and evaluated **independently** (no cross-gate logic). Multiple gates can trigger on the same decision; all triggered gate names are in `gates_triggered`.

---

## 2. Approval Timeout

**Question:** Do pending approvals expire? What happens at N+1?

**Finding:**

- **No timeout.** Pending approvals remain in `_pending_approvals` until explicitly `approve()` or `reject()` is called, or the entry is evicted by overflow (see §6).
- There is no TTL, no "pending > 5 minutes → auto-reject", and no timestamp stored on the pending item for expiry logic.
- **Test:** `test_approval_timeout_pending_does_not_expire` documents that pending items do not expire.

**Recommendation:** Add an optional approval timeout (e.g. 5 or 10 minutes). When an item has been pending longer than the timeout, either auto-reject and remove it, or mark it "expired" and stop considering it for execution. This prevents unbounded accumulation of stale approval requests and avoids confusion when the market has moved.

---

## 3. Bulk Approval

**Question:** Is there an "approve all" endpoint?

**Finding:**

- **No bulk approval.** `HITLGate` has only `approve(decision_id)` and `reject(decision_id)`. There is no `approve_all()` or `bulk_approve()` method.
- The API in `backend/app/api/v1/agents.py` exposes `/hitl/buffer`, `/hitl/{item_id}/approve`, `/hitl/{item_id}/reject`, `/hitl/{item_id}/defer`, and `/hitl/stats`, but these operate on a **separate** in-memory `_hitl_buffer` (ring buffer, max 50). They are **not** wired to the canonical `get_hitl_gate()._pending_approvals`. So:
  - The real pending list is in `hitl_gate._pending_approvals` (capped at 100).
  - The agents API does not call `get_hitl_gate().get_pending()`, `approve()`, or `reject()`; approving via the API does not clear the gate’s pending item.
- **Test:** `test_no_bulk_approve_method` asserts that `HITLGate` has no `approve_all` or `bulk_approve` method.

**Recommendation:**

1. Wire the HITL API to the real gate: e.g. a `GET /api/v1/hitl/pending` that returns `get_hitl_gate().get_pending()`, and `POST /api/v1/hitl/{decision_id}/approve` / `reject` that call `get_hitl_gate().approve(decision_id)` / `reject(decision_id)`.
2. Add a bulk-approve endpoint, e.g. `POST /api/v1/hitl/approve-all`, that approves all current pending items (with optional filters by symbol or age).

---

## 4. Learning Period Auto-Start

**Question:** Does the learning period auto-start on first live trade?

**Finding:**

- **No.** The learning period is active only when `learning_start_timestamp > 0`. That value is set **only** by calling `start_learning_period()` (in `hitl_gate.py`). Nothing in the codebase calls `start_learning_period()` automatically on first live trade or first order.
- **Test:** `test_gate_3_learning_period_does_not_auto_start` asserts that with default config (`learning_start_timestamp == 0`), the learning_period gate does not trigger.

**Recommendation:** When the first live trade is submitted (e.g. in `OrderExecutor` when `auto_execute=True` and an order is sent), call `get_hitl_gate().start_learning_period()` if `learning_start_timestamp == 0`. Alternatively, expose a one-time "Start learning period" action in the UI/API and document that operators must trigger it when going live.

---

## 5. Cross-Gate Logic

**Question:** Do gates interact (e.g. losses + novel regime)?

**Finding:**

- **No interaction.** Each gate is evaluated in sequence and only appends to `gates_triggered` and `gate_details`. There is no combined condition (e.g. "require approval only if both losing_streak and novel_regime"). Multiple gates can fire on the same decision; the result is the union of all triggered gates.
- **Test:** `test_gates_evaluated_independently_multiple_triggered` triggers both low_confidence and learning_period on one decision.

**Recommendation:** No change required unless product wants compound rules (e.g. "require approval only when both losing streak and novel regime"). Current behavior is clear and testable.

---

## 6. _pending_approvals Bounded at 100 — Overflow

**Question:** What happens to overflow when more than 100 pending?

**Finding:**

- **Capped at 100.** When `len(self._pending_approvals) >= MAX_PENDING_APPROVALS` (100), the **oldest** entry (first key in insertion order) is removed with `pop(oldest_key)`, then the new result is added. So the 101st pending approval causes the first one to be dropped; no explicit "rejected due to overflow" event is published.
- **Test:** `test_overflow_101st_pending_evicts_oldest` and `test_overflow_integration_via_check` verify that after 101+ triggers, pending count stays at 100 and the oldest decision_id is no longer in `get_pending()`.

**Recommendation:** Consider publishing a one-off event (e.g. `hitl.overflow_evicted`) when an item is evicted, so operators can see that an approval request was dropped. Optionally add a metric `hitl_evictions_total` for monitoring.

---

## 7. HITL Bypass (HITL_ENABLED=false)

**Question:** Can HITL be completely bypassed?

**Finding:**

- **Yes.** When `HITLConfig(enabled=False)` (or `config.enabled = False`), `check()` returns immediately with an empty `GateResult()` (no approval required). So all six gates are bypassed. There is no env var `HITL_ENABLED` in the codebase; the gate is configured programmatically via `HITLConfig` or `update_config()`. To make it configurable from env, one would set `HITLConfig(enabled=os.environ.get("HITL_ENABLED", "true").lower() == "true")` (or similar) where the gate is constructed.
- **Test:** `test_hitl_disabled_bypasses_all_gates` asserts that with `enabled=False`, a decision that would trigger multiple gates (low confidence, novel regime, sector concentration, trade size) still returns `requires_approval=False` and no `gates_triggered`.

**Recommendation:** If operations need to disable HITL without code change, add `HITL_ENABLED` to config (e.g. in `core/config.py`) and pass it into `HITLConfig(enabled=...)` when creating or updating the gate.

---

## 8. Additional Findings

### Portfolio context and trade size

- **Trade value estimate:** In `_estimate_trade_value()`, when `portfolio_context` is provided with `account_value`, the estimate is `account_value * 0.02 * scale` (2% per trade). So the trade_size gate uses a **hardcoded 2%** of portfolio, not real position sizing from Kelly or the executor. If the executor later sizes at 1% or 3%, the gate’s estimate can be wrong.
- **Pipeline:** `run_council()` is invoked from `CouncilGate` with a `context` that does **not** include `portfolio_context`. So `context.get("portfolio_context")` in the runner is typically `None`. That means in the main signal → council → verdict pipeline, **trade_size** and **sector_concentration** gates never see portfolio data unless something else injects it. To make these gates effective, the caller of `run_council()` (e.g. CouncilGate) should pass in portfolio context (account value, sector allocation).

### Execution block when HITL triggers

- When `hitl_result.requires_approval` is True, the **runner** sets `decision.execution_ready = False` and does **not** publish `council.verdict`. So `OrderExecutor` never receives the verdict and the trade is not executed. Execution is correctly blocked until the decision is approved and re-submitted (re-submission path would require a separate flow; currently "approve" in the gate only removes from pending and does not re-publish a verdict).

---

## 9. Tests Added

All in `backend/tests/test_hitl_gate_audit.py`:

- **Gate 1 (trade size):** `test_gate_1_trade_size_requires_approval_when_above_threshold`, `test_gate_1_trade_size_passes_when_below_threshold`, `test_gate_1_trade_size_no_portfolio_returns_zero_estimate`
- **Gate 2 (confidence):** `test_gate_2_confidence_requires_approval_when_below_threshold`
- **Gate 3 (learning period):** `test_gate_3_learning_period_requires_approval_when_within_days`, `test_gate_3_learning_period_does_not_auto_start`
- **Gate 4 (novel regime):** `test_gate_4_novel_regime_requires_approval`, `test_gate_4_known_regime_passes`
- **Gate 5 (consecutive losses):** `test_gate_5_consecutive_losses_requires_approval`
- **Gate 6 (sector concentration):** `test_gate_6_sector_concentration_requires_approval`
- **Timeout:** `test_approval_timeout_pending_does_not_expire`
- **Overflow:** `test_overflow_101st_pending_evicts_oldest`, `test_overflow_integration_via_check`
- **Bulk:** `test_no_bulk_approve_method`
- **Cross-gate:** `test_gates_evaluated_independently_multiple_triggered`
- **Bypass:** `test_hitl_disabled_bypasses_all_gates`, `test_hold_always_passes`
- **Approve/reject/status:** `test_approve_and_reject_work`, `test_get_status_includes_pending_count`

Run: `cd backend && python -m pytest tests/test_hitl_gate_audit.py -v`

---

## 10. Summary of Recommendations

| # | Recommendation | Priority |
|---|----------------|----------|
| 1 | Add optional approval timeout (e.g. 5–10 min) with auto-reject or "expired" handling | High |
| 2 | Wire HITL API to real gate (`get_pending`, `approve`, `reject`) and add bulk-approve endpoint | High |
| 3 | Auto-start learning period on first live trade (or document manual start) | Medium |
| 4 | Pass `portfolio_context` from CouncilGate (or caller) into `run_council()` so trade_size and sector_concentration gates get real data | Medium |
| 5 | Use real position sizing (e.g. from OrderExecutor/Kelly) for trade value estimate, or document 2% as intentional default | Low |
| 6 | Publish overflow eviction event / metric when 101st pending evicts oldest | Low |
| 7 | Add `HITL_ENABLED` (or equivalent) to config for operational bypass without code change | Low |
