# V3 Architecture - Embodier.ai Trading Intelligence System

## Overview

Consolidated from 18 pages down to **14 pages** for cleaner UX and maintainability.
All pages use V3 widescreen layout with lightweight-charts and real API integration.

> **Current Status**: All 14 pages have V3 UI code written. Pages use Recharts for charting.
> **Next Step**: Migrate remaining Recharts pages to lightweight-charts (LW Charts) for production.

---

## Final 14-Page Architecture

### COMMAND (2 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` | V3 COMPLETE | Main overview with market cards, agent status, portfolio summary |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | V3 COMPLETE | WebSocket-powered agent control with real-time status |

### INTELLIGENCE (3 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Signal Intelligence | `Signals.jsx` | `/signals` | V3 COMPLETE | Velez SLAM DUNK scanner, momentum breakout, heatmap tab included |
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | V3 CODED - NEEDS LW CHARTS | YouTube Knowledge merged as tab. V3 layout done with Recharts, needs LW Charts migration |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | V3 CODED - NEEDS LW CHARTS | API health dashboard. V3 layout done with Recharts, needs LW Charts migration |

### ML & ANALYSIS (5 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| ML Brain & Flywheel | `MLInsights.jsx` | `/ml-insights` | V3 COMPLETE | ML model performance, brain visualization, flywheel metrics |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | V3 CODED - NEEDS LW CHARTS | Finviz/Alpaca screener. V3 layout done with Recharts, needs LW Charts migration |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` | V3 COMPLETE | Full backtest with LW Charts, strategy controls merged in |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | V3 COMPLETE | Real API data, equity curves, trade analysis |
| Market Regime | `MarketRegime.jsx` | `/market-regime` | V3 COMPLETE | VIX regime classification with LW Charts |

### EXECUTION (3 pages)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Active Trades | `Trades.jsx` | `/trades` | V3 COMPLETE | Active position manager with R-Multiple tracking |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | V3 COMPLETE | RiskEquityLC and MonteCarloLC wired up |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` | V3 COMPLETE | 6-Question Zone Checklist, Van Tharp position sizing |

### SYSTEM (1 page)

| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| Settings | `Settings.jsx` | `/settings` | V3 CODED - NEEDS LW CHARTS | User preferences, API keys, notifications. V3 layout done with Recharts |

## V3 Completion Status

- **V3 COMPLETE (LW Charts): 10 pages** - Dashboard, AgentCommandCenter, Signals, MLInsights, Backtesting, PerformanceAnalytics, MarketRegime, Trades, RiskIntelligence, TradeExecution
- **V3 CODED (Recharts, needs LW Charts migration): 4 pages** - SentimentIntelligence, DataSourcesMonitor, Patterns, Settings
- **TOTAL: 14/14 pages have V3 UI code**

## Remaining Work to Production

1. **LW Charts Migration (4 pages)**: Replace Recharts with lightweight-charts in SentimentIntelligence, DataSourcesMonitor, Patterns, Settings
2. **Real API Wiring**: Connect simulated/mock data to live backend endpoints
3. **Final UI Polish**: Apply approved mockup designs (see `/frontend-v2/public/assets/mockups/`)
4. **WebSocket Integration**: Wire real-time data feeds where applicable

## Key Design Standards

- **Layout**: V3 widescreen (no cramped sidebar layouts)
- **Charts**: lightweight-charts (LW Charts) for all financial data visualization
- **Styling**: Tailwind CSS with dark theme, consistent color palette
- **State**: React hooks + context, no Redux
- **Routing**: React Router v6 via App.jsx (14 routes total)
- **API**: Axios services in `/services/` directory
