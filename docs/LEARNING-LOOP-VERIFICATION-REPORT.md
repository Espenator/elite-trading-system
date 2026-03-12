# LEARNING LOOP VERIFICATION REPORT

**Date:** March 12, 2026  
**Branch:** verify/learning-loop-e2e  
**Context:** Architectural Review March 11, 2026 — Section 3 (Feedback Loop & Learning System)

---

## Dropout Point Status

| # | Dropout | Arch Review Status | Current Status | Evidence |
|---|---------|-------------------|----------------|----------|
| 1 | Decision persistence | In-memory 500 cap | **PARTIAL** | `feedback_loop.py`: decisions still in db_service config store (MAX_DECISIONS=500). `record_decision()` now stores `trade_id=council_decision_id` (runner.py L814). WeightLearner still keeps 500 in memory; matching uses trade_id. |
| 2 | Shadow censoring | 45-55% loss | **CONFIGURABLE** | `shadow_tracker.py` / `outcome_tracker.py`: `_resolve_shadow_timeout()` respects `SHADOW_TIMEOUT_POLICY` / `OUTCOME_TIMEOUT_POLICY`. `mark_to_market` + last_known_price → `is_censored=False` (L371-374). Default remains `censor`; set env to `mark_to_market` for learning on timeout. |
| 3 | Confidence floor | 0.5 too strict | **FIXED** | `weight_learner.py` L37: `LEARNER_MIN_CONFIDENCE = 0.20`. Confirmed. |
| 4 | Decision-outcome match | Symbol-only | **FIXED** | `feedback_loop.py`: match by `trade_id` first (L116-119), symbol fallback only when no trade_id. `runner.py`: `trade_id=context.get("trade_id") or blackboard.council_decision_id`. Order payload and OutcomeTracker now carry `council_decision_id` → outcome uses it as `trade_id`. |
| 5 | update_from_outcome() never called | Never called | **FIXED** | `feedback_loop.update_agent_weights(outcome=...)` calls `learner.update_from_outcome(...)` (L216-222). `outcome_tracker._resolve_position()` passes `outcome_data` and calls `update_agent_weights(outcome=outcome_data)` (L527). Confirmed. |

---

## Full Outcome Chain (Trace Points)

| Step | File:Line | Status | Notes |
|------|-----------|--------|------|
| OrderExecutor submits order with council_decision_id | order_executor.py:561, 691-697 | OK | `ExecutionDecision(council_decision_id=verdict_data.get("council_decision_id"))`, `to_order_payload()` includes it. |
| order.submitted payload has council_decision_id | execution_decision.py:77-79 | OK | `payload["council_decision_id"]` when set. |
| OutcomeTracker receives order, stores council_decision_id | outcome_tracker.py:172-196, 56 | OK | `TrackedPosition.council_decision_id`, set from `data.get("council_decision_id")`. |
| OutcomeTracker resolves → record_outcome + update_agent_weights | outcome_tracker.py:511-532 | OK | `trade_id_for_learning = pos.council_decision_id or pos.order_id`. |
| feedback_loop.record_outcome matches by trade_id | feedback_loop.py:114-126 | OK | Prefer trade_id match. |
| feedback_loop.update_agent_weights calls learner.update_from_outcome | feedback_loop.py:216-222 | OK | With outcome_id=trade_id. |
| WeightLearner.update_from_outcome uses trade_id/outcome_id | weight_learner.py:296-313 | OK | Match by trade_id first, then outcome_id, then symbol. |
| WeightLearner record_decision uses council_decision_id | weight_learner.py:147 | OK | `trade_id = getattr(decision, "council_decision_id", "") or getattr(decision, "decision_id", "")`. |

---

## Retention Test Results

- **Test:** `tests/test_learning_retention.py::TestLearningRetention::test_simulate_100_outcomes_retention_rate`
- Outcomes simulated: 100  
- Outcomes reaching WeightLearner: 100/100  
- Retention rate: **100%** (target: ≥ 70%)  
- All 6 learning retention tests pass.

---

## Knowledge Systems

| System | Status | Evidence |
|--------|--------|----------|
| WeightLearner per-regime | **YES** | `weight_learner.py`: `_regime_weights` dict, `get_regime_weight()`, `update_from_outcome()` updates `_regime_weights[agent][entry_regime]` (L371-375). |
| HeuristicEngine MIN_SAMPLE | **10** | Lowered from 25 to 10 in `heuristic_engine.py` (Phase C / arch review). Heuristics formed when memory bank has enough resolved memories. |
| KnowledgeGraph queried in council | **YES** | `runner.py` L234-261: `get_heuristic_engine()`, `get_active_heuristics(regime)`, `knowledge_context` with confirmations/contradictions. |

---

## Debate Learning

- **DuckDB:** `debate_logs` table exists (`duckdb_storage.py` L553), with `council_decision_id` and index.
- **Council decisions:** `council_decisions` table populated in `runner.py` (L695+) with `decision_id`, `council_decision_id`, agent votes, etc.
- **Debate engine:** Debate agents run in Stage 5.5; votes flow into arbiter. Persistence of debate votes to `debate_logs` is schema-ready; population depends on debate engine writing rows (not fully traced in this run).

---

## Changes Made

1. **backend/app/council/runner.py** — `record_decision(..., trade_id=context.get("trade_id") or blackboard.council_decision_id)` so decisions are stored with council_decision_id for matching.
2. **backend/app/services/execution_decision.py** — Added `council_decision_id: str = ""` to `ExecutionDecision`; `to_order_payload()` includes it when set.
3. **backend/app/services/order_executor.py** — Build `ExecutionDecision` with `council_decision_id=verdict_data.get("council_decision_id", "")`. Added `[LEARNING-TRACE]` log on order.submitted.
4. **backend/app/services/outcome_tracker.py** — `TrackedPosition.council_decision_id`; set from order payload; use `trade_id_for_learning = pos.council_decision_id or pos.order_id` when calling feedback_loop and update_agent_weights. Added `[LEARNING-TRACE]` logs.
5. **backend/app/council/feedback_loop.py** — Added `[LEARNING-TRACE]` logs when matching and when calling weight_learner.update_from_outcome.
6. **backend/app/council/weight_learner.py** — `record_decision()` uses `council_decision_id` (DecisionPacket) for trade_id. Added `[LEARNING-TRACE]` when outcome accepted.
7. **backend/app/knowledge/heuristic_engine.py** — `MIN_SAMPLE = 10` (from 25).
8. **backend/tests/test_learning_retention.py** — New: tests for trade_id storage, match by trade_id, update_agent_weights → update_from_outcome, confidence floor 0.20, regime-stratified weights, 100-outcome retention ≥ 70%.

---

## Remaining Issues

1. **Decision history persistence:** Feedback loop and WeightLearner still keep last 500 decisions in config/memory. For full restart resilience, consider persisting decision history to DuckDB (as in council_decisions) and loading on startup.
2. **Shadow timeout default:** Default `SHADOW_TIMEOUT_POLICY=censor` preserves old behavior. Set `SHADOW_TIMEOUT_POLICY=mark_to_market` (and ensure price available) to get learning on timeout.
3. **E2E test:** `test_e2e_pipeline.py::test_e2e_swarm_idea_to_order_submitted` fails in this run for unrelated reasons (regime HYPERSWARM blocks entries; AAPL price=0). No change made to that test.

---

## Tests

- **Before:** 977+ passing (project_state.md).
- **After:** 558+ passed (excluding test_e2e_pipeline), 1 failed (test_e2e_swarm_idea_to_order_submitted — pre-existing environment/regime/price).
- **New tests added:** 6 in `test_learning_retention.py` (all passing).

---

## Commit Message

```
verify(learning): wire council_decision_id through order→outcome→WeightLearner; add LEARNING-TRACE logs and retention tests

- runner: record_decision trade_id = council_decision_id for matching
- ExecutionDecision + order payload + TrackedPosition: carry council_decision_id
- OutcomeTracker: use council_decision_id as trade_id when feeding feedback_loop
- WeightLearner: record_decision uses council_decision_id; LEARNER_MIN_CONFIDENCE=0.20 confirmed
- HeuristicEngine: MIN_SAMPLE 25 → 10
- Add test_learning_retention.py (6 tests, 100% retention in sim)
```
