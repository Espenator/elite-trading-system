# CLAUDE.md — Embodier Trader Council
# 35-Agent DAG with Bayesian-Weighted Arbiter
# Last updated: March 12, 2026 — v4.1.0-dev

## Architecture

The council is a **35-agent Directed Acyclic Graph (DAG)** executed in 7 parallel stages. Every trade signal passes through the full council before execution. Sub-1s latency.

```
Stage 1 (Parallel — 13 agents): Perception + Academic Edge P0/P1/P2
  market_perception, flow_perception, regime, social_perception,
  news_catalyst, youtube_knowledge, intermarket,
  gex_agent, insider_agent, finbert_sentiment_agent,
  earnings_tone_agent, dark_pool_agent, macro_regime_agent

Stage 2 (Parallel — 8 agents): Technical + Data Enrichment
  rsi, bbv, ema_trend, relative_strength, cycle_timing,
  supply_chain_agent, institutional_flow_agent, congressional_agent

Stage 3 (Parallel — 2 agents): Hypothesis + Memory
  hypothesis (LLM via brain gRPC), layered_memory_agent

Stage 4 (Sequential — 1 agent): Strategy
  strategy

Stage 5 (Parallel — 3 agents): Risk + Execution + Portfolio
  risk (VETO), execution (VETO), portfolio_optimizer_agent

Stage 5.5 (Parallel — 3 agents): Debate + Red Team
  bull_debater, bear_debater, red_team

Stage 6 (Sequential — 1 agent): Critic
  critic

Stage 7 (Sequential): Arbiter
  Deterministic BUY/SELL/HOLD with Bayesian-weighted confidence

Post-Arbiter (Background): alt_data_agent (enrichment)
```

## AgentVote Schema (ALL agents MUST return this)

```python
@dataclass
class AgentVote:
    agent_name: str            # e.g. "risk_agent"
    direction: str             # "buy" | "sell" | "hold"
    confidence: float          # 0.0 – 1.0
    reasoning: str             # Human-readable explanation
    veto: bool = False         # Only risk + execution can set True
    veto_reason: str = ""      # Reason for veto
    weight: float = 1.0        # Agent's base weight
    metadata: Dict[str, Any] = field(default_factory=dict)
    blackboard_ref: str = ""   # council_decision_id
```

**Validation**: direction must be "buy"|"sell"|"hold", confidence in [0,1], weight > 0.

## Arbiter Rules

1. **VETO**: If `risk` or `execution` sets `veto=True` → HOLD, `vetoed=True`
2. **REQUIRED**: `regime`, `risk`, `strategy` must vote non-hold for any trade
3. **Confidence**: Bayesian-weighted aggregation across all 35 agent votes
4. **Execution threshold**: confidence > 0.4 AND `execution_ready=True`
5. **VETO_AGENTS** = `{"risk", "execution"}` — ONLY these can veto
6. **New agents do NOT get veto power**

## WeightLearner — Bayesian Beta(α,β)

**File**: `weight_learner.py` (14.8 KB)

Each agent has a learned weight via Bayesian Beta distribution:
- `α` = successful predictions, `β` = failed predictions
- `E[weight] = α / (α + β)` — converges toward true accuracy
- Updated after each trade outcome via `feedback_loop.py`
- Weights used by arbiter for confidence aggregation

**Known issue**: Confidence floor of 0.5 drops 50%+ of outcomes (Phase C fix).

## CouncilGate — Signal → Council Bridge

**File**: `council_gate.py` (8.9 KB)

- Subscribes to `signal.generated` on MessageBus
- Filters signals by threshold (currently 65 — known to be too aggressive)
- Invokes `run_council()` for qualifying signals
- Publishes `council.verdict` with BUY/SELL/HOLD + confidence
- Per-symbol cooldown to prevent duplicate evaluations
- Concurrency limiter (max=3 simultaneous council runs)

**Known issue**: Threshold 65 filters 20-40% of profitable signals (Phase B fix).

## How to Add a New Agent

1. **Create agent file** in `council/agents/`:
   ```python
   # council/agents/my_new_agent.py
   from app.council.schemas import AgentVote

   NAME = "my_new_agent"
   WEIGHT = 0.7  # Start conservative

   async def evaluate(features: dict, context: dict = None) -> AgentVote:
       f = features.get("features", features)
       # ... your analysis logic ...
       return AgentVote(
           agent_name=NAME,
           direction="hold",
           confidence=0.5,
           reasoning="Analysis result",
           weight=WEIGHT,
       )
   ```

2. **Register in `registry.py`**: Add to AGENT_REGISTRY dict

3. **Assign stage in `agent_config.py`**: Place in appropriate parallel stage

4. **Wire in `runner.py`**: Add to the correct stage's agent list

5. **Test**: Run `cd backend && python -m pytest --tb=short -q`

**Rules for new agents**:
- MUST return AgentVote schema
- Do NOT add veto power (only risk + execution can veto)
- Start with conservative weight (0.5-0.7)
- Handle errors gracefully — return HOLD with low confidence on failure
- Use `features.get("features", features)` pattern for feature access

## Orchestration Files (15 total)

| File | Size | Purpose |
|------|------|---------|
| **runner.py** | 29.4 KB | 7-stage parallel DAG orchestrator — the profit spine |
| **arbiter.py** | 6.4 KB | Deterministic BUY/SELL/HOLD with Bayesian weights |
| **schemas.py** | 7.6 KB | AgentVote + DecisionPacket dataclasses |
| **council_gate.py** | 8.9 KB | Signal → Council → OrderExecutor bridge |
| **weight_learner.py** | 14.8 KB | Bayesian Beta(α,β) self-learning weights |
| **blackboard.py** | 11.1 KB | Shared memory state across DAG stages (Thalamus) |
| **shadow_tracker.py** | 8.0 KB | Shadow portfolio — tracks what council WOULD do |
| **self_awareness.py** | 10.8 KB | System metacognition + Bayesian accuracy tracking |
| **homeostasis.py** | 6.3 KB | System stability + auto-healing |
| **overfitting_guard.py** | 9.4 KB | ML overfitting detection for agent predictions |
| **hitl_gate.py** | 12.0 KB | Human-in-the-loop approval gate |
| **feedback_loop.py** | 7.5 KB | Post-trade outcome feedback to agents |
| **task_spawner.py** | 10.7 KB | Dynamic agent registry + spawning |
| **data_quality.py** | 9.0 KB | Data quality scoring for agent inputs |
| **agent_config.py** | 5.4 KB | Settings-driven thresholds for all 35 agents |

### Subsystem Directories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `debate/` | debate_engine.py, debate_scorer.py, debate_utils.py | Bull/Bear debate orchestration |
| `regime/` | bayesian_regime.py | Bayesian regime classification |
| `reflexes/` | circuit_breaker.py | Brainstem protective reflexes |
| `directives/` | loader.py | Trading directive loading |

## Key Subsystems

### Blackboard (Thalamus)
**File**: `blackboard.py` — Shared memory that all agents read/write during a council run. Contains market data, feature vectors, intermediate results from earlier stages.

### Shadow Tracker
**File**: `shadow_tracker.py` — Tracks paper-mode council decisions. Compares what the council decided vs what would have happened. Used for validation before going live.

### Self-Awareness (Metacognition)
**File**: `self_awareness.py` — Monitors council decision quality over time. Tracks win/loss ratios by agent, regime, sector. Flags degrading performance.

### Homeostasis (Auto-Healing)
**File**: `homeostasis.py` — Maintains system balance. Modes: AGGRESSIVE, NORMAL, DEFENSIVE, HALTED. Not yet wired to Kelly sizing (Phase C fix).

### Overfitting Guard
**File**: `overfitting_guard.py` — Detects when agents overfit to recent conditions. Triggers weight resets or retraining when patterns detected.

### HITL Gate
**File**: `hitl_gate.py` — Human-in-the-loop approval. Can require manual approval for trades above configurable thresholds. Ready but not always active.

## All 35 Agents by File

| Agent | File | Weight | Stage |
|-------|------|--------|-------|
| Market Perception | market_perception_agent.py | 1.0 | 1 |
| Flow Perception | flow_perception_agent.py | 0.8 | 1 |
| Regime | regime_agent.py | 1.2 | 1 |
| Social Perception | social_perception_agent.py | 0.7 | 1 |
| News Catalyst | news_catalyst_agent.py | 0.6 | 1 |
| YouTube Knowledge | youtube_knowledge_agent.py | 0.4 | 1 |
| Intermarket | intermarket_agent.py | 0.7 | 1 |
| GEX | gex_agent.py | 0.9 | 1 |
| Insider | insider_agent.py | 0.85 | 1 |
| FinBERT Sentiment | finbert_sentiment_agent.py | 0.75 | 1 |
| Earnings Tone | earnings_tone_agent.py | 0.8 | 1 |
| Dark Pool | dark_pool_agent.py | 0.7 | 1 |
| Macro Regime | macro_regime_agent.py | 1.0 | 1 |
| RSI | rsi_agent.py | — | 2 |
| BBV | bbv_agent.py | — | 2 |
| EMA Trend | ema_trend_agent.py | — | 2 |
| Relative Strength | relative_strength_agent.py | — | 2 |
| Cycle Timing | cycle_timing_agent.py | — | 2 |
| Supply Chain | supply_chain_agent.py | 0.7 | 2 |
| Institutional Flow | institutional_flow_agent.py | 0.7 | 2 |
| Congressional | congressional_agent.py | 0.6 | 2 |
| Hypothesis | hypothesis_agent.py | 0.9 | 3 |
| Layered Memory | layered_memory_agent.py | 0.6 | 3 |
| Strategy | strategy_agent.py | 1.1 | 4 |
| Risk | risk_agent.py | 1.5 | 5 |
| Execution | execution_agent.py | 1.3 | 5 |
| Portfolio Optimizer | portfolio_optimizer_agent.py | 0.8 | 5 |
| Bull Debater | bull_debater.py | — | 5.5 |
| Bear Debater | bear_debater.py | — | 5.5 |
| Red Team | red_team_agent.py | — | 5.5 |
| Critic | critic_agent.py | 0.5 | 6 |
| Alternative Data | alt_data_agent.py | 0.5 | post |
