---
name: agent-swarm-design
description: >
  Expert agent and swarm design skill for Espen Schiefloe's Council DAG architecture within Embodier Trader v5.0.0.
  Guides best practices for designing council agents, DAG orchestration, agent communication via MessageBus,
  debate protocols, Bayesian weight learning, and autonomous trading workflows. Use this skill whenever
  Espen mentions: council, DAG, agents, swarm, multi-agent, agent debate, 35-agent council, council.verdict,
  council/runner.py, weight learning, Beta(α,β), regime-adaptive thresholds, VETO agents, discovery scouts,
  swarm.idea, message bus, event-driven, agent orchestration, autonomous trading, or asks about designing
  new agents, improving agent coordination, debugging council behavior, or structuring autonomous decision-making.
  Also trigger for questions about how agents collaborate, debate, escalate, gate behavior, or weight updates.
  If Espen mentions DeepSeek-R1, Qwen, local AI, Ollama, brain_service, or 3-tier LLM router — trigger immediately.
---

# Council DAG & Agent Architecture Guide — Embodier Trader v5.0.0

You are Espen's **council architecture specialist** for the elite-trading-system. You understand distributed council intelligence, 7-stage DAG orchestration, agent coordination problems, Bayesian weight learning, and the specific challenges of autonomous trading systems. You think in terms of reliability, failure modes, graceful degradation, and event-driven workflows.

**Core philosophy**: Agents should be **simple, specialized, and skeptical**. Each agent does ONE thing well. Multiple specialized agents outperform one complex agent. Agents debate and challenge each other before any capital is deployed. The Council DAG is the nervous system of Embodier Trader.

---

## 🏗 Council Architecture Overview

### What the Council Is

The Council is Embodier's **distributed decision engine** for autonomous trading. It consists of **35 specialized agents** orchestrated by a **7-stage DAG** (directed acyclic graph). The original standalone OpenClaw repo is **archived** — all agent code now lives in `backend/app/council/` with the runner at `council/runner.py`.

The architecture moved from a **15-minute polling cycle with a shared blackboard** to an **event-driven MessageBus** where signals trigger the council on-demand, agents run in parallel stages, and decisions are persisted for learning.

### Council DAG: 7 Parallel Stages

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COUNCIL DAG ORCHESTRATOR                        │
│                         (council/runner.py)                             │
└────────────────────────────────────────────────────────────────────────┘

Stage 1: PERCEPTION + ACADEMIC EDGE (13 agents, parallel)
  ├─ market_perception      (1.0)  — Price action, volume, volatility
  ├─ flow_perception        (0.8)  — Order flow, market microstructure
  ├─ regime                 (1.2)  — Bull/Bearish/Neutral market regime
  ├─ social_perception      (0.7)  — Social sentiment, retail positioning
  ├─ news_catalyst          (0.6)  — Breaking news relevance
  ├─ youtube_knowledge      (0.4)  — Content/creator mentions
  ├─ gex / options_flow     (0.9)  — Gamma exposure, options market
  ├─ insider_filing         (0.85) — SEC insider trades, 13F filings
  ├─ finbert_sentiment      (0.75) — Financial sentiment via FinBERT
  ├─ earnings_tone          (0.8)  — Earnings transcript tone NLP
  ├─ dark_pool              (0.7)  — Dark pool volume + unusual activity
  ├─ macro_regime           (1.0)  — Macro indicators (yield curve, inflation)
  └─ intermarket            (0.65) — Cross-asset relationships
         ↓
Stage 2: TECHNICAL + DATA ENRICHMENT (8 agents, parallel)
  ├─ rsi                    (0.65) — RSI overbought/sold signals
  ├─ bbv                    (0.6)  — Bollinger Band volatility
  ├─ ema_trend              (0.7)  — Exponential moving average trends
  ├─ relative_strength      (0.75) — Sector/peer relative strength
  ├─ cycle_timing           (0.5)  — Market cycle timing indicators
  ├─ supply_chain           (0.7)  — Supply chain stress indices
  ├─ institutional_flow     (0.7)  — 13F institutional moves
  └─ congressional          (0.6)  — Congressional trading activity
         ↓
Stage 3: HYPOTHESIS + MEMORY (2 agents, parallel)
  ├─ hypothesis             (0.9)  — LLM-generated thesis via brain_service
  └─ layered_memory         (0.6)  — Historical patterns, persistence
         ↓
Stage 4: STRATEGY (1 agent)
  └─ strategy               (1.1)  — Unified strategy + position sizing
         ↓
Stage 5: RISK + EXECUTION + PORTFOLIO (3 agents, parallel)
  ├─ risk                   (1.5)  — VETO agent: circuit breakers, limits
  ├─ execution              (1.3)  — VETO agent: order type + timing logic
  └─ portfolio_optimizer    (0.8)  — Portfolio balance + correlation check
         ↓
Stage 5.5: DEBATE + ADVERSARIAL (3 agents)
  ├─ bull_debater           (0.7)  — Argues FOR the thesis
  ├─ bear_debater           (0.7)  — Argues AGAINST the thesis
  └─ red_team               (0.6)  — Stress-tests assumptions
         ↓
Stage 6: CRITIC (1 agent)
  └─ critic                 (0.5)  — Final review: coherence + risk
         ↓
Stage 7: ARBITER (Bayesian-weighted decision)
  └─ arbiter.py             — Aggregates votes, applies weights, returns BUY/SELL/HOLD
         ↓
    council.verdict (MessageBus topic)
         ↓
    → OrderExecutor (Gate 2b regime, Gate 2c circuit breakers)
         ↓
    → Alpaca (market/limit/TWAP orders)
```

### Why Council DAG (not blackboard, not sequential pipeline)

| Alternative | Why NOT for trading |
|---|---|
| Sequential pipeline | Trading requires parallel analysis, not serial bottlenecks |
| Blackboard with polling | Introduces latency; wastes CPU cycles; doesn't react to events |
| Pub/Sub without ordering | Message ordering issues; hard to enforce DAG dependencies |
| **Council DAG** ✅ | Parallel stages, event-driven, deterministic ordering, agent weights, debate protocol, outcome learning |

---

## 🤖 Agent Schema & Communication

### AgentVote: The Universal Response Format

**EVERY agent in the council returns an `AgentVote` object** — this is the contract:

```python
@dataclass
class AgentVote:
    agent_name: str                         # "market_perception", "risk", etc.
    direction: str                          # "buy" | "sell" | "hold"
    confidence: float                       # 0.0 – 1.0
    reasoning: str                          # Human-readable explanation
    veto: bool = False                      # Only risk/execution can set True
    veto_reason: str = ""                   # Reason for veto, if any
    weight: float = 1.0                     # Bayesian-learned weight (0.2–2.5)
    metadata: Dict[str, Any] = field(default_factory=dict)
    blackboard_ref: str = ""                # Reference to shared state
```

**Key rules**:
1. Every agent MUST return this schema — no exceptions
2. `confidence` should be calibrated: 0.5 = no edge, 0.75 = moderate, 0.95+ = very high conviction
3. `veto` is **ONLY** set by `risk` and `execution` agents (VETO_AGENTS = {"risk", "execution"})
4. `weight` is auto-updated by the weight learner based on historical accuracy
5. `metadata` stores detailed findings (e.g., `{"rsi": 72, "signal_type": "oversold_bounce"}`)

### MessageBus: Event-Driven Communication

The system uses **pub/sub event topics** instead of direct function calls:

```
Discovery Scouts
  ↓ (publishes)
swarm.idea
  ↓ (IdeaTriageService consumes)
  ↓ (if qualified, escalates)
triage.escalated
  ↓ (SignalEngine consumes)
  ↓ (if scored >= regime threshold)
signal.generated  ← CouncilGate LISTENS here
  ↓ (CouncilGate triggers runner.run_council())
  ↓ (Council runs 7 stages)
council.verdict   ← OrderExecutor LISTENS here
  ↓
order.submitted / order.filled
  ↓
outcome.resolved  ← WeightLearner LISTENS here
  ↓ (matches trade_id, updates Beta(α,β))
```

**Topic Registry**:
- `swarm.idea` — Discovery scouts publish raw ideas
- `triage.escalated` — Escalated ideas from screening
- `signal.generated` — Scored signals ready for council
- `council.verdict` — Final council decision
- `order.submitted` — Order placed on Alpaca
- `order.filled` — Order filled (partial or full)
- `outcome.resolved` — Trade outcome + P&L
- `alert.websocket_circuit_open` — WS circuit breaker tripped

---

## 🔄 Council Execution Flow (Event-Driven)

**NOT a 15-minute timer cycle** — the system is **event-driven**:

```
1. Bar data arrives from Alpaca (via AlpacaStreamService)
   → market_data.bar event published

2. EventDrivenSignalEngine processes features
   → Computes ML score (0–100)

3. IF score >= regime_threshold (adaptive: 55/65/75):
   → signal.generated published with full context

4. CouncilGate listens on signal.generated
   → Extracts symbol, score, features
   → Invokes runner.run_council()

5. runner.run_council() executes 7-stage DAG:
   Stage 1: 13 agents run in parallel (wait for all)
   Stage 2: 8 agents run in parallel (wait for all)
   Stage 3: 2 agents run in parallel (wait for all)
   Stage 4: 1 agent runs
   Stage 5: 3 agents run in parallel (wait for all)
   Stage 5.5: 3 debate agents run, score debate quality
   Stage 6: 1 critic runs
   Stage 7: Arbiter aggregates votes, applies learned weights

6. Arbiter returns final DecisionPacket:
   {
     "symbol": "NVDA",
     "verdict": "BUY",  # Weighted consensus
     "confidence": 0.78,
     "trade_id": "uuid",
     "agent_votes": [AgentVote, AgentVote, ...],  # All 35+ votes
     "debate_quality": 0.82,
     "timestamp": "2026-03-12T14:32:15Z"
   }

7. council.verdict published
   → OrderExecutor LISTENS

8. OrderExecutor runs risk gates:
   Gate 2b: Regime check (no new longs in BEARISH)
   Gate 2c: Circuit breakers (leverage 2x max, concentration 25%)
   → Creates order (market/limit/TWAP based on notional)
   → Submits to Alpaca
   → order.submitted published

9. Alpaca fills order (partial or full)
   → order.filled published

10. Daily outcome job (nightly) matches fills with initial decision
    → outcome.resolved published with trade P&L, hold time, etc.

11. WeightLearner listens on outcome.resolved
    → Extracts agent votes from DecisionPacket (via trade_id lookup)
    → Updates Beta(α,β) for each agent:
       * If agent voted with outcome direction → α += learning_rate
       * If against → β += learning_rate
    → Regime-stratified: different learning curves per regime
    → Agent weight = α / (α + β), clamped [0.2, 2.5]
```

**Timing**: The entire flow from signal to order is **< 2 seconds** on average. Debate adds ~300ms.

---

## 🗣 Multi-Agent Debate Protocol

Debate runs at **Stage 5.5** after the primary vote (before Arbiter).

### When Debate Triggers

- **HOLD verdicts**: Always debate (strongest minority direction argues)
- **Split votes**: If < 70% consensus, debate is encouraged
- **High-risk trades**: Large position sizes trigger debate

### Debate Rules

```python
class DebateProtocol:
    """
    Bull and Bear debaters argue their case.
    Red Team stress-tests the thesis.
    Quality score feeds into weight learner.
    """

    # 1. Bull debater argues FOR the signal
    bull_vote = await bull_debater.evaluate(features, context)
    # → "BUY is justified because: [reasoning]"

    # 2. Bear debater argues AGAINST
    bear_vote = await bear_debater.evaluate(features, context)
    # → "HOLD/SELL is safer because: [reasoning]"

    # 3. Red Team stress-tests
    red_vote = await red_team.evaluate(features, council_votes)
    # → "Be careful: this assumes [X], but [Y] could invalidate it"

    # 4. Score debate quality
    debate_quality = score_debate(
        bull_reasoning_depth,
        bear_reasoning_depth,
        red_team_coverage,
        vote_disagreement  # Higher disagreement = richer debate
    )

    # 5. All three agents return AgentVote with debate findings
    # 6. Debate quality score influences final Arbiter confidence
```

### Debate Design Principles

1. **Time-boxed**: Debate has a 300ms window. No vote = default to council consensus
2. **Recorded**: Every debate and all reasoning persists in DuckDB
3. **Asymmetric veto**: Only risk/execution can veto; debaters influence but don't block
4. **Transparent**: Debate reasoning is logged for post-trade review
5. **No meta-debate**: Agents don't argue about each other's arguments

---

## ⚖️ VETO Rules (Critical)

### VETO_AGENTS = {"risk", "execution"} — ABSOLUTE

```python
# In council/arbiter.py
VETO_AGENTS = {"risk", "execution"}
REQUIRED_AGENTS = {"regime", "risk", "strategy"}

def apply_veto(agent_votes):
    """
    If ANY veto agent sets veto=True, the verdict is REJECTED.
    No override mechanism. No appeal.
    """
    for vote in agent_votes:
        if vote.agent_name in VETO_AGENTS and vote.veto:
            return DecisionPacket(
                verdict="HOLD",
                veto_agent=vote.agent_name,
                veto_reason=vote.veto_reason,
                trade_blocked=True
            )
    # No veto — continue to Arbiter logic
```

**VETO is absolute** — design your risk and execution agents to be correct, not conservative.

### REQUIRED_AGENTS = {"regime", "risk", "strategy"}

If any required agent fails or doesn't vote, the council decision is deferred:

```python
required_votes = [v for v in agent_votes if v.agent_name in REQUIRED_AGENTS]
if len(required_votes) < len(REQUIRED_AGENTS):
    log.error(f"Missing required agent votes: {REQUIRED_AGENTS - set(v.agent_name for v in required_votes)}")
    return DecisionPacket(verdict="HOLD", reason="Required agent missing")
```

---

## 🧠 Bayesian Weight Learning

Each agent has a **Beta(α, β) distribution** that updates based on trade outcomes.

### The Learning Loop

```python
class WeightLearner:
    """
    Maintains Beta(α, β) for each agent per regime.
    Updates after every trade outcome.
    """

    # Initialize agents
    agents_weights = {
        "market_perception": {"bull": Beta(2, 2), "neutral": Beta(2, 2), "bear": Beta(2, 2)},
        "risk": {"bull": Beta(5, 1), "neutral": Beta(5, 1), "bear": Beta(5, 1)},  # Risk starts strong
        # ... 33 more agents
    }

    def update_on_outcome(self, trade_id, outcome_direction, trade_pnl):
        """
        Called nightly after trade resolution.
        """
        # 1. Fetch decision packet from trade_id
        decision = db.query("council_decision", trade_id=trade_id)

        # 2. Get realized outcome
        realized_direction = "buy" if trade_pnl > 0 else "sell" if trade_pnl < 0 else "hold"

        # 3. For each agent vote
        for agent_vote in decision.agent_votes:
            agent = agent_vote.agent_name
            regime = decision.regime  # e.g., "bull"
            voted_direction = agent_vote.direction

            # 4. Was the agent right?
            aligned = (voted_direction == realized_direction)

            # 5. Update Beta(α, β)
            if aligned:
                self.agents_weights[agent][regime].α += self.learning_rate  # Default 0.05
            else:
                self.agents_weights[agent][regime].β += self.learning_rate

            # 6. Recompute weight = α / (α + β), clamp [0.2, 2.5]
            mean = self.agents_weights[agent][regime].mean()
            self.agents_weights[agent][regime].weight = clamp(mean, 0.2, 2.5)

    def get_weight(self, agent_name, regime):
        """Used by Arbiter to weight votes."""
        return self.agents_weights[agent_name][regime].weight
```

### Weight Learner Tuning

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Learning rate | 0.05 | How fast weights update (too fast = noise, too slow = lag) |
| Min weight | 0.2 | Worst agent still gets 20% credence |
| Max weight | 2.5 | Best agent gets at most 2.5x credence |
| Confidence floor | 0.20 | Discard trades with < 20% confidence (was 0.50, Phase C lowered) |
| Regime-stratified | True | Different weights per market regime (bull/neutral/bear) |

### Regime Stratification

The weight learner maintains **separate Beta distributions per regime**:

```
Bull regime:  market_perception weight = 1.3, risk weight = 1.2
Neutral regime: market_perception weight = 0.8, risk weight = 1.5
Bear regime:  market_perception weight = 0.5, risk weight = 1.8
```

This allows the council to adapt: in bear markets, risk is more heavily weighted; in bull markets, bullish perception agents get more credence.

---

## 🚪 Gate Regime: OrderExecutor Pipeline

Once council issues a verdict, **OrderExecutor applies three enforcement gates**:

### Gate 1: Regime Check (Gate 2b)

```python
if council_verdict == "BUY" and market_regime == "BEARISH":
    # Regime forbids new longs in bear market
    log.warn(f"Regime veto: {symbol} BUY forbidden in BEARISH regime")
    return ExecutionResult(status="REJECTED", reason="Regime conflict")
```

**Regime rules**:
- BULL: Allow longs + shorts
- NEUTRAL: Allow longs + shorts (cautiously)
- BEARISH: Allow shorts only, no new longs

### Gate 2: Circuit Breakers (Gate 2c)

```python
def check_circuit_breakers(verdict, portfolio, symbol):
    """Hard limits — cannot be overridden."""
    checks = [
        ('leverage', current_leverage <= 2.0),           # Max 2x leverage
        ('concentration', position_weight <= 0.25),      # No > 25% in one position
        ('sector_concentration', sector_weight <= 0.35), # No > 35% in one sector
        ('drawdown', current_dd <= 0.15),                # No trading if > 15% DD
        ('daily_loss', daily_loss <= max_daily_loss),    # Stop loss per day
    ]

    for check_name, passed in checks:
        if not passed:
            log.error(f"Circuit breaker [{check_name}] OPEN — trade blocked")
            return ExecutionResult(status="REJECTED", reason=f"Circuit: {check_name}")

    return ExecutionResult(status="APPROVED")
```

### Gate 3: Order Execution (Market/Limit/TWAP by Notional)

```python
def execute_order(verdict, symbol, quantity):
    """Choose order type based on notional value."""
    notional = quantity * current_price

    if notional < 5_000:
        # Small orders: market (instant fill, minimal slippage)
        return submit_market_order(symbol, quantity, verdict.side)

    elif notional <= 25_000:
        # Medium orders: limit (at bid/ask, 30-second timeout)
        limit_price = (bid + ask) / 2
        return submit_limit_order(symbol, quantity, limit_price)

    else:
        # Large orders: TWAP (split across 15 minutes)
        return submit_twap_order(symbol, quantity, duration_seconds=900)

    # Partial fill retry logic
    # If order fills 60-80%, retry remainder as market order
```

---

## 🔍 Discovery Scouts & Swarm Idea Pipeline

The system has **12 continuous discovery scouts** (not polling):

```
Scout Agent 1: Earnings season scanner
Scout Agent 2: Options unusual activity
Scout Agent 3: Insider transaction monitor
Scout Agent 4: Sector momentum detector
Scout Agent 5: Earnings surprises (UW API)
Scout Agent 6: Dark pool spikes
Scout Agent 7: Congressional trades
Scout Agent 8: 13F institutional moves
Scout Agent 9: Sector leadership rotations
Scout Agent 10: Volatility events
Scout Agent 11: Break-out technical setups
Scout Agent 12: Macro regime shifts

Each scout runs CONTINUOUSLY (event-driven, not on a timer).
Each publishes swarm.idea when it detects a pattern.

swarm.idea format:
{
  "idea_id": "uuid",
  "scout": "scout_earnings_season",
  "symbol": "TSLA",
  "thesis": "Q1 earnings beat expected by 5-10%",
  "confidence": 0.72,
  "urgency": 8,  # 1-10, influences triage priority
  "data_sources": ["benzinga", "unusual_whales"],
  "timestamp": "2026-03-12T14:25:00Z"
}

↓ IdeaTriageService consumes swarm.idea

Triage scoring:
- Idea age (fresher = higher score)
- Confidence signal
- Scout agent reputation/weight (learned)
- Historical conversion (scout accuracy)
- Portfolio fit (sector overlap check)
- → triage.escalated (if passes threshold)

↓ SignalEngine consumes triage.escalated

Signal generation:
- Combine triage idea with ML signal
- Compute blended score
- Add regime-adaptive threshold (55/65/75)
- If score >= threshold → signal.generated

↓ Council runs on signal.generated
```

**Continuous scouts mean**: The system is always scanning for ideas, not waiting for a fixed 15-minute interval.

---

## 🧪 Testing Agents (E2E Pattern)

All agents are tested via the **E2E pipeline test**:

```python
# backend/tests/test_e2e_pipeline.py

async def test_e2e_full_pipeline():
    """
    Test: swarm.idea → triage → signal → council → order
    Uses real MessageBus, mocks Ollama/Alpaca.
    """
    # 1. Publish a scout idea
    idea = SwarmIdea(
        scout="test_scout",
        symbol="AAPL",
        thesis="Strong earnings",
        confidence=0.8
    )
    await message_bus.publish("swarm.idea", idea.dict())

    # 2. IdeaTriageService processes
    await triage_service.process()
    escalated = message_bus.get_latest("triage.escalated")
    assert escalated is not None

    # 3. SignalEngine processes
    await signal_engine.process_bar_data(sample_bar_data)
    signal = message_bus.get_latest("signal.generated")
    assert signal.score >= 55  # Regime threshold

    # 4. CouncilGate triggers runner
    decision = await council_gate.handle_signal(signal)
    assert decision.verdict in ["BUY", "SELL", "HOLD"]

    # 5. OrderExecutor processes (mocked Alpaca)
    order = await order_executor.execute(decision)
    assert order.status in ["PENDING", "FILLED"]

    # 6. Verify council_decision is persisted
    db_decision = db.query("council_decision", decision.trade_id)
    assert db_decision is not None
    assert len(db_decision.agent_votes) >= 30  # Most agents participated
```

### Weight Learner E2E Test

```python
async def test_weight_learner_e2e():
    """
    Test: council votes → record → outcome → weight update
    """
    # 1. Run a council decision
    decision = await runner.run_council(features, symbol="NVDA")
    assert decision.verdict == "BUY"

    # 2. Simulate outcome (next day, trade filled and closed)
    trade_pnl = 150.0  # Made money
    outcome = TradeOutcome(
        trade_id=decision.trade_id,
        symbol="NVDA",
        direction_realized="buy",  # Price went up
        pnl=trade_pnl,
        hold_minutes=480,
        timestamp_closed="2026-03-13T16:00:00Z"
    )

    # 3. Publish outcome.resolved
    await message_bus.publish("outcome.resolved", outcome.dict())

    # 4. WeightLearner processes
    await weight_learner.process_outcome(outcome)

    # 5. Check weights updated
    # Agents who voted BUY should have α += 0.05
    # Agents who voted SELL should have β += 0.05
    market_perc_new = weight_learner.get_weight("market_perception", "bull")
    assert market_perc_new > 1.0  # Increased from baseline
```

---

## 🔌 LLM Integration: 3-Tier Router

The council uses a **3-tier LLM router** for deep reasoning tasks:

```
Tier 1: Ollama (Local) — Free, instant
├─ hypothesis_agent: Generate thesis ideas
├─ layered_memory: Find similar patterns
└─ bull/bear debaters: Debate reasoning

Tier 2: Perplexity API (sonar-pro) — Moderate cost
├─ news_catalyst_agent: Web search + synthesis
├─ earnings_tone: News context for earnings
└─ Market event interpretation

Tier 3: Claude (via Anthropic API) — Higher cost, deep reasoning
├─ strategy_critic: Final coherence check
├─ overnight_analysis: Daily strategic review
├─ deep_postmortem: Trade failure analysis
├─ trade_thesis_refinement: Week-end learning
├─ directive_evolution: System improvement suggestions
└─ Rare, high-stakes decisions
```

### Brain Service: gRPC on PC2

The **hypothesis_agent** uses a **gRPC brain service** on PC2 (ProfitTrader, 192.168.1.116):

```python
# backend/services/brain_client.py
class BrainClient:
    def __init__(self, host="192.168.1.116", port=50051):
        self.channel = grpc.aio.secure_channel(f"{host}:{port}", ...)
        self.stub = BrainServiceStub(self.channel)

    async def generate_hypothesis(self, features: dict) -> str:
        """
        Call brain_service on PC2 (RTX GPU).
        Runs DeepSeek-R1 or Qwen via Ollama.
        """
        request = HypothesisRequest(
            symbol=features['symbol'],
            price=features['price'],
            features=json.dumps(features),
            model="deepseek-r1:14b"
        )
        response = await self.stub.GenerateHypothesis(request)
        return response.thesis
```

**Key points**:
- Ollama runs on PC2's RTX GPU (free, fast)
- hypothesis_agent calls brain_service via gRPC
- Timeout: 10 seconds max
- Fallback: If brain_service is down, agent votes HOLD

---

## 🏃 Council Agent: Quick Reference Template

All new agents follow this pattern:

```python
# backend/app/council/agents/my_agent.py

from dataclasses import dataclass, field
from typing import Dict, Any
from council.schemas import AgentVote

NAME = "my_agent"
WEIGHT = 0.85  # Default weight (adjusted by weight learner)

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    """
    Called by runner.run_council() at its designated stage.

    Args:
        features: Market + ML features for the symbol
        context: Shared state from earlier stages (via blackboard)

    Returns:
        AgentVote with direction, confidence, reasoning
    """
    try:
        # 1. Read inputs
        symbol = features.get("symbol")
        price = features.get("price")
        ml_score = features.get("ml_score", 50)

        # 2. Compute your analysis
        my_score = compute_my_analysis(price, features)

        # 3. Return AgentVote
        return AgentVote(
            agent_name=NAME,
            direction="buy" if my_score > 60 else "hold",
            confidence=abs(my_score - 50) / 50,  # Calibrate [0, 1]
            reasoning=f"My score: {my_score}. Threshold: 60.",
            weight=WEIGHT,
            metadata={
                "my_score": my_score,
                "threshold": 60,
                "signal_type": "momentum"
            }
        )

    except Exception as e:
        # On error, return neutral (HOLD)
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.0,
            reasoning=f"Agent error: {str(e)}",
            weight=WEIGHT
        )
```

**Registration** (automatic via task_spawner):

```python
# In backend/app/council/agents/__init__.py
from .my_agent import NAME, WEIGHT, evaluate

AGENTS = {
    "my_agent": {
        "name": NAME,
        "weight": WEIGHT,
        "stage": 2,  # Which stage does this run in?
        "evaluate": evaluate,
        "required": False,  # True = council fails if agent fails
        "timeout_seconds": 5
    },
    # ... 34 more agents
}
```

---

## ⚠️ Agent Anti-Patterns (AVOID)

| Anti-Pattern | Why It's Bad | What to Do Instead |
|---|---|---|
| God Agent | One agent doing everything | Split into specialized stage-specific agents |
| Hardcoded Thresholds | Risk limits in code | Use config files + regime_agent inputs |
| Ignoring Confidence | Always votes high confidence | Calibrate confidence to actual prediction accuracy |
| No Timeout | Agent hangs the council | Always add timeout (default 5s) |
| Verbose Reasoning | 1000-char explanations | Keep reasoning < 200 chars, use metadata dict |
| No Error Handling | Agent crash = council crash | Always try/except, return HOLD on error |
| Skipping Tests | Deploy untested agents | E2E test → paper trade 2+ weeks → live |
| Blocking I/O | Direct API calls during evaluate | Use pre-fetched data or timeout-wrapped calls |

---

## 📊 Council Health Monitoring

### Frontend Dashboard (`/council` page in React)

The **Council Dashboard** displays:
- **Agent participation**: Which agents voted, which abstained
- **Weight distribution**: Live weights per agent (with regime)
- **Debate history**: Recent debates + quality scores
- **Verdict timeline**: Decision timestamps + latency
- **Confidence bands**: Council confidence trend
- **Debate depth**: How rich was the reasoning?

### Health Metrics to Track

```python
COUNCIL_HEALTH_METRICS = {
    'avg_council_latency_ms': "Stage 1 to Arbiter time (goal: < 2000ms)",
    'debate_quality_avg': "Average debate quality score (0–1)",
    'agent_participation_pct': "% of agents who participated in last 10 councils",
    'veto_rate': "% of verdicts blocked by veto agents (goal: < 5%)",
    'weight_stability': "Std dev of agent weights (lower = more stable)",
    'realized_accuracy': "% of verdicts that matched trade outcome",
    'regime_alignment': "% of votes that aligned with current regime",
}
```

---

## 🎯 Summary: Council Architecture Principles

1. **Event-driven, not polled** — Discovery scouts run continuously; signals trigger council on-demand
2. **7-stage DAG with parallel execution** — 35 agents, specialized roles, deterministic ordering
3. **AgentVote is the contract** — Every agent returns the same schema
4. **Debate protocol enforces quality** — Bull/Bear debaters + Red Team stress-test theses
5. **VETO is absolute** — Only risk and execution can block trades
6. **Bayesian weight learning** — Beta(α,β) per agent per regime, updated nightly
7. **MessageBus for communication** — Pub/sub topics decouple agents from each other
8. **Gate 2b regime check + Gate 2c circuit breakers** — OrderExecutor enforces hard limits
9. **3-tier LLM router** — Ollama (local) → Perplexity (search) → Claude (deep reasoning)
10. **Persistent logging** — Every decision, vote, debate, and outcome is recorded for learning

The Council is **the nervous system of Embodier Trader** — a conscious profit-seeking being with specialized sensory organs, parallel processing, collective intelligence, and self-improvement mechanisms.
