# Oleh Continuation Guide - Elite Trading System Frontend-v2

> **UPDATED Feb 25, 2026**: This guide has been completely rewritten to reflect the V3 14-page architecture. See `frontend-v2/src/V3-ARCHITECTURE.md` for the authoritative page list.

---

## Current V3 Status (Feb 25, 2026)

**14 total pages** (consolidated from original 18):
- **10 V3 COMPLETE** - Full widescreen layout, lightweight-charts, real API integration
- **4 NEED V3 UPDATE** - Still using old layout, need conversion to V3 patterns

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

### Pages Needing V3 Update (4) - YOUR PRIORITY

| Page | File | Route | What's Needed |
|------|------|-------|---------------|
| Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | Widescreen layout + LW Charts + YouTube Knowledge tab |
| Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | Widescreen layout + real health endpoints |
| Screener & Patterns | `Patterns.jsx` | `/patterns` | Widescreen layout + Finviz/Alpaca wiring |
| Settings | `Settings.jsx` | `/settings` | Widescreen layout + API key management |

---

## V3 Consolidation (What Was Merged)

4 pages were deleted and merged into existing pages:

| Deleted File | Merged Into | Reason |
|---|---|---|
| `OperatorConsole.jsx` | `AgentCommandCenter.jsx` | Redundant operator view |
| `SignalHeatmap.jsx` | `Signals.jsx` | Heatmap added as tab |
| `YouTubeKnowledge.jsx` | `SentimentIntelligence.jsx` | YouTube analysis merged as tab |
| `StrategyIntelligence.jsx` | `Backtesting.jsx` | Strategy controls merged in |

Legacy routes (`/operator`, `/signal-heatmap`, `/youtube`, `/strategy`) should redirect to new homes.

---

## Priority Tasks for Oleh

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

## V3 Design Patterns (Follow These for All Updates)

1. **No max-width container** - Full widescreen
2. **Dark theme** - `bg-[#0a0a0f]` background, cyan/emerald accents
3. **Lightweight Charts** - Use `lightweight-charts` for all chart visualizations
4. **Real API calls** - Use `useApi()` hook from `../hooks/useApi`
5. **Loading states** - Skeleton loaders while data fetches
6. **Error boundaries** - Graceful error handling with retry
7. **Tab-based layout** - Use tabs for related sub-views
8. **PageHeader component** - Consistent header with title, description, action buttons

---

## File Structure Reference

```
frontend-v2/src/
  pages/              # 14 page components
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
- `docs/mockups-v3/FULL-MOCKUP-SPEC.md` - Full mockup specifications for all pages
- `OLEH-HANDOFF.md` - Original handoff with backend wiring details
- `README.md` - Root project overview

## Quick Start

```bash
cd frontend-v2
npm install
npm run dev
```

Then visit http://localhost:5173 to see the app.
