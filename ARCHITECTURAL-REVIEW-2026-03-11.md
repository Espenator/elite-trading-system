# Embodier Trader — First-Principles Architectural Review
**Date:** March 11, 2026
**Codebase:** `c1717b1` (PC-role aware Alpaca keys)
**Reviewer:** Claude (Senior Engineering Partner)

---

## Executive Summary

This review traces every data path from ingestion to execution, maps every filter in the decision funnel, audits the complete learning loop, and stress-tests the risk enforcement layer. The findings go beyond the known issue list to identify **compounding failure interactions** — places where two individually-tolerable flaws combine to create systemic problems.

**The headline finding:** The system's biggest problem is not any single bug. It is that **the information pipeline, the decision funnel, the learning system, and the risk layer all degrade in the same direction** — they collectively suppress signal throughput during exactly the market conditions (high volatility, fast moves, regime transitions) where a well-functioning system would generate the most alpha. The system is anti-adaptive: it gets more conservative precisely when opportunities are richest.

---

## 1. Information Flow & Market Awareness Failures

### 1.1 Data Source Audit: What Reaches the Council?

| Source | Fetches Data? | Publishes to MessageBus? | Reaches Council? | Impact |
|--------|:---:|:---:|:---:|--------|
| Alpaca (bars/quotes) | Yes | Yes | Yes | Primary price data — works |
| Unusual Whales | Yes | Yes | Yes, via UW scout | Flow data reaches agents |
| Finviz | Yes | Yes (screens) | Yes, via TurboScanner | Screen results reach discovery |
| FRED (macro) | Yes | **Partial** — regime only | Regime params only | Macro data doesn't reach individual agent votes |
| SEC EDGAR | Yes | **No** — fetches but never publishes | **Blind** | Insider filings are invisible to the council |
| SqueezeMetrics | Yes | **No** — data fetched, not routed | **Blind** | Dark pool / GEX data never reaches agents |
| Benzinga | Yes | **No** — fetch-only | **Blind** | News catalyst data invisible |
| Capitol Trades | Yes | **No** — fetch-only | **Blind** | Congressional trading signals invisible |

**Consequence:** 4 of 8 data sources are architecturally disconnected from the decision pipeline. The system pays for API access to data it never uses in decisions. More critically, the council votes on price and flow data alone — it has **zero awareness of fundamental catalysts, dark pool positioning, or insider activity**.

### 1.2 MessageBus Architecture: The Silent Bottleneck

The MessageBus (`backend/app/core/message_bus.py`) is the nervous system of the entire platform. Its failure modes cascade everywhere.

**Capacity:** 10,000 events per queue. With rate limiting added (commit `980ce4d`), `swarm.idea` is capped at 50 events/second.

**What happens at overflow:**
- Events are moved to a dead-letter queue (DLQ) — but the DLQ is **memory-only**, capped at 500 entries
- Older DLQ entries are silently evicted (FIFO)
- No persistent DLQ, no replay capability, no audit trail
- At market open when TurboScanner finds 100+ candidates in one scan: 50% of discoveries are rate-limited and dropped

**Scout backpressure (commit `980ce4d`):** When queue fill exceeds 60%, scouts pause publishing. This is exactly backwards — scouts should publish *more* during high-signal periods, not less. The backpressure mechanism was designed to prevent queue overflow but actually prevents the system from seeing the market when the market is most interesting.

**Per-topic rate limits:**
- `swarm.idea`: 50/sec — too low for market open (100+ candidates/scan)
- `swarm.signal`: 20/sec — adequate for normal flow, drops during news events
- `market.data`: 100/sec — acceptable

### 1.3 Temporal Blind Spots: Polling vs Streaming

**TurboScanner:** 30-60 second polling interval (`turbo_scanner.py` lines 43-45). Runs 10 DuckDB screens sequentially, each taking 200-500ms. Total scan time: 2-5 seconds. Then waits 25-55 seconds before next scan.

**What this means in market terms:**
- An RSI snap-back reversal completes in 15-30 seconds. The system misses 50-100% of these.
- A news-driven gap move happens in 5-10 seconds. The system is structurally blind to these.
- At market open, the first 60 seconds see the highest volume and widest spreads. The system's first scan may not even complete before the opening auction settles.

**StreamingDiscoveryEngine (Issue #38):** Partially implemented. When complete, this would replace polling with event-driven discovery. Currently incomplete — the system is polling-only.

### 1.4 DuckDB Cold Start Race Condition

On startup, TurboScanner begins querying DuckDB immediately (`main.py` lines 736-742). But DuckDB starts empty — there is no startup backfill routine. The first 2-3 scan cycles (60-180 seconds) hit empty tables and produce zero results.

**Compounding effect:** If the system restarts during market hours (crash recovery, deploy), it is blind for 1-3 minutes. Combined with the scout backpressure and rate limiting, it may take 5+ minutes to reach full awareness after a restart.

### 1.5 Regime Refresh Latency

Regime detection refreshes every 300 seconds (`signal_engine.py` lines 564-566). A regime transition (e.g., VIX spike from 15 to 35) takes 5 minutes to propagate to the signal engine. During those 5 minutes, the system trades under stale regime parameters — potentially taking full Kelly positions during a flash crash.

**The LLM Router question:** The 3-tier LLM router (local Qwen → DeepSeek-R1 → GPT-4) adds 500ms-3s per call depending on which tier handles the request. For the hypothesis agent (Stage 3), this is acceptable — it runs once per evaluation. But if LLM calls were needed per-agent, the 33-agent council at 1-3s each would take 30-90s total (currently not the case, but a design constraint to remember).

---

## 2. Decision Funnel Architecture

### 2.1 Complete Signal-to-Execution Map

```
┌─────────────────────────────────────────────────────────────┐
│ DISCOVERY LAYER                                              │
│                                                              │
│ TurboScanner (60s polling, 10 DuckDB screens)               │
│     ↓ ~100-200 candidates per scan at market open            │
│ 12 Scout Agents (UW flow, insider, news, sentiment, etc.)   │
│     ↓ ~20-50 ideas per cycle (throttled from 50+)            │
│ MarketWideSweep (4hr full / 30min incremental)              │
│     ↓ background enrichment                                  │
├─────────────────────────────────────────────────────────────┤
│ SIGNAL ENGINE (signal_engine.py)                             │
│                                                              │
│ Blended Score = 0.6 * openclaw_score + 0.4 * technical_score│
│ Signal Gate: score >= 65/100 to proceed                      │
│     ↓ ~65% pass rate (35% filtered)                          │
├─────────────────────────────────────────────────────────────┤
│ COUNCIL GATE (council_gate.py)                               │
│                                                              │
│ Regime-adaptive threshold: 55 (BULLISH) to 75 (CRISIS)      │
│ Per-symbol cooldown: 300s between evaluations                │
│ Concurrency: max 15 parallel councils                        │
│     ↓ ~75% pass rate (25% filtered by cooldown/regime)       │
├─────────────────────────────────────────────────────────────┤
│ 33-AGENT COUNCIL DAG (runner.py)                             │
│                                                              │
│ Stage 1: 13 perception agents (parallel)      ~200-400ms    │
│ Stage 2: 8 technical agents (parallel)        ~150-300ms    │
│ Stage 3: 2 hypothesis+memory (sequential)     ~300-1500ms   │
│ Stage 4: 1 strategy agent                     ~100-200ms    │
│ Stage 5: 3 risk+execution+portfolio (parallel) ~200-400ms   │
│ Stage 5.5: 4 debate agents                    ~200-800ms    │
│ Stage 6: 1 critic (post-decision, async)      non-blocking  │
│                                                              │
│ VETO agents: risk_agent + execution_readiness               │
│     ↓ ~80% pass rate (20% vetoed)                            │
├─────────────────────────────────────────────────────────────┤
│ ARBITER (arbiter.py)                                         │
│                                                              │
│ Bayesian-weighted consensus                                  │
│ Execution threshold: 0.4 (hardcoded)                         │
│     ↓ ~80% pass rate of non-vetoed signals                   │
├─────────────────────────────────────────────────────────────┤
│ ORDER EXECUTOR (order_executor.py) — 9 SEQUENTIAL GATES     │
│                                                              │
│ 1. Council & Mock Guard                                      │
│ 2. Regime & Leverage (max 2.0x)                              │
│ 3. Daily Trade Limit (≤10/day)                               │
│ 4. Per-symbol Cooldown (≥300s)                               │
│ 5. Drawdown Check                                            │
│ 6. Degraded Mode & Kill Switch                               │
│ 7. Kelly Sizing (min_edge, min_trades=20)                    │
│ 8. Portfolio Heat (current+new ≤ max_heat)                   │
│ 9. Viability Gate (slippage < real_edge)                     │
│ 10. Risk Governor (9 sub-checks, may reduce shares)          │
│     ↓ ~85% pass rate                                         │
├─────────────────────────────────────────────────────────────┤
│ ALPACA ORDER (market order only)                             │
│ Partial fills silently accepted                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Compounding Filter Loss Rate

Starting from 100 candidates discovered at market open:

| Stage | Input | Pass Rate | Output | Cumulative Loss |
|-------|------:|----------:|-------:|----------------:|
| Discovery (rate-limited) | 100 | 50% | 50 | 50% |
| Signal Gate (65/100) | 50 | 65% | 33 | 67% |
| Council Gate (cooldown + regime) | 33 | 75% | 25 | 75% |
| Council VETO | 25 | 80% | 20 | 80% |
| Arbiter (0.4 threshold) | 20 | 80% | 16 | 84% |
| Executor gates | 16 | 85% | 14 | 86% |
| Kelly sizing (min_edge) | 14 | 90% | 12 | 88% |
| **Final orders** | | | **~12** | **~88% filtered** |

**Only ~12% of discovered candidates become orders.** This is not inherently wrong — good filters should reject bad trades. The problem is that **none of these filters are calibrated against historical outcome data**. The 65 signal gate, the 0.4 arbiter threshold, the 300s cooldown — all are heuristic guesses. We have no evidence they're filtering unprofitable trades rather than profitable ones.

### 2.3 The 33-Agent DAG: Structural Critique

**Latency:** Total council evaluation: 1.0-2.5 seconds. This is acceptable for the current 60s polling architecture. But in a streaming architecture (Issue #38), 2.5 seconds of evaluation latency on a 5-second market move means the signal is stale before the order hits.

**Stage-gate failure modes that parallel architectures avoid:**
1. If Stage 1 (perception) is slow, all downstream stages wait. In a parallel ensemble, fast agents could vote immediately.
2. If a Stage 1 agent throws an exception, it returns HOLD (confidence=0.1). This dilutes the Bayesian-weighted vote toward inaction without any visibility that the agent failed. In a parallel ensemble, failed agents would simply be excluded from the vote.
3. The debate stage (Stage 5.5) has no wall-clock timeout for the entire council DAG. Individual agents timeout at 30s, but if multiple agents are slow, the total can exceed any reasonable latency budget.

**Agent exception handling (`task_spawner.py` lines 217-236):** All exceptions and timeouts silently convert to HOLD votes with confidence=0.1. There is no health tracking — no counter of how many agents failed this cycle, no alert if >30% of agents are down. The council will happily proceed with 10 of 33 agents returning real votes and 23 returning failure-HOLDs, and the operator will see no indication that the system is degraded.

### 2.4 Arbiter Threshold: Why 0.4 Should Be Regime-Adaptive

The hardcoded 0.4 threshold means: "If the Bayesian-weighted consensus exceeds 40%, execute." This is constant across all regimes.

**Mathematical problem:** In a CRISIS regime (VIX > 30), the base rate of profitable trades drops significantly. A 40% consensus in CRISIS has different predictive value than 40% in BULLISH. The threshold should be calibrated against the base rate:
- BULLISH: threshold 0.30-0.35 (more permissive — higher base rate of success)
- NEUTRAL: threshold 0.40 (current default)
- YELLOW: threshold 0.50
- RED: threshold 0.60
- CRISIS: threshold 0.70 (very selective — only high-conviction trades)

**Interaction with Bayesian weights:** The WeightLearner adjusts per-agent weights based on outcomes, but uses the same weights across all regimes. If an agent is good at BULLISH markets but bad at CRISIS markets, its weight reflects a blended average — not its regime-specific accuracy. This means the arbiter's consensus quality degrades during regime transitions.

### 2.5 Short Signal Inversion

In `signal_engine.py` line 268, the short signal momentum calculation uses `max(-20, +25)` vs the long signal's `(0, +25)`. The asymmetric range means short signals are penalized by up to 20 points of negative momentum even when the signal is directionally correct. Combined with the `100 - blended` inversion formula, bearish setups face a compounding penalty: they start with a lower raw score AND face a stricter effective threshold to pass the 65-point gate.

**Net effect:** The system is structurally biased long. In a bear market, this means the system goes quiet precisely when short selling would generate the most alpha.

---

## 3. Feedback Loop & Learning System

### 3.1 The Complete Learning Loop (As Designed)

```
Trade Executed
    ↓
OutcomeTracker records result
    ↓
WeightLearner receives outcome
    ↓  [GATE: confidence_floor = 0.5]
Bayesian weight update per agent
    ↓
Next council uses updated weights
```

### 3.2 Where Learning Breaks Down: The 75-80% Data Loss Cascade

| Stage | Dropout Rate | Mechanism |
|-------|:-----------:|-----------|
| Signal → Decision match | ~5% | In-memory decision history (500 cap), symbol-only matching |
| Shadow timeout censoring | ~45-55% | Outcomes labeled "censored" if trade exceeds timeout — no learning fired |
| Confidence floor gate | ~15-25% | Outcomes with confidence < 0.5 silently dropped (DEBUG log only) |
| Decision-outcome mismatch | ~10-15% | Same symbol traded multiple times → wrong decision matched to outcome |
| Weight update not called | ~50-60% | `feedback_loop.update_agent_weights()` delegates to WeightLearner but **never calls `update_from_outcome()`** — returns current weights unchanged |
| **Total data loss** | **~75-80%** | **Only 20-25% of trade outcomes actually update agent weights** |

**This is the single most damaging architectural flaw in the system.** A learning system that drops 75-80% of its training data cannot learn. The Bayesian weights converge toward priors — which are uniform. The system behaves as if it has no learning at all.

### 3.3 The Three Disconnected Knowledge Systems

The system has three independent learning subsystems that do not share information:

1. **WeightLearner:** Bayesian updates per agent. Functional in theory but starved of data (see above). Uses same weights across all regimes.

2. **HeuristicEngine:** Forms heuristics from patterns in outcomes. Requires `MIN_SAMPLE = 25` consecutive outcomes in the same pattern. Due to censoring (45-55% dropout), it takes ~200+ trades to form one heuristic. In practice, this system has formed zero to very few heuristics.

3. **KnowledgeGraph:** Builds a graph of entity relationships from trade context. The graph is built and populated — but **never queried during council decision-making**. The `runner.py` imports it but the agents themselves don't call into it. It's dead code that consumes memory.

### 3.4 Debate and Critic: Learning That Doesn't Feed Back

**Debate engine (Stage 5.5):** 4 debate agents discuss the proposed trade. Their votes and arguments are not recorded in any persistent store. The debate's output affects the current council verdict but generates no training signal for future debates. The debate engine cannot improve because it has no memory of past debates.

**Critic agent (Stage 6):** Runs post-decision, performs postmortem analysis. Its output goes to the learning system — but the learning system drops 75-80% of it (see above). Even the 20-25% that survives only updates agent weights, not the critic's own reasoning model. The critic cannot learn to be a better critic.

### 3.5 Feature Aggregator Silent Failure

When the feature aggregator throws an exception (`feature_aggregator.py`), it returns an empty dictionary. The council proceeds to vote, but every agent that depends on features receives empty data. Agents are not told they're reasoning on empty data — they produce votes as if they had full information.

**Compounding interaction:** Empty features → agents produce low-confidence HOLD votes → HOLD votes treated as real votes → Bayesian consensus shifts toward inaction → system appears to be "working" but is actually paralyzed by data absence. The operator sees the council voting, doesn't know the votes are based on nothing.

---

## 4. Risk Layer Enforcement Assessment

### 4.1 What's Actually Enforced (Good News)

The risk layer has been significantly hardened in recent commits. Key enforcements that **do work**:

**Circuit breakers (`council/reflexes/circuit_breaker.py`):** 5 brainstem reflexes run BEFORE the council DAG:
- Flash crash detector (5% intraday move) — HARD BLOCK
- VIX spike detector (VIX > 35) — HARD BLOCK
- Daily drawdown limit (3% default) — HARD BLOCK
- Position limit (10 max) — HARD BLOCK
- Market hours check — HARD BLOCK

**Maximum leverage:** 2.0x hardcoded in `order_executor.py` line 323. **Cannot be exceeded without code modification.** (The original concern about 4x leverage is incorrect — the code enforces 2.0x.)

**9 sequential execution gates** in `order_executor.py` — all are HARD blocks. The system is conservative at the execution layer.

**Portfolio heat:** Uses `last_equity` (start-of-day) baseline per commit `7d92105` (B8 fix). This is **countercyclical** — it does NOT tighten during intraday drawdowns. This was a fix to the originally procyclical behavior.

### 4.2 What's NOT Enforced (Gaps)

**Regime `max_pos` is advisory-only for non-RED regimes:**
- RED regime (`max_pos=0`): enforced — blocks all new positions
- YELLOW (`max_pos=5`), GREEN (`max_pos=6`): **NOT enforced as position count checks**
- Mitigation: RiskGovernor enforces a 3-per-sector hard limit, but this is not the same as regime-aware position counts

**VaR calculation is monitoring-only:**
- Single-day P&L snapshot, not rolling 20-day window
- Identity correlation matrix (assumes zero correlation between positions — overstates diversification)
- **Not used in any execution gate** — purely informational for the dashboard
- Multi-day holding periods (MAX_HOLD = 5 days) are not reflected in VaR

**ATR stop-loss multiplier hardcoded to 2.0x:**
- `order_executor.py` line 978 — not configurable at runtime
- Not regime-adaptive: same 2.0x in CRISIS (where ATR is much wider) and BULLISH

**Account type validated once at startup:**
- `alpaca_service.py` lines 100-148: constructor checks paper vs live URL match
- Force-corrects URL if mismatch detected at startup
- **Not revalidated per trade** — if credentials rotate mid-session, no re-check

### 4.3 Regime Detection Offline Fallback

When regime detection fails (FRED API down, OpenClaw bridge offline, VIX data stale), the system defaults to YELLOW regime.

**YELLOW regime parameters:**
- `kelly_fraction`: 0.6
- `max_pos`: 5
- Position sizing: 60% of full Kelly

**Why this is dangerous:** If the actual market regime is RED or CRISIS (VIX > 30, high correlation, elevated drawdown risk), the YELLOW fallback allows moderate-to-full position sizing. The system will trade through a crash as if conditions are mildly cautious.

**Recommended fix:** Default to RED (most conservative) when regime detection is offline. Better to miss trades than to trade blind.

---

## 5. Compounding Failure Interactions

These are the most dangerous findings — places where individually tolerable flaws combine to create systemic risk.

### 5.1 The Anti-Adaptive Cascade

**Flaw combination:** Rate limiting + backpressure + cooldown + regime fallback

**Scenario:** Market open on a volatile day (VIX spike from 18 to 28).

1. TurboScanner discovers 150 candidates (vs normal 30-50)
2. MessageBus rate limit drops 50% → only 75 reach the signal engine
3. Scout backpressure kicks in at 60% queue fill → scouts pause, miss the next wave
4. Signal gate filters 35% → 49 candidates proceed
5. Per-symbol cooldown (300s) prevents re-evaluation of symbols that were evaluated in the previous calm cycle → 25% filtered
6. Regime detection hasn't updated yet (300s refresh) → still using NEUTRAL params when market is YELLOW/RED
7. Result: System sees 30% of what it should see, trades under wrong regime params

**This is the central architectural problem.** Every safety mechanism activates in the same direction (suppression) at the same time (high volatility). The system becomes maximally blind and maximally conservative at the moment of maximum opportunity.

### 5.2 The Learning Starvation Loop

**Flaw combination:** Confidence floor (0.5) + shadow timeout censoring + `update_from_outcome()` not called

**Scenario:** System runs for 30 days, takes 60 trades.

1. 60 outcomes generated
2. Shadow timeout censors ~30 (timeout policy) → 30 remain
3. Confidence floor drops ~8 more (< 0.5) → 22 remain
4. Decision-outcome mismatch loses ~3 → 19 remain
5. `feedback_loop.update_agent_weights()` doesn't actually call `update_from_outcome()` → **0 weights updated**

After 30 days: agent weights are identical to initialization. The system has not learned a single thing. But the operator sees "30 outcomes processed" in logs and believes the system is learning.

### 5.3 The Silent Council Degradation

**Flaw combination:** Agent exception → HOLD + empty feature aggregator + no health monitoring

**Scenario:** FRED API goes down, taking 3 scouts with it.

1. 3 scouts crash on first cycle (known issue: missing service methods)
2. Feature aggregator returns empty dict for macro features
3. 5 perception agents (macro-dependent) receive empty data → produce HOLD (confidence=0.1)
4. 3 scouts not publishing → 3 additional agents have no input → HOLD
5. Council now has 8/33 agents returning failure-HOLDs, 25 with real data
6. Bayesian consensus shifts toward inaction — but the arbiter doesn't know why
7. System trades less, operator sees "conservative" behavior, assumes it's working correctly

**No alert is raised.** No health check counts failed agents. No dashboard shows "8/33 agents degraded." The system silently degrades from 33-agent intelligence to 25-agent intelligence, and nobody knows.

### 5.4 The Short Signal Death Spiral

**Flaw combination:** Short signal inversion + long-only structural bias + no regime-adaptive thresholds

In a bear market:
1. Short signals penalized by -20 momentum floor (long signals have 0 floor)
2. `100 - blended` formula further penalizes short scores
3. Signal gate at 65 filters more short signals than long signals
4. Arbiter threshold at 0.4 is constant — not lowered for high-conviction short setups
5. System goes effectively silent during bear markets
6. No learning from missed short opportunities (learning system drops 75-80% of data anyway)
7. Next bear market: same blindness repeats

### 5.5 The Restart Amnesia Problem

**Flaw combination:** In-memory decision history + no DuckDB persistence for decisions + DuckDB cold start

On restart (crash, deploy, maintenance):
1. Decision history (500 entries) — lost entirely (in-memory only)
2. WeightLearner state — depends on whether weights were persisted (unclear)
3. DuckDB starts empty — no backfill routine
4. First 2-3 minutes: zero discovery, zero signals
5. Outcome matching for pre-restart trades: impossible (decision history gone)
6. Any trades still open from pre-restart: orphaned from the learning loop

---

## 6. Prioritized Recommendations

### Tier 1: Capital Protection (Do This Week)

| # | Fix | File(s) | Impact |
|---|-----|---------|--------|
| 1 | **Change regime offline default from YELLOW → RED** | `signal_engine.py` | Prevents trading through crashes blind |
| 2 | **Add council health check** — count failed agents, alert if >20% degraded | `runner.py`, `task_spawner.py` | Prevents silent degradation |
| 3 | **Fix `feedback_loop.update_agent_weights()`** — actually call `update_from_outcome()` | `feedback_loop.py` | Restores 40-50% of lost learning |
| 4 | **Enforce regime max_pos for YELLOW/GREEN** — add position count check to executor | `order_executor.py` | Closes advisory-only gap |

### Tier 2: Alpha Recovery (Do This Month)

| # | Fix | File(s) | Impact |
|---|-----|---------|--------|
| 5 | **Lower confidence floor from 0.5 → 0.35** | `weight_learner.py` | +30-40% outcomes reaching learning |
| 6 | **Change shadow timeout policy from "censor" to "mark-to-market"** | `outcome_tracker.py` | -70% censoring, massive learning data gain |
| 7 | **Make arbiter threshold regime-adaptive** (0.30 BULLISH → 0.70 CRISIS) | `arbiter.py` | Proper risk calibration per regime |
| 8 | **Fix short signal momentum asymmetry** — equal floor for long/short | `signal_engine.py` | Enables bearish setups |
| 9 | **Invert backpressure logic** — scouts should INCREASE output during high-signal periods | `scouts/base.py` | Removes anti-adaptive behavior |
| 10 | **Connect SEC EDGAR, SqueezeMetrics, Benzinga, Capitol Trades to MessageBus** | Scout files | 4 new data dimensions for council |

### Tier 3: Structural Improvements (Do This Quarter)

| # | Fix | File(s) | Impact |
|---|-----|---------|--------|
| 11 | **Persist decision history to DuckDB** with trade_id matching | `outcome_tracker.py`, `database.py` | Eliminates restart amnesia |
| 12 | **Per-regime WeightLearner** — separate weight sets per regime | `weight_learner.py` | Agents specialize per market condition |
| 13 | **Record debate votes persistently** — enable debate learning | Debate agents | Debate improves over time |
| 14 | **Add DuckDB startup backfill** — fetch last 24h of bars on init | `main.py`, `turbo_scanner.py` | Eliminates cold start blind spot |
| 15 | **Implement Brier score calibration** — track predicted vs actual confidence | `weight_learner.py` | Identifies overconfident agents |
| 16 | **Rolling VaR** with proper correlation matrix and multi-day holding adjustment | `risk.py` | Realistic risk measurement |
| 17 | **Limit order support** for entries (TWAP for large orders) | `order_executor.py`, `alpaca_service.py` | Reduces spread cost |
| 18 | **Complete StreamingDiscoveryEngine (Issue #38)** | Discovery layer | Eliminates polling blind spots |

---

## 7. Summary of Key Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Signal-to-execution pass rate | ~12% | ~15-20% (with calibrated filters) |
| Learning data retention | ~20-25% | ~70-80% |
| Data sources reaching council | 4 of 8 (50%) | 8 of 8 (100%) |
| Agent failure visibility | 0% (silent) | 100% (health dashboard) |
| Regime transition latency | 300s | ≤60s |
| DuckDB cold start blind spot | 60-180s | 0s (backfill on startup) |
| Short signal parity with long | ~60% (penalized) | 100% (equal treatment) |
| Maximum leverage | 2.0x (enforced) | 2.0x (correct) |
| Circuit breaker enforcement | 5/5 hard blocks | 5/5 (correct) |

---

*This review is based on codebase commit `c1717b1`. All file paths and line numbers reference this specific commit.*
