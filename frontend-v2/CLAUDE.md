# CLAUDE.md — Embodier Trader Frontend
# React 18 + Vite 5 + TailwindCSS
# Last updated: March 14, 2026

## File Tree

```
src/
├── App.jsx                          # Router: BrowserRouter → Layout → lazy routes
├── main.jsx                         # React root mount
├── index.css                        # Tailwind directives + global styles
├── components/
│   ├── ErrorBoundary.jsx            # Top-level error boundary (wraps entire app)
│   ├── dashboard/
│   │   ├── CNSVitals.jsx            # CNS health indicators
│   │   ├── PerformanceWidgets.jsx   # P&L, Sharpe, drawdown
│   │   ├── ProfitBrainBar.jsx       # Brain activity visualization
│   │   ├── RiskWidgets.jsx          # Risk metrics
│   │   ├── SentimentWidgets.jsx     # Sentiment gauges
│   │   └── TradeExecutionWidgets.jsx# Active trade status
│   ├── layout/
│   │   ├── Layout.jsx               # CNSProvider → Sidebar + Header + Outlet + StatusFooter
│   │   ├── Sidebar.jsx              # 5-section navigation (collapsible)
│   │   ├── Header.jsx               # Top bar with WS connection status
│   │   ├── StatusFooter.jsx         # System status strip + market ticker
│   │   └── NotificationCenter.jsx   # Alert notifications overlay
│   └── ui/
│       ├── Badge.jsx
│       ├── Button.jsx
│       ├── Card.jsx
│       ├── CommandPalette.jsx       # Cmd+K command palette
│       ├── ConfirmDialog.jsx        # Modal confirmation dialog
│       ├── DataTable.jsx            # Sortable data table
│       ├── KeyboardShortcuts.jsx    # Shortcut help overlay (press ?)
│       ├── PageDataError.jsx        # Full-page error display
│       ├── PageHeader.jsx           # Page title + breadcrumbs
│       ├── PageSkeleton.jsx         # Loading skeleton placeholder
│       ├── SectionErrorBoundary.jsx # Granular error boundary for sections
│       ├── Select.jsx
│       ├── Slider.jsx
│       └── TextField.jsx
├── config/
│   └── api.js                       # Endpoint registry + getApiUrl + getWsUrl + auth headers
├── hooks/
│   ├── useApi.js                    # Universal data-fetch (polling, cache, abort, concurrency)
│   ├── cnsEvents.js                 # CNS_EVENTS constant (split for Vite Fast Refresh)
│   ├── useCNS.jsx                   # CNSProvider context + useCNS hook (WS + homeostasis)
│   ├── useKeyboardShortcuts.js      # Ctrl+1-9 nav, ? help, Ctrl+K palette
│   ├── useSentiment.js              # Sentiment-specific data aggregation
│   ├── useSettings.js               # App settings CRUD
│   └── useTradeExecution.js         # Order submission (bracket/OCO/OTO/trailing)
├── pages/
│   ├── AgentCommandCenter.jsx       # + 5 sub-tabs in agent-tabs/
│   ├── AgentCommandCenter.test.jsx
│   ├── Backtesting.jsx
│   ├── Dashboard.jsx
│   ├── Dashboard.test.jsx
│   ├── DataSourcesMonitor.jsx
│   ├── HealthDashboard.jsx          # System health overview
│   ├── MLBrainFlywheel.jsx
│   ├── MLBrainFlywheel.test.jsx
│   ├── MarketRegime.jsx
│   ├── Patterns.jsx
│   ├── PerformanceAnalytics.jsx
│   ├── RiskIntelligence.jsx
│   ├── RiskIntelligence.test.jsx
│   ├── SentimentIntelligence.jsx
│   ├── Settings.jsx
│   ├── SignalIntelligenceV3.jsx
│   ├── StartupHealth.jsx            # Startup health check page
│   ├── SymbolDetail.jsx             # Per-symbol drill-down (/symbol/:ticker)
│   ├── TradeExecution.jsx
│   ├── TradeExecution.test.jsx
│   ├── Trades.jsx
│   ├── TradingViewBridge.jsx        # TradingView chart integration
│   └── agent-tabs/
│       ├── AgentRegistryTab.jsx
│       ├── LiveWiringTab.jsx
│       ├── RemainingTabs.jsx
│       ├── SpawnScaleTab.jsx
│       └── SwarmOverviewTab.jsx
├── services/
│   ├── notifications.js             # Notification singleton (toast + in-app)
│   ├── tradeExecutionService.js     # Trade order API calls
│   └── websocket.js                 # WS client: connect/disconnect/subscribe, auto-reconnect
├── test/
│   └── setup.js                     # Vitest setup
└── utils/
    └── logger.js                    # Console logger wrapper
```

## Architecture

```
BrowserRouter
  └── ErrorBoundary (top-level crash guard)
        └── Layout (connects WS on mount)
              └── CNSProvider (React Context: homeostasis mode, circuit breaker, WS status)
                    └── LayoutInner
                          ├── Sidebar (collapsible, 5 sections, 14+ nav items)
                          ├── Header (WS connection indicator)
                          ├── <Outlet /> → Suspense → lazy-loaded page
                          ├── StatusFooter (API/WS/ML status, market ticker, agent count)
                          ├── NotificationCenter (overlay)
                          └── KeyboardShortcuts (help overlay)
```

## Critical Invariants (NEVER violate)

1. **EXPORTS**: Every `.jsx` file MUST have exactly ONE default export that is a React component. Non-component exports (constants, types, utils) MUST go in separate `.js` files. Required for Vite Fast Refresh.

2. **BACKEND DOWN**: Every component MUST render gracefully when the backend API returns errors or times out. Use loading/error states from useApi. NEVER assume API data exists — always null-check: `data?.field ?? fallback`.

3. **TRADE SAFETY**: Any function that calls `POST /orders/*`, `/metrics/auto-execute`, `/metrics/emergency-flatten`, or `/orders/flatten-all` MUST require user confirmation via ConfirmDialog before executing.

4. **HOOK RULES**: useApi uses the `fetchDataRef` pattern (NOT direct useCallback). Never create a useCallback that references a function defined later in the same scope.

5. **FILE SIZE**: No single `.jsx` file should exceed 800 lines. Extract sub-components into `src/components/{page}/`.

6. **ERROR BOUNDARIES**: CNSProvider is wrapped in CNSErrorBoundary. Each route is wrapped in PageBoundary. Never remove these.

7. **React.memo**: All dashboard widget components (`src/components/dashboard/`) use React.memo. Maintain this pattern for new components.

**Data flow:** `useApi(endpointKey)` → `config/api.js` `getApiUrl()` → Vite proxy `/api` → backend on port 8000.

**WebSocket:** `services/websocket.js` connects via `config/api.js` `getWsUrl()`. CNSProvider subscribes to WS channels for real-time homeostasis/circuit-breaker/verdict updates.

**State:** CNSProvider (via `useCNS` hook) provides system-wide state: homeostasis mode, circuit breaker armed/fired, latest council verdict, WS connection status.

**Notifications:** `services/notifications.js` singleton + react-toastify for toast popups.

## Routes (18 routes)

| Route | File | Section |
|-------|------|---------|
| `/` | → redirect to `/dashboard` | — |
| `/dashboard` | Dashboard.jsx | COMMAND |
| `/agents` | AgentCommandCenter.jsx (5 tab components) | COMMAND |
| `/agents/:tab` | AgentCommandCenter.jsx (tab param) | COMMAND |
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
| `/tradingview` | TradingViewBridge.jsx | EXECUTION |
| `/symbol/:ticker` | SymbolDetail.jsx | EXECUTION |
| `/settings` | Settings.jsx | SYSTEM |
| `/startup-health` | StartupHealth.jsx | SYSTEM |
| `/health` | HealthDashboard.jsx | SYSTEM |

All routes are lazy-loaded with `React.lazy()` + `Suspense`, wrapped in a per-page `PageBoundary` error boundary. 404 catch-all renders inline `NotFound` component.

## Startup Requirements

- **Node.js** 18+
- **Backend** must be running on port 8000 (or set `VITE_BACKEND_URL`)
- **Env vars** (optional, defaults to localhost:8001):
  - `VITE_BACKEND_URL` — backend base URL (e.g. `http://localhost:8001`)
  - `VITE_API_AUTH_TOKEN` — auth token for API headers
  - `VITE_PORT` — dev server port (default 5173)
- **Run:** `npm run dev` — Vite on port 5173, proxies `/api` → backend, `/ws` → backend WS

```bash
npm run dev     # Dev server on :5173, proxies /api + /ws → backend
npm run build   # Production build to dist/
npm run preview # Preview production build
```

## Vite Proxy

```javascript
// vite.config.js — backend default: http://localhost:8001
proxy: {
  "/api": { target: backendUrl, changeOrigin: true },
  "/ws":  { target: wsBackend, ws: true },
}
```

Path alias: `@` → `src/` (e.g. `import { useCNS } from '@/hooks/useCNS'`).

Build chunks: vendor (react/router), recharts, lightweight-charts, reactflow.

## Key Patterns

### Data Fetching — useApi

```javascript
import { useApi } from '../hooks/useApi';

const { data, loading, error } = useApi('councilLatest');           // one-shot
const { data } = useApi('signals', { pollIntervalMs: 15000 });      // polling
// NEVER use raw fetch() or mock data — always useApi with an endpoint key from config/api.js
```

- **Concurrency limiter**: max 6 simultaneous requests (prevents browser connection exhaustion)
- **Stale-while-revalidate cache**: in-memory, 200 entries, 5 min staleness
- **Per-endpoint timeouts**: 5s (signals) to 30s (backtest/council), 25s for healthz
- **Visibility-aware polling**: reduces/pauses when tab is hidden, resumes on focus

### Error Handling

- **ErrorBoundary** (top-level): catches fatal app crashes
- **PageBoundary** (per-route): catches page-level errors, preserves sidebar navigation
- **SectionErrorBoundary**: wraps critical sections (Dashboard, TradeExecution, Risk) for granular recovery without losing the whole page. Reports errors to `/api/v1/system/frontend-errors`.

### Performance

- All components in `components/dashboard/` use `React.memo` — maintain this pattern
- Pages are lazy-loaded via `React.lazy()` + `Suspense` (code-split per route)
- Build uses manual chunks: vendor, recharts, lightweight-charts, reactflow

### Accessibility

- ARIA roles on layout (`role="main"` on content area)
- Skip-to-content link (`.sr-only`) at top of Layout
- Keyboard shortcuts: `Ctrl+1-9` for page navigation, `?` for help overlay, `Ctrl+K` for command palette
- Shortcuts disabled when focus is in input/textarea/select

## Known Issues / Gotchas

1. **useApi.js `fetchData` ordering**: `fetchData` must be declared as `useCallback` BEFORE any `useEffect` that references it — React hooks order matters.
2. **DuckDB in backend is synchronous**: All DuckDB calls in async backend handlers MUST be wrapped in `asyncio.to_thread()` or they block the uvicorn event loop (causes frontend timeouts).
3. **Dashboard widgets use React.memo**: When editing `components/dashboard/*.jsx`, always maintain the `React.memo` wrapper or polling will cause unnecessary re-renders.
4. **SectionErrorBoundary usage**: Wrap critical sections (not entire pages) so one widget crash does not take down the whole view.
5. **No mock data**: Every component must use `useApi` with endpoint keys from `config/api.js`. Never hardcode URLs or use mock data.
6. **All routes inside Layout**: Every page route must be a child of `<Layout />` in App.jsx to get sidebar/header/footer.
7. **Lightweight Charts** for financial charts (not recharts for OHLC/candles). Recharts is used for bar/line/pie charts only.

## Aurora Dark Theme

- **Background**: Dark slate with glass effects (`backdrop-blur`, `bg-opacity`)
- **Primary**: Cyan (#06b6d4), Emerald (#10b981)
- **Alerts**: Amber (#f59e0b), Red (#ef4444)
- **Cards**: `rounded-md`, glass morphism
- **Headers**: ALL CAPS `text-xs` slate-400
- **Font**: JetBrains Mono for data, system sans for UI
- **TailwindCSS only** — no custom CSS unless absolutely necessary
- **Icons**: lucide-react
