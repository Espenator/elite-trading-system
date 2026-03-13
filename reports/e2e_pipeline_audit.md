# End-to-End Trading Pipeline Audit — Phase 4

**Date**: 2026-03-12  
**Scope**: Paper-trading pipeline from market_data.bar → signal → council → order → fill → persistence → learning  
**Mode**: PAPER only (no live orders). Evidence from code, tests, and runtime where available.

---

## Executive summary

| Area | Status | Notes |
|------|--------|------|
| 4.1 Signal → Council → Order | ⚠️ NEEDS ATTENTION | E2E test PASS (mocked); real bar→signal→order not run (requires Alpaca stream). Council size doc inconsistency (33 vs 35). |
| 4.2 Fill → Outcome → Learning | ✅ PASS | Code path and E2E test verified. outcome.resolved → WeightLearner; trade_stats_service → DuckDB. |
| 4.3 Risk gates | ✅ PASS | RED/CRISIS, position limit, portfolio heat, pre-trade checks implemented and code-verified. |

**Critical live-trading blocker (elevated)**: None identified. For full paper-trading proof with real Alpaca paper account, run backend with `TRADING_MODE=paper`, `AUTO_EXECUTE_TRADES=true` (or keep false for shadow), wait for market_data.bar or trigger via API, and capture logs/screenshots per artifacts below.

---

## 1. Timeline table (evidence per stage)

| Step | Timestamp | Latency | Evidence |
|------|-----------|---------|----------|
| 1. market_data.bar | — | — | **Code**: `backend/app/main.py` ~693: `_stream_manager` (AlpacaStreamManager) publishes to MessageBus `market_data.bar`. `backend/app/services/signal_engine.py` 522: `await self.message_bus.subscribe("market_data.bar", self._on_new_bar)`. |
| 2. SignalEngine generates signal | — | — | **Code**: `backend/app/services/signal_engine.py` 539–589: `_on_new_bar` builds quote_rows, `_compute_composite_score`, regime-adaptive threshold from config. Score ≥ threshold → `signal.generated` (see `backend/app/services/signal_engine.py` ~600+). **Test**: E2E asserts `signal.generated` with score 0–100. |
| 3. CouncilGate invokes council | — | — | **Code**: `backend/app/council/council_gate.py` 116–120: subscribes to `signal.generated`; 273–327: `_evaluate_with_council` calls `run_council()` with timeout (default 90s). **Test**: `tests/test_e2e_pipeline.py` 111–118: stub `run_council`; 181: `assert len(verdicts) >= 1`. |
| 4. Council completes (< 2s target) | — | — | **Code**: `backend/app/council/runner.py`: 7-stage DAG; `_check_council_health(..., total_agents=33)`. **Evidence**: No live run captured. E2E uses stubbed council. **Verdict**: ⏭️ SKIPPED for latency — requires live council run + timestamp log. |
| 5. Arbiter produces BUY/SELL/HOLD | — | — | **Code**: `backend/app/council/runner.py` (arbiter call after Stage 6); `backend/app/council/arbiter.py`: `arbitrate(votes)` → DecisionPacket. **Test**: E2E 181–182: `execution_ready is True`, `final_direction == "buy"`. |
| 6. OrderExecutor places order | — | — | **Code**: `backend/app/services/order_executor.py` 186: subscribes to `council.verdict`; 550–559: builds ExecutionDecision; 618–696: `_submit_order` → Alpaca → `publish("order.submitted", payload)`. **Test**: 185: `assert len(orders_submitted) >= 1`, symbol E2E. |
| 7. Order in Alpaca dashboard | — | — | ⏭️ SKIPPED. No paper order placed this audit; would require AUTO_EXECUTE + paper account + screenshot. |
| 8. WebSocket broadcast | — | — | **Code**: `backend/app/main.py` 508–509: `subscribe("order.submitted", _bridge_order_to_ws)`, `subscribe("order.filled", _bridge_order_to_ws)`; 501–506: `broadcast_ws("order", {"type": "order_update", "order": order_data})`. |
| 9. Slack notification | — | — | **Code**: `backend/app/main.py` 539, 553, 571: `_bridge_council_to_slack`, `_bridge_order_to_slack`, `_bridge_fill_to_slack`. Fires on council.verdict (BUY/SELL), order.submitted, order.filled. |
| 10. Fill captured | — | — | **Code**: `backend/app/services/order_executor.py` 933–968: `_poll_for_fill` → on status "filled" → `publish("order.filled", {...})`, `_record_fill_outcome`. |
| 11. Trade in DuckDB | — | — | **Code**: `backend/app/services/trade_stats_service.py` 207–295: `record_outcome(symbol, side, entry_price, exit_price, qty, ...)` INSERT into `trade_outcomes`. Called from outcome path (position close). OutcomeTracker → outcome.resolved; feedback_loop / trade_stats record. |
| 12. WeightLearner updated | — | — | **Code**: `backend/app/main.py` 969–991: `_on_outcome_resolved` → `get_weight_learner().update_from_outcome(symbol, outcome_direction, pnl, r_multiple, is_censored=...)`. **Test**: `tests/test_e2e_pipeline.py` 289–311: `update_from_outcome` and weight increase for correct agent. |

---

## 2. Verdict integrity

| Item | Evidence |
|------|----------|
| **Council size** | **33 agents** (runtime). `backend/app/council/registry.py`: `AGENTS` list has 33 entries; `get_agent_count()` returns 33. CLAUDE.md/docs say "35-agent" — **inconsistency**: treat 33 as source of truth unless product explicitly adds 2. |
| **Completion time** | Not measured this audit. Council timeout: `COUNCIL_GLOBAL_TIMEOUT` env (default 90s). For < 2s claim: add timing in `council_gate.py` around `run_council()` and log. |
| **Arbiter result** | DecisionPacket with `final_direction`, `execution_ready`, `vetoed`. E2E test asserts verdict has `execution_ready=True`, `final_direction="buy"`. |

**Code references**

- Council registry: `backend/app/council/registry.py` lines 8–52 (AGENTS), 75–76 (get_agent_count).
- CouncilGate invoke: `backend/app/council/council_gate.py` 273–327 (`_evaluate_with_council`), 320–327 (`run_council`, timeout).
- Arbiter: `backend/app/council/arbiter.py`; runner assembles votes and calls arbiter.

---

## 3. Learning loop

| Check | Status | Evidence |
|-------|--------|----------|
| Fill captured? | ✅ PASS | OrderExecutor `_poll_for_fill` publishes `order.filled` (order_executor.py 955–967, 986–999). |
| DuckDB recorded? | ✅ PASS | TradeStatsService.record_outcome() INSERT into `trade_outcomes` (trade_stats_service.py 231–295). OutcomeTracker on position close → outcome.resolved; resolver/trade_stats record outcome. |
| WeightLearner updated? | ✅ PASS | main.py 969–991: subscriber to `outcome.resolved` calls `learner.update_from_outcome(...)`. test_e2e_fill_to_weight_learner_update: 289–311 asserts weight increase for correct agent. |

**Flow (code)**

1. Order fill: `order_executor.py` 955 → `publish("order.filled", ...)`.
2. OutcomeTracker: subscribes to `order.submitted` / `order.filled` (outcome_tracker.py 141–142); on position close publishes `outcome.resolved` (outcome_tracker.py 427, 606).
3. main.py 1016: `subscribe("outcome.resolved", _on_outcome_resolved)` → WeightLearner.update_from_outcome (984–989).
4. trade_stats_service.record_outcome (220–295): DuckDB `trade_outcomes` INSERT; optionally calls WeightLearner (304–312).

---

## 4. Risk gates (blocked-orders section)

All checks implemented in `backend/app/services/order_executor.py`. No live “blocked order” run this audit; evidence is code + params only.

| Gate | Status | Evidence |
|------|--------|----------|
| **RED/CRISIS regime blocks order** | ✅ PASS | Gate 2b: `_check_regime()` (295–311). Uses `REGIME_PARAMS` from `backend/app/api/v1/strategy.py` 177–186: RED `max_pos=0`, `kelly_scale=0.25`; CRISIS `max_pos=0`, `kelly_scale=0.0`. If `max_positions == 0 or kelly_scale == 0` → return `("reject", ...)` (304–305). order_executor 376–378: `if regime_result[0] == "reject"` → `_reject(...)`. |
| **Position size limit** | ✅ PASS | Gate 2d (386–411): `_REGIME_MAX_POSITIONS` CRISIS=0, RED=0; current positions from Alpaca; if `current_count >= max_pos` → reject. |
| **Portfolio heat > threshold** | ✅ PASS | Gate 7 (483–491): `_check_portfolio_heat(kelly_pct)`; if not heat_ok → `_reject(..., ExecutionDenyReason.PORTFOLIO_HEAT)`. |
| **Pre-trade check rejection** | ✅ PASS | Gates 1–9: council hold (261–269), execution_ready (264–269), mock source (271–278), regime (376–378), circuit breaker (384–386), drawdown (384–386), degraded/kill (391–394), daily limit (405–419), cooldown (422–431), sizing (396–455), homeostasis (458–481), heat (484–491), viability (494–509), Risk Governor (511–548). Any rejection → order not submitted. |

**Suggested adversarial test**: Unit test that feeds a verdict with `regime="RED"` and signal_data `regime="RED"` and asserts OrderExecutor does not call Alpaca submit (or that `_reject` is called).

---

## 5. Test and command evidence

### 5.1 E2E pipeline tests

```text
# Command (from repo root)
cd backend && python -m pytest tests/test_e2e_pipeline.py -v --tb=short
```

**Result**: 2 passed (1.18s).

- `test_e2e_swarm_idea_to_order_submitted`: swarm.idea → triage → signal.generated → council.verdict → order.submitted (with stubbed council and OrderExecutor Kelly).
- `test_e2e_fill_to_weight_learner_update`: decision recorded → order.filled / outcome.resolved → WeightLearner.update_from_outcome → weights updated.

**Saved output**: `artifacts/commands/e2e_pipeline_test_output.txt`

### 5.2 Council agent count

```text
# Command
cd backend && python -c "from app.council.registry import get_agent_count; print(get_agent_count())"
# Output: 33
```

---

## 6. Recommended artifacts (for future runs)

When running the full system in paper mode:

| Artifact | Path | How to capture |
|----------|------|----------------|
| Pipeline log | `/artifacts/logs/e2e_pipeline.log` | Redirect backend stdout/stderr or configure logging to file. |
| Order submission payload | `/artifacts/http/order_submission.json` | Log first `order.submitted` payload in a test or from MessageBus subscriber. |
| Alpaca paper order | `/artifacts/screenshots/alpaca_paper_order.png` | Manual screenshot of Alpaca paper dashboard after an order. |
| Frontend order update | `/artifacts/screenshots/frontend_order_update.png` | Screenshot of UI after order.submitted WS message. |
| DuckDB trade query | `/artifacts/commands/duckdb_trade_query.txt` | `SELECT * FROM trade_outcomes ORDER BY timestamp DESC LIMIT 10;` (or equivalent) output. |

---

## 7. Status summary (PASS/FAIL/SKIPPED/NEEDS ATTENTION)

| ID | Item | Status |
|----|------|--------|
| 4.1.1 | market_data.bar event exists and is consumed by SignalEngine | ✅ PASS (code) |
| 4.1.2 | SignalEngine generates signal (score ≥ threshold) | ✅ PASS (code + E2E) |
| 4.1.3 | CouncilGate invokes full council | ✅ PASS (code + E2E) |
| 4.1.4 | Council completes in < 2 s | ⏭️ SKIPPED (no live timing) |
| 4.1.5 | Arbiter produces BUY/SELL/HOLD | ✅ PASS (code + E2E) |
| 4.1.6 | OrderExecutor places order (when BUY/SELL) | ✅ PASS (code + E2E; Alpaca mocked) |
| 4.1.7 | Order visible in Alpaca dashboard | ⏭️ SKIPPED (no paper order run) |
| 4.1.8 | WebSocket broadcasts order to frontend | ✅ PASS (code) |
| 4.1.9 | Slack notification on verdict/order/fill | ✅ PASS (code) |
| 4.2.1 | Fill event captured | ✅ PASS (code) |
| 4.2.2 | Trade recorded in DuckDB | ✅ PASS (code: trade_outcomes) |
| 4.2.3 | WeightLearner receives outcome | ✅ PASS (code + E2E) |
| 4.2.4 | Agent weights updated from outcome | ✅ PASS (code + E2E) |
| 4.3.1 | RED/CRISIS regime blocks order | ✅ PASS (code) |
| 4.3.2 | Position size limit blocks order | ✅ PASS (code) |
| 4.3.3 | Portfolio heat blocks order | ✅ PASS (code) |
| 4.3.4 | Pre-trade rejection blocks order | ✅ PASS (code) |

**Doc fix**: `backend/app/council/council_gate.py` line 276 and `backend/app/main.py` line 427 say "13-agent council"; should be "33-agent" (or "35" if product definition includes non-voting components). Recommendation: align all docs with `registry.get_agent_count()` (33).

---

## 8. Conclusion

- **Pipeline path**: Signal → Council → Order → Fill → Outcome → Learning is implemented and covered by E2E tests with mocks. No evidence of a missing link.
- **Risk gates**: RED/CRISIS, position limit, portfolio heat, and other pre-trade checks are in place in OrderExecutor; no live blocked-order test was run.
- **Gaps**: (1) No live run from real `market_data.bar` through to paper order and Alpaca visibility. (2) Council latency < 2 s not measured. (3) Doc inconsistency: 33 vs 35 agents.

To fully satisfy “proof with evidence” for paper trading: run backend in paper mode, trigger or wait for one bar → signal → verdict → order, then capture logs, one `order.submitted` payload, Alpaca screenshot, and DuckDB trade query as in section 6.
