# Cursor Agent Prompt — E2E Intelligence Pipeline & Council Backtest

> Copy everything below the line into Cursor as a single prompt. Spawn 8 agents to run test workstreams in parallel.

---

Read these files first (in order): `CLAUDE.md`, `project_state.md`, `PLAN.md`

## Mission

You are a **senior QA engineer** building and running comprehensive end-to-end tests for the Embodier Trader intelligence pipeline. This system trades real money. Every untested path is a potential loss. Your job is to verify that every stage of the intelligence pipeline — from raw market data to final trade execution to Bayesian weight learning — produces correct, profitable, and safe results.

**Output**: A structured test report (`docs/E2E-INTELLIGENCE-TEST-REPORT-2026-03.md`) with all findings, plus new test files in `backend/tests/` for any gaps discovered. Every finding must include specific file paths, expected vs actual behavior, and severity.

## System Context

- **Repo**: `elite-trading-system` — Python 3.11 FastAPI backend, 35-agent council DAG, DuckDB, Alpaca broker
- **Pipeline**: AlpacaStream → SignalEngine → CouncilGate → 35-agent council (7 stages) → Arbiter → OrderExecutor → Alpaca
- **Status**: v5.0.0, 981+ tests passing, CI GREEN, all phases complete
- **Testing stack**: pytest, async (anyio/asyncio), conftest.py monkey-patches DuckDB to in-memory
- **Key constraint**: All tests must mock external APIs (Alpaca, Ollama, UW, FRED) — never hit real services

## Test Infrastructure

### Existing Tests to Build On
- `backend/tests/test_e2e_pipeline.py` — Full pipeline: swarm.idea → triage → signal → council → order (USE THIS AS THE PATTERN)
- `backend/tests/test_council_dag_integration.py` — Council invocation + regime enforcement
- `backend/tests/conftest.py` — DuckDB in-memory, Alpaca mocks, shared fixtures

### Core Schemas
```python
# All agents return AgentVote — from council/schemas.py
@dataclass
class AgentVote:
    agent_name: str
    direction: str          # "buy" | "sell" | "hold"
    confidence: float       # 0.0 – 1.0
    reasoning: str
    veto: bool = False      # Only risk + execution can set True
    veto_reason: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    blackboard_ref: str = ""

# Council output — DecisionPacket
@dataclass
class DecisionPacket:
    symbol: str
    final_direction: str    # "buy" | "sell" | "hold"
    final_confidence: float
    votes: List[AgentVote]
    decision_id: str
    timestamp: float
    # ... additional fields
```

### Severity Levels for Findings
- `🔴 CRITICAL` — Pipeline produces wrong trade direction, loses money, or silently fails
- `🟠 HIGH` — Risk gate bypassed, weight learning incorrect, data corruption
- `🟡 MEDIUM` — Degraded accuracy, suboptimal sizing, missing edge case handling
- `🔵 LOW` — Code quality, test coverage gap, minor inconsistency

### Finding Format
```markdown
### [SEVERITY] Finding Title
- **Location**: `path/to/file.py` (lines X-Y)
- **Test**: What was tested
- **Expected**: What should happen
- **Actual**: What actually happens (or what's untested)
- **Impact**: What breaks or what risk this creates
- **Fix**: Specific remediation
```

---

## Test Workstreams — Spawn 8 Agents in Parallel

### WORKSTREAM 1: Full Pipeline E2E (Signal → Order)

**Scope**: The complete trading pipeline end-to-end, verifying every MessageBus hop and gate.

**Key files**: `council/council_gate.py`, `council/runner.py`, `council/arbiter.py`, `services/order_executor.py`, `services/signal_engine.py`, `core/message_bus.py`, `services/idea_triage.py`, `services/hyper_swarm.py`

**Existing pattern**: `tests/test_e2e_pipeline.py` (extend this — read it first, understand the MessageBus wiring + mock patterns)

Build and run these tests:

1. **BUY pipeline**: Publish a bullish swarm.idea → verify triage escalates → HyperSwarm generates signal (score=80) → CouncilGate invokes council → majority BUY votes → arbiter returns BUY → OrderExecutor submits buy order → `order.submitted` event fires. Assert every intermediate event on MessageBus.
2. **SELL pipeline**: Same flow but with bearish signal. Verify independent short scoring path (NOT `100 - blended` — that was the old bug). Confirm sell order is submitted with correct direction.
3. **HOLD pipeline**: Signal generates but council votes majority HOLD → verify NO order is submitted, NO `order.submitted` event. This is the "do nothing" path — it must work silently.
4. **VETO pipeline**: Risk agent sets `veto=True` → verify trade is blocked REGARDLESS of majority vote. Test both risk and execution agent vetoes. Verify only these two agents can veto — patch a non-veto agent to set `veto=True` and confirm it's IGNORED.
5. **Decision expiry**: Generate a verdict, wait >30 seconds (mock time), then attempt execution → verify OrderExecutor rejects the stale decision. Assert `decision_id` traceability: every order must reference the `council_decision_id` that authorized it.
6. **Concurrent signals**: Publish 3 signals simultaneously for different symbols → verify CouncilGate's semaphore (max 2 concurrent councils) queues the 3rd correctly. No race conditions, no dropped signals.
7. **Signal below threshold**: Publish signal with score=50 (below GREEN threshold of 55) → verify CouncilGate does NOT invoke council. Counter `_councils_invoked` must not increment.
8. **Pipeline latency**: Measure wall-clock time from `signal.generated` to `council.verdict`. Assert < 5 seconds for mocked agents (real target is < 1.5s but mocks add overhead).

**Output**: New test file `tests/test_e2e_full_pipeline.py` with all 8 tests passing. Report any pipeline bugs found.

---

### WORKSTREAM 2: Council DAG Integrity (35 Agents, 7 Stages)

**Scope**: Verify the 35-agent council runs correctly — every agent produces valid output, stages execute in order, parallel stages are truly parallel, and the blackboard accumulates state.

**Key files**: `council/runner.py` (29.4 KB — the DAG orchestrator), `council/agents/` (32 agent files), `council/blackboard.py`, `council/schemas.py`, `council/agent_config.py`, `council/task_spawner.py`

**Agent inventory** (verify ALL are registered and callable):

Stage 1 (13 agents, parallel): market_perception, flow_perception, regime, social_perception, news_catalyst, youtube_knowledge, intermarket, gex, insider, finbert_sentiment, earnings_tone, dark_pool, macro_regime

Stage 2 (8 agents, parallel): rsi, bbv, ema_trend, relative_strength, cycle_timing, supply_chain, institutional_flow, congressional

Stage 3 (2 agents, parallel): hypothesis, layered_memory

Stage 4 (1 agent, sequential): strategy

Stage 5 (3 agents, parallel): risk, execution, portfolio_optimizer

Stage 5.5 (3 agents, parallel): bull_debater, bear_debater, red_team

Stage 6 (1 agent, sequential): critic

Build and run these tests:

1. **Agent schema compliance**: For each of the 35 agents, call `evaluate()` with a synthetic feature vector and verify it returns a valid `AgentVote` with: `agent_name` matches `NAME`, `direction` in {"buy", "sell", "hold"}, `confidence` in [0.0, 1.0], non-empty `reasoning`, `weight` > 0. Use these synthetic features:
   ```python
   features = {
       "features": {
           "regime": "GREEN", "close": 150.0, "open": 148.0, "high": 151.0,
           "low": 147.5, "volume": 50000000, "sma_20": 149.0, "sma_50": 147.0,
           "rsi_14": 55.0, "atr_14": 2.5, "bb_upper": 153.0, "bb_lower": 145.0,
           "macd": 0.5, "macd_signal": 0.3, "vix": 18.5, "put_call_ratio": 0.85,
           "gex": 500000000, "dix": 0.45, "sector": "Technology",
           "market_cap": 2500000000000, "pe_ratio": 28.5
       }
   }
   ```
2. **Stage ordering**: Instrument `runner.py` to log stage start/end timestamps. Verify: Stage 1 completes before Stage 2 starts, Stage 2 before Stage 3, etc. Within parallel stages (1, 2, 3, 5, 5.5), verify agents start concurrently (within 50ms of each other).
3. **Blackboard accumulation**: After each stage, verify blackboard has accumulated the expected keys. After Stage 1, blackboard should have regime data, perception data. After all stages, blackboard should have complete state. Verify no stage overwrites another stage's data.
4. **Debate influence**: Run council twice with identical features: once with debate agents enabled, once disabled. Verify the arbiter's final confidence differs — proving debate actually influences the verdict (not just cosmetic). Document the delta.
5. **VETO enforcement**: Patch risk_agent to veto → verify final direction is HOLD regardless of 34 BUY votes. Patch a random non-veto agent (e.g., rsi_agent) to set veto=True → verify it's IGNORED and trade proceeds.
6. **REQUIRED_AGENTS**: Remove `regime` agent from the DAG (mock it to raise Exception) → verify runner handles this gracefully (not crash). Document whether it falls back to HOLD or uses remaining agents.
7. **Agent timeout**: Mock one agent to take 30 seconds → verify runner's per-agent timeout kicks in and the DAG continues without it. The slow agent's vote should be absent but the council should still produce a verdict.
8. **Empty/malformed features**: Pass `features={}` and `features=None` → verify NO agent crashes. All should gracefully return HOLD with low confidence, not raise unhandled exceptions.

**Output**: New test file `tests/test_council_dag_full.py`. Report any agents that crash, return invalid votes, or don't honor the schema.

---

### WORKSTREAM 3: Arbiter & Bayesian Weight Learning Backtest

**Scope**: Verify the arbiter's weighted voting math is correct AND the weight learner's Bayesian updates converge to profitable weights over simulated trading history.

**Key files**: `council/arbiter.py` (6.4 KB), `council/weight_learner.py` (14.8 KB), `council/schemas.py`, `data/storage.py` (for agent_weights table), `jobs/daily_outcome_update.py`

Build and run these tests:

1. **Arbiter math — unanimous BUY**: 35 agents all vote BUY with confidence 0.8 → verify final_direction="buy", final_confidence > 0.8 (should be near 1.0 with Bayesian weighting). No vote should be ignored.
2. **Arbiter math — split votes**: 20 BUY (conf 0.7), 10 SELL (conf 0.6), 5 HOLD (conf 0.5) → verify direction matches the Bayesian-weighted majority, not simple count. Higher-weight agents (risk=1.5, regime=1.2) should pull the result.
3. **Arbiter math — edge cases**: (a) All HOLD → verify HOLD. (b) All votes veto'd → verify HOLD with confidence 0. (c) Single vote → verify it becomes the verdict. (d) All confidence=0 → verify HOLD. (e) NaN weight → verify handled (not crash, not NaN propagation).
4. **Weight learner — single update**: Agent "risk" votes BUY with conf 0.7 on AAPL. Trade outcome: +3% profit. Verify Beta(α,β) updates correctly: α increases (successful prediction). Verify weight increases from baseline.
5. **Weight learner — negative update**: Agent "rsi" votes BUY with conf 0.9 on TSLA. Trade outcome: -5% loss. Verify β increases (wrong prediction). Verify weight decreases. Verify it doesn't go below confidence floor 0.20.
6. **Weight learner — convergence backtest**: Simulate 100 council decisions:
   - Agent A: correct 80% of time → should converge to HIGH weight
   - Agent B: correct 50% of time → should converge to MEDIUM weight
   - Agent C: correct 20% of time → should converge to LOW weight (near floor)
   Plot or log the weight trajectory. Verify ordering: weight_A > weight_B > weight_C after 100 rounds.
7. **Regime-stratified learning**: Same agent votes in GREEN and RED regimes. Correct in GREEN (70%), wrong in RED (30%). Verify GREEN weight > RED weight for this agent. Verify regime stratification stores separate Beta params.
8. **Brier score calibration**: Agent says "buy" with confidence 0.9, ten times. 9 trades profit, 1 loses. Compute Brier score. Verify it's < 0.1 (well-calibrated). Agent says "buy" with confidence 0.9, ten times, only 5 profit. Verify Brier score is > 0.3 (poorly calibrated).
9. **Persistence**: Run weight updates, then call get_conn() and verify `agent_weights` table has the updated Beta(α,β) values. Restart weight learner, verify it loads persisted weights (not reset to defaults).
10. **Confidence floor enforcement**: Set an agent's Beta params so its derived weight would be 0.05. Verify the floor clamps it to 0.20. Verify the old floor of 0.50 is NOT in effect (this was a Phase C fix).

**Output**: New test file `tests/test_arbiter_weight_learning.py`. Include a simulated 100-decision backtest with weight convergence verification. Report any math bugs in arbiter or weight learner.

---

### WORKSTREAM 4: Regime-Adaptive Pipeline Testing

**Scope**: Verify that the entire pipeline adapts correctly to market regime changes — thresholds shift, risk gates activate, Kelly scaling adjusts.

**Key files**: `council/regime/bayesian_regime.py`, `council/council_gate.py`, `api/v1/strategy.py` (REGIME_PARAMS), `services/order_executor.py`, `council/reflexes/circuit_breaker.py`, `services/kelly_position_sizer.py`

Build and run these tests:

1. **Signal gate thresholds by regime**:
   - GREEN regime: signal score=56 → council INVOKED (threshold 55). Score=54 → NOT invoked.
   - YELLOW/NEUTRAL regime: score=66 → invoked (threshold 65). Score=64 → NOT invoked.
   - RED regime: score=76 → invoked (threshold 75). Score=74 → NOT invoked.
   - CRISIS regime: score=76 → invoked (threshold 75). Score=74 → NOT invoked.
   For each, verify by checking `_councils_invoked` counter on CouncilGate.
2. **Gate 2b — regime blocks new entries**:
   - RED regime: `REGIME_PARAMS["RED"]["max_pos"]` must equal 0. Verify OrderExecutor rejects new BUY orders (existing positions can still be managed).
   - CRISIS regime: same enforcement plus `kelly_scale` ≤ 0.25.
   - GREEN regime: `max_pos` > 0, normal trading allowed.
3. **Regime transition mid-pipeline**: Start processing a signal in GREEN regime (threshold=55, score=60 passes). Before council completes, regime transitions to RED. Verify: (a) the already-in-flight council completes normally, (b) the resulting verdict is checked against RED regime's max_pos=0 before execution, (c) the order is BLOCKED even though the signal originally qualified.
4. **Kelly scale by regime**:
   - GREEN: kelly_scale=1.0 → full Kelly position size
   - YELLOW: kelly_scale≤0.50 → half or less Kelly
   - RED: kelly_scale≤0.25 → quarter Kelly or less
   Use the Kelly sizer with identical edge/win_rate across regimes and verify position sizes scale correctly.
5. **Regime detection accuracy**: Feed bayesian_regime with known market conditions:
   - VIX=12, SPY trending up, breadth positive → should return GREEN
   - VIX=25, SPY flat, mixed breadth → should return YELLOW/NEUTRAL
   - VIX=35, SPY down 3%, breadth negative → should return RED
   - VIX=50+, SPY down 7%, circuit breakers → should return CRISIS
   Verify the regime classifier handles these scenarios (may need to check what inputs it actually uses).
6. **Regime persistence**: Verify regime state is written to blackboard and accessible to all agents. After regime transition, verify all downstream consumers see the new regime (not cached stale regime).
7. **Historical regime backtest**: Query DuckDB for historical bars across different market conditions. Run regime classifier on each period. Verify regime labels make sense (not stuck on one regime, not flipping every bar).

**Output**: New test file `tests/test_regime_adaptive_pipeline.py`. Report any threshold misconfigurations or regime gate bypasses.

---

### WORKSTREAM 5: Order Execution & Risk Gate Verification

**Scope**: Verify the full order execution chain — from council verdict to Alpaca order submission — with all risk gates properly enforced.

**Key files**: `services/order_executor.py`, `services/kelly_position_sizer.py`, `services/position_manager.py`, `services/alpaca_service.py`, `council/reflexes/circuit_breaker.py`, `services/execution_decision.py`

Build and run these tests:

1. **Happy path**: Council verdict BUY AAPL, confidence 0.8, regime GREEN → Kelly sizer computes position → viability check passes → order submitted to Alpaca. Verify: (a) correct symbol, (b) correct side ("buy"), (c) position size matches Kelly calculation, (d) order type is correct for notional (market < $5K, limit $5K-$25K, TWAP > $25K).
2. **Gate 2c circuit breakers**:
   - Leverage check: Mock portfolio at 1.9x leverage → order passes. Mock at 2.1x → order BLOCKED. Verify the 2x limit.
   - Concentration check: Single position would be 26% of portfolio → order BLOCKED (25% limit). At 24% → passes.
   - Verify both checks are ENFORCED (not just advisory/logged). The order must NOT reach Alpaca when blocked.
3. **Market/limit/TWAP routing**:
   - $3K notional → market order (verify `type="market"`)
   - $15K notional → limit order (verify `type="limit"`, limit_price set with spread buffer)
   - $30K notional → TWAP (verify sliced into multiple orders over time)
4. **Partial fill handling**: Mock Alpaca returning 60% fill on a limit order → verify: (a) retry logic fires (up to 3 retries), (b) remaining 40% is retried, (c) after 3 failed retries the remainder converts to market order, (d) partial position is still tracked correctly.
5. **Portfolio heat**: Set `MAX_PORTFOLIO_HEAT` to 0.06 (6%). Current heat = 5%. New order would add 2% heat → BLOCKED (total would be 7% > 6%). New order would add 0.5% heat → PASSES (5.5% < 6%). Verify `last_equity` is used (not stale equity).
6. **Bracket orders**: BUY order → verify OCO bracket is placed with: (a) stop-loss at entry - 2×ATR, (b) take-profit at entry + 3×ATR (or whatever the R-multiple target is). Verify ATR is sourced from features, not hardcoded.
7. **Emergency flatten**: Trigger emergency flatten → verify ALL positions have sell/cover orders submitted. Verify it works even when Alpaca is slow (retry + exponential backoff). Verify DuckDB `pending_liquidations` queue is used for crash recovery.
8. **Paper vs live safety**: Verify `TRADING_MODE` is checked at startup. In paper mode, orders go to paper endpoint. Verify there's no code path that could accidentally send a paper-mode signal to the live Alpaca account.
9. **Kelly edge cases**: (a) Negative edge → position size = 0 (don't trade). (b) Win rate = 100% → capped at `KELLY_MAX_ALLOCATION` (0.25). (c) Zero trades (no history) → use default conservative sizing. (d) Very small edge (0.01) → verify minimum position check.

**Output**: New test file `tests/test_order_execution_gates.py`. Report any risk gate bypasses or sizing errors.

---

### WORKSTREAM 6: Data Quality & Graceful Degradation

**Scope**: Verify the pipeline handles missing, stale, or corrupt data from any of the 10 data sources without crashing or producing dangerous trades.

**Key files**: `council/data_quality.py` (9 KB), `features/feature_aggregator.py`, `services/` (all data source services), `council/agents/` (all 35 agents), `core/message_bus.py`

Build and run these tests:

1. **Per-source degradation** — For EACH of these 10 sources, mock it as unavailable (raise ConnectionError) and verify the pipeline still produces a verdict (degraded but not crashed):
   - Alpaca (bars + quotes) — CRITICAL: pipeline should HOLD if price data is missing
   - Unusual Whales (options flow) — degrade: GEX/dark_pool/congressional agents return HOLD
   - Finviz (fundamentals) — degrade: screener data missing, fundamental ratios None
   - FRED (macro) — degrade: macro_regime_agent uses cached/default regime
   - SEC EDGAR (insider) — degrade: insider_agent returns HOLD
   - NewsAPI (news) — degrade: news_catalyst_agent returns HOLD
   - Benzinga (earnings) — degrade: earnings_tone_agent returns HOLD
   - SqueezeMetrics (DIX/GEX) — degrade: GEX agent uses UW fallback or HOLD
   - Capitol Trades (congressional) — degrade: congressional_agent returns HOLD
   - Senate Stock Watcher — degrade: fallback already, just HOLD
2. **Feature aggregator with missing data**: Call feature_aggregator with only partial data (e.g., OHLCV but no options data, no macro data). Verify: (a) it returns a feature dict with None/NaN for missing fields, (b) it does NOT crash, (c) data quality score reflects the missing data.
3. **Data quality → council confidence**: When data_quality score is LOW (< 0.3), verify: (a) council's final_confidence is penalized/scaled down, (b) if confidence drops below execution threshold, order is not placed. The system should abstain when data quality is poor.
4. **Stale data detection**: Mock Alpaca returning bars from 2 hours ago (stale). Verify the pipeline detects staleness and either: (a) flags the data quality, (b) rejects the signal, or (c) reduces confidence. Document actual behavior.
5. **All 35 agents with None features**: Call each agent's `evaluate(features={})` and `evaluate(features={"features": {}})`. Verify ZERO crashes across all 35 agents. Every agent should return a valid AgentVote (likely HOLD with low confidence).
6. **MessageBus failure**: Mock MessageBus.publish() to raise an exception. Verify: (a) the publisher doesn't crash, (b) the failure is logged, (c) the pipeline continues (events are fire-and-forget for non-critical channels).
7. **DuckDB unavailable**: Mock `get_conn()` to raise. Verify: (a) endpoints return 503 (not 500 or hang), (b) the server doesn't crash, (c) in-memory fallbacks are used where possible.
8. **Rate limit handling**: Simulate rapid signal generation (100 signals in 1 second). Verify: (a) CouncilGate's semaphore limits concurrent councils, (b) excess signals are queued (not dropped), (c) no OOM from unbounded queue growth.

**Output**: New test file `tests/test_data_quality_degradation.py`. Report any agents that crash on missing data or any source failures that cascade into pipeline crashes.

---

### WORKSTREAM 7: Historical Backtest Simulation

**Scope**: Run the council decision engine against historical market data and verify backtest infrastructure produces meaningful, reproducible results.

**Key files**: `services/backtest_engine.py`, `api/v1/backtest_routes.py`, `jobs/weekly_walkforward_train.py`, `services/walk_forward_validator.py`, `services/execution_simulator.py`, `modules/ml_engine/`

Build and run these tests:

1. **Backtest engine smoke test**: Run a basic backtest over 30 days of historical AAPL data (from DuckDB `daily_ohlcv`). Verify output contains: total_return, sharpe_ratio, max_drawdown, win_rate, total_trades, trade_list. All values should be reasonable (not NaN, not infinity, drawdown ≤ 0).
2. **Council replay backtest**: For each historical bar, feed features through `run_council()` (with mocked LLM agents) and record the verdict. Compare against actual price movement over the next 1-5 bars. Compute: hit rate (direction correct?), average R-multiple, regime-stratified accuracy. This is the CORE backtest — does the council actually predict direction?
3. **Walk-forward validation**: Run `walk_forward_validator` with train=60 days, test=20 days, step=10 days. Verify: (a) train/test windows don't overlap (no look-ahead bias), (b) model is retrained at each step, (c) out-of-sample performance is reported separately from in-sample.
4. **Regime-stratified backtest**: Run the same backtest but report results separately for GREEN, YELLOW, RED, CRISIS periods. Verify: (a) GREEN period has best performance, (b) RED/CRISIS periods show the system correctly abstains or reduces sizing. If RED periods show aggressive trading, this is a 🔴 CRITICAL finding.
5. **Monte Carlo simulation**: Call the Monte Carlo endpoint with historical trade results. Verify: (a) it produces a distribution of outcomes (min, p5, p25, median, p75, p95, max), (b) the distribution is reasonable (not all identical, not infinite variance), (c) VaR and CVaR are computed correctly.
6. **Execution simulator accuracy**: Compare simulated fills against historical Alpaca fills (if available in DuckDB). Verify slippage model is realistic: (a) market orders have spread + impact, (b) limit orders have partial fill probability, (c) TWAP orders have time-weighted cost.
7. **Reproducibility**: Run the same backtest twice with identical parameters. Verify results are IDENTICAL (deterministic). If any randomness exists (e.g., agent evaluation order), document it and verify it's seeded.
8. **Backtest API endpoints**: Hit each backtest endpoint via TestClient:
   - `POST /backtest/` — basic backtest run
   - `GET /backtest/runs` — list historical runs
   - `GET /backtest/results/{run_id}` — specific results
   - `POST /backtest/walkforward` — walk-forward run
   - `POST /backtest/montecarlo` — Monte Carlo sim
   - `GET /backtest/rolling-sharpe` — rolling Sharpe chart data
   - `GET /backtest/drawdown-analysis` — drawdown analysis
   - `GET /backtest/kelly-comparison` — Kelly sizing comparison
   Verify all return 200 with valid JSON. Any 500s are bugs.

**Output**: New test file `tests/test_backtest_intelligence.py`. Include a real 30-day council replay with accuracy metrics. Report the council's actual hit rate and expected profitability.

---

### WORKSTREAM 8: Feedback Loop & Outcome Tracking

**Scope**: Verify the complete learning cycle — from trade execution to outcome measurement to weight adjustment — so the system actually improves over time.

**Key files**: `council/feedback_loop.py` (7.5 KB), `council/weight_learner.py` (14.8 KB), `council/shadow_tracker.py` (8 KB), `council/self_awareness.py` (10.8 KB), `council/overfitting_guard.py` (9.4 KB), `services/outcome_tracker.py`, `jobs/daily_outcome_update.py`

Build and run these tests:

1. **Outcome resolution**: Place a simulated trade: BUY AAPL at $150, stop at $145, target at $160. Mock Alpaca showing current price $158. Verify outcome_tracker resolves it as: (a) open trade, (b) unrealized P&L = +$8/share, (c) R-multiple = (158-150)/(150-145) = 1.6R. Then mock price hitting $160 → verify CLOSED with realized P&L, correct R-multiple, and trade duration recorded.
2. **Feedback loop — win**: Council decided BUY AAPL, trade closed at +2R. Verify `feedback_loop.py` passes the outcome to weight_learner with: (a) each agent's original vote, (b) the actual outcome direction (profit = correct for BUY voters), (c) weight updates fire for all 35 agents. Agents who voted BUY get α incremented. Agents who voted SELL get β incremented (wrong).
3. **Feedback loop — loss**: Council decided BUY TSLA, trade closed at -1R (stopped out). Verify inverse: BUY voters get β incremented (wrong), SELL voters get α incremented (they were right). HOLD voters get neutral update.
4. **Daily outcome job**: Populate DuckDB with 10 mock trades (5 wins, 5 losses). Run `daily_outcome_update` job. Verify: (a) all 10 trades are processed, (b) weight_learner updates fire for each, (c) no trades are missed (the bug was 50%+ dropped due to 0.5 confidence floor — verify this is fixed with floor at 0.20).
5. **Shadow tracker**: Run council in live mode AND shadow/paper mode simultaneously. Verify: (a) both modes record independent decisions, (b) divergence is detected when paper would have traded but live didn't (or vice versa), (c) divergence metrics are tracked over time.
6. **Self-awareness accuracy**: After 50 simulated decisions (30 correct, 20 wrong), verify: (a) self_awareness computes accuracy = 60%, (b) it triggers recalibration if accuracy drops below threshold, (c) metacognition logs are persisted. Verify the system "knows" which agents are performing well vs poorly.
7. **Overfitting guard**: Train an ML model on 30 days of data, test on 10 days. If train accuracy = 95% but test accuracy = 55%, verify overfitting_guard: (a) detects the gap, (b) flags the model as overfit, (c) prevents the overfit model from being promoted to production. Test the threshold: what gap triggers the guard?
8. **Weight learning persistence across restarts**: Run 50 weight updates, verify DuckDB has updated Beta(α,β) values. "Restart" the weight learner (re-instantiate). Verify it loads the persisted weights and continues from where it left off (doesn't reset to priors). This is critical for continuous learning.
9. **Long-term convergence**: Simulate 500 decisions where Agent A is 80% accurate and Agent B is 40% accurate. After 500 rounds, verify: (a) Agent A's weight is ≥ 2x Agent B's weight, (b) the arbiter's decisions improve over time (accuracy in decisions 400-500 should be higher than decisions 1-100), (c) weights are stable (not oscillating wildly).
10. **Trade-ID matching**: Verify the feedback loop matches outcomes to the correct council decision via `trade_id` / `decision_id`. Test edge case: two trades for the same symbol on the same day — verify they link to different council decisions, not the same one.

**Output**: New test file `tests/test_feedback_learning_loop.py`. Report the actual convergence rate and whether the system demonstrably learns from its mistakes.

---

## Final Report Structure

After all 8 agents complete, compile findings into `docs/E2E-INTELLIGENCE-TEST-REPORT-2026-03.md`:

```markdown
# E2E Intelligence Test Report — March 2026

## Executive Summary
- Tests written: X
- Tests passing: X / X
- Critical findings: X
- High findings: X
- Pipeline health: [GREEN/YELLOW/RED]

## Pipeline Correctness
- Signal → Order flow: [PASS/FAIL]
- Council DAG: [PASS/FAIL] (X/35 agents compliant)
- Arbiter math: [PASS/FAIL]
- Risk gates: [PASS/FAIL]

## Intelligence Quality
- Council hit rate (backtest): XX%
- Weight learner convergence: [YES/NO] (X rounds to converge)
- Regime-adaptive accuracy: GREEN=XX%, YELLOW=XX%, RED=XX%
- Brier score (calibration): X.XX

## Risk Gate Verification
- Circuit breakers enforced: [YES/NO]
- Regime blocking works: [YES/NO]
- Kelly sizing correct: [YES/NO]
- Decision expiry enforced: [YES/NO]

## Data Resilience
- Sources tested: X/10
- Agents surviving None data: X/35
- Graceful degradation: [PASS/FAIL]

## Findings (sorted by severity)
[All findings from all workstreams]
```

## Rules for Test Code

1. **Use pytest + anyio/asyncio** — match existing test patterns
2. **Mock all external APIs** — Alpaca, Ollama, UW, FRED, NewsAPI, etc.
3. **Use conftest.py fixtures** — DuckDB in-memory, shared mocks
4. **Never hit real services** — all tests must pass offline
5. **Assert specific values** — not just `is not None` or `assert True`
6. **Each test file must pass independently** — no cross-file dependencies
7. **4-space indentation** — Python standard
8. **All tests must pass** — run `cd backend && python -m pytest tests/test_e2e_full_pipeline.py tests/test_council_dag_full.py tests/test_arbiter_weight_learning.py tests/test_regime_adaptive_pipeline.py tests/test_order_execution_gates.py tests/test_data_quality_degradation.py tests/test_backtest_intelligence.py tests/test_feedback_learning_loop.py -v`
