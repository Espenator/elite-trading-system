# Oleh Continuation Guide - Elite Trading System Frontend-v2

> **UPDATED Feb 26, 2026**: Updated to reflect 14-page architecture with all pages V3 coded. See `frontend-v2/src/V3-ARCHITECTURE.md` for the authoritative page list.

---

## Current V3 Status (Feb 26, 2026)

**14 total pages** (consolidated from original 18):

- **10 V3 COMPLETE** - Full widescreen layout, lightweight-charts, real API integration
- **4 V3 CODED (Recharts)** - V3 layout done with Recharts, need LW Charts migration
- **TOTAL: 14/14 pages have V3 UI code written**

### V3 Complete Pages (10) - NO CHANGES NEEDED

| Page | File | Route |
|------|------|-------|
| Intelligence Dashboard | `Dashboard.jsx` | `/dashboard` |
| Agent Command Center | `AgentCommandCenter.jsx` | `/agents` |
| Signal Intelligence | `Signals.jsx` | `/signals` |
| ML Brain & Flywheel | `MLInsights.jsx` | `/ml-insights` |
| Backtesting Lab | `Backtesting.jsx` | `/backtest` |
| Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` |
| Market Regime | `MarketRegime.jsx` | `/market-regime` |
| Active Trades | `Trades.jsx` | `/trades` |
| Risk Intelligence | `RiskIntelligence.jsx` | `/risk` |
| Trade Execution | `TradeExecution.jsx` | `/trade-execution` |

### Pages Needing LW Charts Migration (4) - YOUR PRIORITY

These pages already have V3 widescreen layout coded with Recharts. They need lightweight-charts migration.

| Page | File | Route | What's Needed |
|------|------|-------|---------------|
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | Replace Recharts with LW Charts + wire real API |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | Replace Recharts with LW Charts + wire health endpoints |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | Replace Recharts with LW Charts + wire Finviz/Alpaca API |
| Settings | `Settings.jsx` | `/settings` | Replace Recharts with LW Charts + wire preferences API |

## V3 Consolidation (What Was Merged)

4 pages were deleted and merged into existing pages:

| Deleted File | Merged Into | Reason |
|-------------|-------------|--------|
| `OperatorConsole.jsx` | `AgentCommandCenter.jsx` | Redundant operator view |
| `SignalHeatmap.jsx` | `Signals.jsx` | Heatmap added as tab |
| `YouTubeKnowledge.jsx` | `SentimentIntelligence.jsx` | YouTube analysis merged as tab |
| `StrategyIntelligence.jsx` | `Backtesting.jsx` | Strategy controls merged in |

Legacy routes (`/operator`, `/signal-heatmap`, `/youtube`, `/strategy`) should redirect to new homes.

## Priority Tasks for Oleh

### Priority 1: LW Charts Migration (4 pages)

For each of the 4 Recharts pages, the V3 layout is already done. The task is:

- Replace `recharts` imports with `lightweight-charts`
- Update chart components to use LW Charts API
- Wire to real backend API endpoints (replace simulated data)
- Test widescreen responsiveness

### Priority 2: Real API Wiring

- Connect all pages to live backend endpoints
- Replace `generateSimulatedData()` patterns with `useApi()` hook calls
- Wire WebSocket connections where applicable

### Priority 3: Final UI Polish

- Apply approved mockup designs from `/frontend-v2/public/assets/mockups/`
- Ensure consistent styling across all 14 pages

## V3 Design Patterns (Follow These for All Updates)

1. **No max-width container** - Full widescreen
2. **Dark theme** - `bg-[#0a0a0f]` background, cyan/emerald accents
3. **Lightweight Charts** - Use `lightweight-charts` for all chart visualizations
4. **Real API calls** - Use `useApi()` hook from `../hooks/useApi`
5. **Loading states** - Skeleton loaders while data fetches
6. **Error boundaries** - Graceful error handling with retry
7. **Tab-based layout** - Use tabs for related sub-views
8. **PageHeader component** - Consistent header with title, description, action buttons

## File Structure Reference

```
frontend-v2/src/
  pages/               # 14 page components
  components/
    layout/            # Layout.jsx, Sidebar.jsx, Header.jsx
    charts/            # Shared chart components (LW Charts wrappers)
    dashboard/         # Dashboard-specific components
    ui/                # Reusable UI (Card, Button, Badge, etc.)
  hooks/               # useApi, useWebSocket, custom hooks
  config/              # API URLs, constants
  data/                # Static data, enums
  lib/                 # Utility functions
  services/            # API service layer
```

## Key Documentation Files

- `frontend-v2/src/V3-ARCHITECTURE.md` - **AUTHORITATIVE** page architecture (14 pages)
- `frontend-v2/public/assets/mockups/` - Approved mockup designs
- `OLEH-HANDOFF.md` - Original handoff with backend wiring details
- `README.md` - Root project overview

## Quick Start

```bash
cd frontend-v2
npm install
npm run dev
```

Then visit http://localhost:5173 to see the app.
