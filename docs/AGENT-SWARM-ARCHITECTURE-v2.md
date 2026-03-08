# Elite Trading System: Intelligent Agent Swarm Architecture v2

**Version**: v3.5.0
**Date**: 2026-03-04
**Last Updated**: March 8, 2026
**Status**: IMPLEMENTED — 32-agent council active as of v3.5.0
**Scope**: Complete redesign of agent layer, LLM integration, learning systems, and compute model

---

## Executive Summary

The system has evolved from a static 17-agent DAG into a **living 32-agent council** (31 agents in the main DAG + 1 background enrichment agent). The council executes a 7-stage DAG with adversarial debate, multi-tier fast/deep routing, and Bayesian weight learning.

As of v3.5.0 (March 8, 2026), the implemented architecture includes:
- **32 council agents** across 4 categories (11 core, 12 academic edge, 6 supplemental, 3 debate/adversarial) + 1 background agent
- **7-stage DAG** (Stages 1–7 plus Stage 5.5 for debate/red-team)
- **Multi-tier evaluation**: fast path (7 agents, threshold ≥45) and deep path (full council, threshold ≥65)
- **15 council orchestration files** (runner, arbiter, hitl_gate, blackboard, etc.)
- **Local brain service** on PC2 via gRPC 50051 (Ollama + vLLM)
- **3 fine-tuned local LLMs** for fast, free, specialized reasoning
- Self-recursive Bayesian weight learning via `weight_learner.py`
- Homeostasis, circuit breakers, and fail-closed safety gates

> **⚠️ Known Critical Bugs (from audit 2026-03-08 — 42 bugs total, see `docs/audits/brain_consciousness_audit_2026-03-08.pdf`)**
>
> 1. **TurboScanner/CouncilGate threshold mismatch** — TurboScanner scores 0.0–1.0 but CouncilGate threshold is `65.0`; signals never enter the council without manual normalization.
> 2. **Double `council.verdict` publication** — Both `runner.py` and `council_gate.py` publish `council.verdict`; risk of duplicate order execution.
> 3. **UnusualWhales flow never published** — Options flow is fetched from API but never published to MessageBus, so flow_perception_agent sees no live flow data.
> 4. **SelfAwareness Bayesian tracking never called** — `self_awareness.py` (286 lines, fully implemented) is never called from `runner.py` or anywhere else.
> 5. **IntelligenceCache.start() never called** — Every council evaluation runs cold; cached intelligence (LLM results, news) is never warmed up.

---

## Part 1: Implemented Architecture (v3.5.0)

### 1.1 Council DAG — 7 Stages

```
                    ┌─────────────────┐
                    │  Council Runner  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼─────────────────────────────────┐
        │ Stage 1: Perception + Academic Edge P0/P1/P2          │
        │   (parallel — 13 agents)                              │
        │   market_perception, flow_perception, regime,         │
        │   social_perception, news_catalyst, youtube_knowledge,│
        │   intermarket, gex, insider, finbert_sentiment,        │
        │   earnings_tone, dark_pool, macro_regime               │
        ├─────────────────────────────────────────────────────┤
        │ Stage 2: Technical Analysis + Data Enrichment         │
        │   (parallel — 8 agents)                               │
        │   rsi, bbv, ema_trend, relative_strength,             │
        │   cycle_timing, supply_chain, institutional_flow,     │
        │   congressional                                        │
        ├─────────────────────────────────────────────────────┤
        │ Stage 3: Hypothesis + Memory (parallel — 2 agents)    │
        │   hypothesis, layered_memory                           │
        ├─────────────────────────────────────────────────────┤
        │ Stage 4: Strategy (1 agent)                           │
        │   strategy                                            │
        ├─────────────────────────────────────────────────────┤
        │ Stage 5: Risk + Execution + Portfolio (parallel — 3) │
        │   risk, execution, portfolio_optimizer                │
        ├─────────────────────────────────────────────────────┤
        │ Stage 5.5: Debate + Red Team (3 agents)               │
        │   bull_debater, bear_debater, red_team                │
        ├─────────────────────────────────────────────────────┤
        │ Stage 6: Critic (1 agent)                             │
        └─────────────────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  Stage 7: Arbiter│
                    │ (deterministic   │
                    │  weighted vote)  │
                    └─────────────────┘
                             │
                    ┌────────┴──────────────┐
                    │ Post-Arbiter (bg):     │
                    │ alt_data (enrichment) │
                    └───────────────────────┘
```

**Total agents: 32** (31 in main DAG + 1 background post-arbiter)

### 1.2 Agent Roster — Complete List

#### 11 Core Agents
| Agent | File | Stage | Role |
|---|---|---|---|
| market_perception | market_perception_agent.py | 1 | Price action, volume, trend |
| flow_perception | flow_perception_agent.py | 1 | Options flow, dark pool |
| regime | regime_agent.py | 1 | Market regime classification |
| social_perception | social_perception_agent.py | 1 | Social media sentiment |
| news_catalyst | news_catalyst_agent.py | 1 | News event detection |
| youtube_knowledge | youtube_knowledge_agent.py | 1 | Video/channel intelligence |
| hypothesis | hypothesis_agent.py | 3 | LLM-based thesis generation |
| strategy | strategy_agent.py | 4 | Trade strategy selection |
| risk | risk_agent.py | 5 | Risk gate + drawdown check |
| execution | execution_agent.py | 5 | Order sizing + timing |
| critic | critic_agent.py | 6 | Final quality gate |

#### 12 Academic Edge Agents (P0–P4)
| Agent | File | Stage | Edge |
|---|---|---|---|
| gex | gex_agent.py | 1 | Gamma exposure (options market structure) |
| insider | insider_agent.py | 1 | Insider trading filings |
| earnings_tone | earnings_tone_agent.py | 1 | Earnings call NLP sentiment |
| finbert_sentiment | finbert_sentiment_agent.py | 1 | FinBERT financial NLP |
| dark_pool | dark_pool_agent.py | 1 | Dark pool print detection |
| macro_regime | macro_regime_agent.py | 1 | Macro regime from FRED/EDGAR |
| supply_chain | supply_chain_agent.py | 2 | Supply chain risk signals |
| institutional_flow | institutional_flow_agent.py | 2 | 13F institutional positioning |
| congressional | congressional_agent.py | 2 | Congressional trading disclosures |
| portfolio_optimizer | portfolio_optimizer_agent.py | 5 | Kelly + correlation sizing |
| layered_memory | layered_memory_agent.py | 3 | Episodic + semantic memory |
| alt_data | alt_data_agent.py | post | Alternative data enrichment (background) |

#### 6 Supplemental Agents
| Agent | File | Stage | Role |
|---|---|---|---|
| rsi | rsi_agent.py | 2 | RSI momentum |
| bbv | bbv_agent.py | 2 | Bollinger Band + Volume |
| ema_trend | ema_trend_agent.py | 2 | EMA trend confirmation |
| intermarket | intermarket_agent.py | 1 | Cross-asset correlation |
| relative_strength | relative_strength_agent.py | 2 | Relative strength vs sector/SPY |
| cycle_timing | cycle_timing_agent.py | 2 | Market cycle phase detection |

#### 3 Debate/Adversarial Agents
| Agent | File | Stage | Role |
|---|---|---|---|
| bull_debater | bull_debater.py | 5.5 | Bullish thesis construction |
| bear_debater | bear_debater.py | 5.5 | Bearish counter-thesis |
| red_team | red_team_agent.py | 5.5 | Adversarial stress test |

### 1.3 Council Orchestration — 15 Files

Located in `backend/app/council/`:

| File | Role |
|---|---|
| `runner.py` | Main DAG orchestrator — runs all 7 stages |
| `arbiter.py` | Deterministic weighted vote → DecisionPacket |
| `schemas.py` | AgentVote, DecisionPacket, CognitiveMeta dataclasses |
| `council_gate.py` | MessageBus bridge: signal.generated → council run |
| `blackboard.py` | Shared context state between agents |
| `hitl_gate.py` | Human-in-the-loop review gate |
| `weight_learner.py` | Bayesian agent weight updates post-trade |
| `self_awareness.py` | Bayesian self-monitoring (implemented, not yet wired) |
| `task_spawner.py` | Async parallel agent execution |
| `overfitting_guard.py` | Walk-forward overfitting detection |
| `data_quality.py` | Input data freshness checks |
| `shadow_tracker.py` | Shadow mode signal tracking |
| `feedback_loop.py` | Trade outcome → weight feedback |
| `homeostasis.py` | System health + circuit breakers (fail-closed) |
| `agent_config.py` | Agent registry + configuration |

Plus subdirectories: `agents/` (32 agent files), `debate/`, `reflexes/`, `regime/`

### 1.4 Multi-Tier Evaluation

The system uses two evaluation paths (via `council_gate.py` + `fast_council.py`):

| Path | Threshold | Agents | Latency |
|---|---|---|---|
| **Fast path** | Score ≥ 45 (COUNCIL_FAST_THRESHOLD) | 7 agents (F1: market_perception+regime, F2: rsi+ema_trend+bbv+relative_strength, F3: risk) | ~200ms |
| **Deep path** | Score ≥ 65 (COUNCIL_GATE_ENABLED threshold) | Full 31-agent DAG | ~2–8s |
| **Bypass** | COUNCIL_GATE_ENABLED=false | 0 agents (fallback verdict) | ~10ms |

Fast path returns a `FastCouncilResult` with an `escalate` flag. Signals in [45, 65) go through fast path; ≥65 goes direct to deep council.

### 1.5 Previous Architecture Limitations (Pre-v3.5.0)

| Limitation | Status in v3.5.0 |
|---|---|
| **Static 17-agent DAG** | ✅ Replaced — 31-agent 7-stage DAG |
| **One-shot voting** | ✅ Replaced — adversarial debate in Stage 5.5 |
| **Passive blackboard** | ✅ Enhanced — BlackboardState shared across all stages |
| **No online learning** | ✅ Partial — Bayesian weight_learner wired; SelfAwareness not yet called |
| **Single LLM tier** | ✅ Replaced — multi-tier: local Ollama brain + cloud fallback |
| **Heuristic Kelly sizing** | ✅ Enhanced — portfolio_optimizer_agent + kelly_position_sizer |
| **No regime routing** | ✅ Added — regime agent + fast/deep tier routing |
| **No debate** | ✅ Added — bull_debater, bear_debater, red_team in Stage 5.5 |

---

## Part 2: Future Architecture Proposals (Beyond v3.5.0)

### 2.1 High-Level Design

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     META-ORCHESTRATOR (Conductor)                        │
│  Routes to specialized swarms based on regime + opportunity type         │
│  Built on LangGraph for stateful cyclical workflow management            │
└──────┬──────────────────────┬──────────────────────┬────────────────────┘
       │                      │                      │
┌──────┴──────┐      ┌───────┴───────┐      ┌──────┴──────────┐
│ ALPHA SWARM │      │  RISK SWARM   │      │ EVOLUTION ENGINE │
│ (find edge) │◄────►│ (protect $)   │      │ (learn & grow)   │
│             │DEBATE│               │      │                  │
│ ┌─────────┐ │      │ ┌───────────┐ │      │ ┌──────────────┐ │
│ │Momentum │ │      │ │Portfolio  │ │      │ │Genetic Agent │ │
│ │ Swarm   │ │      │ │Optimizer  │ │      │ │  Evolver     │ │
│ ├─────────┤ │      │ ├───────────┤ │      │ ├──────────────┤ │
│ │MeanRev  │ │      │ │Correlation│ │      │ │RL Position   │ │
│ │ Swarm   │ │      │ │Monitor    │ │      │ │  Policy      │ │
│ ├─────────┤ │      │ ├───────────┤ │      │ ├──────────────┤ │
│ │Flow     │ │      │ │Stress Test│ │      │ │Agent Spawner │ │
│ │ Swarm   │ │      │ │Simulator  │ │      │ │  / Killer    │ │
│ ├─────────┤ │      │ └───────────┘ │      │ ├──────────────┤ │
│ │Catalyst │ │      └───────────────┘      │ │Self-Recursive│ │
│ │ Swarm   │ │                             │ │  Optimizer   │ │
│ ├─────────┤ │                             │ └──────────────┘ │
│ │Volatility│ │                             └─────────────────┘
│ │ Swarm   │ │
│ └─────────┘ │
└─────────────┘
       │
┌──────┴──────────────────────────────┐
│     LOCAL LLM REASONING LAYER       │
│  ┌────────┐ ┌────────┐ ┌─────────┐ │
│  │ Qwen   │ │Mistral │ │FinTuned │ │
│  │ Judge  │ │ Critic │ │ LLaMA   │ │
│  └────────┘ └────────┘ └─────────┘ │
│  Served via vLLM with PagedAttention │
│  Grammar-constrained structured I/O  │
└──────────────────────────────────────┘
```

### 2.2 Core Design Principles

1. **Decouple direction from sizing** — Alpha swarm determines trade direction; RL policy determines position size. These are different problems requiring different intelligence.
2. **Risk-sensitive rewards everywhere** — Never optimize for raw returns. Always use Sharpe, Sortino, CVaR, max drawdown penalty.
3. **Regime-conditional everything** — Every layer adapts based on detected market regime.
4. **Bounded self-improvement** — Evolve scaffolding and parameters, not core models. STOP/STaR pattern, not Godel Agent.
5. **Incentive alignment** — Each agent's reward is its marginal contribution to system-level P&L (Markov team game formulation).
6. **Explainability** — LLM-based routing provides natural language justification for every decision.

---

## Part 3: Specialized Micro-Swarms

### 3.1 Replace Flat DAG with Regime-Routed Swarms

Instead of 32 agents all voting on every trade, the **Meta-Orchestrator** routes to the right swarm:

| Micro-Swarm | Activates When | Agents Inside (3-5) | Edge Source |
|---|---|---|---|
| **Momentum Swarm** | ADX > 25, clear trend, institutional flow | `flow_reader`, `ema_trend`, `ml_momentum`, `volume_surge` | Ride trends with institutional flow confirmation |
| **Mean Reversion Swarm** | ADX < 20, range-bound, BB squeeze | `bbv`, `rsi_extreme`, `cycle_timing`, `pairs_stat_arb` | Fade extremes with statistical backing |
| **Regime Transition Swarm** | VIX spike, sector rotation, yield curve shift | `regime_hmm`, `intermarket`, `macro_shift`, `crisis_detector` | First-mover on regime changes |
| **Earnings/Catalyst Swarm** | Pre/post earnings, FDA, news event | `news_catalyst`, `options_flow`, `earnings_drift`, `social_surge` | Exploit post-earnings drift anomaly |
| **Volatility Swarm** | VIX > 25, vol crush, term structure inversion | `vol_surface`, `term_structure`, `gamma_exposure`, `vix_mean_rev` | Trade volatility as an asset class |

### 3.2 Swarm Activation Logic

```python
class MetaOrchestrator:
    """LangGraph-based conductor that routes to the right micro-swarm."""

    def select_swarms(self, regime: MarketRegime, features: dict) -> list[MicroSwarm]:
        active = []

        # Always active: Risk Swarm (guardian)
        active.append(self.risk_swarm)

        # Regime-based routing
        if regime in (BULLISH, NEUTRAL) and features["adx"] > 25:
            active.append(self.momentum_swarm)
        if features["adx"] < 20 and features["bb_width"] < 0.05:
            active.append(self.mean_reversion_swarm)
        if self.regime_change_detected():
            active.append(self.regime_transition_swarm)
        if self.catalyst_pending(features["symbol"]):
            active.append(self.catalyst_swarm)
        if features["vix"] > 25 or self.vol_crush_detected():
            active.append(self.volatility_swarm)

        return active  # Typically 2-3 swarms, never all 5
```

**Impact**: Instead of 32 agents generating noise, 6-10 relevant experts generate signal. Signal-to-noise ratio increases dramatically.

---

## Part 4: Agent Debate Protocol

### 4.1 Replace One-Shot Voting with Adversarial Debate

```
┌─────────────────────────────────────────────────────┐
│                DEBATE PROTOCOL                       │
│                                                      │
│  Round 1: THESIS (each alpha agent proposes)         │
│  ├─ Direction: BUY/SELL/HOLD                        │
│  ├─ Entry, Target, Stop                             │
│  ├─ Conviction: 0-100                               │
│  ├─ Reasoning: natural language                     │
│  └─ Evidence: specific data points                  │
│                                                      │
│  Round 2: ADVERSARIAL CHALLENGE                      │
│  ├─ Critic LLM attacks each thesis                  │
│  ├─ "What if VIX spikes 20% tomorrow?"              │
│  ├─ "This pattern failed 60% of the time in 2022"   │
│  ├─ Agent must DEFEND or REVISE thesis              │
│  └─ Agents that can't defend → eliminated           │
│                                                      │
│  Round 3: SYNTHESIS                                  │
│  ├─ Judge LLM evaluates surviving theses            │
│  ├─ Ranks by post-debate conviction                 │
│  ├─ If NO thesis survives → NO TRADE (feature!)     │
│  └─ Winner → Risk Swarm for sizing                  │
│                                                      │
│  Time Budget: 3 rounds x 2s = 6 seconds max         │
└─────────────────────────────────────────────────────┘
```

### 4.2 Why This Matters

The current system has a **confirmation bias problem**. 32 agents looking at correlated indicators all agree because they're seeing the same thing. The adversarial debate (already implemented as Stage 5.5):
- Forces each thesis to survive scrutiny before capital is risked
- The "no thesis survives → no trade" outcome prevents low-conviction entries
- The Critic is trained specifically on trades that LOST money — it knows what failure looks like
- Reduces overtrading (the #1 profit killer for algorithmic systems)

---

## Part 5: Local LLM Reasoning Layer

### 5.1 Three Specialized Local Models

| Model | Role | Base Model | Fine-Tuning Data | GPU Memory | Latency |
|---|---|---|---|---|---|
| **Judge** | Debate moderator, thesis evaluator, swarm router | Qwen2.5-7B | 10K annotated trade debates + outcomes | ~8GB | <200ms |
| **Critic** | Adversarial challenger, devil's advocate | Mistral-7B-v0.3 | Historical trade failures, bear market scenarios, black swan events | ~8GB | <300ms |
| **Alpha** | Signal generation, pattern recognition, feature synthesis | LLaMA-3.1-8B | Fine-tuned on your trade history + outcomes via LoRA | ~8GB | <400ms |

### 5.2 Serving Architecture

```
┌──────────────────────────────────────────────────────┐
│              vLLM Inference Server                     │
│  ┌──────────────────────────────────────────────┐    │
│  │  PagedAttention (40% GPU memory savings)      │    │
│  │  Continuous Batching (10x throughput)          │    │
│  │  Grammar-Constrained Decoding (GBNF)          │    │
│  │  → Eliminates malformed JSON/tool calls        │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  Model Slots (on single RTX 4090 / A100):            │
│  ├─ Slot 1: Qwen-Judge    (7B, 8GB)                 │
│  ├─ Slot 2: Mistral-Critic (7B, 8GB)                │
│  └─ Slot 3: LLaMA-Alpha   (8B, 8GB)                 │
│                                                       │
│  Total VRAM: ~24GB (fits on single RTX 4090)         │
│  Fallback: Cloud API (Claude/GPT) for overflow       │
└──────────────────────────────────────────────────────┘
```

### 5.3 Why Local > Cloud for Trading

| Dimension | Cloud LLMs | Local Fine-Tuned LLMs |
|---|---|---|
| **Latency** | 500ms-5s (network + queue) | 50-400ms (local GPU) |
| **Cost** | $0.003-0.015 per 1K tokens | $0 marginal cost |
| **Customization** | Generic training data | Fine-tuned on YOUR trades |
| **Privacy** | Sends positions to third party | All data stays local |
| **Availability** | API outages, rate limits | Always available |
| **Throughput** | Rate-limited | 1000+ inferences/day free |

### 5.4 Fine-Tuning Pipeline (Weekly)

```python
class WeeklyFineTuner:
    """STOP/STaR pattern: models stay fixed, scaffolding evolves."""

    def fine_tune_alpha_model(self):
        # 1. Collect last week's trade outcomes
        trades = self.db.get_resolved_trades(days=7)

        # 2. Build training pairs
        #    Input: features at time of decision
        #    Output: what the CORRECT decision was (based on outcome)
        pairs = []
        for trade in trades:
            pairs.append({
                "input": trade.features_at_decision_time,
                "output": trade.optimal_action_with_hindsight
            })

        # 3. LoRA fine-tune (lightweight, 15-30 min on single GPU)
        self.alpha_model.lora_finetune(
            pairs,
            learning_rate=1e-5,
            epochs=3,
            lora_rank=16
        )

        # 4. Validate on held-out set before promoting
        if self.validate(self.alpha_model) > self.validate(self.current_model):
            self.promote(self.alpha_model)
        else:
            self.rollback()  # Safety: don't deploy worse model
```

---

## Part 6: Mixture of Experts (MoE) Signal Layer

### 6.1 TradExpert Pattern

Based on state-of-the-art research (LLMoE, TradExpert 2025), replace the monolithic signal engine with a Mixture of Experts:

```
┌──────────────────────────────────────────────────────────┐
│                  MoE SIGNAL LAYER                         │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Technical │  │  Flow    │  │  News/   │  │  Macro   │ │
│  │  Expert   │  │  Expert  │  │ Sentiment│  │  Expert  │ │
│  │ (XGBoost) │  │(XGBoost) │  │ Expert   │  │(XGBoost) │ │
│  │           │  │          │  │(LLaMA)   │  │          │ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘ │
│        │             │             │             │        │
│        └──────┬──────┴──────┬──────┘             │        │
│               │             │                    │        │
│        ┌──────┴─────────────┴────────────────────┘        │
│        │                                                  │
│  ┌─────┴──────────────────────────────────────────────┐  │
│  │            LLM-BASED GATING ROUTER                  │  │
│  │  Qwen-Judge dynamically weights experts based on:   │  │
│  │  - Current regime (trending vs ranging vs crisis)   │  │
│  │  - Data quality (is flow data fresh? news relevant?)│  │
│  │  - Historical expert accuracy per regime            │  │
│  │  Output: weighted combination + explanation         │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 6.2 Anti-Routing Collapse

From MIGA research: prevent the gating network from always favoring the same expert.
- **Group aggregation**: Force router to allocate minimum 10% weight to each expert
- **Load balancing loss**: Penalize uneven expert utilization during training
- **Regime-stratified evaluation**: Each expert must prove value in every regime, not just one

---

## Part 7: Self-Recursive Learning Engine

### 7.1 Three Learning Loops at Three Timescales

```
┌──────────────────────────────────────────────────────────────────┐
│                    LEARNING ARCHITECTURE                          │
│                                                                   │
│  LOOP 1: INTRA-DAY (every 30 minutes during market hours)        │
│  ├─ Track open position P&L trajectory                           │
│  ├─ Compare agent predictions vs actual price movement            │
│  ├─ Update agent confidence calibration (Platt scaling)          │
│  ├─ Adjust swarm activation thresholds based on today's regime   │
│  └─ Fast Bayesian update: agent_alpha += 0.1 if correct          │
│                                                                   │
│  LOOP 2: END-OF-DAY (nightly, after market close)                │
│  ├─ Full postmortem on all trades (win/loss/scratch analysis)    │
│  ├─ Retrain XGBoost experts with today's features + outcomes     │
│  ├─ Update MoE gating weights based on expert accuracy today     │
│  ├─ Run abbreviated genetic evolution (5 generations)            │
│  ├─ Recalibrate RL reward function if Sharpe drifting            │
│  └─ Generate "lessons learned" for Critic model context          │
│                                                                   │
│  LOOP 3: WEEKLY EVOLUTION (Saturday)                             │
│  ├─ Full genetic evolution cycle (30 generations)                │
│  ├─ LoRA fine-tune local LLMs on week's trade outcomes           │
│  ├─ Feature importance analysis → prune/add features             │
│  ├─ Spawn new agent variants from genetic crossover              │
│  ├─ Kill agents with 60-day Sharpe < 0                           │
│  ├─ Walk-forward validation of entire system                     │
│  ├─ Backtest evolved population on last 3 months                 │
│  └─ Promote survivors to live trading (with paper trade gate)    │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Genetic Evolution Engine

```python
class AgentGenome:
    """DNA of a trading agent — everything that can be evolved."""
    features: list[str]           # Which indicators this agent uses
    feature_weights: dict         # Importance of each feature
    entry_thresholds: dict        # When to enter (RSI < X, ADX > Y)
    exit_thresholds: dict         # When to exit (profit target, stop loss)
    regime_affinity: list[str]    # Which regimes this agent thrives in
    lookback_period: int          # How far back it looks (5-200 bars)
    timeframe: str                # 1min, 5min, 15min, 1hr, daily
    risk_tolerance: float         # How much drawdown it accepts
    model_type: str               # xgboost, lightgbm, linear, rule-based


class GeneticEvolutionEngine:
    """Darwinian evolution of trading agents."""

    population_size: int = 50     # 50 agent variants compete
    generations: int = 30         # 30 generations per evolution cycle
    mutation_rate: float = 0.15   # 15% chance of random parameter tweak
    crossover_rate: float = 0.70  # 70% of children are bred from 2 parents
    elite_keep: int = 5           # Top 5 always survive (elitism)

    def evolve_weekly(self):
        for gen in range(self.generations):
            # 1. FITNESS: Backtest each agent on last 3 months
            fitness = {}
            for agent in self.population:
                result = self.backtester.run(agent, months=3)
                fitness[agent] = self.fitness_function(result)

            # 2. SELECTION: Top 20% survive
            survivors = self.tournament_select(self.population, fitness, k=10)

            # 3. CROSSOVER: Breed winning configs
            children = []
            for _ in range(int(self.population_size * self.crossover_rate)):
                parent_a = random.choice(survivors)
                parent_b = random.choice(survivors)
                child = self.crossover(parent_a, parent_b)
                children.append(child)

            # 4. MUTATION: Random parameter tweaks
            mutants = []
            for _ in range(self.population_size - len(survivors) - len(children)):
                base = random.choice(survivors)
                mutant = self.mutate(base)
                mutants.append(mutant)

            # 5. NEW GENERATION
            self.population = survivors + children + mutants

        # 6. PROMOTE: Top agents graduate to live (with paper trade gate)
        champions = self.top_k(self.population, k=3)
        for agent in champions:
            if self.paper_trade_validation(agent, days=5):
                self.deploy_to_live(agent)

    def fitness_function(self, backtest_result) -> float:
        """Multi-objective fitness: Sharpe + Sortino - MaxDD penalty."""
        return (
            backtest_result.sharpe_ratio * 0.4
            + backtest_result.sortino_ratio * 0.3
            - backtest_result.max_drawdown * 0.2
            + backtest_result.profit_factor * 0.1
        )

    def crossover(self, parent_a: AgentGenome, parent_b: AgentGenome) -> AgentGenome:
        """Uniform crossover: each gene randomly from parent A or B."""
        child = AgentGenome()
        child.features = random.choice([parent_a.features, parent_b.features])
        child.lookback_period = random.choice([
            parent_a.lookback_period, parent_b.lookback_period
        ])
        child.entry_thresholds = {
            k: random.choice([
                parent_a.entry_thresholds.get(k, 0),
                parent_b.entry_thresholds.get(k, 0)
            ])
            for k in set(parent_a.entry_thresholds) | set(parent_b.entry_thresholds)
        }
        # ... similar for all genome fields
        return child

    def mutate(self, genome: AgentGenome) -> AgentGenome:
        """Random perturbation of one or more genes."""
        mutant = copy.deepcopy(genome)
        if random.random() < self.mutation_rate:
            mutant.lookback_period += random.randint(-20, 20)
        if random.random() < self.mutation_rate:
            # Swap one feature for a random alternative
            idx = random.randint(0, len(mutant.features) - 1)
            mutant.features[idx] = random.choice(ALL_AVAILABLE_FEATURES)
        if random.random() < self.mutation_rate:
            mutant.risk_tolerance *= random.uniform(0.8, 1.2)
        return mutant
```

---

## Part 8: Deep RL Position Sizing

### 8.1 Replace Heuristic Kelly with Learned Policy

```python
class RLPositionSizer:
    """PPO-based position sizing learned from simulation."""

    # STATE: Everything the sizer needs to know
    state_space = {
        "portfolio_value": float,          # Current total equity
        "open_positions": int,             # Number of open trades
        "unrealized_pnl_pct": float,       # Current floating P&L
        "regime": int,                     # 0=crisis, 1=bear, 2=neutral, 3=bull
        "vix": float,                      # Current VIX level
        "signal_score": float,             # Alpha swarm conviction (0-100)
        "debate_survival_rounds": int,     # How many debate rounds thesis survived
        "sector_exposure": list[float],    # Current exposure per sector
        "correlation_to_portfolio": float, # New trade correlation to existing
        "time_of_day": float,              # 0.0 (open) to 1.0 (close)
        "day_of_week": int,                # 0=Mon, 4=Fri
        "recent_win_rate": float,          # Last 20 trades win rate
        "atr_normalized": float,           # Current volatility of target
    }

    # ACTION: What the sizer decides
    action_space = {
        "position_size_pct": (0.0, 0.15),  # 0% to 15% of portfolio
        "stop_distance_atr": (0.5, 3.0),   # Stop loss in ATR multiples
        "take_profit_atr": (1.0, 5.0),     # Take profit in ATR multiples
    }

    # REWARD: Risk-adjusted, not raw return
    def compute_reward(self, trade_result):
        raw_return = trade_result.pnl_pct
        risk_penalty = max(0, trade_result.max_adverse_excursion - 0.02) * 10
        correlation_penalty = trade_result.portfolio_correlation * 0.5
        drawdown_penalty = max(0, trade_result.contribution_to_drawdown) * 20

        return raw_return - risk_penalty - correlation_penalty - drawdown_penalty
```

### 8.2 Training Pipeline

1. **Phase 1: Simulation** — Train PPO on 10 years of historical data via backtester (millions of episodes)
2. **Phase 2: Paper Trade** — Deploy with real signals but no real money for 30 days
3. **Phase 3: Shadow Mode** — Run alongside heuristic Kelly, compare results, no override
4. **Phase 4: Live** — Gradually shift allocation from Kelly to RL (25% → 50% → 100%)

---

## Part 9: Swarm Communication Protocol

### 9.1 Replace Passive Blackboard with Active Messaging

```python
class SwarmMessageBus:
    """Three communication channels for inter-agent intelligence."""

    # Channel 1: BROADCAST — alert all agents in all swarms
    async def broadcast(self, sender: str, message: SwarmMessage):
        """Critical events that all agents need to know."""
        # Example: "REGIME SHIFT: Bull → Neutral detected at 14:32"
        # Example: "CIRCUIT BREAKER: VIX > 35, all swarms defensive"
        for swarm in self.active_swarms:
            for agent in swarm.agents:
                await agent.receive_broadcast(message)

    # Channel 2: WHISPER — agent-to-agent direct messaging
    async def whisper(self, sender: str, recipient: str, message: SwarmMessage):
        """Private intel sharing between specific agents."""
        # Example: flow_reader → momentum_agent:
        #   "Unusual call buying on AAPL, 3x normal volume, Jan 150 calls"
        agent = self.find_agent(recipient)
        await agent.receive_whisper(sender, message)

    # Channel 3: CHALLENGE — request adversarial debate
    async def challenge(self, challenger: str, target: str, thesis: Thesis):
        """Force an agent to defend its thesis."""
        # Example: risk_agent → alpha_agent:
        #   "Defend your TSLA long. What happens if Nasdaq drops 3%?"
        target_agent = self.find_agent(target)
        defense = await target_agent.defend_thesis(thesis, challenger)
        return defense
```

### 9.2 Emergent Intelligence

With active messaging, agents can form **ad-hoc coalitions**:

```
Scenario: Flow agent detects unusual options activity on AAPL

1. flow_reader WHISPERS to momentum_agent:
   "Unusual call buying on AAPL — 5x average volume on $200 calls"

2. momentum_agent checks technicals, WHISPERS back:
   "Confirmed: AAPL breaking out of 20-day range with volume"

3. momentum_agent BROADCASTS to Momentum Swarm:
   "High-conviction AAPL setup — flow + technical alignment"

4. Momentum Swarm activates fast-track evaluation (skips full debate)

5. risk_agent CHALLENGES: "AAPL earnings in 3 days — vol crush risk"

6. flow_reader DEFENDS: "Call buying is POST-earnings expiry, not pre-earnings"

7. Thesis survives → routed to RL sizer

Total time: ~3 seconds (vs 10-15 seconds for full council DAG)
```

---

## Part 10: Dynamic Agent Population

### 10.1 Agent Lifecycle Management

```
┌──────────────────────────────────────────────────────────────┐
│                  AGENT LIFECYCLE                              │
│                                                               │
│  BIRTH                                                        │
│  ├─ Genetic crossover produces new agent genome               │
│  ├─ New data source comes online → specialist agent spawned   │
│  ├─ Regime change → regime-specific agents activated          │
│  └─ Manual: human designs new agent for specific edge         │
│                                                               │
│  CHILDHOOD (Paper Trade, 5-10 days)                          │
│  ├─ Agent runs in shadow mode alongside live agents           │
│  ├─ Signals recorded but not executed                         │
│  ├─ Must achieve Sharpe > 0.5 on paper to graduate            │
│  └─ Must show low correlation to existing live agents         │
│                                                               │
│  ADULTHOOD (Live Trading)                                    │
│  ├─ Full voting rights in relevant micro-swarm                │
│  ├─ Weight determined by Bayesian performance tracking         │
│  ├─ Continuous monitoring of accuracy, latency, error rate     │
│  └─ Rewarded with higher weight for consistent alpha          │
│                                                               │
│  PROBATION (30-day Sharpe < 0)                               │
│  ├─ Weight reduced to 0.25x                                   │
│  ├─ Flagged for investigation: is it the agent or the market? │
│  └─ 30 more days to recover or face termination               │
│                                                               │
│  DEATH (60-day Sharpe < 0 OR correlation > 0.9 with peer)    │
│  ├─ Removed from live swarm                                   │
│  ├─ Genome archived for future crossover potential             │
│  ├─ Post-mortem analysis: why did it fail?                    │
│  └─ Lessons fed to Critic model training data                 │
│                                                               │
│  TARGET: 8-15 live agents at any time                        │
│  The WHICH 8-15 changes weekly based on what's working        │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 Correlation-Based Merging

```python
def prune_redundant_agents(self):
    """If two agents are >0.9 correlated, merge them."""
    for agent_a, agent_b in combinations(self.live_agents, 2):
        correlation = self.compute_signal_correlation(agent_a, agent_b, days=30)
        if correlation > 0.9:
            # Keep the one with higher Sharpe
            keeper = max(agent_a, agent_b, key=lambda a: a.sharpe_30d)
            killed = min(agent_a, agent_b, key=lambda a: a.sharpe_30d)
            # Merge: keeper inherits any unique features from killed
            keeper.genome.features = list(set(
                keeper.genome.features + killed.genome.features
            ))
            self.kill_agent(killed, reason="merged_redundant")
```

---

## Part 11: Compute Architecture

### 11.1 Current vs Proposed

| Resource | Current | Proposed |
|---|---|---|
| **CPU** | Single Python asyncio process | Multi-process: orchestrator + vLLM + trainers |
| **GPU** | XGBoost training only (offline) | vLLM inference (3 models) + XGBoost + RL training |
| **Memory** | ~2GB RAM | ~8GB RAM + 24GB VRAM |
| **Parallelism** | Agent-level asyncio | Swarm-level multiprocess + intra-swarm asyncio |
| **Throughput** | ~100 evaluations/day | ~1000+ evaluations/day |
| **Batch Inference** | None (one symbol at a time) | Batch: evaluate watchlist in parallel |

### 11.2 Process Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PC1: TRADING ENGINE                                         │
│                                                              │
│  Process 1: Meta-Orchestrator (LangGraph)                   │
│  ├─ Swarm routing, debate coordination, decision pipeline    │
│  ├─ Redis pub/sub for inter-process messaging                │
│  └─ Async event loop for market data                        │
│                                                              │
│  Process 2: vLLM Inference Server (GPU)                     │
│  ├─ 3 models loaded: Judge, Critic, Alpha                   │
│  ├─ HTTP API for inference requests                         │
│  ├─ Continuous batching for throughput                       │
│  └─ Grammar-constrained decoding for structured output      │
│                                                              │
│  Process 3: Evolution & Training (GPU, off-hours)           │
│  ├─ Genetic evolution engine (weekly)                       │
│  ├─ RL policy training (nightly)                            │
│  ├─ XGBoost retraining (nightly)                            │
│  └─ LoRA fine-tuning (weekly)                               │
│                                                              │
│  Process 4: Backtester (CPU-intensive)                      │
│  ├─ Vectorized backtest engine                              │
│  ├─ Used by genetic evolution for fitness evaluation        │
│  └─ Walk-forward validation                                 │
├─────────────────────────────────────────────────────────────┤
│  PC2: BRAIN SERVICE (existing, enhanced)                     │
│  ├─ Cloud LLM fallback (Claude for deep analysis)           │
│  ├─ Overnight deep postmortem analysis                      │
│  └─ Complex scenario simulation                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 12: Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
| Task | Description | Effort |
|---|---|---|
| Working backtester | Vectorized replay engine with Sharpe/drawdown output | Large |
| Micro-swarm routing | Replace flat DAG with regime-routed swarm activation | Medium |
| Micro-swarm routing | Replace flat 32-agent DAG with regime-routed swarm activation | Medium |

### Phase 2: Intelligence (Weeks 3-4)
| Task | Description | Effort |
|---|---|---|
| Agent debate protocol | 3-round adversarial debate with timeout | Medium |
| MoE signal layer | 4 specialized experts + LLM gating router | Large |
| Connect ML to signals | XGBoost predictions become primary signal source | Medium |

### Phase 3: Local LLM Layer (Weeks 5-6)
| Task | Description | Effort |
|---|---|---|
| vLLM setup | Deploy 3 local models with grammar-constrained decoding | Medium |
| Judge model | Fine-tune Qwen for debate moderation + routing | Large |
| Critic model | Fine-tune Mistral on historical trade failures | Large |
| Alpha model | Fine-tune LLaMA on trade outcomes via LoRA | Large |

### Phase 4: Learning & Evolution (Weeks 7-8)
| Task | Description | Effort |
|---|---|---|
| Intra-day learning loop | 30-minute confidence recalibration | Medium |
| Nightly retraining | XGBoost + MoE weights + RL reward tuning | Medium |
| Genetic evolution engine | Full agent genome + crossover + mutation + selection | Large |
| Agent spawner/killer | Dynamic population with lifecycle management | Medium |

### Phase 5: RL Position Sizing (Weeks 9-10)
| Task | Description | Effort |
|---|---|---|
| RL environment | Gym-compatible trading env with realistic simulation | Large |
| PPO training | Train position sizing policy on historical data | Large |
| Shadow mode | Run RL sizer alongside Kelly, compare results | Medium |
| Gradual rollout | 25% → 50% → 100% allocation shift | Small |

### Phase 6: Swarm Communication (Weeks 11-12)
| Task | Description | Effort |
|---|---|---|
| Active message bus | Broadcast + whisper + challenge channels | Medium |
| Emergent coalition logic | Ad-hoc swarm formation from agent signals | Medium |
| Fast-track evaluation | High-conviction multi-signal bypass of full debate | Small |

---

## Part 13: Expected Impact

| Metric | Current System | After v2 | Why |
|---|---|---|---|
| **Signal-to-Noise** | Medium (32 agents, some correlated) | High (3-5 relevant experts per trade) | Micro-swarm routing |
| **Bad Trade Prevention** | Weak (one-shot vote can confirm bias) | Strong (adversarial debate kills weak theses) | Debate protocol |
| **Adaptation Speed** | Days (post-trade Bayesian update) | 30min intra-day + nightly + weekly | 3-loop learning |
| **Strategy Discovery** | Manual (human codes agents) | Automated (genetic evolution breeds strategies) | Evolution engine |
| **Position Sizing** | Heuristic (unvalidated formula) | Optimal (RL learned from millions of simulations) | PPO policy |
| **LLM Cost** | ~$50-100/day (cloud API calls) | ~$5/day (mostly local, cloud for overflow) | Local LLM layer |
| **LLM Relevance** | Generic (not trained on your data) | Specialized (fine-tuned on your trades weekly) | LoRA fine-tuning |
| **Agent Quality** | Static (bad agents persist) | Darwinian (bad agents die, good agents breed) | Spawner/killer |
| **Compute Efficiency** | Low (32 sequential agents) | High (parallel swarms + batch inference) | Multi-process architecture |

---

## Summary

### v3.5.0 Status (Implemented)

The v3.5.0 system implements a **32-agent council** with a 7-stage DAG, adversarial debate, multi-tier fast/deep evaluation, and Bayesian weight learning. The core swarm is live and operational. Five critical bugs remain (see the warning box in the Executive Summary above).

### Future Roadmap (Proposed — beyond v3.5.0)

The proposals below represent the next evolution toward a fully autonomous, self-improving system:

- **Micro-swarms** replace the flat 32-agent DAG (right experts for right market) [proposed]
- **Genetic evolution** replaces manual agent design (breeds better strategies automatically) [proposed]
- **Deep RL** replaces heuristic Kelly sizing (learns optimal sizing from data) [proposed]
- **Dynamic population** replaces fixed agents (Darwinian survival of the fittest) [proposed]

Already implemented as of v3.5.0:
- **Adversarial debate** in Stage 5.5 (bull_debater, bear_debater, red_team) [✅ done]
- **Local LLMs** via brain_service on PC2 (Ollama gRPC 50051) [✅ done]
- **Active MessageBus** replaces passive blackboard (async pub/sub, Redis-backed) [✅ done]
- **Bayesian weight learning** via weight_learner.py [✅ done]
- **Homeostasis + circuit breakers** fail-closed safety [✅ done]
