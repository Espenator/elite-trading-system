# CLAUDE.md — Embodier Trader Frontend
# React 18 + Vite + TailwindCSS
# Last updated: March 12, 2026 — v4.1.0-dev

## Stack

- **Framework**: React 18 + Vite 5
- **Styling**: TailwindCSS + Aurora dark theme (glass effects, cyan/emerald/amber/red color tokens)
- **Charts**: Lightweight Charts (TradingView)
- **Icons**: lucide-react
- **Router**: react-router-dom v6 — all routes inside `<Layout />` wrapper
- **Data**: All pages use `useApi()` hook — **never raw fetch, never mock data**

## Page Routes (14 pages)

| Route | File | Section |
|-------|------|---------|
| `/dashboard` | Dashboard.jsx | COMMAND |
| `/agents` | AgentCommandCenter.jsx (+ 5 tab components) | COMMAND |
| `/signal-intelligence-v3` | SignalIntelligenceV3.jsx | INTELLIGENCE |
| `/sentiment` | SentimentIntelligence.jsx | INTELLIGENCE |
| `/data-sources` | DataSourcesMonitor.jsx | INTELLIGENCE |
| `/ml-brain` | MLBrainFlywheel.jsx | ML & ANALYSIS |
| `/patterns` | Patterns.jsx | ML & ANALYSIS |
| `/backtest` | Backtesting.jsx | ML & ANALYSIS |
| `/performance` | PerformanceAnalytics.jsx | ML & ANALYSIS |
| `/market-regime` | MarketRegime.jsx | ML & ANALYSIS |
| `/trades` | Trades.jsx | EXECUTION |
| `/risk` | RiskIntelligence.jsx | EXECUTION |
| `/trade-execution` | TradeExecution.jsx | EXECUTION |
| `/settings` | Settings.jsx | SYSTEM |

Sidebar: 5 sections (COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM) — 14 nav items.

## Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useApi` | `hooks/useApi.js` | Universal data-fetch (polling, caching, abort). ALL pages use this. |
| `useSentiment` | `hooks/useSentiment.js` | Sentiment-specific data aggregation |
| `useSettings` | `hooks/useSettings.js` | App settings CRUD |
| `useTradeExecution` | `hooks/useTradeExecution.js` | Order submission + bracket/OCO/OTO/trailing |

### useApi Pattern

```javascript
import { useApi } from '../hooks/useApi';

// Basic usage — endpoint key from config/api.js
const { data, loading, error } = useApi('councilLatest');

// With polling
const { data } = useApi('signals', { pollIntervalMs: 15000 });

// NEVER do this:
// fetch('/api/v1/signals')  ← WRONG
// const data = [{ mock: true }]  ← WRONG
```

## Components

### Layout (`components/layout/` — 5 files)
- `Layout.jsx` — Sidebar + Header + StatusFooter via `<Outlet />`
- `Sidebar.jsx` — 5-section navigation (14 items)
- `Header.jsx` — Top bar with CNS status
- `StatusFooter.jsx` — System status strip
- `NotificationCenter.jsx` — Alert notifications

### Dashboard Widgets (`components/dashboard/` — 6 files)
- `CNSVitals.jsx` — CNS health indicators
- `PerformanceWidgets.jsx` — P&L, Sharpe, drawdown
- `ProfitBrainBar.jsx` — Brain activity visualization
- `RiskWidgets.jsx` — Risk metrics
- `SentimentWidgets.jsx` — Sentiment gauges
- `TradeExecutionWidgets.jsx` — Active trade status

### Shared UI (`components/ui/` — 9 files)
Badge, Button, Card, DataTable, PageHeader, Select, Slider, TextField

## Config

- **Endpoint registry**: `src/config/api.js` — 189 endpoint definitions. ALL API URLs defined here.
- **WebSocket**: `src/services/websocket.js` — CNS channel subscriptions, auto-reconnect

## Vite Proxy Config

```javascript
// vite.config.js
proxy: {
  "/api": { target: backendUrl, changeOrigin: true },  // → :8000
  "/ws": { target: wsBackend, ws: true },               // → ws://:8000
}
```

Default port: 5173 (falls back to 5174 or 3000 if in use).

## Aurora Dark Theme

- **Background**: Dark slate with glass effects (`backdrop-blur`, `bg-opacity`)
- **Primary colors**: Cyan (#06b6d4), Emerald (#10b981)
- **Alert colors**: Amber (#f59e0b), Red (#ef4444)
- **Cards**: `rounded-md` per design system, glass morphism
- **Headers**: ALL CAPS `text-xs` slate-400
- **Font**: JetBrains Mono for data, system sans for UI

## Rules

1. **NO mock data** — every component must use `useApi`
2. **All routes inside `<Layout />`** — fixes sidebar rendering
3. **API keys from config/api.js** — never hardcode endpoints
4. **TailwindCSS only** — no custom CSS unless absolutely necessary
5. **Lightweight Charts** for financial charts (not recharts)
6. **lucide-react** for icons

## Commands

```bash
npm run dev     # Dev server on :5173, proxies /api → :8000
npm run build   # Production build to dist/
npm run preview # Preview production build
```

## Mockup Source of Truth

All design decisions reference `docs/mockups-v3/images/` (23 mockup images). See `docs/MOCKUP-FIDELITY-AUDIT.md` for pixel-by-pixel comparison.
