# V3 Architecture - Embodier.ai Trading Intelligence System

## Overview

Consolidated from 18 pages down to **14 sidebar pages** (+ 1 hidden route) for cleaner UX and maintainability.
All pages use V3 widescreen layout with dark theme. Charting uses a mix of **lightweight-charts** (LW Charts) and **Recharts** -- migration to 100% LW Charts is in progress.

> **Current Status (Feb 27, 2026 - Deep Code Audit):** All 15 routed pages have V3 UI code.
> **7 pages still import Recharts** (see Charting Audit below). 5 pages use LW Charts. Some pages use both.
> AgentCommandCenter.jsx is the largest page (1,995 lines) with **8 internal tabs** and 5 decomposed agent components.
> **Next Step**: Complete Recharts-to-LW-Charts migration, wire real API endpoints, final UI polish, WebSocket integration.

> **IMPORTANT**: This is the AUTHORITATIVE architecture doc. Sidebar.jsx defines the 14 visible pages.
> App.jsx defines all routes including SignalIntelligenceV3 (hidden route, not in sidebar).

---

## Final 15-Route Architecture (matches App.jsx)

### COMMAND (2 pages)

| Page | File | Route | Charting | Status | Notes |
|------|------|-------|----------|--------|-------|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` | Recharts (Radar, AreaChart) + LW Charts | V3 CODED | Main overview with market cards, agent status, portfolio summary. Uses both Recharts and LW Charts |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | None (SVG only) | V3 CODED | 1,995 lines, 8 internal tabs, 5 decomposed components. See Agent Command Center section below |

### INTELLIGENCE (4 routes, 3 in sidebar)

| Page | File | Route | Charting | Status | Notes |
|------|------|-------|----------|--------|-------|
| Signal Intelligence | `Signals.jsx` | `/signals` | None | V3 COMPLETE | Velez SLAM DUNK scanner, momentum breakout, heatmap tab |
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | Recharts (PieChart) | V3 CODED - NEEDS LW CHARTS | useSentiment hook wired. PieChart from Recharts still in use |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | Recharts (PieChart) | V3 CODED - NEEDS LW CHARTS | API health dashboard. PieChart from Recharts still in use |
| Signal Intelligence V3 | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | Recharts + LW Charts | V3 CODED | **Hidden route** (not in sidebar). 1,107 lines, Kelly edge + quality columns. Uses both libraries |

### ML & ANALYSIS (5 pages)

| Page | File | Route | Charting | Status | Notes |
|------|------|-------|----------|--------|-------|
| ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | Recharts only | V3 CODED - NEEDS LW CHARTS | ML model performance, brain visualization. Still on Recharts |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | None | V3 COMPLETE | Finviz/Alpaca screener, no charts needed |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` | Recharts + LW Charts | V3 CODED | Uses both: LW Charts for equity curve/drawdown, Recharts for histograms/heatmaps |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | Recharts + LW Charts (dynamic import) | V3 CODED | Dynamic LW Charts import with Recharts fallback |
| Market Regime | `MarketRegime.jsx` | `/market-regime` | LW Charts only | V3 COMPLETE | VIX regime classification, fully on LW Charts |

### EXECUTION (3 pages)

| Page | File | Route | Charting | Status | Notes |
|------|------|-------|----------|--------|-------|
| Active Trades | `Trades.jsx` | `/trades` | None | V3 COMPLETE | Active position manager with R-Multiple tracking. 2 tabs: OPEN/CLOSED |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` | None | V3 COMPLETE | Order entry with Alpaca integration |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | None | V3 COMPLETE | Portfolio risk metrics, correlation matrix |

### SYSTEM (1 page)

| Page | File | Route | Charting | Status | Notes |
|------|------|-------|----------|--------|-------|
| Settings | `Settings.jsx` | `/settings` | None | V3 COMPLETE | API keys, preferences, system config. Multiple internal settings tabs |

---

## Agent Command Center - Deep Architecture

The Agent Command Center (`AgentCommandCenter.jsx`) is the most complex page at **1,995 lines (76.3 KB)**.
It contains **8 internal tab views** and imports **5 decomposed V3 agent components**.

### 8 Internal Tabs

| Tab ID | Label | Icon | Status | Description |
|--------|-------|------|--------|-------------|
| `overview` | Overview | Eye | Built | Regime Gauge, Swarm Status, Alerts, Consensus Engine, Agent Grid, Candidates Heatmap + V3 enhanced panels |
| `agents` | Agents | Bot | Built | Agent cards with SHAP bars + Node Control Panel table |
| `swarm` | Swarm Control | Boxes | Built | Regime Gauge + Operator Overrides (spawn/kill teams, bias slider) + Team detail cards |
| `candidates` | Candidates | Target | Built | Full ranked candidate table + symbol score heatmap |
| `alerts` | LLM Flow | Radio | Built | WebSocket LLM alert stream (max 8 alerts) |
| `brain-map` | Brain Map | Network | Placeholder | Static SVG DAG with 5 nodes (DATA, NLP, BRAIN, SIG, RISK). Needs dynamic wiring from agents array |
| `leaderboard` | Leaderboard | Trophy | Placeholder | Table with deterministic mock data (win rate, P&L, Sharpe). Needs real agent metrics |
| `blackboard` | Blackboard | ClipboardList | Placeholder | Real-Time Blackboard pub/sub feed + HITL Ring Buffer. Uses mock intervals, needs real WebSocket |

### 5 Decomposed Agent Components (`components/agents/`)

| Component | File | Used In |
|-----------|------|---------|
| Swarm Topology | `SwarmTopology.jsx` | Overview tab |
| Conference Pipeline | `ConferencePipeline.jsx` | Overview tab |
| Drift Monitor | `DriftMonitor.jsx` | Overview tab |
| System Alerts | `SystemAlerts.jsx` | Overview tab |
| Agent Resource Monitor | `AgentResourceMonitor.jsx` | Overview tab |

### Backend Endpoints Used

- `GET /api/v1/agents` - Agent list and status
- `POST /api/v1/agents/:id/start|stop` - Agent lifecycle control
- `GET /api/v1/openclaw/*` - Macro regime, swarm status, candidates, consensus
- WebSocket channels: `agents` (agent status), `llm-flow` (LLM alerts)

---

## Charting Audit (Feb 27, 2026)

### Pages Using Recharts (7 pages - MIGRATION NEEDED)

| Page | Recharts Components Used | Also Uses LW Charts? |
|------|--------------------------|----------------------|
| Dashboard.jsx | Radar, AreaChart, Area | Yes |
| SignalIntelligenceV3.jsx | AreaChart, BarChart, RadarChart, ScatterChart | Yes |
| Backtesting.jsx | Area, ScatterChart, Scatter, XAxis, YAxis, Tooltip, CartesianGrid, Legend | Yes |
| PerformanceAnalytics.jsx | CartesianGrid, Tooltip, ResponsiveContainer | Yes (dynamic import) |
| MLBrainFlywheel.jsx | Tooltip, Legend, ResponsiveContainer | No |
| SentimentIntelligence.jsx | PieChart, Pie, Cell | No |
| DataSourcesMonitor.jsx | PieChart, Pie, Cell | No |

### Pages Using LW Charts (5 pages)

| Page | LW Charts Usage |
|------|-----------------|
| MarketRegime.jsx | Direct import: createChart, ColorType |
| Dashboard.jsx | Direct import: createChart, ColorType |
| Backtesting.jsx | Direct import: createChart, ColorType, CrosshairMode |
| SignalIntelligenceV3.jsx | Direct import: createChart, CrosshairMode, LineStyle |
| PerformanceAnalytics.jsx | Dynamic import (try/catch fallback) |

### LW Charts Wrapper Components (`components/charts/`)

| Component | File | Purpose |
|-----------|------|---------|
| Data Source Sparkline | `DataSourceSparkLC.jsx` | Sparkline for data source health |
| Equity Curve | `EquityCurveChart.jsx` | Portfolio equity curve |
| Mini Chart | `MiniChart.jsx` | Small inline price charts |
| Monte Carlo | `MonteCarloLC.jsx` | Monte Carlo simulation visualization |
| Pattern Frequency | `PatternFrequencyLC.jsx` | Pattern frequency histogram |
| Risk Equity | `RiskEquityLC.jsx` | Risk-adjusted equity chart |
| Risk History | `RiskHistoryChart.jsx` | Historical risk metrics |
| Sentiment Timeline | `SentimentTimelineLC.jsx` | Sentiment over time |

### Pages With No Charts (7 pages)

Signals.jsx, AgentCommandCenter.jsx (SVG only), Trades.jsx, RiskIntelligence.jsx, TradeExecution.jsx, Settings.jsx, Patterns.jsx

---

## Pages With Internal Tabs

| Page | Tabs |
|------|------|
| AgentCommandCenter.jsx | 8 tabs: Overview, Agents, Swarm Control, Candidates, LLM Flow, Brain Map, Leaderboard, Blackboard |
| Trades.jsx | 2 tabs: OPEN, CLOSED |
| Settings.jsx | Multiple tabs: api-keys, trading, risk, notifications, appearance, etc. |

---

## V3 Completion Summary

- **V3 COMPLETE (no charts or LW Charts only):** 7 pages - Signals, MarketRegime, Trades, RiskIntelligence, TradeExecution, Settings, Patterns
- **V3 CODED (uses Recharts, needs migration):** 4 pages - SentimentIntelligence, DataSourcesMonitor, MLBrainFlywheel (Recharts only)
- **V3 CODED (hybrid Recharts + LW Charts):** 4 pages - Dashboard, Backtesting, PerformanceAnalytics, SignalIntelligenceV3
- **V3 CODED (complex, no charts):** 1 page - AgentCommandCenter (8 tabs, 3 placeholder tabs need real data)
- **TOTAL: 15 routed pages (14 in sidebar + 1 hidden)**

---

## Remaining Work to Production

1. **Recharts Migration**: Migrate 7 pages from Recharts to LW Charts (or keep Recharts PieChart for non-financial gauges)
2. **Agent Command Center**: Wire Brain Map, Leaderboard, and Blackboard tabs to real data
3. **Real API Wiring**: Connect simulated/mock data to live backend endpoints
4. **Final UI Polish**: Apply approved mockup designs (see `/docs/mockups-v3/`)
5. **WebSocket Integration**: Wire real-time data feeds where applicable

---

## Key Design Standards

- **Layout**: V3 widescreen (no cramped sidebar layouts)
- **Charts**: Migrating to lightweight-charts (LW Charts) for all financial data. Recharts still used in 7 pages
- **Styling**: Tailwind CSS with dark theme (`#0a0a0f` background, `#06b6d4` cyan accent)
- **State**: React hooks + context, no Redux
- **Routing**: React Router v6 via App.jsx (15 routes)
- **API**: useApi hook in `/hooks/`, services in `/services/`
- **Code Splitting**: React.lazy() for all page imports in App.jsx
- **Components**: Shared UI in `/components/ui/`, charts in `/components/charts/`, agents in `/components/agents/`

---

## File Structure

```
frontend-v2/src/
  components/
    agents/          # 5 decomposed agent components (SwarmTopology, ConferencePipeline, etc.)
    charts/          # 8 LW Charts wrapper components
    dashboard/       # Dashboard-specific components
    layout/          # Layout components (Sidebar, etc.)
    ui/              # Shared UI (Card, Badge, Button, DataTable, PageHeader, Slider, etc.)
  config/            # API URLs, constants
  hooks/             # useApi, useWebSocket, custom hooks
  lib/               # Utility functions
  pages/             # 15 page components (14 sidebar + 1 hidden)
  services/          # API service layer, websocket, openclawService
  App.jsx            # Router with 15 routes + lazy loading
  V3-ARCHITECTURE.md # This file - AUTHORITATIVE architecture doc
  main.jsx           # App entry point
```
