# V3 Architecture - Embodier.ai Trading Intelligence System

## Overview
Consolidated from 18 pages down to **14 pages** for cleaner UX and maintainability.
All pages use V3 widescreen layout with lightweight-charts and real API integration.

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
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | NEEDS V3 UPDATE | YouTube Knowledge merged as tab. Needs widescreen + LW charts |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | NEEDS V3 UPDATE | API health dashboard. Needs widescreen layout |

### ML & ANALYSIS (5 pages)
| Page | File | Route | Status | Notes |
|------|------|-------|--------|-------|
| ML Brain & Flywheel | `MLInsights.jsx` | `/ml-insights` | V3 COMPLETE | ML model performance, flywheel metrics |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | NEEDS V3 UPDATE | Finviz/Alpaca screener. Needs widescreen layout |
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
| Settings | `Settings.jsx` | `/settings` | NEEDS V3 UPDATE | User preferences, API keys, notifications |

---

## V3 Completion Status

- **V3 COMPLETE: 10 pages** - Dashboard, AgentCommandCenter, Signals, MLInsights, Backtesting, PerformanceAnalytics, MarketRegime, Trades, RiskIntelligence, TradeExecution
- **NEEDS V3 UPDATE: 4 pages** - SentimentIntelligence, DataSourcesMonitor, Patterns, Settings

---

## Deleted Pages (V3 Consolidation)

These pages were removed and their functionality merged into remaining pages:

| Deleted File | Merged Into | Reason |
|-------------|-------------|--------|
| `OperatorConsole.jsx` | `AgentCommandCenter.jsx` | Redundant operator view - agent controls consolidated |
| `SignalHeatmap.jsx` | `Signals.jsx` | Heatmap added as tab within Signal Intelligence |
| `YouTubeKnowledge.jsx` | `SentimentIntelligence.jsx` | YouTube analysis merged as tab in Sentiment page |
| `StrategyIntelligence.jsx` | `Backtesting.jsx` | Strategy controls merged into Backtesting Lab |

Legacy routes (`/operator`, `/signal-heatmap`, `/youtube`, `/strategy`) redirect to their new homes.

---

## OLEH: Remaining Work to Complete V3

### Priority 1: SentimentIntelligence.jsx (HIGH)
- Convert to V3 widescreen layout (no max-width container)
- Add lightweight-charts for sentiment trend visualization
- Add YouTube Knowledge as a tab (was separate page)
- Wire to real `/api/sentiment` endpoint
- Add Unusual Whales options flow data tab

### Priority 2: Patterns.jsx (HIGH) 
- Convert to V3 widescreen layout
- Wire Finviz screener to real `/api/finviz/screener` endpoint
- Wire Alpaca asset data to real `/api/alpaca/assets` endpoint
- Add lightweight-charts for pattern visualization
- Remove any mock/fake data

### Priority 3: DataSourcesMonitor.jsx (MEDIUM)
- Convert to V3 widescreen layout
- Wire to real `/api/health` and `/api/data-sources/status` endpoints
- Add real-time WebSocket status updates
- Show OpenClaw integration status

### Priority 4: Settings.jsx (LOW)
- Convert to V3 widescreen layout
- Wire react-toastify notifications
- Add API key management
- Add user preference persistence

---

## Key V3 Design Patterns

All V3 pages follow these patterns:

1. **No max-width container** - Full widescreen `<div className="p-6 space-y-6">`
2. **Dark theme** - `bg-[#0a0a0f]` background, cyan/emerald accents
3. **Lightweight Charts** - Use `lightweight-charts` for all chart visualizations
4. **Real API calls** - Use `useApi()` hook from `../hooks/useApi`
5. **Loading states** - Skeleton loaders while data fetches
6. **Error boundaries** - Graceful error handling with retry
7. **Tab-based layout** - Use tabs for related sub-views (e.g., Signals has Scanner/Heatmap/History tabs)
8. **PageHeader component** - Consistent header with title, description, action buttons

---

## File Structure
```
frontend-v2/src/
  pages/           # 14 page components
  components/
    layout/        # Layout.jsx, Sidebar.jsx, Header.jsx
    charts/        # Shared chart components (LW Charts wrappers)
    dashboard/     # Dashboard-specific components
    ui/            # Reusable UI components (Card, Button, Badge, etc.)
  hooks/           # useApi, useWebSocket, custom hooks
  config/          # API URLs, constants
  data/            # Static data, enums
  lib/             # Utility functions
  services/        # API service layer
```

---

*Last updated: V3 consolidation commit series*
