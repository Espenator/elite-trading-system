# Frontend Polish Audit — enhance/frontend-polish

**Date:** March 12, 2026  
**Scope:** 14 pages, Aurora dark theme, mockup source: `docs/mockups-v3/images/` (and FULL-MOCKUP-SPEC.md).

## Summary of changes

- **Loading:** Consistent `PageSkeleton` (shimmer) used as Suspense fallback for all lazy routes; optional per-page data loading skeleton via `PageSkeleton` and `PageDataError` for useApi flows.
- **Error:** Per-route `PageBoundary` (existing) with retry; `PageDataError` component for API failure + retry on pages that use it.
- **WebSocket:** Header shows green (LIVE) / yellow (RECONNECTING) / red (DOWN); useCNS exposes `wsReconnecting`; websocket emits `reconnecting` on state change.
- **Toasts:** Trade executed, circuit breaker triggered, council verdict (evaluation complete), API connection lost/restored — all via useCNS + Layout.
- **Keyboard:** Ctrl+K (Cmd+K) opens command palette; Escape closes modals/command palette; Ctrl+1–9 navigates to first 9 sidebar routes.
- **Kill Switch:** Trade Execution page — prominent header button, two-step confirmation modal, Escape to close, success/error toasts; `emergencyStop` in tradeExecutionService.
- **No mock data:** Trade Execution uses only API data; empty states for ladder, order book, news, status, positions when no data.

## 14 pages vs mockups (intentional deviations)

| # | Route | Page | Mockup reference | Match / deviations |
|---|--------|------|------------------|---------------------|
| 1 | `/dashboard` | Dashboard.jsx | 02-intelligence-dashboard | Good; loading via Suspense + optional PageSkeleton/PageDataError where useApi used. |
| 2 | `/agents` | AgentCommandCenter.jsx | 01, 05, 05b, 05c, blackboard, brain map, node control | Partial (per project_state.md); tabs and panels aligned to spec. |
| 3 | `/sentiment` | SentimentIntelligence.jsx | 04-sentiment-intelligence | Partial; heatmap/scanner polish as per existing audit. |
| 4 | `/data-sources` | DataSourcesMonitor.jsx | 09-data-sources-manager | Close. |
| 5 | `/signal-intelligence-v3` | SignalIntelligenceV3.jsx | 03-signal-intelligence | Good. |
| 6 | `/ml-brain` | MLBrainFlywheel.jsx | 06-ml-brain-flywheel | Good. |
| 7 | `/patterns` | Patterns.jsx | 07-screener-and-patterns | Good. |
| 8 | `/backtest` | Backtesting.jsx | 08-backtesting-lab | Good. |
| 9 | `/performance` | PerformanceAnalytics.jsx | 11-performance-analytics | Partial; trading grade/heatmap as per audit. |
| 10 | `/market-regime` | MarketRegime.jsx | 10-market-regime | Close. |
| 11 | `/trades` | Trades.jsx | Active-Trades.png | Close. |
| 12 | `/risk` | RiskIntelligence.jsx | 13-risk-intelligence | Partial; emergency actions present. |
| 13 | `/trade-execution` | TradeExecution.jsx | 12-trade-execution | Good; Kill Switch prominent with confirmation; no mock data; empty states. |
| 14 | `/settings` | Settings.jsx | 14-settings | Good. |

**Intentional deviations:** Per `project_state.md` and `MOCKUP-FIDELITY-AUDIT.md`, ACC Swarm Overview and some ACC tabs have structural gaps (dense panels, missing HITL tables). This polish does not restructure those; it adds loading/error patterns, WS indicator, toasts, shortcuts, and Kill Switch. Card radius/header styling and JetBrains Mono are design-system choices already documented.

## Responsive notes

- Layout uses `min-w-0`, `overflow-hidden`, and flex/grid so content scales at 1920×1080, 2560×1440, 3840×2160.
- Command palette and modals are centered and max-width constrained; no new CSS files, Tailwind only.

## Files touched

- `frontend-v2/src/App.jsx` — PageSkeleton as Suspense fallback.
- `frontend-v2/src/components/ui/PageSkeleton.jsx` — New.
- `frontend-v2/src/components/ui/PageDataError.jsx` — New (data error + retry).
- `frontend-v2/src/components/ui/CommandPalette.jsx` — New (Ctrl+K).
- `frontend-v2/src/components/layout/Layout.jsx` — Command palette state, keyboard shortcuts, API lost/restored toasts.
- `frontend-v2/src/components/layout/Header.jsx` — WS reconnecting (yellow) state.
- `frontend-v2/src/hooks/useCNS.jsx` — wsReconnecting, toasts for verdict/circuit breaker/trade.
- `frontend-v2/src/services/websocket.js` — Emit `reconnecting` on state change.
- `frontend-v2/src/services/tradeExecutionService.js` — emergencyStop.
- `frontend-v2/src/pages/TradeExecution.jsx` — Kill Switch toasts, Escape for modal, no mock data, empty states.
- `frontend-v2/tailwind.config.js` — shimmer keyframe + animation.

## Build

Run: `cd frontend-v2 && npm run build` — expect zero warnings.
