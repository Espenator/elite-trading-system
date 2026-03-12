# Embodier Trader — Final Pre-Production Safety Audit

**Date:** March 12, 2026  
**Auditor:** Senior systems architect (adversarial, code-only verification)  
**Codebase:** elite-trading-system (v5.0.0)  
**Scope:** Trade lifecycle, learning loop, safety mechanisms, startup, contracts, GitHub issues, security

---

## 1. EXECUTIVE SUMMARY

**Overall readiness:** **NOT production-ready for live capital.** One P0 bug prevents any council-approved trade from reaching the OrderExecutor (TradeExecutionRouter never started; OrderExecutor subscribes to a topic nothing publishes). The learning loop runs but with wrong attribution (no `trade_id` passed to WeightLearner; outcome.resolved has no `agent_votes`), so the system cannot attribute credit/blame to individual agents.

**Biggest risk:** **Zero trades execute** in the current wiring: CouncilGate publishes `council.verdict` → OrderExecutor listens only to `execution.validated_verdict` → TradeExecutionRouter (which would forward after validation) is never started and `execution.validated_verdict` is not in MessageBus VALID_TOPICS, so even if the router were started, publishes would be dropped.

**#1 action:** Start TradeExecutionRouter in `main.py` after CouncilGate and OrderExecutor, and add `execution.validated_verdict` to `message_bus.VALID_TOPICS`. Then pass `trade_id`/`council_decision_id` from outcome.resolved into WeightLearner.update_from_outcome and include agent_votes in the outcome payload (or have WeightLearner look up by council_decision_id from its own record_decision history).

---

## 2. PHASE 0: DOCS VS CODE — DISCREPANCIES

| Doc claim | Code reality | Severity |
|-----------|--------------|----------|
| "OrderExecutor receives council.verdict" (main.py comment line 472, CLAUDE.md) | OrderExecutor subscribes to **execution.validated_verdict** only (order_executor.py:186). Nothing in main.py publishes to that topic; TradeExecutionRouter is never started. | P0 |
| "35-agent council" | runner.py and agent_config list 35 agents in 7 stages; count matches. | OK |
| "44 router registrations" (CLAUDE.md) | main.py include_router count is 44+ (with health, metrics, ws registry). | OK |
| "runner.py publishes council.verdict" (prior audit BUG 2) | runner.py does **not** publish council.verdict; council_gate.py is the single publisher (runner.py ~937: "council.verdict publish is handled canonically by council_gate.py"). | BUG 2 fixed in code |
| "33-agent DAG" in ARCHITECTURAL-REVIEW / PLAN | Code uses 35 agents; docs sometimes say 33. | P2 (doc only) |
| "feedback_loop.update_agent_weights() never calls update_from_outcome()" (prior audit) | feedback_loop.update_agent_weights(outcome=...) **does** call learner.update_from_outcome() (feedback_loop.py:215). OutcomeTracker also calls it via council_record + update_agent_weights. main.py _on_outcome_resolved also calls learner.update_from_outcome() directly. | Fixed in code |

---

## 3. FINDINGS TABLE

| # | Severity | Category | File(s) | Finding | Fix Effort |
|---|----------|----------|---------|---------|------------|
| 1 | **P0** | Money path | main.py, order_executor.py, message_bus.py | OrderExecutor subscribes to `execution.validated_verdict`; only TradeExecutionRouter publishes it; router is never started; topic not in VALID_TOPICS. **No council verdicts ever reach OrderExecutor.** | 2–4 h |
| 2 | **P0** | Learning loop | main.py (1002–1008), outcome_tracker.py (to_dict) | _on_outcome_resolved does not pass `trade_id`/`council_decision_id` to WeightLearner.update_from_outcome(). Outcome payload (to_dict) has no `agent_votes`. Learning falls back to symbol-only match → wrong attribution when same symbol trades multiple times; SelfAwareness credits 13 agents equally. | 2–4 h |
| 3 | P1 | Learning loop | outcome_tracker.py | outcome.resolved event is pos.to_dict(); to_dict() does not include `agent_votes`. WeightLearner needs per-agent votes for attribution; they exist only in postmortem path (from WeightLearner.get_decision_by_trade_id) and are not in the event. | 2 h |
| 4 | P1 | Safety | risk_shield_api.py, order_executor.py | Kill switch / emergency flatten: endpoints exist (risk_shield emergency-action, metrics emergency-flatten, orders flatten-all). OrderExecutor.emergency_flatten has retry (10x) and _flatten_lock. If Alpaca is down, it queues _retry_flatten_until_success. **Verified:** logic exists; recommend integration test with Alpaca stub. | 1 h (test) |
| 5 | P1 | Safety | main.py (1556) | hitl.approval_needed **is** subscribed in main.py (_on_hitl_approval_needed); forwards to alert.health. Prior audit "ZERO subscribers" is **fixed**. | — |
| 6 | P2 | Money path | message_bus.py | `execution.validated_verdict` not in VALID_TOPICS; if router were started, publish() would log error and return without queuing. | 5 min |
| 7 | P2 | Docs | CLAUDE.md, project_state.md | OrderExecutor described as subscribing to council.verdict; actual subscription is execution.validated_verdict. | 5 min |
| 8 | P2 | Learning loop | council_gate.py (377–382) | CouncilGate calls learner.record_decision(decision) after council run; WeightLearner._decision_history is populated from this path. Outcome resolution uses symbol/trade_id match; without trade_id from main, symbol match can be wrong. | Covered by #2 |

---

## 4. PHASE 1: MONEY PATH — VERIFICATION

### Step-by-step (code-only)

| Step | Subscriber wired in main.py? | Publisher / data | Field match / failure behavior | Test? |
|------|------------------------------|------------------|--------------------------------|-------|
| AlpacaStreamManager → market_data.bar | N/A (publisher) | AlpacaStreamManager (main.py 458–469) publishes bars; no direct subscribe in main for “consumption” — EventDrivenSignalEngine subscribes in its start() (signal_engine.py:524). | — | — |
| EventDrivenSignalEngine ← market_data.bar | Yes (via engine.start()) | signal_engine subscribes in start(); main starts EventDrivenSignalEngine (main 375–377). | OK | — |
| EventDrivenSignalEngine → signal.generated | N/A | Publishes symbol, score, direction, etc. MessageBus coerces score to 0–100 at publish (message_bus.py 358–369). | OK | — |
| CouncilGate ← signal.generated | Yes when council_gate_enabled (main 407–416) | CouncilGate.start() subscribes (council_gate.py:134). Coerces score in _on_signal (council_gate.py:234–237). | OK | test_council_gate_publishes_single_verdict_per_signal |
| CouncilGate → council.verdict | N/A | Single publisher (council_gate.py). Runner does not publish. | OK | — |
| **OrderExecutor ← council.verdict?** | **No** | OrderExecutor subscribes to **execution.validated_verdict** (order_executor.py:186). **Nothing in main.py starts TradeExecutionRouter**; no other code publishes execution.validated_verdict. **Verdicts never reach OrderExecutor.** | **BROKEN** | — |
| OrderExecutor → order.submitted/filled | N/A | After _on_council_verdict (which is never called with real verdicts in current wiring). | N/A | — |
| OutcomeTracker ← order.submitted | Yes (outcome_tracker.start in main 627–632) | outcome_tracker subscribes in start() (outcome_tracker.py:143–144). | OK | — |
| OutcomeTracker → outcome.resolved | N/A | Publishes pos.to_dict() (no agent_votes). | See #2, #3 | — |
| _on_outcome_resolved ← outcome.resolved | Yes (main 1034) | main subscribes (main.py:1034). Calls WeightLearner.update_from_outcome without trade_id; SelfAwareness gets agent_votes from payload (always empty). | See #2 | — |

### Known bugs verification

- **BUG 1 (score scale):** **Fixed.** score_semantics.coerce_signal_score_0_100() scales 0–1 → 0–100; CouncilGate uses it (council_gate.py:234–237); MessageBus coerces at publish for signal.generated (message_bus.py 358–369).
- **BUG 2 (double verdict):** **Fixed.** Only council_gate.py publishes council.verdict; runner.py does not. OrderExecutor has 60s verdict dedup (order_executor.py:216–229) but listens to execution.validated_verdict, not council.verdict.
- **BUG 3 (Unusual Whales not wired):** Partially. message_bus.py lists unusual_whales.flow, .congress, .darkpool, .insider as PUBLISH_ONLY. No subscribers in main; perception.unusualwhales is WIRED. Agents that need UW data may get it via other paths (e.g. scouts); not re-verified end-to-end.

---

## 5. PHASE 2: LEARNING LOOP

- **_on_outcome_resolved (main.py ~987):** Calls WeightLearner.update_from_outcome(symbol, outcome_direction, pnl, r_multiple, is_censored). **Does not pass trade_id or council_decision_id.** Outcome payload has council_decision_id (from to_dict) but it is not forwarded to the learner.
- **Fallback when agent_votes empty:** outcome_data.get("agent_votes", {}) is always {} (to_dict does not include agent_votes). So SelfAwareness always credits the same 13 hardcoded agents (main 1024–1028) → anti-learning.
- **WeightLearner:** Uses _decision_history (max 500); populated by CouncilGate.record_decision(decision) (council_gate.py 377–382). update_from_outcome matches by trade_id first, then symbol. Without trade_id from main, only symbol match is used → wrong decision possible for repeated same-symbol trades.
- **OutcomeTracker:** Does not put agent_votes in outcome.resolved payload; postmortem path builds agent_votes from WeightLearner.get_decision_by_trade_id for DuckDB only.

---

## 6. PHASE 3: SAFETY MECHANISMS

- **Kill switch / emergency flatten:** Present. risk_shield_api.execute_emergency_action(kill_switch), metrics_api.trigger_emergency_flatten, orders.flatten_all; OrderExecutor.emergency_flatten with lock and retry. Alpaca down → _retry_flatten_until_success (10 attempts). Recommend automated test.
- **Circuit breakers:** order_executor.py runs circuit_breaker.check_all (and council_gate pre-council); gates 2b/2c, drawdown, daily limit, heat, etc. present.
- **Regime lockout:** RED regime and circuit breakers can block; regime refresh latency (e.g. 300s) and offline default (e.g. YELLOW) remain as in prior audit.
- **HITL:** hitl.approval_needed has a subscriber in main.py (1556); logs and forwards to alert.health.
- **Trading mode / auth:** validate_account_safety() used when auto_execute is True (main 348–361). Emergency/kill endpoints use require_auth (Bearer).

---

## 7. PHASE 4: STARTUP & BOOT

- MessageBus is started before EventDrivenSignalEngine and CouncilGate. OrderExecutor started after CouncilGate. TradeExecutionRouter is **not** started.
- Failure isolation: Ollama/Redis down → logged; council can be disabled via COUNCIL_GATE_ENABLED/LLM_ENABLED; signal_to_verdict_fallback exists when council disabled.
- execution.validated_verdict not in VALID_TOPICS → any future router publish would be dropped.

---

## 8. PHASE 5 & 6: CONTRACTS & GITHUB ISSUES

- API/WS: Not re-audited in depth; 43 route files and WS channels per REPO-MAP; frontend uses useApi and config.
- **#70 (P0: #45, #46, #47):** #45 (score scale) fixed; #46 (double verdict) fixed; #47 (UW wiring) partially open (PUBLISH_ONLY topics).
- **#45:** Fixed (coerce at bus + gate).
- **#46:** Fixed (single publisher).
- **#47:** Open (topics published, no subscribers in main).

---

## 9. PHASE 7: SECURITY

- No hardcoded secrets observed in the grep (ALPACA, API_KEY, SECRET, TOKEN, PASSWORD) under backend/*.py excluding .env and __pycache__.
- Trading and emergency endpoints use require_auth / Depends(require_auth).

---

## 10. P0 FINDING #1 — FIX: VERDICT PIPELINE

**File(s):** `backend/app/main.py`, `backend/app/core/message_bus.py`

**Reproduction:** Start app; trigger a council-approved verdict (e.g. via test or signal). CouncilGate publishes council.verdict. OrderExecutor never receives it because it subscribes to execution.validated_verdict and nothing publishes that topic.

**Proposed fix:**

1. **main.py** — After OrderExecutor.start(), start TradeExecutionRouter and subscribe it to council.verdict:

```python
# After: await _order_executor.start()
from app.services.trade_execution_router import TradeExecutionRouter
_router = TradeExecutionRouter(message_bus=_message_bus)
await _router.start()
log.info("TradeExecutionRouter started (council.verdict -> execution.validated_verdict)")
```

2. **message_bus.py** — Add to VALID_TOPICS:

```python
"execution.validated_verdict",
```

**Test:** Publish council.verdict with valid payload (council_decision_id, symbol, final_direction, etc.); assert OrderExecutor._on_council_verdict is invoked (e.g. via mock or metric).

---

## 11. P0 FINDING #2 — FIX: LEARNING ATTRIBUTION

**File(s):** `backend/app/main.py` (_on_outcome_resolved), optionally `backend/app/services/outcome_tracker.py` (to_dict)

**Reproduction:** Resolve an outcome; call update_from_outcome without trade_id. Match by symbol only; run two trades on same symbol — second outcome can match first decision.

**Proposed fix:**

1. **main.py** — Pass trade_id/council_decision_id into update_from_outcome:

```python
learner.update_from_outcome(
    symbol=outcome_data.get("symbol", ""),
    outcome_direction="win" if outcome_data.get("pnl_pct", 0) > 0.001 else "loss",
    pnl=outcome_data.get("pnl", 0.0),
    r_multiple=outcome_data.get("r_multiple", 0.0),
    is_censored=is_censored,
    trade_id=outcome_data.get("council_decision_id") or outcome_data.get("order_id"),
)
```

2. **Outcome payload (optional but recommended):** When building outcome.resolved, include agent_votes from WeightLearner.get_decision_by_trade_id(council_decision_id) so _on_outcome_resolved can pass them to SelfAwareness (or have SelfAwareness look up by council_decision_id). Alternatively, keep passing outcome to WeightLearner with trade_id and have WeightLearner drive attribution; SelfAwareness could then use the same decision lookup.

**Test:** Resolve two outcomes for same symbol with different council_decision_ids; assert WeightLearner updates the correct decision’s agents (e.g. by checking which decision was matched in update_from_outcome).

---

## 12. RISK MATRIX

**What can lose money (by $ impact):**

1. **No execution at all** (P0 #1) — capital not deployed as intended; opportunity cost.
2. **Wrong learning attribution** (P0 #2) — weights drift incorrectly; future trades worse.
3. Regime/cooldown/threshold misconfiguration — over-trading or under-trading.

**What can crash the system (by frequency):**

1. DuckDB lock / init race (prior audit).
2. Background loop crashes (mitigated by _supervised_loop).
3. Redis/Ollama down → graceful degradation.

**What degrades silently (by detection difficulty):**

1. **Verdicts not reaching OrderExecutor** — no orders; hard to notice without tracing bus.
2. **Learning without trade_id** — wrong attribution; only visible when comparing decision history to outcomes.
3. Agent_votes always empty in outcome.resolved — SelfAwareness and per-agent learning degraded.

---

## 13. RECOMMENDED FIX ORDER

1. **Branch: fix/verdict-pipeline** — Start TradeExecutionRouter in main; add execution.validated_verdict to VALID_TOPICS; add test that verdict reaches OrderExecutor.
2. **Branch: fix/learning-attribution** — Pass trade_id/council_decision_id in _on_outcome_resolved; optionally add agent_votes to outcome.resolved and use in SelfAwareness; add test for correct decision matching.
3. **Branch: docs** — Update CLAUDE.md and project_state.md: OrderExecutor receives verdicts via TradeExecutionRouter (execution.validated_verdict).

---

## 14. WHAT IS ACTUALLY GOOD

- **Score scale (0–100):** Coerced at MessageBus and CouncilGate; BUG 1 fixed.
- **Single council.verdict publisher:** Only council_gate.py; BUG 2 fixed.
- **Council health:** _check_council_health in runner; degraded/critical logging.
- **Circuit breakers:** Enforced in council_gate (pre-council) and order_executor (gates 2b/2c, etc.).
- **Emergency flatten:** Implemented with lock and retry; auth on endpoints.
- **HITL:** hitl.approval_needed has subscriber; forwards to alert.health.
- **Feedback loop:** update_agent_weights(outcome=...) does call WeightLearner.update_from_outcome(); OutcomeTracker also feeds council_record + update_agent_weights; main.py also calls update_from_outcome on outcome.resolved.
- **WeightLearner.record_decision:** Called from CouncilGate; _decision_history populated; matching by trade_id works when trade_id is provided.
- **E2E / council tests:** test_e2e_audit_enhancements and test_council_invocation_single_path pass (13 tests).

---

---

## 15. FIXES APPLIED IN-REPO (same session)

- **P0 #1 (verdict pipeline):** TradeExecutionRouter is now started in `main.py` after OrderExecutor; `execution.validated_verdict` added to `message_bus.VALID_TOPICS`; router stopped on shutdown. Verdicts now flow: council.verdict → TradeExecutionRouter → execution.validated_verdict → OrderExecutor.
- **P0 #2 (learning attribution):** `_on_outcome_resolved` now passes `trade_id=outcome_data.get("council_decision_id") or outcome_data.get("order_id")` to `WeightLearner.update_from_outcome()` so matching uses council_decision_id when available.
- **Tests:** `test_order_executor` updated to expect `execution.validated_verdict` subscription and to allow `execution.result` publish on hold/reject (audit trail). All 32 targeted tests pass.

*Re-verify in your environment before deploying live capital.*
