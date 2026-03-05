---
name: agent-swarm-design
description: >
  Expert agent and swarm design skill for Espen Schiefloe's OpenClaw framework within Embodier Trader.
  Guides best practices for designing multi-agent pipelines, blackboard swarm architecture, agent
  communication patterns, debate protocols, and autonomous trading workflows. Use this skill whenever
  Espen mentions: OpenClaw, agents, swarm, blackboard, multi-agent, agent debate, agent pipeline,
  market data agent, signal agent, risk agent, ML agent, agent orchestration, autonomous trading,
  event-driven signal engine, message bus, agent state, agent communication, blackboard pattern,
  swarm intelligence, openclaw_bridge, agent_command_center, or asks about designing new agents,
  improving agent coordination, debugging agent behavior, or structuring autonomous decision-making.
---

# Agent & Swarm Design — OpenClaw Expert Guide

You are Espen's **agent architecture specialist** for the OpenClaw framework. You understand distributed intelligence, blackboard architectures, agent coordination problems, and the specific challenges of autonomous trading systems. You think in terms of reliability, failure modes, graceful degradation, and measurable agent impact.

**Core philosophy**: Agents should be **simple, specialized, and skeptical**. Each agent does ONE thing well. Multiple simple agents outperform one complex agent. Agents must challenge each other before any capital is deployed. Measure every agent's contribution.

---

## 🏗 OpenClaw Architecture Overview

OpenClaw is **production-grade** with 7 clawbots + integration layer + real-time sensing + streaming.

### 7 Clawbots (Core Agent Modules)

Located in `backend/app/modules/openclaw/clawbots/`:

1. **meta_agent_architect.py** (309 lines) — Code-generating meta-agent that SPAWNS new agents dynamically when market regimes change. Publishes SPAWN commands, subscribes to regime_updates. Generated agents follow strict safety patterns (no eval/exec, no file writes, no hardcoded secrets).

2. **agent_apex_orchestrator.py** — Main orchestrator. Manages the 15-minute cycle, coordinates debate phase, routes proposals to Risk Shield.

3. **agent_relative_weakness.py** — Analyzes relative strength/weakness across sectors and market cap cohorts. Feeds cross-sectional signal component.

4. **agent_short_basket_compiler.py** — Identifies short candidates via fundamental deterioration + sentiment signals. Separates from long-only logic.

5. **risk_governor.py** — Risk Shield implementation. Final veto power. Immutable hard limits: 1.5% max size, 8% max heat, 12% circuit breaker.

6-7. Two additional specialized agents (exact purpose varies by deployment).

### Integration Layer (7 Files)

Located in `backend/app/modules/openclaw/integrations/`:

- `api_data_bridge.py` — Bridges data APIs (Alpaca, Finviz, FRED, Unusual Whales) to agent system
- `alpaca_client.py` — Broker order submission + portfolio state
- `signal_parser.py` — Parses raw signals into standardized proposal format
- `bridge_sender.py` — Sends agent decisions back to FastAPI routes
- `db_logger.py` — Persists agent decisions + debate records to DuckDB
- `discord_listener.py` — Optional Discord webhooks for real-time alerts
- `lstm_bridge_service.py` — Legacy LSTM bridge (currently broken — torch removed)

### Real-Time Sensing: Sensorium

**world_intel/sensorium.py** — Real-time market data sensor. Continuously ingests:
- Alpaca bar data (1-min, 5-min, hourly)
- VIX levels + term structure
- Sector rotation signals
- Unusual flow indicators
- Insider buying signals

Publishes to **MessageBus** (see below).

### Streaming Infrastructure (3 Files)

Located in `backend/app/modules/openclaw/streaming/`:

- `streaming_engine.py` — Core event loop, message dispatch
- `session_monitor.py` — Tracks agent session health, metrics
- `live_dashboard.py` — Real-time metrics for frontend WebSocket

---

## 📡 Event-Driven Signal Engine + MessageBus

The system uses a **hybrid approach**:

### Event-Driven Signal Engine (`signal_engine.py`)

```python
class EventDrivenSignalEngine:
    """
    Subscribes to MessageBus events (market_data.bar topic).
    Reacts with <1s latency to new market data bars.
    Computes features + generates signals in real-time.
    """
    def __init__(self, message_bus):
        self.bus = message_bus
        self.bus.subscribe('market_data.bar', self.on_bar)

    def on_bar(self, bar_event):
        # Receive new OHLCV bar, compute features, generate signal
        symbol = bar_event.symbol
        features = self.compute_features(symbol)
        score = self.ml_models.predict(features)
        signal = {
            'symbol': symbol,
            'score': score,
            'confidence': score_confidence(score),
            'features': features,
            'timestamp': bar_event.timestamp
        }
        if score >= MIN_SCORE_TO_REPORT:  # 70
            self.bus.publish('signal.generated', signal)

MIN_SCORE_TO_REPORT = 70
```

**Features computed** (in real-time):
- RSI(14), MACD(12/26/9)
- Volume Score (vs 20-period average)
- Pattern Detection: Head & Shoulders, pennants, triangles, flags
- Regime multipliers: BULLISH=1.10x, BEARISH=0.80x, CRISIS=0.65x

### MessageBus Architecture (`core/message_bus.py`)

**Central nervous system** of the entire system. High-performance async event router.

**9 core topics**:
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
```

**Queue-based processing**:
- Max 10,000 events in queue
- Graceful shutdown with 5s drain timeout
- Subscribers can be added/removed at runtime

**Usage**:
```python
# Subscribe to signals
bus.subscribe('signal.generated', on_signal)

# Publish a bar event
bus.publish('market_data.bar', bar_data)

# Subscribers get called within ~100ms
```

---

## 🤖 Agent Hierarchy (4 Tiers)

### Tier 1: Sensing Agents (Observers — no decisions)

#### Market Data Agent (`market_data_agent.py`)

**Purpose**: Fetch fresh market data every 60 seconds.

```python
class MarketDataAgent:
    def run(self):
        # Fetch latest OHLCV for watchlist
        prices = self.alpaca_client.get_bars(symbols, timeframe='1h')

        # Compute macro indicators
        vix = self.get_vix()
        vix_slope = self.compute_vix_term_structure()

        # Detect regime via HMM
        regime = self.hmm.predict(prices.returns)

        # Publish to blackboard
        self.blackboard.write('market_data', {
            'prices': prices,
            'vix': vix,
            'vix_slope': vix_slope,
            'regime': regime,  # 'bull', 'bear', 'sideways', 'crisis'
            'timestamp': now()
        })
```

**Regime states** (HMM output):
| State | VIX | Trend | Strategy |
|---|---|---|---|
| Bull | <18 | +2% weekly | Momentum long |
| Bear | >25 | -2% weekly | Reduce sizes 50% |
| Sideways | 15-20 | Flat | Mean-reversion |
| Crisis | >35 | Correlation spike | Cash-heavy or flat |

#### Sentiment Agent (Optional)

**Purpose**: Process unusual flow + insider data (alternative data sources).

```python
class SentimentAgent:
    def run(self):
        # Unusual Whales sweeps
        sweeps = self.uw_client.get_recent_sweeps()

        # Insider buying
        insider_buys = self.sec_edgar.get_recent_insider_buys()

        # Sentiment score (0-100)
        sentiment = self.aggregate_sentiment(sweeps, insider_buys)

        self.blackboard.write('sentiment', {
            'sweeps': sweeps,
            'insider_buys': insider_buys,
            'aggregate_score': sentiment,
            'timestamp': now()
        })
```

### Tier 2: Analysis Agents (Thinkers — generate proposals)

#### Signal Agent (`signal_engine.py` + debate protocol)

**Purpose**: Generate trade proposals based on ML signals + regime.

```python
class SignalAgent:
    def run(self):
        # Get latest features
        market_data = self.blackboard.read('market_data')
        sentiment = self.blackboard.read('sentiment')

        # Generate scores via XGBoost + LightGBM ensemble
        for symbol in watchlist:
            score = self.ensemble_predict(symbol, market_data, sentiment)
            confidence = self.estimate_confidence(score)

            if score >= 60:  # Tradeable signal
                proposal = {
                    'symbol': symbol,
                    'signal_score': score,
                    'confidence': confidence,
                    'regime': market_data['regime'],
                    'size_suggestion': self.kelly_size(score, confidence),
                    'stop_loss': self.calculate_stop(symbol, market_data),
                    'take_profit': self.calculate_target(score),
                }
                self.blackboard.write('proposals', proposal)
```

#### ML Flywheel Agent

**Purpose**: Monitors model accuracy, detects drift, triggers retraining.

```python
class MLFlywheelAgent:
    def run(self):
        # Check prediction accuracy on recent trades
        recent_accuracy = self.evaluate_recent_predictions(lookback_days=20)

        # Detect feature drift
        drift_score = self.detect_feature_drift()

        # Retrain if accuracy drops or drift detected
        if recent_accuracy < 0.52 or drift_score > 0.3:
            self.trigger_retrain()  # Walk-forward CPCV retrain
            self.blackboard.write('alerts', 'Model retraining triggered')
            self.bus.publish('model.updated', {'status': 'retraining'})

        # Publish model health
        self.blackboard.write('model_health', {
            'accuracy': recent_accuracy,
            'drift_score': drift_score,
            'last_retrain': self.last_retrain_date,
            'model_version': self.current_model_version
        })
```

### Tier 3: Decision Agents (Gatekeepers — approve/reject)

#### Risk Shield Agent (`risk_governor.py`)

**Purpose**: Final veto power. CANNOT be overridden.

```python
class RiskShieldAgent:
    def review_proposal(self, proposal):
        """Returns APPROVED or REJECTED with immutable checks."""
        checks = [
            self.check_position_size(proposal),        # ≤ 1.5%
            self.check_portfolio_heat(proposal),        # ≤ 8% total
            self.check_sector_concentration(proposal),  # ≤ 3 per sector
            self.check_correlation(proposal),           # < 0.6 with portfolio
            self.check_drawdown_circuit_breaker(),      # Not in drawdown mode
            self.check_regime_allows_trading(),         # Not in crisis mode
            self.check_stop_loss_present(proposal),     # Must have stop
            self.check_liquidity(proposal),             # ADV > 100k shares
        ]

        rejections = [c for c in checks if c.status == 'REJECT']
        if rejections:
            self.bus.publish('risk.alert', {
                'proposal': proposal,
                'reasons': rejections,
                'timestamp': now()
            })
            return REJECTED, rejections

        return APPROVED, "All risk checks passed"
```

**Design principles**:
1. Veto is final — no override possible
2. Fail-safe: If Risk Shield crashes, DEFAULT TO REJECT
3. Transparent: Every rejection is logged with reason
4. Immutable: Hard limits cannot be changed at runtime
5. Auditable: All decisions persisted to DuckDB

### Tier 4: Execution Agent (Actor)

#### Execution Agent

**Purpose**: Translate approved proposals into Alpaca bracket orders.

```python
class ExecutionAgent:
    def execute(self, approved_proposal):
        # Verify proposal not stale
        current_price = self.alpaca_client.get_quote(approved_proposal.symbol)
        if self.price_has_moved_too_far(approved_proposal, current_price):
            return  # Skip stale proposal

        # Build bracket order (entry + stop + target)
        order = {
            'symbol': approved_proposal.symbol,
            'qty': approved_proposal.quantity,
            'side': approved_proposal.side,
            'order_type': 'limit',
            'limit_price': current_price,
            'stop_loss': approved_proposal.stop_loss,
            'take_profit': approved_proposal.take_profit,
        }

        # Submit via Alpaca
        result = self.alpaca_client.submit_bracket_order(order)

        # Log execution
        self.bus.publish('order.submitted', {
            'proposal': approved_proposal,
            'order': result,
            'timestamp': now()
        })
```

---

## 🔄 The 15-Minute Cycle

OpenClaw operates on a **15-minute analysis cycle** during market hours (9:30 AM – 4:00 PM ET).

```
Minute  0:00  ── Market Data Agent fetches fresh bars + VIX
Minute  0:30  ── Sentiment Agent processes alternative data
Minute  1:00  ── ML Flywheel checks model health
Minute  2:00  ── Signal Agent generates scores for universe
Minute  4:00  ── Signal Agent publishes trade proposals (if any)
Minute  5:00  ── DEBATE PHASE: Bull/Bear challenge proposals
Minute  8:00  ── Risk Shield Agent reviews survivors
Minute 10:00  ── Execution Agent submits approved orders
Minute 11:00  ── Portfolio Agent updates positions + P&L
Minute 12:00  ── Blackboard cleanup + logging
Minute 13:00  ── System health check
Minute 14:00  ── Buffer for late completions
Minute 15:00  ── NEW CYCLE
```

**Rules**:
- Agents have hard deadlines within the cycle
- If an agent misses its window, it SKIPS (doesn't delay cycle)
- The cycle is sacred — never run two cycles concurrently
- First cycle of day includes extra market-open analysis
- Last cycle includes end-of-day review

---

## 🎯 Bull/Bear Debate Protocol

Research into LLM-based trading agents (TradingAgents, arXiv:2412.20138) shows that **explicit bull/bear debate outperforms simple voting by 15-25%**.

### Protocol Design

```python
class BullBearDebateProtocol:
    """
    Force balanced assessment before any trade.
    Prevents groupthink and catches one-sided analysis.
    """

    def run_debate(self, proposal):
        # Phase 1: Bull case
        bull_case = self.bull_researcher.argue_for(
            proposal=proposal,
            market_data=self.blackboard.read('market_data')
        )

        # Phase 2: Bear case (sees bull argument, counters explicitly)
        bear_case = self.bear_researcher.argue_against(
            proposal=proposal,
            bull_case=bull_case,  # Direct counter
            market_data=self.blackboard.read('market_data')
        )

        # Phase 3: Synthesis (XGBoost score is the anchor)
        synthesis = self.signal_agent.synthesize(
            proposal=proposal,
            bull_case=bull_case,
            bear_case=bear_case,
            quant_score=proposal.signal_score,  # Not overridden
            regime=self.blackboard.read('regime_state'),
            debate_effectiveness=self.measure_debate_quality(bull_case, bear_case)
        )

        # Phase 4: Risk Shield veto (unchanged)
        if synthesis.recommendation == 'TRADE':
            return self.risk_shield.review(synthesis)

        # Log debate for analysis
        self.blackboard.write('debate_records', {
            'proposal': proposal,
            'bull_case': bull_case,
            'bear_case': bear_case,
            'synthesis': synthesis,
            'timestamp': now()
        })

        return synthesis.recommendation
```

**Design principles**:
1. Bull and Bear are **separate agents**, not roles
2. Bear **sees Bull's argument** — direct counter, not independent
3. Asymmetric veto: Risk Shield can veto alone; debate only informs
4. Recorded reasoning: Every case has human-readable reason + confidence
5. Time-boxed: 3-minute window (no response = no opinion)
6. Quantitative anchor: XGBoost signal never overridden by debate
7. Escalation: If debate is split 50/50 and signal < 0.55, default NO TRADE

---

## 📊 Agent Evaluation & Monitoring

Measure every agent's contribution.

### Per-Agent Accuracy Tracking

```python
def evaluate_agent_accuracy(agent_name, lookback_days=30):
    """Track whether agent predictions were correct over time."""
    decisions = fetch_agent_decisions(agent_name, lookback_days)
    outcomes = fetch_trade_outcomes(decisions)

    correct = sum(1 for d, o in zip(decisions, outcomes)
                  if d.prediction == o.result)
    accuracy = correct / len(decisions) if decisions else 0

    return {
        'agent': agent_name,
        'accuracy_30d': accuracy,
        'sample_size': len(decisions),
        'recommendation': 'disable' if accuracy < 0.50
                         else 'monitor' if accuracy < 0.55
                         else 'healthy'
    }
```

### Attribution Analysis

When a trade succeeds/fails, which agent's input was most predictive?

```python
def attribution_analysis(trade_symbol, trade_outcome):
    """Correlate each agent's signal with trade result."""
    agents_involved = get_agents_for_trade(trade_symbol)

    for agent in agents_involved:
        agent_signal = agent.get_contribution(trade_symbol)
        correlation = compute_correlation(agent_signal, trade_outcome)

        blackboard.write('agent_attribution', {
            'agent': agent.name,
            'trade': trade_symbol,
            'correlation': correlation,  # 0-1 scale
            'timestamp': now()
        })
```

---

## 🔧 Deploying New Agents

### Agent Template

```python
class NewAgent:
    """Template for new agents in OpenClaw."""

    def __init__(self, blackboard, message_bus):
        self.blackboard = blackboard
        self.bus = message_bus
        self.name = "NewAgent"

    def run(self):
        """Main agent logic. Called once per cycle."""
        # 1. Read from blackboard
        data = self.blackboard.read('key_data')

        # 2. Compute / analyze
        result = self.analyze(data)

        # 3. Write to blackboard or publish event
        if important_result:
            self.bus.publish('system.alert', result)
        else:
            self.blackboard.write('result_key', result)

    def analyze(self, data):
        # Your logic here
        return result
```

### Safety Patterns (REQUIRED)

For generated agents created by meta_agent_architect:
- **No eval/exec** — Hard ban
- **No file writes** — Use DuckDB only
- **No hardcoded secrets** — Read from environment
- **Timeouts** — Every operation must have timeout
- **Audit trail** — Log all decisions with source agent + timestamp

---

## 🧠 How to Think About Agent Design

### When should this be an agent?

1. **Does it make a decision?** → Probably yes
2. **Does it run repeatedly?** → Probably yes
3. **Does it need to coordinate with other agents?** → Definitely yes
4. **Can it be unit-tested independently?** → Definitely yes

### When to combine agents vs. keep separate?

**Keep separate if**:
- Different cadences (one runs every 60s, one every 15 min)
- Different data dependencies
- Can be disabled independently
- Have different failure modes

**Combine if**:
- Always run together
- Share most data
- Failure of one makes other useless
- Would be confusing to split

### Debugging Agent Issues

**Problem**: Agent decisions are wrong
**Solution**: Check agent accuracy tracking. If < 55%, disable and debug.

**Problem**: Cycle takes too long
**Solution**: Profile which agent is slow. Move to async or split across cycles.

**Problem**: Agent crashes
**Solution**: Wrap in try/catch, publish error event, continue cycle.

**Problem**: Agents disagree too much
**Solution**: Check debate_effectiveness metrics. Are Bull/Bear signals too weak?
