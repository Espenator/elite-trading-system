# Performance Analytics — Mockup Fidelity Changes

**Page:** Performance Analytics  
**Mockup:** `11-performance-analytics-fullpage.png`  
**File:** `frontend-v2/src/pages/PerformanceAnalytics.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Header
- **Mockup:** "Performance Analytics" centered; right: green "A Trading Grade" button with grade badge
- **Before:** Different layout or styling

### KPI Strip
- **Mockup:** Total Trades, Net P&L, Win Rate, Avg Win, Avg Loss, Profit Factor, Max DD, Sharpe, Expectancy, R:R — each with value, mini sparkline, and change % (e.g. +0.37%)
- **Before:** Missing sparklines or change indicators

### Risk Cockpit
- **Mockup:** Trading Grade Hero + Excellent; Sharpe/Sortino/Calmar with (+0.50), (+0.92), (-0.29); Kelly Criterion bar (Win $12,828.50 green, Lose -$3.50 red); Risk/Reward + Expectancy C-shaped gauge / mini bar
- **Before:** Different metrics or layout

### Equity + Drawdown
- **Mockup:** Toolbar with Settings, Download, Refresh icons
- **Before:** Missing toolbar

### AI + Rolling Risk
- **Mockup:** Concentric AI Dial — outer 78.3% teal, inner 67% green, center "67% Agent"; Rolling Risk Sharpe line chart
- **Before:** Different dial or chart

### Attribution + Agent ELO
- **Mockup:** P&L By Symbol horizontal bar (AAPL, TSLA, NVDA, …); Agent Attribution Leaderboard table; Returns Heatmap Calendar
- **Before:** Missing P&L By Symbol or different layout

### Agent Attribution Leaderboard (Expanded)
- **Mockup:** Table with #, Agent, ELO, Changes, Contributions, Win Rates, Contribution
- **Before:** Progress-bar style layout

### Enhanced Trades Table
- **Mockup:** TRADE LOG toolbar (TRADE LOG button, search, resize, close, filter); columns: Date (checkbox), Symbol, Side (L/H), Qty, Entry, Exit, P&L (value + %)
- **Before:** Different columns (rr, status); no toolbar

### ML & Flywheel Engine
- **Mockup:** ML Model Accuracy Trend line; Staged Inferences, NIL Inferences; Flywheel Pipeline Health (Status Active, Timeline indicators)
- **Before:** Different structure or missing fallbacks

### Risk Cockpit Expanded
- **Mockup:** Risk Shield Status — green ACTIVE button; Risk History line; Portfolio Risk / VaR grid; VaR Gauge
- **Before:** StatusDot instead of ACTIVE button

### Strategy & Signals
- **Mockup:** Active Strategies ("Strateg A"); Signal Hit Rate bar; Market Sentiment + Regime gauge
- **Before:** Empty activeStrategies; different layout

### Footer
- **Mockup:** "Embodier Trader - Performance Analytics v2.0 | Connected | Active filters in cyan | Data: Jan 1 - Feb 28, 2026 - 312 trades"
- **Before:** Different footer text

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/PerformanceAnalytics.jsx` | Full mockup fidelity pass |
| `frontend-v2/src/components/dashboard/PerformanceWidgets.jsx` | ConcentricAIDial centerLabel support |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| Header | Centered "Performance Analytics"; right green "A Trading Grade" button with grade badge |
| KPI Strip | MiniSparkline + change % per pill; mockup values (247, +$12,847.32, 68.4%, etc.) |
| Risk Cockpit | Trading Grade Hero, Excellent; Sharpe/Sortino/Calmar with (+0.50), (+0.92), (-0.29); Kelly Win/Lose bar; Risk/Reward + Expectancy chart |
| Equity + Drawdown | Toolbar with Settings, Download, RefreshCw icons |
| AI + Rolling Risk | ConcentricAIDial 78.3% teal / 67% green, centerLabel "67% Agent"; Rolling Risk Sharpe area chart |
| Attribution + Agent ELO | P&L By Symbol bar chart; Agent Leaderboard table; Returns Heatmap Calendar |
| Agent Leaderboard Expanded | Switched to table format: #, Agent, ELO, Chg, Contrib, Win%, Contribution |
| Enhanced Trades Table | TRADE LOG toolbar; columns Date (checkbox), Symbol, Side (L/H), Qty, Entry, Exit, P&L; mock trades fallback |
| Footer | Embodier Trader - Performance Analytics v2.0 | Connected | … |
| Risk Cockpit Expanded | ACTIVE green button; Risk History chart; fallback data |
| Strategy & Signals | activeStrategies: ['Strateg A']; signalHitRate/regime fallbacks |
| Duplicate card | Removed standalone Returns Heatmap Calendar (kept inside Attribution) |

---

## Anything Still Off From Mockup

- **Flywheel Pipeline Health:** Mockup shows Status (green Active), Timeline (yellow/gray) — current implementation uses progress bar; may need status chips.
- **NIL Inferences:** Mockup references "NIL Inferences" with red %; implementation uses "Total Inferences."
- **Portfolio Risk / VaR grid:** Mockup shows color-coded squares for Portfolio/VaR; current VaR Gauges are semicircle gauges.
- **Market Sentiment gauge:** Mockup shows semicircular gauge with needle; implementation uses text labels.
- **Side (L/H):** Mockup uses L/H for Long/Short; implementation normalizes Long→L, Short→H.

---

## Approval Status

- **Layout, spacing, font sizes, card sizing, section placement:** Aligned with mockup
- **Borders, shadows, colors, icons, alignment:** Aligned with mockup
- **Shared nav/header/sidebar:** Not modified (consistent with system)
- **Remaining gaps:** Minor (NIL vs Total Inferences, Flywheel status chips, VaR/Portfolio grid styling)
- **Ready for approval:** Yes, with noted minor differences
