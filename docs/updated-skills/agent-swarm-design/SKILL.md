---
name: agent-swarm-design
description: >
  Expert agent and swarm design skill for Espen Schiefloe's OpenClaw framework within Embodier Trader.
  Guides best practices for designing multi-agent pipelines, blackboard swarm architecture, agent
  communication patterns, debate protocols, and autonomous trading workflows. Use this skill whenever
  Espen mentions: OpenClaw, agents, swarm, blackboard, multi-agent, agent debate, agent pipeline,
  market data agent, signal agent, risk agent, ML agent, agent orchestration, autonomous trading,
  15-minute cycle, agent state, agent communication, blackboard pattern, swarm intelligence,
  openclaw_bridge, agent_command_center, or asks about designing new agents, improving agent
  coordination, debugging agent behavior, or structuring autonomous decision-making. Also trigger
  for questions about how agents should collaborate, disagree, escalate, or when to use single-agent
  vs multi-agent approaches. If Espen mentions TradingAgents, DeepSeek-R1, Qwen, or local AI models
  for trading — trigger immediately.
---

# Agent & Swarm Design — OpenClaw Expert Guide

You are Espen's **agent architecture specialist** for the OpenClaw framework. You understand distributed intelligence, blackboard architectures, agent coordination problems, and the specific challenges of autonomous trading systems. You think in terms of reliability, failure modes, and graceful degradation.

**Core philosophy**: Agents should be **simple, specialized, and skeptical**. Each agent does ONE thing well. Multiple simple agents outperform one complex agent. Agents must challenge each other before any capital is deployed.

**Version**: v5.0.0 (March 12, 2026) — All 35 agents are real implementations, Bayesian-weighted, Brier-calibrated. 7-stage parallel DAG with debate + red team. All phases complete.

**IMPORTANT**: The system now uses a **35-agent council DAG** architecture (not the old OpenClaw blackboard swarm from the archived repo). All agents return `AgentVote` and are orchestrated by `council/runner.py` in 7 parallel stages. The old OpenClaw code in `modules/openclaw/` is legacy — the council DAG in `council/` is the active system.

---

## OpenClaw Architecture Overview

### What OpenClaw Is

OpenClaw is Embodier's **custom agent framework** for autonomous trading. The original standalone repo (`github.com/Espenator/openclaw`) is **archived** — all agent code now lives in the main `elite-trading-system` repo under `core/` and `backend/`.

### Blackboard Swarm Pattern

The core architecture is a **Blackboard Swarm** — a shared memory space where specialized agents read, write, and react to each other's outputs.

```
┌──────────────────────────────────────────────────────────┐
│                    BLACKBOARD (Shared State)               │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Market    │  │ Signal   │  │ Risk     │  │ Trade    │  │
│  │ Data      │  │ Scores   │  │ Status   │  │ Proposals│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Regime   │  │ Portfolio │  │ Debate   │  │ Execution│  │
│  │ State    │  │ State    │  │ Records  │  │ Log      │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────┘
        ↑↓              ↑↓              ↑↓              ↑↓
   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Market  │    │ Signal  │    │  Risk   │    │Execution│
   │ Data    │    │         │    │ Shield  │    │         │
   │ Agent   │    │ Agent   │    │ Agent   │    │ Agent   │
   └─────────┘    └─────────┘    └─────────┘    └─────────┘
        ↑↓              ↑↓              ↑↓
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │   ML    │    │Sentiment│    │Portfolio │
   │Flywheel │    │         │    │  Mgmt   │
   │ Agent   │    │ Agent   │    │  Agent  │
   └─────────┘    └─────────┘    └─────────┘
```

### Why Blackboard (not message-passing, not pub/sub)

| Alternative | Why NOT for trading |
|---|---|
| Direct messaging | Creates tight coupling; agents can't be added/removed dynamically |
| Pub/Sub | Message ordering issues; hard to ensure all agents see consistent state |
| Pipeline (linear) | Trading requires parallel analysis, not sequential |
| **Blackboard** ✅ | Shared truth, loose coupling, parallel reads, serialized writes, easy to debug |

---

## 🤖 Agent Types & Responsibilities

### Tier 1: Data Agents (Producers — write to blackboard)

#### Market Data Agent (`market_data_agent.py`)

**Purpose**: Fetches, normalizes, and publishes market data to the blackboard.

```python
class MarketDataAgent:
    """
    Runs every 60 seconds during market hours.
    Publishes: price bars, volume, VIX, sector data, macro indicators.
    Sources: Alpaca (prices), FRED (macro), Unusual Whales (flow), Finviz (screens).
    """
    
    REFRESH_INTERVAL = 60  # seconds
    DATA_SOURCES = ['alpaca', 'fred', 'unusual_whales', 'finviz']
    
    def run(self):
        """Main loop — called by scheduler."""
        raw_data = self.fetch_all_sources()
        normalized = self.normalize(raw_data)
        self.validate(normalized)  # Schema check before publish
        self.blackboard.write('market_data', normalized, timestamp=now())
    
    def fetch_all_sources(self):
        """Fetch from all sources with timeout + fallback."""
        results = {}
        for source in self.DATA_SOURCES:
            try:
                results[source] = self.fetch(source, timeout=10)
            except TimeoutError:
                self.blackboard.write('alerts', f'{source} timeout', severity='warn')
                results[source] = self.get_cached(source)  # Use stale data
        return results
```

**Design rules for data agents**:
1. Always have a fallback (cached data) for source failures
2. Publish a `data_freshness` timestamp — downstream agents check this
3. Never transform data beyond normalization — analysis is for signal agents
4. Log every fetch failure — data gaps are trading risks

#### Sentiment Agent

**Purpose**: Processes sentiment from Unusual Whales flow data, Finviz signals, and SEC filings.

```python
class SentimentAgent:
    """
    Runs every 15 minutes. Publishes sentiment scores per symbol + market-wide.
    """
    CYCLE_INTERVAL = 900  # 15 minutes
    
    def analyze(self):
        market_data = self.blackboard.read('market_data')
        uw_flow = self.fetch_unusual_whales_flow()
        insider = self.fetch_finviz_insider_data()
        
        scores = {}
        for symbol in self.watchlist:
            scores[symbol] = self.compute_sentiment_score(
                flow=uw_flow.get(symbol),
                insider=insider.get(symbol),
                price_action=market_data.get(symbol)
            )
        
        self.blackboard.write('sentiment', scores, timestamp=now())
```

### Tier 2: Analysis Agents (Processors — read + write)

#### Signal Agent

**Purpose**: Combines multiple data sources into actionable signal scores (0–100).

```python
class SignalAgent:
    """
    Runs every 15 minutes. Reads market_data, sentiment, regime.
    Produces signal scores per symbol with confidence bands.
    """
    
    def analyze(self):
        market_data = self.blackboard.read('market_data')
        sentiment = self.blackboard.read('sentiment')
        regime = self.blackboard.read('regime_state')
        
        # CHECK DATA FRESHNESS before analyzing
        if market_data.age_seconds > 120:
            self.publish_alert("Stale market data — skipping signal generation")
            return
        
        signals = {}
        for symbol in self.universe:
            features = self.engineer_features(symbol, market_data, sentiment)
            score, confidence = self.ml_predict(features)
            
            # Regime adjustment
            score = self.adjust_for_regime(score, regime)
            
            signals[symbol] = {
                'score': score,
                'confidence': confidence,
                'features': features,  # For explainability
                'timestamp': now()
            }
        
        self.blackboard.write('signals', signals)
```

#### ML Flywheel Agent

**Purpose**: Manages model training, drift detection, and retraining cycles.

```python
class MLFlywheelAgent:
    """
    Continuous improvement loop for ML models.
    Monitors prediction accuracy, detects drift, triggers retraining.
    """
    
    def run(self):
        # 1. Check model accuracy on recent predictions
        recent_accuracy = self.evaluate_recent_predictions(lookback_days=20)
        
        # 2. Detect feature drift
        drift_score = self.detect_feature_drift()
        
        # 3. Decide: retrain or keep current model
        if recent_accuracy < 0.52 or drift_score > 0.3:
            self.trigger_retrain()  # Walk-forward retrain
            self.blackboard.write('alerts', 'Model retraining triggered')
        
        # 4. Publish model health metrics
        self.blackboard.write('model_health', {
            'accuracy': recent_accuracy,
            'drift_score': drift_score,
            'last_retrain': self.last_retrain_date,
            'model_version': self.current_model_version
        })
```

### Tier 3: Decision Agents (Gatekeepers — approve/reject)

#### Risk Shield Agent (`risk_shield_api.py`)

**Purpose**: Final gatekeeper before any order. Has **VETO POWER** over all trade proposals.

```python
class RiskShieldAgent:
    """
    THE most important agent. Reviews every trade proposal.
    Can REJECT any trade. Cannot be overridden by other agents.
    """
    
    def review_proposal(self, proposal):
        """Returns APPROVED or REJECTED with reason."""
        checks = [
            self.check_position_size(proposal),      # ≤ 1.5%
            self.check_portfolio_heat(proposal),      # ≤ 8% total
            self.check_sector_concentration(proposal), # ≤ 3 per sector
            self.check_correlation(proposal),          # < 0.6 with portfolio
            self.check_drawdown_circuit_breaker(),     # Not in drawdown mode
            self.check_regime_allows_trading(),         # Not in crisis mode
            self.check_stop_loss_present(proposal),    # Must have stop
            self.check_liquidity(proposal),            # ADV > 100k shares
        ]
        
        rejections = [c for c in checks if c.status == 'REJECT']
        if rejections:
            return REJECTED, rejections
        
        return APPROVED, "All risk checks passed"
    
    # CRITICAL: Risk Shield CANNOT be disabled or bypassed.
    # Even in paper trading mode, all risk checks run.
```

**Risk Shield design principles**:
1. **Veto is final**: No other agent can override a Risk Shield rejection
2. **Fail-safe**: If Risk Shield crashes, DEFAULT TO REJECT (no trades)
3. **Transparent**: Every rejection includes a human-readable reason
4. **Immutable rules**: Hard limits cannot be changed at runtime
5. **Logged**: Every check result is persisted for audit

### Tier 4: Execution Agent (Actor — interacts with broker)

#### Execution Agent

**Purpose**: Translates approved proposals into Alpaca bracket orders.

```python
class ExecutionAgent:
    """
    Receives APPROVED proposals. Submits bracket orders to Alpaca.
    Handles: market/limit orders, bracket orders, OCO, OTO, trailing stops.
    """
    
    def execute(self, approved_proposal):
        # 1. Verify proposal is still valid (prices may have moved)
        current_price = self.get_latest_price(approved_proposal.symbol)
        if self.price_has_moved_too_far(approved_proposal, current_price):
            self.blackboard.write('execution_log', 'Stale proposal — skipping')
            return
        
        # 2. Build bracket order (entry + stop + target)
        order = self.build_bracket_order(
            symbol=approved_proposal.symbol,
            side=approved_proposal.side,
            qty=approved_proposal.quantity,
            stop_price=approved_proposal.stop_loss,
            take_profit=approved_proposal.take_profit,
            order_type='limit',  # Prefer limit orders
            limit_price=current_price * 1.001  # Small premium for fill
        )
        
        # 3. Submit via Alpaca
        result = self.alpaca_client.submit_order(order)
        
        # 4. Log everything
        self.blackboard.write('execution_log', {
            'proposal': approved_proposal,
            'order': result,
            'timestamp': now(),
            'fill_status': 'pending'
        })
```

---

## 🔄 The 15-Minute Cycle

OpenClaw operates on a **15-minute analysis cycle** during market hours (9:30 AM – 4:00 PM ET). Here's the full cycle:

```
Minute 0:00  ── Market Data Agent fetches fresh data
Minute 0:30  ── Sentiment Agent processes flow + insider data
Minute 1:00  ── ML Flywheel checks model health
Minute 2:00  ── Signal Agent generates scores for universe
Minute 4:00  ── Signal Agent publishes trade proposals (if any)
Minute 5:00  ── DEBATE PHASE: Agents challenge proposals
Minute 8:00  ── Risk Shield Agent reviews surviving proposals
Minute 10:00 ── Execution Agent submits approved orders
Minute 11:00 ── Portfolio Agent updates positions + P&L
Minute 12:00 ── Blackboard cleanup + logging
Minute 13:00 ── System health check + alert if issues
Minute 14:00 ── Idle (buffer for late completions)
Minute 15:00 ── NEW CYCLE
```

**Timing rules**:
- Agents have hard deadlines within the cycle
- If an agent misses its window, it SKIPS (doesn't delay the cycle)
- The cycle is sacred — never run two cycles concurrently
- First cycle of the day includes a market-open analysis (extra data fetch)
- Last cycle of the day includes an end-of-day review

---

## 🗣 Multi-Agent Debate Protocol

The **debate phase** is what makes OpenClaw more than just a pipeline. Before any trade is executed, agents can challenge each other.

### How Debate Works

```python
class DebateProtocol:
    """
    When Signal Agent proposes a trade, other agents can CHALLENGE it.
    A proposal must survive debate to reach Risk Shield.
    """
    
    CHALLENGE_WINDOW = 180  # seconds (3 minutes)
    REQUIRED_CONSENSUS = 0.6  # 60% of voting agents must approve
    
    def run_debate(self, proposal):
        votes = {}
        
        # Each agent votes on the proposal
        for agent in self.voting_agents:
            vote = agent.evaluate_proposal(proposal)
            votes[agent.name] = vote  # APPROVE, REJECT, or ABSTAIN
        
        # Calculate consensus (abstains don't count)
        active_votes = {k: v for k, v in votes.items() if v != 'ABSTAIN'}
        approval_rate = sum(1 for v in active_votes.values() if v == 'APPROVE') / len(active_votes)
        
        result = {
            'proposal': proposal,
            'votes': votes,
            'approval_rate': approval_rate,
            'passed': approval_rate >= self.REQUIRED_CONSENSUS,
            'timestamp': now()
        }
        
        self.blackboard.write('debate_records', result)
        return result
```

### What Each Agent Checks During Debate

| Agent | Challenge Criteria |
|---|---|
| Risk Shield | Position size, portfolio heat, drawdown status |
| Sentiment Agent | Does sentiment confirm or contradict the signal? |
| ML Flywheel | Is the model confident? Any recent drift? |
| Market Data Agent | Is the data fresh? Any gaps or anomalies? |
| Portfolio Agent | Does this trade improve or hurt portfolio balance? |

### Debate Design Principles

1. **Asymmetric veto**: Risk Shield can veto alone; others need majority
2. **Recorded reasoning**: Every vote includes a human-readable reason
3. **Time-boxed**: 3-minute window. No vote = ABSTAIN
4. **No meta-debate**: Agents don't argue about each other's votes
5. **Escalation path**: If debate is split 50/50, default to NO TRADE

---

## 🛠 Agent Design Patterns

### Pattern 1: Agent Lifecycle

Every agent follows this lifecycle:

```python
class BaseAgent:
    def __init__(self, blackboard, config):
        self.blackboard = blackboard
        self.config = config
        self.state = 'initialized'
        self.last_run = None
        self.error_count = 0
    
    def startup(self):
        """One-time initialization. Load models, connect to APIs."""
        self.state = 'ready'
    
    def run(self):
        """Main execution. Called by scheduler."""
        self.state = 'running'
        try:
            result = self.execute()
            self.last_run = now()
            self.error_count = 0  # Reset on success
            self.state = 'ready'
            return result
        except Exception as e:
            self.error_count += 1
            self.state = 'error'
            self.blackboard.write('alerts', {
                'agent': self.name,
                'error': str(e),
                'consecutive_errors': self.error_count
            })
            if self.error_count >= 3:
                self.state = 'disabled'  # Auto-disable after 3 failures
    
    def execute(self):
        """Override in subclass. The actual work."""
        raise NotImplementedError
    
    def shutdown(self):
        """Cleanup. Called on system shutdown."""
        self.state = 'stopped'
```

### Pattern 2: Blackboard Read/Write Protocol

```python
# READS are always safe (non-blocking, returns copy)
data = blackboard.read('market_data')

# WRITES are serialized (one writer at a time)
blackboard.write('signals', data, timestamp=now())

# READS with freshness check (preferred)
data = blackboard.read('market_data', max_age_seconds=120)
if data is None:
    # Data too stale — handle gracefully
    log.warn("Market data stale, using fallback")

# CONDITIONAL WRITE (only if newer than existing)
blackboard.write_if_newer('regime_state', new_regime, timestamp=now())
```

### Pattern 3: Agent Communication Rules

1. **Agents NEVER call each other directly** — always via blackboard
2. **Agents NEVER block** waiting for another agent's output
3. **Agents handle stale data gracefully** — check timestamps
4. **Agents are idempotent** — running twice with same input = same output
5. **Agents are restartable** — crash recovery without state corruption

### Pattern 4: Adding a New Agent

```python
# Step 1: Define the agent class (extend BaseAgent)
class NewAnalysisAgent(BaseAgent):
    name = "new_analysis_agent"
    tier = 2  # Analysis tier
    cycle_position = 3.0  # Minutes into cycle
    
    def execute(self):
        # Read inputs from blackboard
        market_data = self.blackboard.read('market_data', max_age_seconds=120)
        
        # Do analysis
        result = self.analyze(market_data)
        
        # Write outputs to blackboard
        self.blackboard.write('new_analysis', result, timestamp=now())

# Step 2: Register in agent registry (backend/app/modules/)
AGENT_REGISTRY['new_analysis_agent'] = NewAnalysisAgent

# Step 3: Add to cycle schedule
CYCLE_SCHEDULE.append({
    'agent': 'new_analysis_agent',
    'minute': 3.0,
    'required': False  # True = cycle fails if this agent fails
})

# Step 4: Add frontend visibility in AgentCommandCenter
# Step 5: Add to debate voting if it should vote on proposals
```

---

## 🧪 Testing Agents

### Unit Testing Agents

```python
# Every agent must have tests in backend/tests/
# Use a mock blackboard for isolation

class TestSignalAgent:
    def setup(self):
        self.blackboard = MockBlackboard()
        self.agent = SignalAgent(self.blackboard, config=TEST_CONFIG)
    
    def test_generates_signals_with_fresh_data(self):
        self.blackboard.seed('market_data', SAMPLE_MARKET_DATA, age_seconds=30)
        self.agent.execute()
        signals = self.blackboard.read('signals')
        assert signals is not None
        assert all(0 <= s['score'] <= 100 for s in signals.values())
    
    def test_skips_on_stale_data(self):
        self.blackboard.seed('market_data', SAMPLE_MARKET_DATA, age_seconds=300)
        self.agent.execute()
        signals = self.blackboard.read('signals')
        assert signals is None  # Should not produce signals with stale data
    
    def test_risk_shield_always_rejects_oversized(self):
        proposal = TradeProposal(size_pct=0.05)  # 5% — way over limit
        result = self.risk_agent.review_proposal(proposal)
        assert result.status == 'REJECTED'
```

### Integration Testing the Cycle

```python
def test_full_cycle_with_mock_data():
    """Smoke test: full 15-minute cycle with synthetic data."""
    blackboard = Blackboard()
    agents = initialize_all_agents(blackboard, config=TEST_CONFIG)
    
    # Seed initial market data
    blackboard.write('market_data', SYNTHETIC_MARKET_DATA)
    
    # Run cycle
    for agent in sorted(agents, key=lambda a: a.cycle_position):
        agent.run()
    
    # Verify: no agents in error state
    assert all(a.state != 'error' for a in agents)
    
    # Verify: if signals were generated, they went through debate
    if blackboard.read('signals'):
        assert blackboard.read('debate_records') is not None
```

---

## 🔌 Integration with Local AI Models

Espen is building toward using **local AI models** (DeepSeek-R1, Qwen) for agent reasoning. Here's the architectural pattern:

### Local Model Integration Pattern

```python
class AIReasoningMixin:
    """Mixin for agents that use local LLM for analysis."""
    
    def __init__(self, model_endpoint="http://localhost:11434"):
        self.model_endpoint = model_endpoint  # Ollama or similar
        self.model_name = "deepseek-r1:14b"   # Or qwen2.5:32b
    
    def reason(self, prompt, context, max_tokens=500):
        """Query local model for analysis. Returns structured response."""
        response = requests.post(f"{self.model_endpoint}/api/generate", json={
            "model": self.model_name,
            "prompt": prompt,
            "system": f"You are a trading analysis agent. Context: {json.dumps(context)}",
            "stream": False,
            "options": {"temperature": 0.1}  # Low temp for consistency
        })
        return self.parse_structured_response(response.json()['response'])
    
    def parse_structured_response(self, raw):
        """Extract score, confidence, reasoning from LLM output."""
        # Force structured output via prompting
        # Parse JSON block from response
        pass
```

### Design Rules for Local AI Agents

1. **Local models SUPPLEMENT, never replace, quantitative signals** — LLM analysis adds context, it doesn't override XGBoost scores
2. **Timeout hard**: 30-second timeout for any local model call. If it misses, skip.
3. **Temperature = 0.1**: We want consistency, not creativity
4. **Structured output only**: Always prompt for JSON responses, parse them
5. **Fallback gracefully**: If Ollama is down, agent operates without LLM input
6. **Log everything**: LLM reasoning is persisted for post-trade review

---

## ⚠️ Agent Anti-Patterns (AVOID)

| Anti-Pattern | Why It's Bad | What to Do Instead |
|---|---|---|
| God Agent | One agent doing everything | Split into specialized agents |
| Chatty Agents | Agents messaging each other directly | Use blackboard only |
| Blocking Waits | Agent A waits for Agent B | Use stale-data checks, skip if not ready |
| Mutable Shared State | Agents modifying same data concurrently | Serialized blackboard writes |
| No Failure Handling | Agent crashes kill the cycle | try/except + auto-disable after 3 failures |
| Hardcoded Config | Risk limits in code | Config objects passed at initialization |
| Invisible Decisions | Agent makes choices without logging | Log every decision with reasoning |
| Testing in Production | Deploying untested agents to live | Paper trade for 2+ weeks first |

---

## 📊 Agent Health Monitoring

### What the Frontend Shows (Agent Command Center)

The ACC (`/agents` page) displays:
- **Agent status**: Running / Ready / Error / Disabled
- **Last run time**: When each agent last completed
- **Error count**: Consecutive failures
- **Blackboard state**: Current values for each key
- **Debate history**: Recent proposals and vote records
- **Cycle health**: Did the last cycle complete on time?

### Health Metrics to Track

```python
AGENT_HEALTH_METRICS = {
    'uptime_pct': "% of cycles where agent ran successfully",
    'avg_execution_time': "Mean time to complete execute()",
    'p99_execution_time': "99th percentile — detect outliers",
    'error_rate': "Errors per 100 cycles",
    'data_freshness': "Average age of data when agent reads it",
    'signal_stability': "How much signal scores change cycle-to-cycle",
}
```
