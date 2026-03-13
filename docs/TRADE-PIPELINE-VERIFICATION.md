# Trade Pipeline Verification — Signal → Council → Order

**Verified:** March 13, 2026

## 1. Council evaluate via API

- **Endpoint:** `POST /api/v1/council/evaluate` (auth required)
- **Request:** `CouncilEvalRequest` accepts `symbol`, optional `timeframe`, `score`, `direction`, `features`, `context`.
- **Test:** `tests/test_e2e_all_functions.py::TestCouncilEvaluate::test_council_evaluate_returns_direction_confidence_decision_id`
  - Sends `{"symbol":"AAPL","score":80,"direction":"buy"}` with `auth_headers`.
  - Asserts status 200 and response has `final_direction`, `final_confidence`, `council_decision_id`.
- **Flow:** Request → `run_council()` in `council/runner.py` → CouncilGate bridges `signal.generated` → council; API calls `run_council()` directly with symbol/context.

## 2. All 33 agents (registry) and veto rules

- **Registry:** `backend/app/council/registry.py` — `AGENTS` list has 33 entries; `get_agent_count()` ≥ 33.
- **VETO_AGENTS:** `council/arbiter.py` — `VETO_AGENTS = {"risk", "execution"}`. Only `risk_agent` and `execution_agent` may set `veto=True`.
- **Agent contract:** Each agent in `council/agents/` has `NAME`, `WEIGHT`, and `async evaluate(features, context) -> AgentVote` (agent_name, direction, confidence, reasoning, veto, weight).
- **Tests:**  
  - `test_council_registry_agents_and_veto_only_risk_execution` — registry count and VETO_AGENTS.  
  - `test_run_council_returns_35_votes` — run_council returns ≥ 25 votes (schema check; some agents may be skipped in coordinator mode).

## 3. Order executor gate chain and council_decision_id

- **File:** `backend/app/services/order_executor.py`
- **Gate order:** Gate 0 (decision TTL 30s) → Gate 1 (council approve, execution_ready) → Gate 2 (mock guard) → **Gate 2b (regime)** → **Gate 2c (circuit breaker)** → 2d (regime position count) → Gate 3 (daily limit) → Gate 4 (cooldown) → Gate 5 (drawdown) → Gate 5b/5c (degraded/kill switch) → **Gate 6 (Kelly sizing)** → 6b (homeostasis) → **Gate 7 (portfolio heat)** → **Gate 8 (viability)** → Gate 9 (risk governor) → build `ExecutionDecision` → submit.
- **council_decision_id:** Verdict’s `council_decision_id` is passed into `ExecutionDecision` and into `to_order_payload()`; every `order.submitted` payload includes `council_decision_id` when present.
- **Bracket orders:** When `ORDER_USE_BRACKETS=true` (env), `use_bracket_orders` is True; `_execute_order` sets `order_class="bracket"` with `take_profit` and `stop_loss` when both are present.

## 4. WebSocket after verdict and order

- **After council.verdict:** `main.py` subscribes to `council.verdict` and:
  - `broadcast_ws("council", { type, symbol, direction, confidence, council_decision_id, verdict })`
  - `broadcast_ws("council_verdict", { type: "council_verdict", verdict })`
- **After order.submitted:** `main.py` subscribes to `order.submitted` (and order.filled, order.cancelled) and `broadcast_ws("order", { type: "order_update", order: order_data })`. OrderExecutor also calls `_notify_frontend()` which `broadcast_ws("order", {...})`.

## 5. Frontend WebSocket subscriptions

- **Council:**  
  - `SwarmOverviewTab.jsx`, `RemainingTabs.jsx`: `ws.subscribe("council", handler)`.  
  - `TradeExecution.jsx`, `useCNS.jsx`: `council_verdict` channel (WS_CHANNELS.council_verdict).
- **Order:**  
  - `main.py` bridges `order.submitted` → `broadcast_ws("order", { type: "order_update", order: order_data })`.  
  - Frontend pages that subscribe to `"order"` receive this; data shape includes symbol, side, qty, price, and (from payload) `council_decision_id`.

## Rules enforced

- **VETO_AGENTS** = {risk, execution}; CouncilGate required; **council_decision_id** on every order (in ExecutionDecision and order payload); decisions expire 30s; DuckDB via `get_conn()` only.

## Run tests

```bash
cd backend && python -m pytest --tb=short -q
```

Key tests: `test_council_evaluate_returns_direction_confidence_decision_id`, `test_council_registry_agents_and_veto_only_risk_execution`, `test_run_council_returns_35_votes`, `test_execution_decision_to_order_payload`, and order executor / execution gate tests.
