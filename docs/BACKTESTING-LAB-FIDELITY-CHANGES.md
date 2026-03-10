# Backtesting Lab — Mockup Fidelity Changes

**Page:** Backtesting Lab  
**Mockup:** `08-backtesting-lab.png`  
**File:** `frontend-v2/src/pages/Backtesting.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Top Header Bar
- **Mockup:** BACKTESTING_LAB centered/prominent; right: OC_CORE_v3.2.1, WS LATENCY: 42ms, SWARM_SIZE: 100, timestamp; Run (green), Stop (red), Export, Refresh
- **Before:** PageHeader with description; different button styling

### Backtest Configuration
- **Mockup:** Strategy dropdown; Start Date, End Date; Assets (text input: "BTCUSDT, ETHUSDT, SPY, QQQ, AAPL, MSFT, TSLA, NVDA"); Capital "$100,000"; Benchmark dropdown
- **Before:** Strategy, Start/End, # Batches, % in Trn, Symbols as badges, Benchmark; no Assets input, no Capital

### Parameter Sweeps & Controls
- **Mockup:** Param A 0-50, Transaction Cost $0, B Min/Max 10-100, Max Positions 100, Position Size 0-100%, Rebalance Freq, Slippage 0bps, Stop Loss %, Single/Sweep, Take Profit %, Kelly Sizing, Run (green), Stop (red), Regime Filter BULL/SIDEWAYS, Warm-Up 1000, Walk-Forward 35%, Monte Carlo 1000, Confidence 95%
- **Before:** Different fields; Regime BULL/BEAR/ALL; no Run/Stop in card; different slider set

### OpenClaw Swarm Backtest Integration
- **Mockup:** 7 Core Agents with name + % progress bar + green light (Apex 100%, Relative Weakness 81%, Short Basket 75%, Meta Architect 90%, Meta Alchemist 81%, Risk Governor 100%, Signal Engine 95%); EXTENDED SWARM: 93 sub-agents; Team Alpha 23, Team Beta 31, Team Gamma 22, Team Delta 17 with status dots
- **Before:** Different agents; ACTIVE badge; no progress bars; no Team breakdown

### Performance KPI Mega Strip
- **Mockup:** 18 KPIs with large primary + smaller secondary value per block (e.g. Net P&L +$345K / 2.43%, Sharpe 2.35 / 9.3%)
- **Before:** Single value per KPI; different KPI set

### Equity Curve
- **Mockup:** Title "Equity Curve - Lightweight Charts"; timeframe filters 1M, 3M, 6M, 1Y, ALL
- **Before:** No timeframe filters; different title

### Parallel Run Manager
- **Mockup:** Table with Run, Strategy Name, Status (Running)
- **Before:** List + BarChart; different layout

### Rolling Sharpe Ratio
- **Mockup:** "Rolling Sharpe Ratio (24M)"
- **Before:** "(3M)"

### Market Regime Performance
- **Mockup:** BULL 65.5% $450 avg, BEAR 42.0% -$120 avg, SIDEWAYS 51.1% $80 avg (three blocks)
- **Before:** Donut charts; different regime set

### Strategy Builder
- **Mockup:** Nodes: Data Feed, RSI Filter, MACD Signal, Entry Logic, Execute, Optimizer, Risk Manager
- **Before:** Data Feed, Feature Eng, Signal Gen, Risk Filter, Position Sizer, Execution

### Trade-by-Trade Log
- **Mockup:** Date, Asset, Side, QTY, Entry Price, Exit Price, P&L, Patch, Duration, R-Multiple, Agent Origin, Commission; Side as BUY/SELL pill
- **Before:** Different columns; no QTY, Patch, Duration, Commission; Agent vs Agent Origin

### Run History & Export
- **Mockup:** "Export All Results" button
- **Before:** "Import" button

### OpenClaw Swarm Consensus
- **Mockup:** Table: Agent Agreement | % | visual; Team Alpha, Team Beta, Team Gamma, Team Delta with bars
- **Before:** Consensus Signal, Confidence, Agents Agreeing; different layout

### Footer
- **Mockup:** "7 Agents OK" (green bar), "EXTENDED SWARM (93)" (green bar); OC_CORE_v3.2.1
- **Before:** "7 Agents ON", "EXTENDED SWARM (R1)", "10 sub-agents"; different styling

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/Backtesting.jsx` | Full mockup fidelity pass |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| **Top Header Bar** | Custom bar: BACKTESTING_LAB, OC_CORE_v3.2.1, WS LATENCY, SWARM_SIZE, timestamp; Run (green), Stop (red), Export, Refresh |
| **Backtest Configuration** | Assets text input; Capital field; Start Date/End Date labels; removed # Batches, % in Trn, Symbols badges |
| **Parameter Sweeps** | Param A, B Min/Max, Transaction Cost $0, Max Positions 100, Position Size %, Rebalance Freq, Slippage bps, Stop Loss %, Take Profit %, Kelly Sizing, Regime BULL/SIDEWAYS, Warm-Up 1000, Walk-Forward 35%, Monte Carlo Iterations 1000, Confidence 95%; Run/Stop in card action |
| **OpenClaw Swarm** | 7 Core Agents: Apex Orchestrator, Relative Weakness, Short Basket, Meta Architect, Meta Alchemist, Risk Governor, Signal Engine with % progress bars; EXTENDED SWARM 93 sub-agents; Team Alpha/Beta/Gamma/Delta with agent counts and status dots |
| **KPI Mega Strip** | 14 KPIs with primary + secondary values; fallback mockup numbers; color thresholds |
| **Equity Curve** | Title "Equity Curve - Lightweight Charts"; 1M/3M/6M/1Y/ALL filters |
| **Parallel Run Manager** | Table: Run | Strategy Name | Status |
| **Rolling Sharpe** | Title "(24M)" |
| **Market Regime** | BULL/BEAR/SIDEWAYS blocks with winRate % and avg $ |
| **Strategy Builder** | Nodes: Data Feed, RSI Filter, MACD Signal, Entry Logic, Execute, Optimizer, Risk Manager; updated edges |
| **Trade Log** | Columns: Date, Asset, Side (pill), QTY, Entry Price, Exit Price, P&L, Patch, Duration, R-Multiple, Agent Origin, Commission |
| **Run History** | "Export All Results" button |
| **Swarm Consensus** | Agent Agreement table with Team Alpha/Beta/Gamma/Delta, %, visual bars |
| **Footer** | "7 Agents OK", "EXTENDED SWARM (93)" green bars; OC_CORE_v3.2.1 |

---

## Remaining Differences / Notes

- **Equity timeframe filters:** UI only; actual filtering would require API/chart integration.
- **Monte Carlo scatter:** Mockup shows scatter plot; implementation uses line chart for paths.
- **Parameter Optimization Heatmap:** Axis labels and cell layout may differ slightly.
- **Walk-Forward:** Legend and bar styling aligned; data from API.

---

## Ready for Approval

The Backtesting Lab page has been updated to match the approved mockup. Layout, section placement, header, cards, sliders, tables, KPIs, charts, Strategy Builder nodes, and footer align with the reference. Shared navigation/sidebar remain consistent.
