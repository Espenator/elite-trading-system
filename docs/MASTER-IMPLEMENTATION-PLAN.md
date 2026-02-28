# Master Implementation Plan - Elite Trading System

> **Created**: Feb 28, 2026 | **Status**: ACTIVE
> **Decision**: Recharts REMOVED. LW Charts + custom SVG only.

## Current State

- 15 routed pages (14 sidebar + 1 hidden)
- 11 approved mockups (07/08/09 approved Feb 28)
- CI GREEN (22 tests), FastAPI + React Vite + DuckDB
- Data: Alpaca, Unusual Whales, FinViz (NO yfinance)

## Execution Order

### PHASE 1: THE GREAT CLEANUP

#### 1A. Delete docs/mockups-v2/
- [ ] Remove entire docs/mockups-v2/ (superseded by v3)

#### 1B. Remove Dead Python Routes
- [ ] Audit/remove youtube_knowledge.py
- [ ] Audit/remove quotes.py (superseded by market.py)
- [ ] Audit/remove training.py (duplicates ml_brain.py?)
- [ ] Audit/remove strategy.py (unused by frontend?)
- [ ] Clean router includes in main.py

#### 1C. Remove Recharts Entirely
LW Charts for financial data. Custom SVG for pies/donuts.

7 pages need Recharts removed:
- [ ] Dashboard.jsx (Radar, AreaChart)
- [ ] SignalIntelligenceV3.jsx (AreaChart, BarChart, RadarChart, ScatterChart)
- [ ] Backtesting.jsx (Area, ScatterChart)
- [ ] PerformanceAnalytics.jsx (CartesianGrid, Tooltip)
- [ ] MLBrainFlywheel.jsx (Tooltip, Legend)
- [ ] SentimentIntelligence.jsx (PieChart -> SVG donut)
- [ ] DataSourcesMonitor.jsx (PieChart -> SVG donut)
- [ ] Remove recharts from package.json

---

### PHASE 2: CORE HUBS (Approved Mockups, Bad Code)

#### 2A. Dashboard.jsx -> Mockup 02 [REWRITE]
Current code does NOT match mockup. Needs:
- Top ticker bar (P&L, equity, deployed %, signals, regime, Sharpe, Kelly)
- Center grid of all 14 page thumbnails with live mini-previews
- Right panel: Top Picks donut, Agent Competition, News & Pattern Triggers
- Bottom stage status bar
Wires: market.py, portfolio.py, status.py
Effort: MAJOR REWRITE

#### 2B. AgentCommandCenter.jsx -> Mockups 01/05/05b/registry [ENHANCE]
1,995 lines, 8 tabs. 3 tabs are PLACEHOLDER with fake data:
- Brain Map: static SVG, needs dynamic agent wiring
- Leaderboard: Math.random() data, needs real /api/v1/agents metrics
- Blackboard: mock intervals, needs real WebSocket
Overview tab missing: Health Matrix dot grid, ELO table, Team Status cards
Wires: /api/v1/agents, /api/v1/openclaw/*, WebSocket
Effort: MODERATE

#### 2C. SignalIntelligenceV3.jsx -> Mockup 03 [ENHANCE]
1,107 lines. Missing:
- 14 Scanner Module toggles with sliders
- External Sensors panel (Twitter/Reddit/Discord status)
- Execution & Automation Engine panel
- ML Model Control with retrain buttons
Wires: signals.py, signal_engine.py
Effort: MODERATE

#### 2D. SentimentIntelligence.jsx -> Mockup 04 [ENHANCE]
Needs: Agent weight sliders, stock heatmap tiles, PAS regime banner,
radar chart (replace PieChart), Prediction Market panels, Scanner Status Matrix
Wires: sentiment.py
Effort: MODERATE

#### 2E. MLBrainFlywheel.jsx -> Mockup 06 [ENHANCE]
Needs: 7 KPI cards, Model Performance chart (LW), Stage 4 Probability table,
Deployed Inference Fleet (6 model cards), Flywheel Learning Log
Wires: ml_brain.py, flywheel.py
Effort: MODERATE

---

### PHASE 3: NEW INTEGRATIONS (Newly Approved Mockups)

#### 3A. DataSourcesMonitor.jsx -> Mockup 09 [REWRITE]
Current code is basic. Mockup needs:
- Top Metrics Bar (Connected count, Health %, Ingestion rate, WS status)
- AI-Powered Add Source Input with quick-add chips
- Source List with category filter tabs (ALL/Screener/Options/Market/Macro/etc)
- Right panel: Credential Editor (API key/secret, connection test)
- Supplementary sources row
Wires: data_sources.py
Effort: MAJOR REWRITE

#### 3B. Patterns.jsx -> Mockup 07 [REWRITE]
Split-panel agent-based architecture:
- Left: SCREENING ENGINE - Scanner Agent Cards, 10+ Trading Metric Controls
- Right: PATTERN INTELLIGENCE - Pattern Agent Cards, ML Metric Controls
- Bottom: Consolidated Live Feed, Pattern Arsenal, Forming Detections
- Actions: Spawn Agent, Clone, Spawn Swarm, Templates, Kill All
Wires: patterns.py, stocks.py
Effort: MAJOR REWRITE

#### 3C. Backtesting.jsx -> Mockup 08 [MAJOR ENHANCE]
Needs: Config panel, Parameter Sweeps, Regime Filter, OpenClaw integration,
16+ KPI Mega Strip, Parallel Run Manager, Monte Carlo, Parameter Heatmap,
Strategy Builder (ReactFlow), Walk-Forward Analysis, Trade Log
Wires: backtest_routes.py
Effort: MAJOR REWRITE

---

### PHASE 4: POLISH

#### 4A. Sidebar Navigation Audit
- [ ] Verify 14 visible pages with correct labels matching mockups
- [ ] Groupings: COMMAND(2) / INTELLIGENCE(3) / ML & ANALYSIS(5) / EXECUTION(3) / SYSTEM(1)
- [ ] All mockup sidebars show consistent 15-page navigation

#### 4B. Pages Without Mockups (Keep As-Is)
Performance Analytics, Market Regime, Active Trades, Risk Intelligence, Trade Execution, Settings

#### 4C. Final API Wiring
- [ ] Audit every page for mock/fake data
- [ ] Wire all useApi() hooks to real endpoints
- [ ] Test WebSocket connections

## Priority Matrix

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P0 | Remove Recharts + dead code | LOW | HIGH |
| P0 | Sidebar nav audit | LOW | HIGH |
| P1 | Dashboard.jsx rewrite | HIGH | HIGH |
| P1 | AgentCC wire real data | MOD | HIGH |
| P1 | DataSourcesMonitor rewrite | HIGH | HIGH |
| P2 | SignalIntelligenceV3 | MOD | HIGH |
| P2 | SentimentIntelligence | MOD | MED |
| P2 | MLBrainFlywheel | MOD | MED |
| P3 | Patterns.jsx rewrite | HIGH | MED |
| P3 | Backtesting.jsx rewrite | HIGH | MED |

## Rules
- NO mock data in production
- All data via useApi() or useWebSocket()
- NO yfinance
- 4-space Python indentation
- BMP unicode only in JSX
- LW Charts for financial, SVG for non-financial
- Mockups in docs/mockups-v3/images/ are source of truth
