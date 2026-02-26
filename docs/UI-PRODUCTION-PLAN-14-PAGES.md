# Embodier Trader: 14-Page UI Production Plan
## Intelligence Council Synthesis (GPT-5.2 + Claude Opus 4.6 + Gemini 3.1 Pro)
## Date: February 26, 2026

---

## 1. Design System Specifications

All 14 ultra-wide dashboard pages adhere to these strict specs:

### Resolution & Density
- **Primary Canvas:** 3840 x 2160 (4K)
- **Also supports:** 3440x1440, 5120x1440 ultra-wide
- **Density:** 10x+ data density (Bloomberg-terminal grade)
- **Format:** Flat 2D digital rendering (no 3D bezels or monitor backgrounds)

### Color Palette (Dark Mode)
- **Background Base:** Deep Slate `#0a0a0f`
- **Panel Background:** Darker Slate `#13131a`
- **Panel Borders/Dividers:** Subtle Blue-Gray `#23232f`
- **Text:** Primary White `#f8fafc`, Muted Gray `#64748b`

### Semantic Accents
- **Bullish/Active/Success:** Emerald Green `#10b981`
- **Primary Brand/Tech:** Cyan `#06b6d4`
- **Warning/Validation:** Amber `#f59e0b`
- **Bearish/Danger/Short:** Red `#ef4444`
- **Training/AI Process:** Purple `#8b5cf6`

### Typography
- **UI Text:** Clean Sans-Serif (Inter, Segoe UI, or Roboto)
- **Financial Tickers/Logs:** Monospace (Consolas, JetBrains Mono)
- **Scale:** Designed for legibility at 4K resolution

### Layout Constants
- **Left Sidebar:** 360px default, 500px expanded (workspace mode), 72px collapsed
- **Topbar Height:** ~140px with search + notifications + profile
- **Cards:** Glassmorphism, 8px rounded corners, subtle shadows
- **Tables:** TanStack Table v8 for dense virtualized data (standardized across all pages)

---

## 2. Charting Library Assignments

Three libraries mapped by intent (council unanimous agreement):

### TradingView Lightweight Charts (Canvas-based)
For intensive financial price action. High-performance HTML5 Canvas rendering.

| Page | Usage |
|------|-------|
| Intelligence Dashboard | Equity curve with benchmark overlay |
| Active Trades | Real-time candlestick + volume bars via WebSocket |
| Trade Execution | Entry/exit zone visualization on price chart |
| Signal Intelligence | Multi-timeframe price overlays |
| Backtesting Lab | Equity curve with drawdown + benchmark |
| Performance Analytics | Rolling Sharpe/equity line charts |
| Market Regime | VIX/breadth historical lines |

### Recharts (SVG-based)
For analytics, distributions, and AI transparency visuals.

| Page | Usage |
|------|-------|
| ML Brain & Flywheel | Model performance trends, training progress |
| Intelligence Dashboard | P&L distribution histogram, sector bars |
| Risk Intelligence | VaR distribution, stress test bars, radar charts |
| Performance Analytics | Attribution breakdowns, confusion matrices |
| Backtesting Lab | Walk-forward bars, Monte Carlo distribution |
| Signal Intelligence | SHAP horizontal bars, Agent Consensus Donut |
| Screener & Patterns | Pattern hit frequency, sector heatmap bars |
| Sentiment Intelligence | Sentiment shift timeline, topic distributions |
| Settings | System metrics, usage charts |

### React Flow (Node-based Diagrams)
For interactive agent/pipeline visualization.

| Page | Usage |
|------|-------|
| Agent Command Center | Swarm Brain Map with interactive agent nodes |
| Data Sources Monitor | Data ingestion pipeline topology |
| ML Brain & Flywheel | Neural network architecture diagram |

---

## 3. UI Status Matrix (14 Pages)

**Current Status: 2 Pages Completed | 12 Pages Remaining**

| # | Section | Page Name | Primary Charting Lib | Status |
|---|---------|-----------|---------------------|--------|
| 1 | COMMAND | Intelligence Dashboard | Recharts / LW Charts | DONE |
| 2 | COMMAND | Agent Command Center | React Flow | PENDING |
| 3 | INTELLIGENCE | Signal Intelligence | LW Charts / Recharts | PENDING |
| 4 | INTELLIGENCE | Sentiment Intelligence | Recharts | PENDING |
| 5 | INTELLIGENCE | Data Sources Monitor | React Flow / Recharts | PENDING |
| 6 | AI ENGINE | ML Brain & Flywheel | Recharts / React Flow | DONE |
| 7 | AI ENGINE | Screener & Patterns | Recharts / LW Charts | PENDING |
| 8 | AI ENGINE | Backtesting Lab | LW Charts / Recharts | PENDING |
| 9 | AI ENGINE | Performance Analytics | LW Charts / Recharts | PENDING |
| 10 | TRADING | Market Regime | LW Charts / Recharts | PENDING |
| 11 | TRADING | Active Trades | LW Charts | PENDING |
| 12 | TRADING | Risk Intelligence | Recharts | PENDING |
| 13 | TRADING | Trade Execution | LW Charts | PENDING |
| 14 | SYSTEM | Settings | Recharts | PENDING |

---

## 4. Per-Page Specifications

### Page 3: Agent Command Center (NEXT TO BUILD)
- **Purpose:** Central swarm intelligence hub for all AI agents
- **Key Panels:** Agent Swarm Overview grid, Task Queue, Communication Log, Performance Heatmap, Resource Utilization, Deployment Controls, Coordination Graph
- **Data Services:** Agent orchestrator, thread manager, event bus, health checks
- **Primary Lib:** React Flow (Swarm Brain Map with clickable nodes)

### Page 4: Signal Intelligence
- **Purpose:** Real-time signal generation, scoring, validation pipeline
- **Key Panels:** Stage funnel tiles (Universe > Compression > Ignition > Ranked), 50+ row signal table, Signal Detail inspector, Multi-timeframe alignment heatmap, Options flow summary, SHAP bars
- **Data Services:** `/api/v1/signals`, `/api/v1/openclaw/scores`

### Page 5: Sentiment Intelligence
- **Purpose:** News/sentiment aggregation and trading impact analysis
- **Key Panels:** Global/sector/symbol sentiment indices, News stream with badges, Sentiment shift timeline, Topic clusters, Entity recognition, Earnings risk alerts

### Page 6: Data Sources Monitor
- **Purpose:** Production SRE dashboard for trading data infrastructure
- **Key Panels:** Service health (Alpaca/Finviz/FRED/UW), Latency/error rates, Ingestion waterfall timeline, Queue metrics, Cache hit ratios, Missing data heatmap, Stale quote detection

### Page 7: Screener & Patterns
- **Purpose:** Universe filtering and pattern forensics
- **Key Panels:** Finviz-like filter builder, 100+ row results table, Pattern gallery cards, Chart with overlayed pattern regions, Pattern confidence/expectancy, Batch scan manager

### Page 8: Backtesting Lab
- **Purpose:** Strategy validation with robustness testing
- **Key Panels:** 30+ parameter strategy builder, Equity curve with benchmark/drawdown, Walk-forward windows, Monte Carlo (1000 paths), Rolling Sharpe, MAE/MFE, Kelly sizing, 40+ row trade log

### Page 9: Performance Analytics
- **Purpose:** Hedge-fund-grade portfolio analytics workstation
- **Key Panels:** Rolling Sharpe/win rate/exposure, Attribution by strategy/sector/timeframe, Edge decomposition by pattern/score/regime, Confusion matrix, Daily review checklist

### Page 10: Market Regime
- **Purpose:** Risk-on/off control room
- **Key Panels:** Regime banner (GREEN/YELLOW/RED), Input dials (VIX, breadth, yield curve, credit spreads), Allowed actions/risk caps, Stress scenarios, Transition probability matrix, Regime history timeline

### Page 11: Active Trades
- **Purpose:** Fast position management book
- **Key Panels:** 25+ row positions table (entry/stop/target/R/unrealized), Mini sparkline charts per position, Trailing stops manager, Alerts/scale-out plans, Fill log, Slippage analysis

### Page 12: Risk Intelligence
- **Purpose:** Conservative production-grade risk dashboard
- **Key Panels:** 12 KPI cards (VaR, Beta, Sortino, Calmar, Treynor, Omega), Exposure by sector/asset, Guardrails table, 15x15 correlation matrix, Monte Carlo fan chart, Stress test outcomes, Greeks per position

### Page 13: Trade Execution
- **Purpose:** No-nonsense execution terminal
- **Key Panels:** Active Setup card, Zone checklist (must-pass gates), Van Tharp sizing + capital at risk, Scale-in protocol, Order ticket with bracket orders, Pre-trade journal, Risk acceptance confirmation

### Page 14: Settings
- **Purpose:** Pro admin console
- **Key Panels:** Trading style toggles, AI trust level, Scan intervals, Risk per trade/max positions, API keys (masked) with connection tests, Notification routing (Telegram/email/webhook), Data retention, Model registry with rollback

---

## 5. UI Page Generation Workflow

### The 3-Version Pipeline

For each remaining page, generate 3 visual versions using multi-model AI:

**Stage 1: Parallel Generation**
- **Version A (Comet/Claude):** Focus on data density and information architecture
- **Version B (Gemini 2.5 Pro):** Focus on visual fidelity and chart aesthetics
- **Version C (Perplexity/Max):** Focus on interaction patterns and innovative layouts

**Stage 2: Synthesis**
- Upload V1/V2/V3 to synthesis model
- Combine best elements: layout from A, visuals from B, interactions from C
- Enforce design system consistency (colors, fonts, sidebar, density)
- Output: Final 4K PNG (3840x2160)

**Stage 3: Implementation Lock**
- Final mockup becomes the locked reference (V4 Lock)
- Generate page spec bundle: data contract + component list + acceptance checklist
- Code React component with proper library assignments
- Wire to FastAPI backend endpoints
- Commit to main branch

### Per-Page Spec Bundle (Required Before Coding)
1. **Page Spec:** Purpose, key panels, data density requirements
2. **Data Contract:** Exact API endpoints and response shapes
3. **Component Map:** Which charting lib for each panel
4. **Acceptance Checklist:** Visual fidelity, data wiring, responsive behavior

### Definition of Done (Per Page)
- [ ] 3 visual versions generated (V1/V2/V3)
- [ ] Synthesis complete (V4 final 4K mockup)
- [ ] React component coded with correct charting libraries
- [ ] Wired to FastAPI backend (zero mock data)
- [ ] Committed to main branch
- [ ] Renders correctly at 3840x2160

### Asset Naming Convention
```
frontend/assets/ui/v4/
  01_Intelligence_Dashboard_FINAL_3840x2160.png
  02_Agent_Command_Center_FINAL_3840x2160.png
  ...
  14_Settings_FINAL_3840x2160.png

frontend/assets/ui/v4/iter/
  03_Signal_Intelligence_V1.png
  03_Signal_Intelligence_V2.png
  03_Signal_Intelligence_V3.png
```

---

## 6. Council Consensus Notes

### All Models Agreed On:
- 3840x2160 (4K) with terminal-grade density
- Dark theme with cyan/emerald/amber/red accents
- LW Charts for trading, Recharts for analytics, React Flow for agent graphs
- 14-page nav with 2 done / 12 remaining
- Page-by-page workflow with repeatable pipeline and Definition of Done

### Key Disagreements Resolved:
- **Sidebar width:** Compromise = 360px default, 500px expanded, 72px collapsed
- **LW Charts vs Recharts boundary:** LW Charts for any price-action chart, Recharts for everything else
- **Pipeline ownership:** 3 parallel versions + synthesis step + V4 lock

### Unique Insights:
- **Claude:** Standardize on TanStack Table v8 for all dense tables
- **GPT-5.2:** Support 3440x1440 and 5120x1440 ultra-wide scaling

---

## 7. Next Steps

1. **BUILD Page 3: Agent Command Center** - React Flow foundations
2. **BUILD Page 4: Signal Intelligence** - LW Charts + SHAP bars
3. Continue one page at a time through the matrix
4. Each page follows: Spec > V1/V2/V3 > Synthesis > Code > Wire > Commit

---

*Generated by Intelligence Council (GPT-5.2 Thinking + Claude Opus 4.6 Thinking + Gemini 3.1 Pro)*
*Perplexity Thread: Embodier Trader Space*
*Last Updated: February 26, 2026*
