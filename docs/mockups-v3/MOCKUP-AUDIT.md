# Mockup Fidelity Audit — Frontend v2 (14 Pages)

**Date:** March 12, 2026  
**Branch:** enhance/frontend-polish  
**Source of truth:** `docs/mockups-v3/FULL-MOCKUP-SPEC.md` + `docs/mockups-v3/images/` (reference PNGs)

## Summary

| # | Page | Route | Mockup reference | Status | Notes |
|---|------|--------|------------------|--------|------|
| 1 | Intelligence Dashboard | `/dashboard` | 20 KPI cards, ticker, equity, heatmap | Aligned | Real API only; loading/error states added |
| 2 | Agent Command Center | `/agents` | 01-agent-command-center-final.png, tabs | Aligned | Kill Switch in header; 5 tabs |
| 3 | Sentiment Intelligence | `/sentiment` | 04-sentiment-intelligence.png | Aligned | useApi + useSentiment |
| 4 | Data Sources Manager | `/data-sources` | 09-data-sources-manager.png | Aligned | API health, freshness |
| 5 | Signal Intelligence V3 | `/signal-intelligence-v3` | 03-signal-intelligence.png | Aligned | EV table, Kelly columns |
| 6 | ML Brain & Flywheel | `/ml-brain` | 06-ml-brain-flywheel.png | Aligned | Post-trade, DAG |
| 7 | Screener & Patterns | `/patterns` | 07-screener-and-patterns.png | Aligned | Finviz/Alpaca screener |
| 8 | Backtesting Lab | `/backtest` | 08-backtesting-lab.png | Aligned | Equity curve, LW Charts |
| 9 | Performance Analytics | `/performance` | 11-performance-analytics-fullpage.png | Aligned | Attribution, benchmarks |
| 10 | Market Regime | `/market-regime` | 10-market-regime-green/red.png | Aligned | VIX regime, HMM |
| 11 | Active Trades | `/trades` | Active-Trades.png | Aligned | OPEN/CLOSED tabs, useApi |
| 12 | Risk Intelligence | `/risk` | 13-risk-intelligence.png | Aligned | Emergency actions + confirm |
| 13 | Trade Execution | `/trade-execution` | 12-trade-execution.png | Aligned | Kill Switch added with modal; no mock data |
| 14 | Settings | `/settings` | 14-settings.png | Aligned | useSettings, useApi |

## Intentional deviations

- **Trade Execution:** Order book / news / system log show empty state when API returns no data (no placeholder rows) for production compliance.
- **All pages:** Loading uses shared shimmer skeleton; error state uses shared `PageErrorState` with retry.
- **Header:** WebSocket indicator shows three states: green (LIVE), yellow (RECONNECTING), red (DOWN).

## Pixel / layout checks

- **Resolution:** Layout tested at 1920×1080, 2560×1440, 3840×2160; grid and flex scale via Tailwind; no fixed pixel widths that break at 4K.
- **Aurora theme:** BG #111827, borders rgba(42,52,68,0.5), primary #00D9FF, emerald #10B981, amber #F59E0B, red #EF4444 — unchanged.
- **Sidebar:** 256px expanded, 64px collapsed; section labels #00D9FF; active left bar 3px.

## Data source verification

- No page uses hardcoded mock data for production content; all data via `useApi()` or specialized hooks (useSentiment, useSettings, useTradeExecution).
- Empty states show “No data” or equivalent, not fake rows.
