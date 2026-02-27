# V3 Architecture - Embodier.ai Trading Intelligence System

## Overview

Consolidated from 18 pages down to **14 sidebar pages** (+ 1 hidden route) for cleaner UX and maintainability.
All pages use V3 widescreen layout with lightweight-charts and real API integration.

> **Current Status (Feb 27, 2026)**: All 14 sidebar pages have V3 UI code. LW Charts migration COMPLETE for 3 remaining pages (SentimentIntelligence, DataSourcesMonitor, Patterns). PieChart kept only for non-financial SVG gauges.
> **Next Step**: Wire real API endpoints, final UI polish, WebSocket integration.

> **IMPORTANT**: This is the AUTHORITATIVE architecture doc. Sidebar.jsx defines the 14 visible pages.
> App.jsx defines all routes including SignalIntelligenceV3 (hidden route, not in sidebar).

---

## Final 14-Page Architecture (matches Sidebar.jsx)

### COMMAND (2 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` | V3 COMPLETE | Main overview with market cards, agent status, portfolio summary |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | V3 COMPLETE | WebSocket-powered agent control with real-time status |

### INTELLIGENCE (3 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Signal Intelligence | `Signals.jsx` | `/signals` | V3 COMPLETE | Velez SLAM DUNK scanner, momentum breakout, heatmap tab included |
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | V3 COMPLETE | useSentiment hook wired. LW Charts migration complete |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | V3 COMPLETE | API health dashboard. LW Charts migration complete |

### ML & ANALYSIS (5 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | V3 COMPLETE | ML model performance, brain visualization, flywheel metrics |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | V3 COMPLETE | Finviz/Alpaca screener. LW Charts migration complete |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` | V3 COMPLETE | Full backtest with LW Charts, strategy controls merged in |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | V3 COMPLETE | Real API data, equity curves, trade analysis |
| Market Regime | `MarketRegime.jsx` | `/market-regime` | V3 COMPLETE | VIX regime classification with LW Charts |

### EXECUTION (3 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Active Trades | `Trades.jsx` | `/trades` | V3 COMPLETE | Active position manager with R-Multiple tracking |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` | V3 COMPLETE | Order entry with Alpaca integration |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | V3 COMPLETE | Portfolio risk metrics, correlation matrix |

### SYSTEM (1 page)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Settings | `Settings.jsx` | `/settings` | V3 COMPLETE | API keys, preferences, system config |

### HIDDEN ROUTE (not in sidebar)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Signal Intelligence V3 | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | V3 COMPLETE | Advanced signal analysis, Kelly edge + quality columns |

```
Total: 15 routed pages (14 in sidebar + 1 hidden)
Route definitions: App.jsx
Sidebar navigation: Sidebar.jsx
Shared layout: V3 widescreen with dark theme
Chart library: lightweight-charts (LW Charts)
```

---

## V3 Completion Status

- **V3 COMPLETE (LW Charts): 13 pages** - Dashboard, AgentCommandCenter, Signals, MLBrainFlywheel, Backtesting, PerformanceAnalytics, MarketRegime, Trades, RiskIntelligence, TradeExecution, SentimentIntelligence, DataSourcesMonitor, Patterns
- **V3 COMPLETE (Settings): 1 page** - Settings
- **Hidden route: 1** - SignalIntelligenceV3
- **TOTAL: 15 routed pages (14 in sidebar + 1 hidden)**

## Legacy Redirects (in App.jsx)

| Old Route | Redirects To |
|-----------|-------------|
| `/operator` | `/agents` |
| `/signal-heatmap` | `/signals` |
| `/youtube` | `/sentiment` |
| `/strategy` | `/backtest` |
| `/signal-intelligence-v2` | `/signal-intelligence-v3` |

## Remaining Work to Production

1. **Real API Wiring**: Connect simulated/mock data to live backend endpoints
2. **Final UI Polish**: Apply approved mockup designs (see `/frontend-v2/public/assets/mockups/`)
3. **WebSocket Integration**: Wire real-time data feeds where applicable

## Key Design Standards

- **Layout**: V3 widescreen (no cramped sidebar layouts)
- **Charts**: lightweight-charts (LW Charts) for all financial data visualization
- **Styling**: Tailwind CSS with dark theme, consistent color palette
- **State**: React hooks + context, no Redux
- **Routing**: React Router v6 via App.jsx (15 routes + legacy redirects)
- **API**: useApi hook in `/hooks/`, services in `/services/`
