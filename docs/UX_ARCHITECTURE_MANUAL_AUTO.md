# Manual vs Auto Trading Modes: UX Architecture Report
## Frontend Design Audit & Operator-Centered Redesign

**Date**: 2026-03-08
**System**: Embodier.ai Elite Trading Platform
**Repository**: https://github.com/Espenator/elite-trading-system
**Author**: Senior Product Designer / UX Architect

---

## Executive Summary

This platform currently lacks a cohesive Manual vs Auto mode paradigm. The existing frontend focuses on AI intelligence, multi-agent systems, and analytics **without clearly communicating execution authority or operator control**. The UI must be reorganized around two primary operating modes — **Manual** and **Auto** — while making risk, execution status, and decision visibility the central design language.

**Current Reality**:
- Alpaca paper trading is already integrated as the execution layer
- No third "simulator" mode is needed in the user-facing experience
- Backend already has sophisticated risk controls, circuit breakers, and agent councils
- Frontend lacks visible execution mode switching, authority status, or trade approval flows

**Design Goal**:
Transform this from an analytics dashboard into a **trustworthy operator cockpit** where mode, risk, execution authority, and system health are immediately visible and controllable.

---

## A. Current Frontend Audit

### Current Page Structure

The frontend consists of **14 pages** across 5 navigation sections:

#### **COMMAND Section** (2 pages)
- `Dashboard.jsx` - 75KB, massive multi-widget intelligence dashboard
- `AgentCommandCenter.jsx` - Agent status and control

#### **INTELLIGENCE Section** (3 pages)
- `SentimentIntelligence.jsx` - Sentiment tracking
- `DataSourcesMonitor.jsx` - External data source health
- `SignalIntelligenceV3.jsx` - Multi-layer signal generation and scoring

#### **ML & ANALYSIS Section** (5 pages)
- `MLBrainFlywheel.jsx` - ML training and inference
- `Patterns.jsx` - Pattern recognition and screening
- `Backtesting.jsx` - 50KB, comprehensive backtest laboratory
- `PerformanceAnalytics.jsx` - Trade performance metrics
- `MarketRegime.jsx` - 41KB, HMM regime state machine

#### **EXECUTION Section** (3 pages)
- `Trades.jsx` - Active positions and orders (read-only view)
- `RiskIntelligence.jsx` - 47KB, risk monitoring and shields
- `TradeExecution.jsx` - Trade staging and execution

#### **SYSTEM Section** (1 page)
- `Settings.jsx` - 53KB, general configuration

---

### What the Current UI Suggests

The platform appears designed as an **AI intelligence observatory** rather than a trading command center:

1. **Intelligence-First, Not Execution-First**
   - Pages emphasize signals, agents, ML models, and analytics
   - Execution is hidden in a small subsection
   - No visible "mode" concept (Manual vs Auto)

2. **Fragmented Concepts**
   - Signal generation spread across multiple pages (SignalIntelligenceV3, Patterns, Dashboard)
   - Risk controls in one place, execution in another, settings in a third
   - No single source of truth for execution authority

3. **Analytics Overload**
   - Multiple pages with overlapping charts (Performance, Backtesting, Dashboard all show equity curves)
   - Regime detection is a full standalone page, but doesn't clearly link to execution behavior
   - Too many agent/swarm views without clear operator action paths

4. **Missing Operator Controls**
   - No visible Manual/Auto toggle
   - No execution authority status indicator
   - No trade approval queue in Manual mode
   - No circuit breaker status
   - No "kill switch" or emergency controls visible at top level
   - No visible Alpaca account connection status

---

### Where Manual vs Auto is Absent

**COMPLETELY MISSING**:
- Mode selector/toggle (Manual vs Auto)
- Execution authority indicator (who decides: human or system?)
- Trade approval workflow (Manual mode: operator reviews and clicks "Execute")
- Auto mode arming/disarming controls
- Visible risk gates and execution blockers
- "Why was this trade blocked?" explanations
- Trade-by-trade decision audit trail

**Dashboard (`Dashboard.jsx`)**:
- Shows agent status, signals, regime, sentiment
- Does NOT show: current mode, execution authority, pending approval queue, risk breaker status

**Settings (`Settings.jsx`)**:
- Has risk configuration sliders
- Does NOT have: Manual/Auto mode switch, execution authority panel, circuit breaker panel, account status

**TradeExecution (`TradeExecution.jsx`)**:
- Shows signals and allows staging orders
- Does NOT distinguish: Manual approval flow vs Auto execution flow
- No visible "Auto is armed" vs "Manual approval required" state

**RiskIntelligence (`RiskIntelligence.jsx`)**:
- Excellent risk metrics and VaR gauges
- Has "Emergency Stop All" button
- Does NOT show: whether Auto is allowed to trade, current execution authority, circuit breaker state integrated with mode

---

### Pages That Are Overloaded or Overlapping

1. **Dashboard is a monolith** (75KB, 2,500+ lines)
   - Combines agent status, signals, regime, performance, recent trades, sentiment, knowledge, ML flywheel
   - Should be refactored into a **focused cockpit** showing only: mode, health, risk, pending actions, today's stats

2. **SignalIntelligenceV3 vs Dashboard vs Patterns**: Signal generation is fragmented
   - SignalIntelligenceV3 shows scanners, scoring, intel modules
   - Dashboard shows recent signals
   - Patterns shows screener results
   - **Should consolidate into one "Signal Intelligence" view**

3. **PerformanceAnalytics vs Backtesting**: Both show equity curves, trade logs, performance metrics
   - Backtesting: historical simulation analysis
   - Performance: live paper-trading results
   - **Should clearly separate**: Backtesting = validation tool, Performance = live results

4. **RiskIntelligence vs Settings**: Risk configuration is split
   - RiskIntelligence shows current risk state
   - Settings has risk sliders
   - **Should merge into unified Risk Control Plane**

5. **MarketRegime is isolated**:
   - Beautiful regime state machine
   - Does NOT show how regime affects execution behavior (max positions, kelly multiplier changes)
   - **Should be a widget in Dashboard or integrated into Trade Execution flow**

---

## B. Recommended Product UX Model

### Clean Operator Mental Model

The operator should think in **three layers**:

**Layer 1: MODE** (Manual vs Auto)
- **Manual**: System recommends, human executes
- **Auto**: System recommends AND executes (subject to strict controls)

**Layer 2: AUTHORITY** (Who can execute?)
- Auto Armed + All gates passed → Auto can execute
- Auto Armed + Gates blocking → Auto cannot execute
- Manual → Operator must click "Execute" for every trade

**Layer 3: RISK** (What limits are active?)
- Portfolio heat, max positions, daily loss limits
- Circuit breakers (drawdown, loss streak, volatility spike)
- Regime-based restrictions (e.g., RED regime = no trading)

### Role of Manual Mode

**Manual Mode** is the default safe mode:

- System performs full analysis: signals, scoring, risk checks, position sizing
- System stages "ready to execute" trade candidates
- **Operator must click "Execute" to place the paper trade**
- UI shows:
  - Pending approval queue
  - Recommended trade details (symbol, side, size, stop, target)
  - Risk consumed per trade
  - Why this trade qualifies or is blocked
  - One-click approve/reject buttons

**Design Language**:
- Green "Approve" and red "Reject" buttons prominent
- Trade cards show full transparency: score, agents involved, risk, regime context
- Operator sees real-time Alpaca paper account balance and positions

### Role of Auto Mode

**Auto Mode** allows the system to execute without human approval:

- Same analysis as Manual mode
- **System automatically places trades** if all conditions pass:
  - Signal confidence ≥ threshold
  - Risk budget available
  - No circuit breakers triggered
  - Regime allows trading
  - Position limits not exceeded
- UI shows:
  - "Auto Armed" status with bright indicator
  - Recent auto-executed trades (last 5)
  - **Why trades were blocked** (not just executed trades)
  - Current risk budget consumed
  - Emergency pause/kill switch always visible

**Design Language**:
- Bright "Auto Armed" indicator (e.g., pulsing cyan badge)
- Recent executions shown as audit trail
- Blocked trades shown with explanations ("Max positions reached", "Confidence too low", etc.)
- Kill switch red and prominent

**What Should Be Locked When Auto Is Armed**:
- Risk limits should require confirmation to change mid-session
- Strategy selection should be locked
- Max position limits should be locked
- Operator can still manually execute trades in Auto mode (override)

**Warnings Required to Enable Auto**:
- "Auto mode will place paper trades automatically. Confirm risk limits are correct."
- "Circuit breakers active: Max daily loss $X, Max positions Y, etc."
- Require clicking through confirmation dialog with checklist

### Role of Backtesting and Analytics

**Backtesting** = Historical validation tool (research mode, not live):
- Stays as a separate page (`Backtesting.jsx`)
- Used to validate strategies before enabling Auto mode
- Shows walk-forward analysis, Monte Carlo, parameter sweeps
- **Link to Auto**: "Strategy Grade B+ → Approved for Auto with $500 max risk"

**Performance Analytics** = Live paper-trading results:
- Shows real Alpaca paper account performance
- Rolling metrics, agent attribution, trade log
- **Link to Auto**: "Auto disabled: Sharpe < 1.0 (current: 0.82)"

**Regime Intelligence** = Market context that affects execution:
- Regime state determines risk multipliers
- RED regime → Auto disabled or heavily restricted
- GREEN regime → Auto allowed with higher risk
- **Should be a dashboard widget, not a standalone page** (or reduce prominence)

### Role of Settings and Control Plane

**Settings** becomes the **Execution Control Plane**:

A single page with clear tabs:

**Tab 1: Mode & Authority**
- Manual / Auto toggle (large, obvious)
- Alpaca account status (connected, paper/live indicator)
- Execution permissions (Auto enabled/disabled, why?)
- Emergency controls (Pause Auto, Kill Switch)

**Tab 2: Risk Limits**
- Max risk per trade (%)
- Max open positions (#)
- Max portfolio heat (%)
- Max daily loss ($)
- Max weekly drawdown (%)
- Circuit breakers (loss streak, volatility spike, drawdown threshold)

**Tab 3: Strategy & Filters**
- Active strategy selection
- Symbol whitelist/blacklist
- Sector concentration limits
- Market hours restrictions
- Minimum liquidity / spread filters

**Tab 4: Execution Policies**
- Stop-loss required (yes/no)
- Take-profit policy
- Position sizing method (Kelly, fixed %, etc.)
- Order types (limit/market preference)

**Tab 5: Agent Consensus**
- Minimum agent confidence
- Required agent agreement (e.g., 3 out of 5 must agree)
- Agent weighting configuration

---

## C. Recommended Navigation Structure

### Primary Navigation (Sidebar)

Reorganize into **5 clear sections**:

#### **1. COMMAND** (Operator Cockpit)
- **Dashboard** - Mode, health, risk, queue, today's stats
- ~~Agent Command Center~~ → Demote to Dashboard widget

#### **2. EXECUTION** (Trade Flow)
- **Trade Execution** - Approval queue (Manual) or auto execution log (Auto)
- **Active Trades** - Current positions and orders (keep as-is)
- **Settings / Control Plane** - Mode, risk limits, authority (PROMOTED)

#### **3. RISK & PERFORMANCE** (Results & Safety)
- **Risk Intelligence** - Risk status, circuit breakers, shields
- **Performance** - Live paper-trading results
- ~~Market Regime~~ → Demote to Dashboard widget or Settings context

#### **4. INTELLIGENCE** (Signal Generation)
- **Signal Intelligence** - Unified signal generation (merge SignalIntelligenceV3 + Patterns)
- ~~Sentiment~~ → Demote to Dashboard widget
- ~~Data Sources~~ → Demote to Settings subtab

#### **5. RESEARCH** (Validation & Analysis)
- **Backtesting** - Strategy validation laboratory
- **ML Brain & Flywheel** - Model training and inference
- ~~Agent Command~~ → Move here as "Agent Management"

---

### Pages to Merge

1. **SignalIntelligenceV3.jsx + Patterns.jsx → "Signal Intelligence"**
   - Single page with tabs: Scanners, Patterns, Scoring, Signals
   - Reduce duplication, increase clarity

2. **Dashboard widgets absorb**:
   - Agent status (from AgentCommandCenter)
   - Regime indicator (from MarketRegime) → Small widget showing current regime and risk multiplier
   - Sentiment gauge (from SentimentIntelligence)
   - Data source health (from DataSourcesMonitor)

3. **Settings absorbs**:
   - Manual/Auto mode switch (NEW)
   - Alpaca account status (NEW)
   - Risk configuration (currently scattered)
   - Circuit breaker controls (from RiskIntelligence)

---

### Pages to Demote to Widgets or Secondary Views

- **MarketRegime** → Dashboard widget (regime badge + params) + optional drill-down modal
- **SentimentIntelligence** → Dashboard widget (sentiment gauge + score)
- **DataSourcesMonitor** → Settings subtab "Data Sources"
- **AgentCommandCenter** → Research section "Agent Management" (less prominent)

---

## D. Key Page Redesigns

### **1. Dashboard** (Primary Cockpit)

**Purpose**: 10-second status check for the operator

**Key Modules** (in order of visual priority):

**Top Header Bar**:
```
[MODE: Manual | Auto]  [ACCOUNT: Alpaca Paper ✓]  [HEALTH: All Systems OK]  [RISK: 15/25% Heat]
[Emergency Pause] [Kill Switch]
```

**Status Strip** (KPI row):
```
Today P&L: +$247  |  Open Positions: 3/6  |  Win Rate: 68%  |  Circuit Breakers: CLEAR  |  Auto: ARMED
```

**Main Grid** (3 columns):

**Left Column: Execution Queue**
- **Manual Mode**: Pending trades waiting for approval (cards with Approve/Reject buttons)
- **Auto Mode**: Recent auto-executions (last 5) + blocked trades with reasons

**Center Column: System Health**
- Agent council status (7 core agents OK, swarm size 150)
- Market regime badge (GREEN, confidence 87%)
- Risk shield status (VaR, drawdown, exposure gauges)
- Data source health (API latency, feed status)

**Right Column: Today's Activity**
- Recent executed trades (last 5, with P&L)
- Active positions summary (3 positions, total value)
- Alerts requiring attention (if any)

**Bottom Row: Intelligence Widgets**
- Sentiment gauge (Bullish 72%)
- Top signal (NVDA, score 96, STAGED)
- Regime flow mini-diagram

**Must-Have Controls**:
- Manual / Auto toggle (top-left, large)
- Emergency Pause (disables Auto immediately)
- Kill Switch (closes all positions, halts trading)

**Must-Have Status Indicators**:
- Mode badge (MANUAL in blue, AUTO in cyan with pulse)
- Account status (Alpaca Paper ✓, balance visible)
- System health (green/amber/red indicator)
- Risk health (% portfolio heat consumed)
- Auto armed status (large badge when Auto is active)

**Must-Have Warnings**:
- Circuit breakers triggered (red banner)
- Auto disabled (amber banner with reason)
- Account disconnected (red banner)

---

### **2. Settings / Execution Control Plane**

**Purpose**: Configure mode, risk, and execution authority

**Key Tabs**:

**Tab 1: Mode & Authority** ⭐ DEFAULT TAB
```
┌─ Mode Selection ────────────────────────────────┐
│  ○ Manual    ● Auto                             │
│                                                  │
│  Auto Status: ARMED ✓                           │
│  Alpaca Account: PAPER ✓ ($25,000 balance)      │
│  Execution Permission: GRANTED                   │
│                                                  │
│  [Emergency Pause Auto]  [Kill Switch]          │
└──────────────────────────────────────────────────┘
```

**Tab 2: Risk Limits**
```
Max Risk Per Trade: [2.0]% slider
Max Open Positions: [6] slider
Max Portfolio Heat: [25]% slider
Max Daily Loss: [$500] input
Max Weekly Drawdown: [8]% slider

Circuit Breakers:
  ☑ Loss Streak (3 consecutive losses)
  ☑ Drawdown Threshold (-5%)
  ☑ Volatility Spike (VIX > 30)
  ☑ Market Hours Only
```

**Tab 3: Strategy & Filters**
```
Active Strategy: [Mean Reversion V2] dropdown
Symbols: [NVDA, AMD, TSLA, AAPL, ...]
Sector Concentration Max: [30]%
Min Liquidity: [$1M] daily volume
Max Spread: [0.5]%
```

**Tab 4: Execution Policies**
```
Stop-Loss Required: ☑ Yes
Stop Type: [Trailing] dropdown
Take-Profit Policy: [Risk-Reward 2:1] dropdown
Position Sizing: [Kelly Criterion 25%] dropdown
```

**Tab 5: Agent Consensus**
```
Min Signal Confidence: [75]% slider
Required Agent Agreement: [3/5] slider
Agent Weighting: [Configure] button → modal
```

**Must-Have Controls**:
- Save/Apply button (confirms all changes)
- Reset to Safe Defaults button
- Export/Import configuration

**Must-Have Warnings**:
- "Changing risk limits while Auto is armed requires confirmation"
- "Stop-loss disabled: HIGH RISK"
- "No circuit breakers enabled: UNSAFE"

---

### **3. Trade Execution**

**Purpose**: Approve trades (Manual) or monitor auto executions (Auto)

**Manual Mode View**:

**Header**:
```
Mode: MANUAL  |  Pending Approval: 2 trades  |  Risk Available: 10/25%
```

**Approval Queue** (cards):
```
┌─ NVDA LONG ──────────────────────────────────┐
│ Score: 96 (SLAM DUNK)                        │
│ Agents: Apex Orchestrator, Signal Engine    │
│ Entry: $145.28  Stop: $142.10  Target: $151.50│
│ Size: 50 shares ($7,264 notional)            │
│ Risk: 2.2% ($546 at risk)                    │
│ Regime: GREEN (confidence 87%)               │
│ Why Eligible: High confidence, regime allows│
│                                              │
│ [✓ Approve] [✗ Reject]                       │
└──────────────────────────────────────────────┘
```

**Recent Decisions** (audit trail):
```
10:32 AM  NVDA LONG  Approved  +$123 (open)
10:18 AM  AMD LONG   Rejected  (Low confidence)
09:45 AM  TSLA SHORT Approved  -$45 (closed)
```

**Auto Mode View**:

**Header**:
```
Mode: AUTO [ARMED]  |  Auto Executions Today: 5  |  Blocked: 2  |  Risk: 15/25%
```

**Recent Auto Executions**:
```
10:45 AM  NVDA LONG   Auto ✓  96 score  $145.28  50 shares
10:32 AM  PLTR LONG   Auto ✓  91 score  $44.80   100 shares
10:18 AM  AMD LONG    BLOCKED (Max positions reached)
```

**Blocked Trades with Explanations**:
```
┌─ AMD LONG ────────────────────────────────────┐
│ Score: 88 (STRONG GO)                         │
│ BLOCKED: Max open positions reached (6/6)     │
│ Would have executed if position slot available│
└───────────────────────────────────────────────┘
```

**Must-Have Controls (Manual)**:
- Approve/Reject buttons per trade
- Approve All (with confirmation)
- Reject All

**Must-Have Controls (Auto)**:
- Pause Auto (suspends execution)
- Resume Auto
- Manual Override (force execute a trade)

**Must-Have Status**:
- Pending approval count (Manual)
- Auto armed indicator (Auto)
- Risk budget consumed
- Execution queue depth

---

### **4. Active Trades** (keep largely as-is, minor additions)

**Purpose**: Monitor open positions and orders

**Additions to Current Design**:
- Mode indicator in header (Manual / Auto)
- "Executed By" column in trades table (Manual approval / Auto execution / Operator override)
- Circuit breaker status in header
- Quick link to close all positions (emergency)

---

### **5. Risk Intelligence**

**Purpose**: Monitor risk health and circuit breakers

**Additions to Current Design**:

**Top Section - Auto Execution Status**:
```
Auto Mode: ARMED ✓
Execution Permission: GRANTED
Circuit Breakers: 0 triggered

Why Auto Can Execute:
  ✓ Risk budget available (15/25% used)
  ✓ No circuit breakers active
  ✓ Drawdown within limits (-2.1% vs -5% max)
  ✓ Regime allows trading (GREEN)
```

**Circuit Breaker Panel** (new):
```
Loss Streak: CLEAR (0/3 consecutive losses)
Drawdown: CLEAR (-2.1% / -5% threshold)
Daily Loss: CLEAR (-$50 / -$500 limit)
Volatility Spike: CLEAR (VIX 18.5 / 30 threshold)
```

**Emergency Actions** (keep existing):
- Kill Switch
- Hedge
- Reduce
- Freeze

**Must-Have Additions**:
- "Why is Auto blocked?" explanation when Auto is disabled
- Circuit breaker history (last 7 days)
- Link to Settings to adjust circuit breaker thresholds

---

### **6. Signal Intelligence** (merge SignalIntelligenceV3 + Patterns)

**Purpose**: Understand signal generation and scoring

**Tabs**:
- **Scanners**: 14 scanner modules (currently in SignalIntelligenceV3)
- **Patterns**: Screener results (currently in Patterns)
- **Scoring**: Global scoring engine (currently in SignalIntelligenceV3)
- **Signals**: Recent signals table

**Key Additions**:

**Signals Table Columns**:
- Symbol, Score, Direction, Price
- **Execution Status**: Pending Approval / Auto Executed / Blocked / Rejected
- **Why Blocked**: (if blocked) "Max positions", "Low confidence", etc.
- Actions: View Chart, Approve (if Manual), Details

**Must-Have Clarity**:
- Each signal shows whether it would pass Auto execution criteria
- Blocked signals show specific reason
- Link to approve signal directly from this page (Manual mode)

---

### **7. Performance Analytics**

**Purpose**: Live paper-trading performance

**Key Distinction from Backtesting**:
- This page shows **real Alpaca paper account** results
- Equity curve uses real trade data from Alpaca
- Agent attribution shows which agents generated profitable signals
- Trade log shows actual executed trades (Manual + Auto)

**Additions**:
- Mode breakdown: "Manual: 12 trades, Auto: 8 trades"
- Auto eligibility: "Strategy Grade B+ → Auto enabled"
- Performance thresholds: "Sharpe must stay > 1.0 to keep Auto enabled"

**Link to Settings**:
- "Auto disabled: Sharpe fell below 1.0 (current: 0.82). Adjust threshold in Settings."

---

### **8. Backtesting**

**Purpose**: Validate strategies before enabling Auto

**Keep Largely As-Is**, with Additions:

**Top Banner**:
```
Strategy: Mean Reversion V2
Backtest Grade: B+ (Sharpe 1.8, Win Rate 68%)
Auto Status: APPROVED for Auto with $500 max risk
[Enable Auto with This Strategy]
```

**Link to Auto**:
- "This strategy qualifies for Auto mode. Go to Settings to enable."
- "Current live performance: Sharpe 1.2 (backtest: 1.8) → Degradation warning"

---

## E. Manual vs Auto UX Behavior

### Exact Mode Switching Workflow

#### **Switching from Manual to Auto**:

1. **User clicks Auto toggle in Dashboard or Settings**
2. **System shows confirmation dialog**:
```
┌─ Enable Auto Trading ────────────────────────┐
│ Auto mode will allow the system to place     │
│ paper trades automatically without approval.  │
│                                               │
│ Verify your current limits:                  │
│  ☑ Max risk per trade: 2.0%                   │
│  ☑ Max open positions: 6                      │
│  ☑ Max daily loss: $500                       │
│  ☑ Circuit breakers active                    │
│  ☑ Stop-loss required                         │
│                                               │
│ Account: Alpaca Paper ($25,000 balance)       │
│                                               │
│ [Cancel]  [Confirm: Enable Auto]             │
└───────────────────────────────────────────────┘
```
3. **User clicks Confirm**
4. **System sets mode to Auto, shows "Auto Armed" indicator**
5. **Dashboard updates**: Approval queue → Auto execution log
6. **Trade Execution page updates**: Shows recent auto executions + blocked trades

#### **Switching from Auto to Manual**:

1. **User clicks Manual toggle or Emergency Pause**
2. **System immediately disables Auto execution** (no confirmation needed for safety switch)
3. **System shows notification**: "Auto mode disabled. No new trades will execute automatically."
4. **Dashboard updates**: Auto execution log → Approval queue
5. **Trade Execution page updates**: Shows pending approval trades

---

### What Changes in UI When Manual is Active

**Dashboard**:
- Mode badge: "MANUAL" (blue)
- Execution Queue widget shows "Pending Approval: 2 trades" with cards
- Approve/Reject buttons visible
- No "Auto Armed" indicator

**Settings**:
- Mode toggle on "Manual"
- Risk limits freely editable (no warnings about changing limits while Auto is armed)

**Trade Execution**:
- Approval Queue view active
- Each trade card has Approve/Reject buttons
- Recent decisions audit trail

**Signal Intelligence**:
- Signals table shows "Pending Approval" status
- "Approve" button available per signal

**Risk Intelligence**:
- Shows "Manual Mode: Operator approval required for all trades"
- Circuit breaker status still visible but less emphasized

---

### What Changes in UI When Auto is Active

**Dashboard**:
- Mode badge: "AUTO [ARMED]" (cyan, pulsing)
- Execution Queue widget shows "Auto Executions Today: 5" with recent trades
- Recent executions list (last 5) with timestamps
- Blocked trades section with reasons
- Emergency Pause button prominent (red, top-right)

**Settings**:
- Mode toggle on "Auto"
- **Warning banners when editing risk limits**:
  - "Auto is currently armed. Changing risk limits requires confirmation."
  - [Save Changes] button shows confirmation: "Update risk limits while Auto is active?"

**Trade Execution**:
- Auto Execution Log view active
- Recent auto-executed trades with timestamps, scores, agents
- Blocked trades with detailed explanations
- "Pause Auto" button prominent
- Manual override button (operator can still force execute trades)

**Signal Intelligence**:
- Signals table shows "Auto Executed" or "Blocked" status
- No Approve button (read-only)
- "Why Blocked" column shows reasons

**Risk Intelligence**:
- Shows "Auto Mode: System executing trades automatically"
- **Auto Execution Status panel** (new):
  - "Auto Permission: GRANTED" (green) or "BLOCKED" (red)
  - List of reasons Auto can/cannot execute
  - Circuit breaker status emphasized

---

### What Should Be Locked When Auto is Armed

**Locked (require confirmation to change)**:
- Max risk per trade
- Max open positions
- Max daily loss
- Circuit breaker thresholds
- Active strategy selection
- Stop-loss requirement
- Minimum signal confidence

**Unlocked (can change anytime)**:
- Emergency Pause / Kill Switch (always available)
- Chart timeframes, display preferences
- Alerts and notifications

**Confirmation Dialog for Locked Items**:
```
┌─ Confirm Change ───────────────────────────────┐
│ Auto mode is currently ARMED and actively      │
│ trading. Changing this setting may affect      │
│ in-flight decisions.                            │
│                                                 │
│ Change: Max risk per trade 2.0% → 3.0%         │
│                                                 │
│ [Cancel]  [Pause Auto & Apply]  [Force Apply]  │
└─────────────────────────────────────────────────┘
```

---

### Warnings and Confirmations Required

#### **Enable Auto**:
- Confirmation dialog (shown above)
- Checklist of active risk limits
- Verification of account connection

#### **Disable Auto / Emergency Pause**:
- No confirmation (instant, for safety)
- Notification: "Auto trading paused. You can resume in Settings."

#### **Kill Switch**:
- Strong confirmation:
```
┌─ EMERGENCY KILL SWITCH ────────────────────────┐
│ ⚠️  WARNING: This will immediately:            │
│   • Close ALL open positions at market         │
│   • Cancel ALL pending orders                  │
│   • Disable Auto trading                       │
│   • Halt all new signals                       │
│                                                 │
│ This is an IRREVERSIBLE emergency action.      │
│                                                 │
│ Type CONFIRM to proceed: [________]            │
│                                                 │
│ [Cancel]  [EXECUTE KILL SWITCH]                │
└─────────────────────────────────────────────────┘
```

#### **Change Risk Limits While Auto Armed**:
- Confirmation (shown above)
- Options: Pause Auto first, or Force apply

#### **Manual Override in Auto Mode**:
- Minor confirmation:
```
Manual Override: Execute this trade immediately?
This will bypass Auto execution and be attributed to you.
[Cancel] [Execute]
```

---

## F. Landing Page / Marketing Recommendations

**Current Marketing (if exists)**: Likely emphasizes AI, agents, machine learning, automation

**Recommended Honest Messaging**:

### Hero Section
```
Operator-Controlled AI Trading Intelligence
Disciplined Paper Trading with Manual and Auto Modes
```

### Feature Highlights

**1. Manual Mode: You Decide**
- AI-powered signal generation and risk analysis
- Full trade transparency with score, agents, and context
- One-click approve/reject for every trade
- Real-time paper trading through Alpaca

**2. Auto Mode: Disciplined Automation**
- Strict risk controls and circuit breakers
- Regime-aware execution with operator oversight
- Complete audit trail of every decision
- Paper trading only (live trading roadmap)

**3. Risk-First Design**
- Portfolio heat limits and position sizing
- Circuit breakers: loss streaks, drawdowns, volatility
- Emergency pause and kill switch
- Explainable AI: see why every trade is approved or blocked

**4. Validated Intelligence**
- 31-agent council decision system
- Walk-forward validated strategies
- Backtesting laboratory with Monte Carlo
- Live performance vs backtest comparison

### What Messaging to Remove

**Remove**:
- "Fully autonomous money printer"
- "Set and forget"
- "Guaranteed profits"
- Any hype about "AI takes over"

**Replace With**:
- "Operator-controlled intelligence"
- "Disciplined automation"
- "Measurable validation"
- "Risk-first trading"

### Product Screenshots to Highlight

**Screenshot 1: Dashboard Cockpit**
- Show Manual mode with pending approval queue
- Highlight: "You decide on every trade"

**Screenshot 2: Auto Mode Armed**
- Show Auto armed indicator + recent executions
- Highlight: "Auto mode with full transparency and circuit breakers"

**Screenshot 3: Risk Intelligence**
- Show circuit breaker panel + emergency controls
- Highlight: "Risk controls at the center of everything"

**Screenshot 4: Trade Explainability**
- Show trade card with agents, score, risk, regime context
- Highlight: "Understand why every trade is suggested or blocked"

---

## G. Frontend Implementation Plan

### Where State for Mode and Execution Authority Should Live

**Recommended State Architecture**:

1. **Global Context: `ExecutionModeContext.jsx`**
```jsx
const ExecutionModeContext = createContext();

export function ExecutionModeProvider({ children }) {
  const [mode, setMode] = useState('MANUAL'); // 'MANUAL' | 'AUTO'
  const [autoArmed, setAutoArmed] = useState(false);
  const [accountStatus, setAccountStatus] = useState(null); // Alpaca connection
  const [circuitBreakers, setCircuitBreakers] = useState([]);
  const [riskLimits, setRiskLimits] = useState({});

  // Sync with backend
  useEffect(() => {
    fetchExecutionConfig().then(setConfig);
  }, []);

  const enableAuto = async () => { /* POST /execution/mode */ };
  const disableAuto = async () => { /* POST /execution/mode */ };
  const emergencyPause = async () => { /* POST /execution/emergency/pause */ };
  const killSwitch = async () => { /* POST /execution/emergency/kill */ };

  return (
    <ExecutionModeContext.Provider value={{
      mode, autoArmed, accountStatus, circuitBreakers, riskLimits,
      enableAuto, disableAuto, emergencyPause, killSwitch
    }}>
      {children}
    </ExecutionModeContext.Provider>
  );
}

export const useExecutionMode = () => useContext(ExecutionModeContext);
```

2. **Hook in Components**:
```jsx
function Dashboard() {
  const { mode, autoArmed, emergencyPause } = useExecutionMode();

  return (
    <div>
      <ModeBadge mode={mode} armed={autoArmed} />
      {autoArmed && <button onClick={emergencyPause}>Emergency Pause</button>}
      {mode === 'MANUAL' ? <ApprovalQueue /> : <AutoExecutionLog />}
    </div>
  );
}
```

---

### What Shared Components Should Be Created

**Priority Shared Components**:

1. **`<ModeBadge />`** - Shows MANUAL or AUTO status
```jsx
<ModeBadge mode={mode} armed={autoArmed} />
// Renders: [MANUAL] or [AUTO ARMED] with appropriate styling
```

2. **`<ExecutionAuthorityPanel />`** - Shows why Auto can/cannot execute
```jsx
<ExecutionAuthorityPanel
  mode={mode}
  canExecute={canExecute}
  blockers={blockers}
/>
// Shows list of passing/failing gates
```

3. **`<CircuitBreakerStatus />`** - Shows active circuit breakers
```jsx
<CircuitBreakerStatus breakers={circuitBreakers} />
// Shows: Loss Streak CLEAR, Drawdown CLEAR, etc.
```

4. **`<TradeApprovalCard />`** - Manual mode trade approval
```jsx
<TradeApprovalCard
  trade={trade}
  onApprove={handleApprove}
  onReject={handleReject}
/>
```

5. **`<AutoExecutionLogCard />`** - Auto mode execution record
```jsx
<AutoExecutionLogCard execution={execution} />
// Shows: time, symbol, auto✓, score, status
```

6. **`<BlockedTradeCard />`** - Explanation for blocked trades
```jsx
<BlockedTradeCard trade={trade} reason={reason} />
// Shows why trade didn't execute
```

7. **`<EmergencyControls />`** - Pause/Kill buttons
```jsx
<EmergencyControls
  onPause={emergencyPause}
  onKill={killSwitch}
/>
```

8. **`<AlpacaAccountStatus />`** - Account connection indicator
```jsx
<AlpacaAccountStatus status={accountStatus} />
// Shows: Alpaca Paper ✓ $25,000
```

9. **`<RiskBudgetGauge />`** - Portfolio heat consumed
```jsx
<RiskBudgetGauge current={15} max={25} />
// Shows: 15/25% heat consumed with gauge
```

10. **`<ModeConfirmationDialog />`** - Enable Auto confirmation
```jsx
<ModeConfirmationDialog
  open={confirmOpen}
  limits={riskLimits}
  onConfirm={enableAuto}
  onCancel={closeDialog}
/>
```

---

### What Config-Driven UI Patterns Should Be Used

**Config-Driven Risk Limits**:
```jsx
const RISK_LIMITS = [
  { key: 'maxRiskPct', label: 'Max Risk Per Trade', type: 'slider', min: 0, max: 5, step: 0.1, unit: '%' },
  { key: 'maxPositions', label: 'Max Open Positions', type: 'slider', min: 1, max: 20, step: 1, unit: '' },
  { key: 'maxDailyLoss', label: 'Max Daily Loss', type: 'input', unit: '$' },
  // ...
];

// Render dynamically
{RISK_LIMITS.map(limit => <RiskLimitControl key={limit.key} config={limit} />)}
```

**Config-Driven Circuit Breakers**:
```jsx
const CIRCUIT_BREAKERS = [
  { key: 'lossStreak', label: 'Loss Streak', threshold: 3, type: 'count' },
  { key: 'drawdown', label: 'Drawdown', threshold: -5, type: 'pct' },
  { key: 'volatility', label: 'VIX Spike', threshold: 30, type: 'value' },
  // ...
];

// Check status dynamically
{CIRCUIT_BREAKERS.map(breaker => <CircuitBreakerRow key={breaker.key} config={breaker} />)}
```

**Config-Driven Mode Behavior**:
```jsx
const MODE_CONFIGS = {
  MANUAL: {
    dashboardWidget: 'ApprovalQueue',
    tradeExecutionView: 'ApprovalFlow',
    showApproveButtons: true,
    allowAutoExecute: false,
  },
  AUTO: {
    dashboardWidget: 'AutoExecutionLog',
    tradeExecutionView: 'ExecutionLog',
    showApproveButtons: false,
    allowAutoExecute: true,
  },
};

// Use in components
const config = MODE_CONFIGS[mode];
return config.showApproveButtons ? <ApproveButton /> : null;
```

---

### Which Files to Modify First

**Phase 1: Foundation (1-2 days)**
1. Create `src/contexts/ExecutionModeContext.jsx` - Global state
2. Create `src/components/execution/ModeBadge.jsx` - Mode indicator
3. Create `src/components/execution/EmergencyControls.jsx` - Pause/Kill buttons
4. Modify `src/App.jsx` - Wrap app in ExecutionModeProvider

**Phase 2: Dashboard (2-3 days)**
5. Modify `src/pages/Dashboard.jsx` - Add mode indicator, approval queue widget, auto log widget
6. Create `src/components/execution/ApprovalQueue.jsx` - Manual mode queue
7. Create `src/components/execution/AutoExecutionLog.jsx` - Auto mode log
8. Create `src/components/execution/TradeApprovalCard.jsx` - Trade cards for Manual

**Phase 3: Settings (2-3 days)**
9. Modify `src/pages/Settings.jsx` - Add Mode & Authority tab, reorganize risk limits
10. Create `src/components/execution/ModeConfirmationDialog.jsx` - Enable Auto dialog
11. Create `src/components/execution/CircuitBreakerPanel.jsx` - Circuit breaker config

**Phase 4: Trade Execution (2 days)**
12. Modify `src/pages/TradeExecution.jsx` - Conditional Manual/Auto views
13. Create `src/components/execution/BlockedTradeCard.jsx` - Blocked trade explanations

**Phase 5: Risk Intelligence (1 day)**
14. Modify `src/pages/RiskIntelligence.jsx` - Add Auto execution status panel

**Phase 6: Integration (1-2 days)**
15. Modify `src/components/layout/Sidebar.jsx` - Promote Settings, adjust navigation
16. Update all pages to use `useExecutionMode()` hook
17. Add AlpacaAccountStatus to header

---

## H. Concrete Next Tasks

### Step-by-Step Implementation Order

#### **Week 1: Foundation & Core Components**

**Day 1: State Management**
- [ ] Create ExecutionModeContext with mode, autoArmed, account status
- [ ] Add API endpoints for mode switching (/api/execution/mode)
- [ ] Wire context provider into App.jsx

**Day 2: Shared Components (Set 1)**
- [ ] Build ModeBadge component
- [ ] Build EmergencyControls component (Pause + Kill Switch)
- [ ] Build AlpacaAccountStatus component

**Day 3: Shared Components (Set 2)**
- [ ] Build CircuitBreakerStatus component
- [ ] Build RiskBudgetGauge component
- [ ] Build ExecutionAuthorityPanel component

**Day 4: Dashboard Widgets**
- [ ] Build ApprovalQueue widget (Manual mode)
- [ ] Build AutoExecutionLog widget (Auto mode)
- [ ] Build TradeApprovalCard component

**Day 5: Dashboard Integration**
- [ ] Modify Dashboard.jsx to show mode-specific widgets
- [ ] Add mode badge to Dashboard header
- [ ] Add emergency controls to Dashboard
- [ ] Add account status to Dashboard header

---

#### **Week 2: Settings & Trade Execution**

**Day 6: Settings Redesign (Part 1)**
- [ ] Refactor Settings into tabbed interface
- [ ] Build Mode & Authority tab with toggle
- [ ] Add ModeConfirmationDialog for enabling Auto

**Day 7: Settings Redesign (Part 2)**
- [ ] Consolidate risk limits into Settings Risk tab
- [ ] Build CircuitBreakerPanel for Settings
- [ ] Add warnings for changing limits while Auto is armed

**Day 8: Trade Execution (Manual)**
- [ ] Refactor TradeExecution to conditionally show Manual vs Auto views
- [ ] Build Manual approval flow UI
- [ ] Add Approve/Reject functionality

**Day 9: Trade Execution (Auto)**
- [ ] Build Auto execution log view
- [ ] Create BlockedTradeCard component
- [ ] Add "Why Blocked" explanations

**Day 10: Integration Testing**
- [ ] Test Manual → Auto transition
- [ ] Test Auto → Manual transition
- [ ] Test Emergency Pause flow
- [ ] Test Kill Switch flow

---

#### **Week 3: Polish & Validation**

**Day 11: Risk Intelligence Integration**
- [ ] Add Auto execution status panel to RiskIntelligence
- [ ] Integrate circuit breakers with mode state
- [ ] Add "Why Auto is blocked" explanations

**Day 12: Signal Intelligence Updates**
- [ ] Add execution status to signals table
- [ ] Show "Why Blocked" column for blocked signals
- [ ] Add approve action from signals page (Manual mode)

**Day 13: Performance Analytics Updates**
- [ ] Add mode breakdown (Manual vs Auto trades)
- [ ] Show Auto eligibility status
- [ ] Link to Settings for Auto enable/disable

**Day 14: Navigation & Layout**
- [ ] Update Sidebar with new navigation structure
- [ ] Promote Settings to Execution section
- [ ] Demote MarketRegime to widget or modal

**Day 15: Final Polish**
- [ ] Add loading states for mode transitions
- [ ] Add success/error toasts for mode changes
- [ ] Test all user flows end-to-end
- [ ] Update any hardcoded references to "simulator"

---

### High-Priority Components (Build These First)

**Critical Path Components**:
1. `ExecutionModeContext` - Without this, nothing else works
2. `ModeBadge` - Visual indicator needed everywhere
3. `EmergencyControls` - Safety must be immediately accessible
4. `ModeConfirmationDialog` - Required to enable Auto safely
5. `ApprovalQueue` - Core Manual mode UX
6. `AutoExecutionLog` - Core Auto mode UX
7. `TradeApprovalCard` - Manual operator action
8. `BlockedTradeCard` - Explainability for Auto mode

**Secondary Priority**:
- CircuitBreakerStatus
- ExecutionAuthorityPanel
- AlpacaAccountStatus
- RiskBudgetGauge

---

### High-Priority Page Refactors

**Must Refactor (Week 1-2)**:
1. **Dashboard.jsx** - Add mode indicator + conditional widgets
2. **Settings.jsx** - Add Mode & Authority tab + risk consolidation
3. **TradeExecution.jsx** - Conditional Manual/Auto views

**Should Refactor (Week 3)**:
4. **RiskIntelligence.jsx** - Add Auto execution status
5. **SignalIntelligenceV3.jsx** - Add execution status + actions
6. **PerformanceAnalytics.jsx** - Add mode breakdown

**Can Defer**:
7. MarketRegime → Widget conversion (not blocking)
8. Sidebar reorganization (not blocking)

---

### Recommended Shared State Model

**Context Hierarchy**:
```
<App>
  <ExecutionModeProvider>     ← Mode, Auto, Account
    <RiskLimitsProvider>       ← Max risk, positions, heat
      <CircuitBreakerProvider> ← Active breakers
        <Router>
          <Layout>
            {pages}
          </Layout>
        </Router>
      </CircuitBreakerProvider>
    </RiskLimitsProvider>
  </ExecutionModeProvider>
</App>
```

**Or Consolidate into Single Context**:
```
<ExecutionControlContext>
  - mode (MANUAL | AUTO)
  - autoArmed (boolean)
  - accountStatus (object)
  - riskLimits (object)
  - circuitBreakers (array)
  - actions: { enableAuto, disableAuto, pause, kill }
</ExecutionControlContext>
```

**Recommended**: **Single consolidated context** for simplicity and atomic updates.

---

### API Endpoints Needed (Backend Coordination)

**Mode Management**:
- `GET /api/execution/mode` - Get current mode and status
- `POST /api/execution/mode` - Switch mode (Manual ↔ Auto)
- `POST /api/execution/emergency/pause` - Emergency pause Auto
- `POST /api/execution/emergency/kill` - Kill switch

**Execution Authority**:
- `GET /api/execution/authority` - Check if Auto can execute (gates)
- `GET /api/execution/blockers` - Get reasons Auto is blocked

**Manual Approval**:
- `POST /api/execution/approve/:signalId` - Approve trade for execution
- `POST /api/execution/reject/:signalId` - Reject trade

**Auto Execution Log**:
- `GET /api/execution/log` - Recent auto executions + blocked trades
- `GET /api/execution/audit` - Full audit trail

**Circuit Breakers**:
- `GET /api/risk/circuit-breakers` - Active breaker status
- `POST /api/risk/circuit-breakers/reset` - Reset triggered breakers

**Account Status**:
- `GET /api/alpaca/account/status` - Connection, balance, paper/live indicator

---

## Summary of Recommendations

### The Big Picture

Transform the platform from an **AI analytics dashboard** into a **trustworthy operator cockpit** by:

1. **Introducing Manual vs Auto modes as first-class concepts** throughout the UI
2. **Making execution authority always visible**: who decides (human or system)?
3. **Centralizing risk controls** in Settings as the Execution Control Plane
4. **Adding transparency to every decision**: why approved, why blocked
5. **Demoting analytics pages** that don't serve the operator's primary flow
6. **Consolidating fragmented concepts** (signals, risk, regime) into focused views

### Success Metrics

**User should be able to answer in <5 seconds**:
- ✅ What mode am I in? (Manual or Auto)
- ✅ Is Auto allowed to trade right now? (Yes/No + Why)
- ✅ What trades are pending my approval? (Manual: queue count)
- ✅ What did Auto execute today? (Auto: recent log)
- ✅ What is my current risk exposure? (% heat gauge)
- ✅ Are circuit breakers active? (CLEAR or TRIGGERED)
- ✅ How do I stop everything immediately? (Emergency Pause, Kill Switch)

**Platform feels like**:
- A professional command center, not a toy
- Operator always in control, never surprised
- Risk-first, not hype-first
- Transparent AI, not black box

---

## Appendix: Current vs Proposed Navigation

### Current Navigation (14 pages)
```
COMMAND
  - Dashboard
  - Agent Command Center
INTELLIGENCE
  - Sentiment Intelligence
  - Data Sources Monitor
  - Signal Intelligence V3
ML & ANALYSIS
  - ML Brain & Flywheel
  - Patterns
  - Backtesting
  - Performance Analytics
  - Market Regime
EXECUTION
  - Trades
  - Risk Intelligence
  - Trade Execution
SYSTEM
  - Settings
```

### Proposed Navigation (11 pages)
```
COMMAND
  - Dashboard ⭐ (mode, health, queue, stats)

EXECUTION
  - Trade Execution ⭐ (approval/log)
  - Active Trades
  - Settings / Control Plane ⭐ (mode + risk + authority)

RISK & PERFORMANCE
  - Risk Intelligence
  - Performance ⭐ (live paper results)

INTELLIGENCE
  - Signal Intelligence ⭐ (merged V3 + Patterns)

RESEARCH
  - Backtesting
  - ML Brain & Flywheel
  - Agent Management (demoted)
```

**Widgets/Demoted**:
- Market Regime → Dashboard widget
- Sentiment → Dashboard widget
- Data Sources → Settings subtab

---

**End of Report**

This design-first plan provides a clear roadmap for reorganizing the frontend around Manual and Auto modes, making execution authority and risk controls visible and trustworthy, and transforming the platform into an operator cockpit worthy of real trading decisions.
