# Trading Assistant Plan — Embodier Trader + TradingView Dual-System

**Version**: 1.0.0 | **Date**: March 12, 2026 | **Author**: Claude (Senior Engineering Partner)

---

## Executive Summary

This plan establishes Claude as an active trading assistant operating alongside Embodier Trader. The setup creates a dual-system workflow where Embodier Trader handles AI-powered signal generation and council-based decision making, while TradingView provides charting, visual confirmation, and price-level alerts. Claude orchestrates the bridge between them — delivering morning briefings, monitoring trades, performing market analysis, and pushing top ideas to TradingView.

---

## 1. Daily Schedule — The Trading Day Rhythm

### Pre-Market (7:00–9:30 AM ET)

| Time | Task | How |
|------|------|-----|
| 7:00 AM | **Overnight Scan** | Check Embodier Trader overnight signals, review any after-hours news via council's news_catalyst_agent data |
| 8:00 AM | **Market Regime Check** | Pull HMM regime state + VIX futures, FRED macro indicators. Set the day's risk posture |
| 9:00 AM | **Morning Briefing** (Scheduled Task) | Extract top 3-5 trade ideas from Embodier Trader → format for TradingView alerts → deliver Slack summary |
| 9:15 AM | **TradingView Setup** | Review Pine Script overlay alerts. Confirm entry levels, stop-loss, take-profit on charts |

### Market Hours (9:30 AM–4:00 PM ET)

| Frequency | Task | How |
|-----------|------|-----|
| Continuous | **Trade Monitoring** | Watch council verdicts, order fills, position P&L via WebSocket channels |
| Every 30 min | **Quick Pulse** | Check portfolio heat, regime shifts, any VETO triggers |
| On signal | **New Signal Review** | When signal.generated fires, review council reasoning + confidence |
| On fill | **Execution Confirmation** | Verify fills, confirm bracket orders set, update TradingView annotations |
| 12:00 PM | **Midday Check** | Reassess morning positions. Any regime changes? New catalysts? |

### Post-Market (4:00–6:00 PM ET)

| Time | Task | How |
|------|------|-----|
| 4:15 PM | **Close Review** | Pull day's trades, P&L, Brier calibration updates |
| 4:30 PM | **Trade Journal** | Document each trade: entry reasoning, council verdict, outcome, lessons |
| 5:00 PM | **Next-Day Prep** | Scan for earnings, macro events, expiring alerts. Update watchlist |

### Weekend

| Task | When |
|------|------|
| Weekly performance review | Saturday morning |
| Walk-forward validation check | Saturday |
| Strategy parameter review | Sunday evening |
| Week-ahead macro calendar | Sunday evening |

---

## 2. The 9 AM Morning Briefing — Core Routine

This is the centerpiece. Every trading day at 9:00 AM ET, Claude runs a scheduled task that:

### Step 1: Pull Embodier Trader Data
```
GET /api/v1/signals/kelly-ranked         → Top signals by edge × quality
GET /api/v1/council/latest               → Most recent council verdicts
GET /api/v1/market/regime                → Current HMM regime state
GET /api/v1/risk/portfolio-heat          → Current exposure
GET /api/v1/positions/                   → Open positions
```

### Step 2: Filter & Rank
- Only signals with score ≥ regime-adaptive threshold (55/65/75)
- Only confidence ≥ 0.4 (medium+ conviction)
- Exclude symbols with active positions (no doubling up)
- Rank by: Kelly edge × confidence × regime suitability
- Take top 3-5 ideas

### Step 3: Format for TradingView
For each trade idea, generate:
```
Symbol: AAPL
Direction: LONG
Entry Zone: $178.50 - $179.20 (limit)
Stop Loss: $174.80 (2x ATR = $3.70)
Target 1: $186.60 (2R)
Target 2: $190.30 (3R, trail)
Position Size: 1.2% ($X,XXX)
Council Confidence: 87%
Key Agents: regime(bull), momentum(0.82), flow(0.79)
Regime: GREEN (bull) — full sizing allowed
```

### Step 4: Deliver
- **Slack**: Post formatted briefing to #trade-alerts
- **TradingView**: Create/update alerts via webhook to TradingView Alerts bot
- **Summary**: Human-readable morning note with market context

---

## 3. TradingView Integration Architecture

### Current State
- **Inbound**: TradingView Alerts Slack bot (A0AFQ89RVEV) exists — can receive TradingView webhooks
- **Inbound endpoint**: `POST /webhooks/tradingview` processes alerts as `signal.external` events
- **Outbound**: No mechanism to push FROM Embodier TO TradingView yet

### Integration Options (Ranked)

#### Option A: Pine Script Signal Overlay (Recommended)
Create a custom Pine Script indicator that reads from an external JSON data source and plots entry/exit levels on TradingView charts.

**How it works:**
1. Embodier Trader publishes daily signals to a simple JSON endpoint (public or token-gated)
2. Pine Script indicator fetches this data via `request.security()` or manual input
3. Indicator plots entry zones, stop-loss lines, and target levels on the chart
4. `alertcondition()` triggers when price enters the entry zone

**Pros**: Real-time chart overlay, native TradingView alerts, visual confirmation
**Cons**: Pine Script can't make HTTP requests — requires a bridge (see below)

#### Option B: Manual Morning Setup (Simplest — Start Here)
Claude generates the briefing, Espen manually sets alerts in TradingView based on the levels.

**How it works:**
1. 9 AM scheduled task delivers briefing to Slack
2. Briefing includes exact levels: entry, stop, targets
3. Espen opens TradingView, draws levels, sets alerts
4. Takes ~5 min per symbol, ~15-25 min for 3-5 ideas

**Pros**: Zero new infrastructure, full human control, start immediately
**Cons**: Manual work each morning, possible to miss or mistype levels

#### Option C: TradingView Webhook Bridge (Future)
Build a small bridge service that pushes alerts INTO TradingView.

**How it works:**
1. New endpoint on Embodier Trader: `POST /api/v1/tradingview/push-signals`
2. Service creates TradingView alerts programmatically (requires TradingView Premium API access or third-party bridge like PineConnector/WebhookTrade)
3. Alerts auto-fire when price hits entry zones

**Pros**: Fully automated, zero manual work
**Cons**: Requires TradingView API access or third-party service, additional cost

### Recommended Rollout
1. **Phase 1 (Now)**: Option B — manual setup with Claude's morning briefing
2. **Phase 2 (Week 2-3)**: Pine Script indicator that visually displays Embodier signal levels
3. **Phase 3 (Month 2)**: Evaluate automated bridge if manual process is too slow

---

## 4. Trade Monitoring & Review

### What Claude Monitors

#### Active Position Tracking
```
For each open position:
- Current P&L (unrealized)
- Distance to stop-loss (in R-multiples)
- Distance to target
- Time in trade (vs 23-day max)
- Regime alignment (still favorable?)
- Any new council signals (contradicting?)
```

#### Risk Dashboard
```
Portfolio-level:
- Total portfolio heat (target: ≤ 8%)
- Sector concentration
- Correlation cluster risk
- Drawdown from peak
- Daily P&L
```

#### Alert Triggers (Claude flags these immediately)
- Position hits 1R profit → suggest trailing stop
- Position hits stop-loss → confirm exit, log lesson
- Regime change → reassess all positions
- VETO triggered → immediate attention
- Portfolio heat > 6% → warn before new trades
- Circuit breaker activated → full stop, assess
- Council confidence drops below 0.3 on existing position → flag for review

### Trade Review Process

After each trade closes:

1. **Outcome**: Win/Loss, R-multiple achieved
2. **Council Accuracy**: Did the council direction match the outcome?
3. **Agent Attribution**: Which agents were most accurate? (feeds weight learner)
4. **Entry Quality**: How close to optimal entry? Slippage?
5. **Exit Quality**: Did we capture the move? Left money on table?
6. **Lessons**: One sentence — what would we do differently?

---

## 5. Market Analysis — When and What

### Daily Analysis Points

| Time | Analysis | Data Sources |
|------|----------|-------------|
| Pre-market | Overnight gap scan, futures, Asia/Europe session | Alpaca pre-market, FRED, NewsAPI |
| 9:00 AM | Full regime + sector analysis, top ideas | All 10 data sources via council |
| 10:30 AM | First-hour review: which signals triggered? | Alpaca real-time, council verdicts |
| 12:00 PM | Midday regime check, sector rotation | HMM, Unusual Whales flow |
| 3:30 PM | Power hour prep: any late-day setups? | Signal engine, flow data |
| 4:15 PM | Day close analysis | Full portfolio review |

### Weekly Analysis

| Day | Analysis |
|-----|----------|
| Monday | Week-ahead calendar: earnings, FOMC, employment data |
| Wednesday | Mid-week review: how are positions tracking? |
| Friday | Weekly P&L, Sharpe tracking, weight learner review |
| Weekend | Deep backtest review, parameter validation |

### What Claude Analyzes

1. **Macro Regime**: VIX, yield curve, put/call ratio, sector rotation
2. **Signal Quality**: Hit rate of recent signals, confidence calibration
3. **Council Performance**: Agent Brier scores, weight drift, consensus levels
4. **Flow Data**: Unusual options activity, dark pool prints, institutional accumulation
5. **News Catalysts**: Earnings surprises, macro announcements, geopolitical events
6. **Technical Levels**: Key S/R on indices (SPY, QQQ), breadth indicators

---

## 6. Dual-System Synergy — How They Work Together

```
┌─────────────────────────────────────┐
│         EMBODIER TRADER              │
│  (AI Signal Engine + 35-Agent DAG)   │
│                                      │
│  Strengths:                          │
│  · ML-powered signal scoring         │
│  · Multi-agent consensus             │
│  · Risk management automation        │
│  · Kelly position sizing             │
│  · Backtest validation               │
│  · 10 data sources                   │
└──────────────┬───────────────────────┘
               │ Morning Briefing (9 AM)
               │ Signal levels, stops, targets
               ▼
┌─────────────────────────────────────┐
│          TRADINGVIEW                 │
│  (Charting + Visual Alerts)          │
│                                      │
│  Strengths:                          │
│  · Best-in-class charting            │
│  · Pattern recognition (visual)      │
│  · Multi-timeframe analysis          │
│  · Community indicators              │
│  · Price alerts at exact levels      │
│  · Mobile notifications              │
└──────────────┬───────────────────────┘
               │ Entry Alert Fires
               │ (price hits entry zone)
               ▼
┌─────────────────────────────────────┐
│         EXECUTION DECISION           │
│                                      │
│  · Embodier council said BUY 87%     │
│  · TradingView chart confirms setup  │
│  · Claude verifies regime + risk     │
│  · → Execute via Alpaca              │
└─────────────────────────────────────┘
```

### When Systems Agree → High Conviction
Both Embodier's AI and TradingView's visual analysis point the same direction. Full Kelly sizing.

### When Systems Disagree → Caution
Embodier says BUY but TradingView chart shows resistance / bearish divergence. Reduce size or skip.

### TradingView as Visual Confirmation Layer
Embodier is quantitative; TradingView adds qualitative visual confirmation:
- Is the entry zone at a clean support/resistance level?
- Does the chart pattern support the trade direction?
- Are there bearish divergences the ML might miss?
- How does volume profile look at the entry zone?

---

## 7. Scheduled Task: Morning Trade Briefing

### Task Configuration
```
Task ID: morning-trade-briefing
Schedule: 9:00 AM ET, weekdays only (Mon-Fri)
Cron: 0 9 * * 1-5 (Eastern Time)
```

### Task Prompt (what Claude executes each morning)
```
You are Espen's trading assistant at Embodier.ai. It is now 9:00 AM ET on a trading day.

Perform the following morning briefing routine:

1. CHECK REGIME
   - Query the Embodier Trader backend at http://localhost:8000/api/v1/market/regime
   - Report current HMM state (bull/bear/sideways/crisis)
   - Note VIX level and any regime transitions

2. REVIEW OPEN POSITIONS
   - Query http://localhost:8000/api/v1/positions/
   - For each position: current P&L, distance to stop, time in trade
   - Flag any positions needing attention (near stop, time limit, regime change)

3. PULL TOP SIGNALS
   - Query http://localhost:8000/api/v1/signals/kelly-ranked
   - Filter: score ≥ regime threshold, confidence ≥ 0.4
   - Rank by Kelly edge × confidence
   - Select top 3-5 new ideas (exclude symbols with open positions)

4. FORMAT TRADE IDEAS FOR TRADINGVIEW
   For each idea:
   - Symbol, Direction (LONG/SHORT)
   - Entry zone (price range)
   - Stop-loss level (ATR-based)
   - Target 1 (2R) and Target 2 (3R)
   - Position size as % of portfolio
   - Council confidence and key agent signals

5. DELIVER BRIEFING
   - Post summary to Slack #trade-alerts channel
   - Include: regime status, open position review, new ideas
   - Format: clean, scannable, with emoji indicators

6. FLAG CALENDAR EVENTS
   - Check for earnings reports on watchlist stocks today
   - Note any FOMC, employment, CPI, or other macro events
   - Warn if any open positions have earnings this week
```

---

## 8. Pine Script: Embodier Signal Overlay (Phase 2)

A custom Pine Script indicator to display Embodier's trade ideas on TradingView charts.

### Concept
```pine
//@version=5
indicator("Embodier Signals", overlay=true)

// Input: Signal levels (updated manually or via alert message)
entryLong  = input.float(0.0, "Long Entry")
stopLoss   = input.float(0.0, "Stop Loss")
target1    = input.float(0.0, "Target 1 (2R)")
target2    = input.float(0.0, "Target 2 (3R)")
direction  = input.string("none", "Direction", options=["long", "short", "none"])

// Plot levels
plot(direction != "none" ? entryLong : na, "Entry", color=color.blue, linewidth=2)
plot(direction != "none" ? stopLoss : na, "Stop", color=color.red, linewidth=2)
plot(direction != "none" ? target1 : na, "T1 (2R)", color=color.green, linewidth=1)
plot(direction != "none" ? target2 : na, "T2 (3R)", color=color.lime, linewidth=1)

// Alert when price enters entry zone
longEntry = direction == "long" and close <= entryLong and close >= entryLong * 0.997
shortEntry = direction == "short" and close >= entryLong and close <= entryLong * 1.003

alertcondition(longEntry, "Long Entry Zone", "EMBODIER: Price in LONG entry zone")
alertcondition(shortEntry, "Short Entry Zone", "EMBODIER: Price in SHORT entry zone")
```

### Usage Flow
1. Morning briefing provides levels per symbol
2. Espen opens each chart in TradingView
3. Updates the Embodier Signal indicator inputs with the levels
4. Enables alerts — TradingView notifies when price hits entry zone
5. On alert: verify with Embodier council, then execute via Alpaca

---

## 9. Implementation Roadmap

### Week 1: Foundation
- [x] Document this plan
- [ ] Create scheduled task for 9 AM morning briefing
- [ ] Test morning briefing with paper trading data
- [ ] Establish Slack channel structure (#morning-briefing, #trade-alerts, #trade-journal)
- [ ] Manual TradingView alert setup for first trade ideas

### Week 2-3: Refinement
- [ ] Fine-tune briefing format based on real usage
- [ ] Create Pine Script signal overlay indicator
- [ ] Add post-market review to scheduled tasks
- [ ] Build trade journal template

### Month 2: Automation
- [ ] Evaluate TradingView webhook bridge options
- [ ] Add midday and power-hour check-in tasks
- [ ] Weekly performance report automation
- [ ] Backtest comparison: Embodier-only vs dual-system decisions

### Month 3: Optimization
- [ ] Track signal-to-trade conversion rate
- [ ] Measure value-add of TradingView visual confirmation
- [ ] Optimize morning briefing timing (8:30 AM vs 9:00 AM)
- [ ] Consider TradingView Premium for programmatic alerts

---

## 10. How Claude Can Best Help

Based on research and the system's capabilities, here's where Claude adds the most value:

### High-Value Activities
1. **Morning briefing synthesis** — Combining 10 data sources + 35 agents into actionable trade ideas
2. **Risk monitoring** — Continuous portfolio heat, regime shift, and VETO tracking
3. **Trade journaling** — Documenting every trade with council reasoning and outcome analysis
4. **Pattern recognition** — Spotting when council agents are miscalibrated or when regime transitions are forming
5. **Second opinion** — When Espen is unsure, Claude can walk through the pre-trade checklist methodically

### Medium-Value Activities
6. **Calendar awareness** — Flagging earnings, FOMC, macro events that affect open positions
7. **TradingView setup** — Generating exact levels for quick alert configuration
8. **Weekly reviews** — Sharpe tracking, weight learner performance, strategy drift detection
9. **What-if analysis** — "What if I add this position? How does heat change?"

### Lower-Value (But Still Useful)
10. **Code maintenance** — Keeping the system running, fixing bugs, adding features
11. **Documentation** — Updating skills, project docs, trading journal entries
12. **Research** — New signal sources, strategy ideas, ML improvements

### What Claude Should NOT Do
- Make autonomous trading decisions without Espen's confirmation
- Override council verdicts based on "gut feel"
- Increase position sizes beyond Kelly recommendations
- Trade during circuit breaker or CRISIS regime without explicit approval
- Provide specific investment advice (always frame as "the system suggests" not "you should")

---

## Appendix: Key API Endpoints for Morning Briefing

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/v1/signals/kelly-ranked` | GET | Top signals ranked by Kelly edge × quality |
| `/api/v1/council/latest` | GET | Most recent council decision |
| `/api/v1/council/evaluate` | POST | Run full council evaluation for a symbol |
| `/api/v1/market/regime` | GET | Current HMM regime state |
| `/api/v1/risk/portfolio-heat` | GET | Current portfolio exposure |
| `/api/v1/positions/` | GET | Open positions |
| `/api/v1/signals/active/{symbol}` | GET | Active signal with entry/stop/target |
| `/api/v1/council/calibration` | GET | Agent Brier score calibration |
| `/api/v1/council/weights` | GET | Current Bayesian agent weights |

## Appendix: Signal Output Format

```json
{
  "symbol": "AAPL",
  "score": 82,
  "direction": "buy",
  "confidence": 0.87,
  "kelly_fraction": 0.012,
  "entry_zone": [178.50, 179.20],
  "stop_loss": 174.80,
  "target_1": 186.60,
  "target_2": 190.30,
  "regime": "bull",
  "council_decision_id": "uuid",
  "top_agents": ["regime(1.2)", "momentum(0.82)", "flow(0.79)"],
  "risk_notes": "Portfolio heat at 4.2%, sector OK, no earnings this week"
}
```
