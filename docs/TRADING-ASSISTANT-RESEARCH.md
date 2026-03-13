# Trading Assistant Research — Deep Dive Findings

**Date**: March 12, 2026 | **Purpose**: Research compilation for Embodier Trader + TradingView dual-system trading assistant

---

## 1. TradingView ↔ Alpaca Automation — The Bridge That Matters Most

### The Problem
Embodier Trader generates signals internally. TradingView is the visual charting layer. We need a bidirectional bridge:
- **Outbound**: Embodier signals → TradingView alerts (for visual confirmation + mobile notifications)
- **Inbound**: TradingView alerts → Embodier Trader → Alpaca execution (already built: `POST /webhooks/tradingview`)

### Best Option: TradersPost as Relay Service

**TradersPost** (traderspost.io) is the most mature TradingView-to-Alpaca bridge:
- Connects TradingView alerts directly to Alpaca via webhooks
- Supports order types: market, limit, stop, bracket
- Has a free tier for basic automation
- Strategy-specific settings for risk management parameters
- No code required on their end — just webhook URL + JSON payload

**Architecture with TradersPost:**
```
Embodier Trader                    TradingView                    Alpaca
     │                                  │                            │
     │─── Morning Briefing ────────────>│ (set alerts on charts)     │
     │                                  │                            │
     │                                  │── Alert fires ──>          │
     │                                  │   (webhook POST)           │
     │                                  │       │                    │
     │                          TradersPost relay                    │
     │                                  │       │                    │
     │                                  │       └──> Alpaca order ──>│
     │                                  │                            │
     │<─── Fill notification ───────────│<─── Alpaca webhook ────────│
```

**Alternative bridges evaluated:**
- **PineConnector**: MT4/MT5 only. Dropping MT4 support Oct 2025. Not relevant for Alpaca.
- **Autoview**: Chrome extension OR webhook platform. Works with Alpaca. Good fallback.
- **SignalBridge**: Newer, lighter. TradingView → broker via webhook relay.
- **Direct DIY**: Self-hosted webhook relay (we already have `POST /webhooks/tradingview`). Most control, most maintenance.

### Recommended Path
1. **Phase 1 (now)**: Use our existing webhook endpoint + Webhook.site for testing
2. **Phase 2**: Evaluate TradersPost free tier for TradingView → Alpaca relay
3. **Phase 3**: If volume justifies, build full DIY relay with our existing infrastructure

### Webhook Payload Standard (for our outbound signals)
```json
{
  "ticker": "AAPL",
  "action": "buy",
  "price": 178.50,
  "stop_loss": 174.80,
  "take_profit": 186.60,
  "position_size_pct": 1.2,
  "order_type": "limit",
  "confidence": 0.87,
  "regime": "bull",
  "council_decision_id": "uuid-here",
  "source": "embodier_trader",
  "timestamp": "2026-03-12T09:00:00-04:00"
}
```

---

## 2. Pre-Market Analysis Routine — Data Sources & Timing

### Professional Pre-Market Workflow (Research-Backed)

The professional trader pre-market routine happens in 3 phases:

**Phase 1: Macro Scan (7:00-8:00 AM ET)**
- Futures: S&P 500 (ES), Nasdaq (NQ), Russell (RTY) — direction + magnitude
- VIX futures — volatility expectation
- Treasury yields — risk appetite signal
- Dollar index (DXY) — cross-asset correlation
- Asia/Europe session summary — overnight moves

**Phase 2: Event Calendar (8:00-8:30 AM ET)**
- Economic releases: CPI, PPI, NFP, FOMC, GDP (check FRED + economic calendar)
- Earnings before open (BMO): which watchlist stocks report today?
- Ex-dividend dates, options expiration, index rebalancing
- Congressional/insider filing alerts (Unusual Whales)

**Phase 3: Signal Synthesis (8:30-9:15 AM ET)**
- Pre-market movers: top gappers up/down (Barchart, MarketChameleon)
- Unusual options activity overnight (Unusual Whales flow data)
- Our ML signals: XGBoost scores, HMM regime, Kelly rankings
- Council pre-evaluation on top candidates

### Key Data Sources for Pre-Market

| Source | What It Provides | Already Integrated? |
|--------|-----------------|---------------------|
| Alpaca pre-market data | Quotes, bars from 4 AM ET | YES — AlpacaStreamService |
| FRED | Yield curves, VIX, macro indicators | YES — FRED API key |
| Unusual Whales | Options flow, dark pool, congressional | YES — UW API key |
| Finviz | Screener, pre-market gappers | YES — Finviz API key |
| NewsAPI | Breaking headlines | YES — NewsAPI key |
| Barchart.com | Pre-market movers, gappers | NO — web scrape only |
| Market Chameleon | Pre-market trading data | NO — requires subscription |
| CNBC/CNN pre-market | Futures, overview | NO — web search for summary |
| Earnings Whispers | Earnings calendar + expectations | NO — web search |

**Gap**: We already have 6/9 of the key data sources integrated. The remaining 3 (Barchart, Market Chameleon, Earnings Whispers) can be covered by Claude's web search capabilities in the morning briefing rather than building formal integrations.

---

## 3. AI Trading Assistant Best Practices (Industry Research)

### What the Best AI Trading Platforms Do

Research across 12+ AI trading platforms (Trade Ideas, TrendSpider, TradesViz, etc.) reveals common patterns:

**1. Modular Architecture** (confirmed — we already have this)
- One system for signal generation (our 35-agent council)
- One system for risk management (circuit breakers, Kelly sizer)
- One system for execution (OrderExecutor → Alpaca)
- One system for monitoring (planned: briefing service)

**2. Human-in-the-Loop is Non-Negotiable**
- Every major platform emphasizes human oversight
- AI suggests, human decides (especially for position sizing and timing)
- Our HITL gate is already built and is the right pattern
- Morning briefing format is better than autonomous execution

**3. Trade Ideas' "Holly" AI Pattern**
- Trade Ideas' Holly AI scans millions of data points daily before market open
- Generates a shortlist of high-probability setups
- Presents them as "ideas" not "commands"
- This is exactly what our morning briefing should do

**4. Real-Time Scanning Must Be Server-Side**
- Client-side scanning introduces latency
- Our backend MessageBus + event-driven architecture is the right approach
- Embodier Trader already processes signals server-side

### Claude-Specific Trading Assistant Capabilities

From Anthropic's own documentation and community projects:

**Claude as Morning Research Analyst:**
- Connect via MCP to Slack, Notion, Google Calendar
- Synthesize overnight data into structured briefing
- Flag earnings, macro events from calendar
- Cross-reference multiple data sources

**Claude Trading Skills (tradermonty/claude-trading-skills):**
A community project with 40+ trading skills that validates our approach. Key skills relevant to us:
- **Sector Analyst**: Rotation patterns, cyclical vs defensive scoring
- **Market Top Detector**: Distribution day counting (O'Neil method)
- **Macro Regime Detector**: Cross-asset ratio analysis
- **Portfolio Manager**: Alpaca MCP integration for real-time holdings
- **Position Sizer**: Kelly criterion + ATR + fixed fractional methods
- **Earnings Trade Analyzer**: Post-earnings scoring (5-factor system)
- **VCP Screener**: Minervini volatility contraction patterns

**What we can adopt from this project:**
- The structured skill format (we already use this)
- Economic calendar integration pattern
- Multi-factor scoring frameworks for screening
- The idea of specialized "analyst" personas for different market aspects

### Critical Guardrails (from all sources)

1. **Never auto-execute without human confirmation** — especially in live trading
2. **Always include stop-loss in every idea** — no exceptions
3. **Frame as "the system suggests" not "you should buy"** — avoid financial advice liability
4. **Paper trade new strategies for minimum 2 weeks** before live
5. **Log everything** — every signal, every decision, every outcome for post-mortem

---

## 4. Trade Journaling & Performance Review Automation

### Best-in-Class Trade Journal Features (Research)

From analyzing TradesViz, TradeFuse, Trademetria, and TraderSync:

**Must-Have Metrics Per Trade:**
- R-multiple (profit/loss expressed as multiples of initial risk)
- Time in trade (days/hours)
- Regime at entry vs exit
- Council confidence at entry
- Which agents were correct vs wrong
- Entry quality (how close to optimal)
- Exit quality (captured move % vs available move)
- Emotion/discipline tags (optional manual input)

**Must-Have Portfolio Analytics:**
- Daily/weekly/monthly P&L curve
- Sharpe ratio (rolling 30/60/90 day)
- Max drawdown (rolling + from peak)
- Win rate by regime, by direction, by sector
- Average R-multiple per trade
- Recovery factor (net profit / max drawdown)
- Agent attribution (which agents predicted correctly most often)

**Weekly Review Template:**
```
## Week of [DATE]
### Performance
- P&L: $X,XXX (+X.X%)
- Trades: X wins, X losses (XX% win rate)
- Avg R: +X.XX
- Max drawdown: X.X%
- Sharpe (30d rolling): X.XX

### Best Trade
- [SYMBOL]: +X.XR, council was 87% confident, regime GREEN
- What worked: [entry timing / thesis accuracy / exit discipline]

### Worst Trade
- [SYMBOL]: -1.0R (stopped out), council was 62% confident
- What went wrong: [regime shifted / thesis invalidated / poor timing]

### Agent Calibration
- Most accurate this week: [agent_name] (X/X correct)
- Least accurate: [agent_name] (X/X correct)
- Weight drift: [any significant Bayesian updates]

### Regime Summary
- Monday-Wednesday: GREEN (bull), full sizing
- Thursday: YELLOW transition, reduced to 50%
- Friday: Back to GREEN

### Next Week
- Earnings: [list watchlist stocks reporting]
- Macro: [FOMC / CPI / NFP if applicable]
- Open positions: [X positions, $X heat, X days avg]
```

### Building This Into Embodier Trader

The system already tracks most of this data:
- `council.verdict` events contain decision details
- `order.submitted` / `order.filled` events track execution
- `outcome.resolved` events track results
- `weight_learner.py` tracks agent accuracy via Bayesian updates
- DuckDB stores the full audit trail

**What's needed:**
1. A `BriefingService.generate_weekly_review()` method that queries DuckDB for the week's trades and council decisions
2. A `/api/v1/briefing/weekly` endpoint
3. A scheduled task for Saturday morning
4. A Slack-formatted summary posted to #trade-journal

---

## 5. Webhook.site Testing Strategy

The webhook.site URL (`https://webhook.site/6dbab002-7eca-43b8-8d92-8dd8c73495b7`) serves as our test target.

### Testing Plan
1. **Unit test**: POST a sample signal payload from backend to webhook.site, verify it arrives
2. **Integration test**: Run morning briefing → verify outbound webhook fires
3. **Format validation**: Confirm payload matches TradingView-compatible JSON
4. **Latency test**: Measure round-trip time

### Environment Variable
```
TRADINGVIEW_WEBHOOK_URL=https://webhook.site/6dbab002-7eca-43b8-8d92-8dd8c73495b7
```

When ready for production, swap to TradersPost webhook URL or our own relay.

---

## 6. Recommended Scheduled Tasks (Full Set)

| Task ID | Schedule | Purpose |
|---------|----------|---------|
| `morning-trade-briefing` | 9:00 AM ET, Mon-Fri | Top signals, regime, positions, TradingView levels |
| `midday-pulse` | 12:30 PM ET, Mon-Fri | Regime check, position review, new catalysts |
| `closing-review` | 4:15 PM ET, Mon-Fri | Day's P&L, fills, journal entries |
| `weekly-performance` | 10:00 AM ET, Saturday | Full weekly review with Sharpe, attribution, lessons |
| `week-ahead-prep` | 6:00 PM ET, Sunday | Earnings calendar, macro events, watchlist refresh |

The morning briefing is already created. The others should be added as we validate the morning routine works well.

---

## 7. Key Insights & Recommendations

### What Sets Our System Apart
Most AI trading tools are either:
- **Signal generators only** (Trade Ideas, TrendSpider) — no execution, no journaling
- **Execution bots only** (PineConnector, Autoview) — no analysis, no judgment
- **Journals only** (TradesViz, Trademetria) — no signals, no monitoring

Embodier Trader + Claude as assistant is **all three in one**, plus:
- 35-agent multi-perspective analysis (unique in the space)
- Bayesian self-learning agent weights (unique)
- Regime-adaptive everything (signal thresholds, position sizing, strategy selection)
- Full audit trail with council-level reasoning

### Biggest Risk: Over-Automation
The research consistently warns against:
- Removing human judgment from the loop
- Auto-executing without confirmation
- Trusting backtest results without live validation
- Adding complexity that breaks during volatility

**Our mitigation**: HITL gate is mandatory. Morning briefing is advisory, not auto-executing. Claude frames ideas as suggestions. Paper trading before any live changes.

### Immediate Next Steps (Priority Order)
1. **Build the briefing service backend** (the Claude Code prompt is ready)
2. **Test webhook delivery** to webhook.site with sample payloads
3. **Run the morning briefing** for 5 trading days in paper mode
4. **Evaluate**: Are the signals actionable? Are the levels accurate? Is the timing right?
5. **Iterate**: Adjust format, timing, and signal filters based on real usage

---

## Sources

- [TradersPost: Connect Alpaca to TradingView](https://blog.traderspost.io/article/how-to-connect-alpaca-to-tradingview)
- [Alpaca Forum: TradingView Webhook Solution](https://forum.alpaca.markets/t/solution-tradingview-alerts-webhook-to-alpaca-for-automated-trading/4680)
- [Alpaca: Low-Code Algo Trading with TradingView](https://alpaca.markets/learn/low-code-algorithimic-trading-on-alpaca-using-tradingview)
- [TradingView: Webhook Alert Configuration](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/)
- [Claude: Build a Daily Briefing](https://claude.com/resources/use-cases/build-a-daily-briefing-across-your-tools)
- [Claude Trading Skills (tradermonty)](https://github.com/tradermonty/claude-trading-skills)
- [LSEG: Claude Financial Skills](https://www.lseg.com/en/insights/supercharge-claudes-financial-skills-with-lseg-data)
- [PickMyTrade: Claude 4.1 Trading Guide](https://blog.pickmytrade.trade/claude-4-1-for-trading-guide/)
- [Best AI Trading Tools 2026](https://www.pragmaticcoders.com/blog/top-ai-tools-for-traders)
- [TradesViz: Free Trading Journal](https://www.tradesviz.com/)
- [TradeFuse: AI Trading Journal](https://tradefuse.app/)
- [Barchart Pre-Market Data](https://www.barchart.com/stocks/pre-market-trading)
- [PineConnector: TradingView to MT4/MT5](https://www.pineconnector.com/)
- [Autoview: TradingView Automation](https://autoview.com/broker/alpaca/)
