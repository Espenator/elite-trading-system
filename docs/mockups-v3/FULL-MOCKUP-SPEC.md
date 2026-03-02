# Embodier Trader - Full Mockup Specification V3

> **UPDATED Mar 2, 2026 (9:00 AM EST)**: Consolidated to **14 sidebar pages**. Signals.jsx merged into SignalIntelligenceV3. AlignmentEngine embedded in Settings + TradeExecution. See `frontend-v2/src/V3-ARCHITECTURE.md` for authoritative architecture.
> See `frontend-v2/src/V3-ARCHITECTURE.md` for authoritative architecture.
> See `docs/UI-DESIGN-SYSTEM.md` for exact colors, fonts, spacing.

## Mockup Status

| # | Page | Mockup Image | Status |
|---|------|-------------|--------|
| 1 | Agent CC - Swarm Overview | `01-agent-command-center-final.png` | APPROVED |
| 2 | Signal Intelligence V3 | `03-signal-intelligence.png` | APPROVED |
| 3 | Sentiment Intelligence | `04-sentiment-intelligence.png` | APPROVED |
| 4 | Agent CC - Live Wiring | `05-agent-command-center.png` | APPROVED |
| 5 | Agent CC - Spawn & Scale | `05b-agent-command-center-spawn.png` | APPROVED |
| 6 | Agent CC - Agent Registry | `agent-rgistery.png` | APPROVED |
| 9 | Data Sources Manager | `09-data-sources-manager.png` | APPROVED |
| 10 | ML Brain & Flywheel | `06-ml-brain-flywheel.png` | APPROVED |
| 11 | Screener & Patterns | `07-screener-and-patterns.png` | APPROVED |
| 12 | Backtesting Lab | `08-backtesting-lab.png` | APPROVED |
| 13 | Performance Analytics | `11-performance-analytics-fullpage.png` | APPROVED |
| 14 | Market Regime | `10-market-regime-green.png`, `10-market-regime-red.png` | APPROVED |
| 15 | Active Trades | `Active-Trades.png` | APPROVED |
| 16 | Risk Intelligence | `13-risk-intelligence.png` | APPROVED |
| 17 | Trade Execution | `12-trade-execution.png` | APPROVED |
| 18 | Settings | `14-settings.png` | APPROVED |

**Process**: Generate 3 versions per page using model council (Gemini 3.1 Pro, Comet MAX, etc.). User explicitly approves each before coding.

---

## Design System (EXACT)

- BG: #0B0E14 (deep slate), Accents: Cyan #06b6d4 / Amber #F59E0B / Red #ef4444
- Fonts: Inter (UI text), JetBrains Mono (monospace data, tickers, logs)
- Resolution: 2560px+ widescreen, scrollable, maximum data density
- Every element CLICKABLE and HOTLINKED to deeper data
- V3 = Ultra-dense, every element hotlinked, 10x+ data depth

---

## Per-Page Specifications

### COMMAND

#### 1. Intelligence Dashboard (`Dashboard.jsx`, `/dashboard`)
- 20 KPI micro-cards (2 rows of 10)
- Real-time P&L ticker, multi-timeframe equity curves
- Sector rotation heatmap, agent consensus ring
- Market breadth, order flow, risk mini-panel
- News feed ticker, Flywheel status mini-ring
- Wires: market.py, portfolio.py, status.py

#### 2. Agent Command Center (`AgentCommandCenter.jsx`, `/agents`)
8 internal tabs (from approved mockup):

**Tab 1: Swarm Overview** (APPROVED MOCKUP)
- Health matrix, activity feed, topology, resource monitor, conference pipeline, drift monitor, alerts, blackboard

**Tab 2: Agent Registry** (APPROVED MOCKUP)
- Master agent table (20+ cols), agent inspector, config panel, SHAP importance, lifecycle controls

**Tab 3: Spawn & Scale** (APPROVED MOCKUP)
- Spawn orchestrator, OpenClaw control, NLP spawn prompt, template grid, custom builder, active agents table

**Tab 4: Live Wiring Map** (APPROVED MOCKUP)
- Network topology (5 columns), connection health matrix, node discovery, WebSocket channels, API route map

**Tab 5: Blackboard & Comms**
- Real-time Blackboard pub/sub feed with INSPECT hotlinks
- HITL Ring Buffer, message filtering, agent-to-agent comms

**Tab 6: Conference & Consensus**
- Conference pipeline visualization, consensus voting, agent contributions

**Tab 7: ML Ops**
- Brain map DAG, model leaderboard, training metrics, model versioning

**Tab 8: Logs & Telemetry**
- LLM flow alerts, system logs, performance telemetry, error tracking

---

### INTELLIGENCE

#### 3. Signal Intelligence (`Signals.jsx`, `/signals`)
- Velez SLAM DUNK scanner, momentum breakout scanner
- Signal heatmap, ranked signal table
- 20 signal cards with SHAP waterfall charts
- Signal correlation matrix, historical accuracy table
- Wires: signals.py, signal_engine.py

#### 4. Sentiment Intelligence (`SentimentIntelligence.jsx`, `/sentiment`)
- OpenClaw agent swarm, heatmap grid, 30-day sentiment chart
- Trade signals, radar chart, prediction market
- Scanner status matrix, sector sentiment breakdown
- Wires: sentiment.py

#### 5. Data Sources Manager (`DataSourcesMonitor.jsx`, `/data-sources`)
- API health dashboard with sparklines per source
- Data freshness indicators, latency charts
- Source configuration, rate limit tracking
- Wires: data_sources.py

#### 6. Signal Intelligence V3 (`SignalIntelligenceV3.jsx`, `/signal-intelligence-v3`)
- Hidden route (not in sidebar)
- Full EV table with Kelly edge + quality columns
- 1,107 lines, advanced signal analysis

---

### ML & ANALYSIS

#### 7. ML Brain & Flywheel (`MLBrainFlywheel.jsx`, `/ml-brain`)
- 15 post-trade autopsy cards with SHAP waterfalls
- Recursive improvement DAG, learning curves
- Retraining scheduler, model versioning timeline
- DPQ Pair Quality Matrix, HITL feedback
- Wires: ml_brain.py, flywheel.py

#### 8. Screener & Patterns (`Patterns.jsx`, `/patterns`)
- Finviz/Alpaca stock screener with configurable filters
- Pattern recognition results, chart pattern detection
- Wires: patterns.py, stocks.py

#### 9. Backtesting Lab (`Backtesting.jsx`, `/backtest`)
- Strategy builder, parameter optimization
- Equity curve (LW Charts), drawdown chart
- Sharpe/Calmar/MaxDD metrics, trade-by-trade analysis
- Monte Carlo simulation, walk-forward validation
- Wires: backtest_routes.py

#### 10. Performance Analytics (`PerformanceAnalytics.jsx`, `/performance`)
- Portfolio performance metrics, attribution analysis
- Risk-adjusted returns, benchmark comparison
- Dynamic LW Charts with Recharts fallback
- Wires: performance.py

#### 11. Market Regime (`MarketRegime.jsx`, `/market-regime`)
- VIX regime classification (GREEN/YELLOW/RED)
- HMM state visualization (LW Charts)
- Sector rotation analysis, regime history
- Wires: market.py

---

### EXECUTION

#### 12. Active Trades (`Trades.jsx`, `/trades`)
- 2 tabs: OPEN and CLOSED positions
- R-Multiple tracking, position sizing
- Real-time P&L per position
- Wires: portfolio.py, alpaca_service.py

#### 13. Risk Intelligence (`RiskIntelligence.jsx`, `/risk`)
- Portfolio risk metrics, VaR/CVaR
- Correlation matrix, exposure breakdown
- Risk Governor status (8 safety checks)
- Wires: risk.py, risk_shield_api.py

#### 14. Trade Execution (`TradeExecution.jsx`, `/trade-execution`)
- Order entry with Alpaca integration
- Order book, execution quality
- Position sizing calculator
- Wires: orders.py, alpaca_service.py

---

### SYSTEM

#### 15. Settings (`Settings.jsx`, `/settings`)
- API key management (Alpaca, Finviz, etc.)
- Trading preferences, risk parameters
- Notification settings, appearance config
- Multiple internal tabs
