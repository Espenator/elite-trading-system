---
name: agent-swarm-design
description: >
  Expert agent and council design skill for Espen Schiefloe's Embodier Trader within the elite-trading-system.
  Guides best practices for the 35-agent council DAG, Bayesian-weighted arbiter, 7-stage parallel pipeline,
  debate protocol, MessageBus architecture, CouncilGate bridging, WeightLearner, 12 discovery scouts,
  3-tier LLM router, brain service, and CNS (Central Nervous System) architecture. Use this skill whenever
  Espen mentions: council, agents, swarm, DAG, arbiter, debate, red team, MessageBus, CouncilGate,
  WeightLearner, shadow tracker, self-awareness, homeostasis, overfitting guard, HITL gate, scouts,
  discovery, LLM router, brain service, gRPC, Ollama, CNS, brainstem, cortex, thalamus, blackboard,
  AgentVote, veto agents, signal pipeline, event-driven, or asks about designing new agents, improving
  agent coordination, debugging agent behavior, or structuring autonomous decision-making.
---

# Agent & Council Design — Expert Guide

You are Espen's **agent architecture specialist** for the Embodier Trader system. You understand the 35-agent council DAG, Bayesian-weighted arbitration, event-driven pipelines, and the specific challenges of autonomous trading systems. You think in terms of reliability, failure modes, graceful degradation, and measurable agent impact.

**Core philosophy**: Agents should be **simple, specialized, and skeptical**. Each agent does ONE thing well. Multiple simple agents outperform one complex agent. Agents must challenge each other before any capital is deployed. Measure every agent's contribution via Bayesian weights.

**Version**: v5.0.0 (March 12, 2026) — All Phases complete. ~95% production-ready.

---

## CNS Architecture Overview (Central Nervous System)

The Embodier Trader uses a **biological nervous system** metaphor for its architecture:

| CNS Component | System Component | Purpose |
|---|---|---|
| **Brainstem** | `reflexes/circuit_breaker.py` | Automatic protective reflexes (leverage limits, concentration caps) |
| **Spinal Cord** | Council DAG (35 agents, 7 stages) | Core decision-making pipeline — fast, parallel |
| **Cortex** | 3-tier LLM router (Ollama → Perplexity → Claude) | Deep reasoning for complex situations |
| **Thalamus** | `blackboard.py` | Shared state relay — all agents read/write here |
| **Autonomic** | `weight_learner.py` (Bayesian Beta(α,β)) | Unconscious learning — agent weights converge over time |
| **PNS Sensory** | Data ingestion, scouts, AlpacaStream | External data flowing in |
| **PNS Motor** | OrderExecutor, Alpaca API | Actions flowing out (trades) |

---

## 35-Agent Council DAG

The council is a **Directed Acyclic Graph** with 7 parallel stages. All agents return `AgentVote` from `council/schemas.py`. The arbiter combines votes using Bayesian-weighted scores.

### Agent Registry (32 agent files → 35 registered agents)

Located in `backend/app/council/agents/`:

**Stage 1: Perception (5 agents)**
| Agent | File | Purpose |
|---|---|---|
| Flow Perception | `flow_perception_agent.py` | Unusual Whales options flow analysis |
| Market Perception | `market_perception_agent.py` | Broad market reading (price, volume, breadth) |
| Social Perception | `social_perception_agent.py` | Social media + news sentiment |
| Dark Pool | `dark_pool_agent.py` | Dark pool flow + DIX/GEX (SqueezeMetrics) |
| GEX | `gex_agent.py` | Gamma exposure analysis |

**Stage 2: Technical (4 agents)**
| Agent | File | Purpose |
|---|---|---|
| RSI | `rsi_agent.py` | RSI-based signal generation |
| EMA Trend | `ema_trend_agent.py` | Exponential moving average trend analysis |
| BBV (Bollinger Band Volume) | `bbv_agent.py` | Bollinger + volume confluence |
| Relative Strength | `relative_strength_agent.py` | Cross-sectional relative strength/weakness |

**Stage 3: Hypothesis (3 agents)**
| Agent | File | Purpose |
|---|---|---|
| Hypothesis | `hypothesis_agent.py` | LLM-powered hypothesis generation (brain service) |
| Earnings Tone | `earnings_tone_agent.py` | Earnings call transcript sentiment |
| News Catalyst | `news_catalyst_agent.py` | Breaking news catalyst detection |

**Stage 4: Strategy (5 agents)**
| Agent | File | Purpose |
|---|---|---|
| Strategy | `strategy_agent.py` | Core strategy signal synthesis |
| Macro Regime | `macro_regime_agent.py` | Macro environment assessment (FRED, VIX) |
| Regime | `regime_agent.py` | HMM/PELT regime classification |
| Cycle Timing | `cycle_timing_agent.py` | Market cycle + seasonal timing |
| Intermarket | `intermarket_agent.py` | Cross-market correlation analysis |

**Stage 5: Risk & Execution (2 agents — VETO POWER)**
| Agent | File | Purpose |
|---|---|---|
| **Risk** | `risk_agent.py` | **VETO AGENT** — position size, heat, drawdown checks |
| **Execution** | `execution_agent.py` | **VETO AGENT** — liquidity, spread, fill probability |

**VETO_AGENTS = {"risk", "execution"}** — Only these two can veto. No other agent can.

**Stage 5.5: Academic Edge (6 agents)**
| Agent | File | Purpose |
|---|---|---|
| Alt Data | `alt_data_agent.py` | Alternative data synthesis |
| Congressional | `congressional_agent.py` | Congressional trading disclosures |
| Insider | `insider_agent.py` | SEC Form 4 insider transactions |
| Institutional Flow | `institutional_flow_agent.py` | 13F institutional positioning |
| Supply Chain | `supply_chain_agent.py` | Supply chain disruption signals |
| FinBERT Sentiment | `finbert_sentiment_agent.py` | Transformer-based financial NLP |

**Stage 6: Debate & Red Team (3 agents)**
| Agent | File | Purpose |
|---|---|---|
| Bull Debater | `bull_debater.py` | Argues FOR the trade proposal |
| Bear Debater | `bear_debater.py` | Argues AGAINST (sees bull case, counters directly) |
| Red Team | `red_team_agent.py` | Adversarial stress-testing of the thesis |

**Stage 7: Synthesis (4 agents)**
| Agent | File | Purpose |
|---|---|---|
| Critic | `critic_agent.py` | Final quality check on reasoning |
| Portfolio Optimizer | `portfolio_optimizer_agent.py` | Portfolio-level position optimization |
| Layered Memory | `layered_memory_agent.py` | Historical pattern matching from memory |
| YouTube Knowledge | `youtube_knowledge_agent.py` | Knowledge base from financial education |

### Arbiter (Final Decision)

**File**: `council/arbiter.py`

The arbiter combines all `AgentVote` responses using **Bayesian-weighted scores**:

```python
# Each agent has a weight from WeightLearner: Beta(α, β)
# Weight = α / (α + β) — converges toward agent's true accuracy
# Agents that predict well get higher weights over time
# VETO agents can reject regardless of weighted score
```

---

## Council Orchestration (15 files)

Located in `backend/app/council/`:

| File | Purpose |
|---|---|
| `runner.py` | Council execution engine — runs 7-stage DAG |
| `arbiter.py` | Bayesian-weighted final decision maker |
| `schemas.py` | `AgentVote` schema — all agents MUST return this |
| `council_gate.py` | Signal → Council bridge (threshold = 65) |
| `weight_learner.py` | Bayesian Beta(α,β) weight updates |
| `blackboard.py` | Shared state (Thalamus) — agents read/write |
| `shadow_tracker.py` | Shadow mode tracking (paper trades) |
| `self_awareness.py` | System self-monitoring and introspection |
| `homeostasis.py` | System balance maintenance |
| `overfitting_guard.py` | Detects overfitting in agent predictions |
| `hitl_gate.py` | Human-in-the-loop gate (ready, not always active) |
| `feedback_loop.py` | Trade outcome → agent weight feedback |
| `registry.py` | Agent registration and discovery |
| `agent_config.py` | Agent configuration and stage assignment |
| `data_quality.py` | Input data quality validation |
| `task_spawner.py` | Dynamic task creation |

### Debate Engine (3 files)

Located in `council/debate/`:

| File | Purpose |
|---|---|
| `debate_engine.py` | Orchestrates Bull/Bear/RedTeam debate |
| `debate_scorer.py` | Scores debate quality and argument strength |
| `debate_utils.py` | Shared debate utilities |

---

## Event Pipeline

```
AlpacaStreamService → SignalEngine → CouncilGate → Council (35 agents, 7 stages) → OrderExecutor → Alpaca
                                          ↕
                                  MessageBus (pub/sub, 10K queue)
                                          ↕
                           12 Scouts → swarm.idea topic → IdeaTriage
```

### Event-Driven Execution (NOT 15-minute polling)

The system is **event-driven with sub-1s council latency**:

1. **AlpacaStreamService** receives real-time market data
2. **SignalEngine** computes features + generates signal scores
3. **CouncilGate** evaluates if signal crosses threshold (currently 65)
4. **Council DAG** runs 7 parallel stages, all agents vote
5. **Arbiter** combines Bayesian-weighted votes
6. **OrderExecutor** submits bracket orders (with Gate 2b regime + Gate 2c circuit breakers)

### MessageBus Architecture (`core/message_bus.py`)

Central nervous system event router. High-performance async.

**Core topics**:
```
market_data.bar         → New OHLCV bars from Alpaca
market_data.quote       → Tick data
signal.generated        → Generated signals (score >= 70)
order.submitted         → Order placed on broker
order.filled            → Order filled
order.cancelled         → Order cancelled
model.updated           → ML model retrained
risk.alert              → Risk Shield rejections or warnings
system.heartbeat        → 30s system health pulse
swarm.idea              → Scout discovery ideas
```

**Queue**: Max 10,000 events, graceful shutdown with 5s drain timeout.

---

## 12 Discovery Scouts (Continuous)

Located in `backend/app/services/scouts/`:

| Scout | File | Purpose |
|---|---|---|
| Flow Hunter | `flow_hunter.py` | Unusual options flow detection |
| Gamma | `gamma.py` | Gamma exposure squeeze candidates |
| Insider | `insider.py` | SEC Form 4 insider buying |
| Macro | `macro.py` | FRED macro regime shifts |
| News | `news.py` | Breaking news catalysts |
| Congress | `congress.py` | Congressional trade disclosures |
| Earnings | `earnings.py` | Upcoming earnings catalysts |
| Sector Rotation | `sector_rotation.py` | Sector momentum shifts |
| Sentiment | `sentiment.py` | Aggregate sentiment anomalies |
| Short Squeeze | `short_squeeze.py` | Short interest + squeeze setups |
| Correlation Break | `correlation_break.py` | Cross-asset correlation disruptions |
| IPO | `ipo.py` | New IPO / SPAC opportunities |

**CRITICAL**: Discovery is **continuous, not polling-based** (Issue #38). Scouts publish to `swarm.idea` topic on MessageBus.

All scouts extend `base.py` and are registered via `registry.py`. Phase A1 fixed 5 crashing scouts by adding missing service methods.

---

## 3-Tier LLM Intelligence Router

Located in `backend/app/services/llm_router.py` + `llm_clients/`:

```
Tier 1: Ollama (Local)      → Routine tasks, fast response, no API cost
         ↓ (if needs search)
Tier 2: Perplexity           → Web search + synthesis, moderate cost
         ↓ (if needs deep reasoning)
Tier 3: Claude               → Deep reasoning, 6 specific tasks only
```

### LLM Clients
| Client | File | Model | Use Case |
|---|---|---|---|
| Ollama | `llm_clients/ollama_client.py` | Local models on RTX GPU | Routine agent tasks |
| Perplexity | `llm_clients/perplexity_client.py` | Perplexity API | Search-augmented analysis |
| Claude | `llm_clients/claude_client.py` | Claude API | Deep reasoning (6 tasks) |

### Brain Service (PC2)
- **Protocol**: gRPC on port 50051
- **Hardware**: RTX GPU on ProfitTrader (192.168.1.116)
- **Client**: `services/brain_client.py`
- **Primary user**: `hypothesis_agent.py`

### Cognitive Layer
| Component | Purpose |
|---|---|
| MemoryBank | Historical pattern storage and retrieval |
| HeuristicEngine | Rule-based rapid decision heuristics |
| KnowledgeGraph (ETBI) | Entity-relationship graph for market knowledge |

---

## CouncilGate: Signal → Council Bridge

**File**: `council/council_gate.py`

CouncilGate decides which signals get sent to the full council for evaluation.

```python
# Current threshold: 65
# KNOWN ISSUE: This filters 20-40% of profitable signals (Phase B fix)
# Signals below threshold are logged but not sent to council
```

**Rules**:
- Signals MUST go through CouncilGate — do NOT bypass
- Gate evaluates signal score, confidence, and basic quality checks
- Below threshold → logged, not traded
- Above threshold → full council evaluation

---

## WeightLearner: Bayesian Agent Weights

**File**: `council/weight_learner.py`

Each agent's vote weight is learned over time using **Bayesian Beta distributions**:

```python
# Agent weight = Beta(α, β)
# α = successful predictions, β = failed predictions
# E[weight] = α / (α + β)
# As agent accumulates correct predictions, weight increases
# As agent accumulates wrong predictions, weight decreases
# This is mathematically correct and proven (see CLAUDE.md)
```

**KNOWN ISSUE**: Confidence floor of 0.5 drops 50%+ of trade outcomes from learning (Phase C fix).

---

## Order Executor Enforcement (Phase A)

**File**: `services/order_executor.py`

Three enforcement gates added in Phase A:

| Gate | Check | Action |
|---|---|---|
| **Gate 2b** (Regime) | regime max_pos=0 or kelly_scale=0 | Block entry (RED/CRISIS regime) |
| **Gate 2c** (Circuit Breaker) | leverage > 2x or concentration > 25% | Block entry |
| **Safety Gate** | Account type vs TRADING_MODE | Force SHADOW mode on mismatch |

**VIX-based regime fallback**: When OpenClaw bridge is offline, uses VIX levels for regime classification.

---

## AgentVote Schema (ALL agents must return this)

**File**: `council/schemas.py`

```python
class AgentVote:
    agent_name: str          # e.g., "risk_agent"
    direction: str           # "BULLISH", "BEARISH", "NEUTRAL"
    confidence: float        # 0.0 - 1.0
    score: float             # 0 - 100
    reasoning: str           # Human-readable explanation
    veto: bool = False       # Only risk + execution agents can set True
    metadata: dict = {}      # Agent-specific data
```

---

## Bull/Bear Debate Protocol

Research shows explicit bull/bear debate outperforms simple voting by 15-25%.

### Protocol Flow

1. **Bull Debater** argues FOR the trade proposal
2. **Bear Debater** sees Bull's argument, argues AGAINST (direct counter)
3. **Red Team** adversarially stress-tests the thesis
4. **Debate Scorer** evaluates argument quality
5. Debate result feeds into Arbiter's final decision

### Design Principles
1. Bull and Bear are **separate agents**, not roles
2. Bear **sees Bull's argument** — direct counter, not independent
3. Asymmetric veto: Risk/Execution agents can veto alone; debate only informs
4. Time-boxed: agents have deadlines within the DAG stage
5. Quantitative anchor: ML signal score is never overridden by debate alone
6. Split verdict: If debate is split 50/50 and signal < 0.55, default NO TRADE

---

## Agent Evaluation & Monitoring

### Bayesian Weight Tracking
Every agent's accuracy is tracked via WeightLearner Beta(α,β) distributions. Over time:
- Accurate agents gain weight in arbiter decisions
- Inaccurate agents lose weight
- New agents start with uniform prior Beta(1,1)

### Self-Awareness System
**File**: `council/self_awareness.py`
- Monitors council decision quality over time
- Tracks win/loss ratios by agent, by regime, by sector
- Flags degrading agent performance

### Homeostasis
**File**: `council/homeostasis.py`
- Maintains system balance
- Prevents runaway behavior (e.g., all agents agree too often)
- Monitors diversity of opinions

### Overfitting Guard
**File**: `council/overfitting_guard.py`
- Detects when agents overfit to recent market conditions
- Triggers retraining or weight resets when detected

---

## Shadow Tracker

**File**: `council/shadow_tracker.py`

Tracks what the council WOULD have done vs what it actually did:
- In SHADOW mode: council runs but doesn't execute trades
- Records hypothetical P&L for comparison
- Used for validation before going live with new agents or parameters

---

## Deploying New Agents

### Agent Template

All agents MUST:
1. Return `AgentVote` from `council/schemas.py`
2. Be registered in `council/registry.py`
3. Be assigned to a stage in `council/agent_config.py`
4. Handle errors gracefully (don't crash the DAG)

```python
from app.council.schemas import AgentVote

class NewAgent:
    def __init__(self, blackboard, message_bus):
        self.blackboard = blackboard
        self.bus = message_bus
        self.name = "new_agent"

    async def vote(self, symbol: str, context: dict) -> AgentVote:
        # 1. Read from blackboard
        data = self.blackboard.read('key_data')

        # 2. Analyze
        score, confidence = self.analyze(data, symbol)

        # 3. Return AgentVote (REQUIRED schema)
        return AgentVote(
            agent_name=self.name,
            direction="BULLISH" if score > 60 else "BEARISH" if score < 40 else "NEUTRAL",
            confidence=confidence,
            score=score,
            reasoning="Explanation of analysis",
            veto=False,  # Only risk/execution can veto
        )
```

### Safety Rules
- **No eval/exec** — Hard ban
- **No file writes** — Use DuckDB only
- **No hardcoded secrets** — Read from environment
- **Timeouts** — Every operation must have timeout
- **Audit trail** — All decisions logged via AgentVote

---

## Debugging Agent Issues

**Agent decisions are wrong**: Check WeightLearner Beta(α,β). If weight < 0.45, agent is underperforming.

**Council takes too long**: Profile which stage is slow. Check if external APIs (LLM, data sources) are timing out.

**Agent crashes**: `_supervised_loop()` wrapper auto-recovers (3 retries + Slack alerts). Check logs.

**Agents agree too much**: Check homeostasis metrics. Debate protocol should force disagreement.

**Scout not finding ideas**: Check if underlying data source API is returning data. Phase A1 fixed 5 scout crashes.

**Signals not reaching council**: Check CouncilGate threshold (currently 65). Known issue: filters 20-40% of profitable signals.
