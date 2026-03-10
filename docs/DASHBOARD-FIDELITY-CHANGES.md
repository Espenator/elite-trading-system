# Dashboard — Mockup Fidelity Changes

**Page:** Dashboard (Intelligence Dashboard)  
**Mockup:** `02-intelligence-dashboard.png`  
**File:** `frontend-v2/src/pages/Dashboard.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Header
- **Mockup:** EMBODIER TRADER (light blue); metrics: SPX, NDAQ, DOW, BTC, Equity, P/L, Deployed 0.7M, Signals 23, Regime BULL, Sharpe 2.14, Kelly 10.3%, Alpha +5.5%, Hi John
- **Before:** Regime/SCORE/RISK/SENT badges; different metric order and labels (Deployed %, Win, MaxDD)

### Table Toolbar
- **Mockup:** Select All, Filter, Group, Timesframe, OrderFlow, Threshold, Refine, Execute (green)
- **Before:** Sort pills (15 options); Timeframe buttons; Auto-Exec, LIVE, Flywheel status

### Table Columns
- **Mockup:** CMP, Flow, Status, Source, Symbol, Direction, TriggerID, Level, Liquidity, Quant, Bid, Ask, Delta, Gamma, Vega, Theta, Rho, IV, Volume, P/L, Actions (MOD, REM)
- **Before:** Sym, Dir, Score, Regime, ML, Sent, Tech, Agent, Swarm, SHAP, Kelly, Entry, Tgt, Stop, R-Mult, P&L, Sec, Mom, Vol, News, Pat

### Table Footer / Bottom Buttons
- **Mockup:** "25 rows. 15.0 LT (In-Day Stat) | 0:27 | Prep est 0.02s | Daily 97% | Week 71.02%"; EXECUTE X 99 (green), EXIT ALL (red)
- **Before:** Run Scan, Export CSV, Exec Top 5; signal count

### Right Column
- **Mockup:** TOP TRADE IDEAS (circular chart, metrics, EXECUTE NOW, SCALE, LIMIT), AGENT COMPOSITION (Agent, Symbol, S, Q, TP, SL, P/L, Actions), SWARM CONCENSUS PER TIKER (bars), NEWS & PATTERN TRIGGERS, FDI CHECK (Price, Max DD, Trade Confidence, APPROVE BID, REJECT BID)
- **Before:** Swarm Consensus, Signal Strength Bar Chart, Regime Donut + Top Trades Donut, Selected Symbol Detail, Risk & Order Proposal, Cognitive Intelligence, Equity Curve, ML Flywheel

### Footer
- **Mockup:** RUN SCAN, DEBATE, BROKER, EXECUTE, HELP/DOCS, PAUSE, EMERGENCY STOP; CPU, GPU, RAM, NET, PID
- **Before:** Spawn Agent, Flatten All, EMERGENCY STOP; WS, API, Agents, CPU, GPU, Uptime

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/Dashboard.jsx` | Header, toolbar, table, right column, footer |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| Header | Simplified to logo + title; KPIs: SPX, NDAQ, DOW, BTC, Equity, P/L, Deployed, Signals, Regime, Sharpe, Kelly, Alpha, Hi John |
| Toolbar | Replaced sort pills with Select All, Filter, Group, Timesframe, OrderFlow, Threshold, Refine, Execute |
| Table | Columns: CMP, Flow, Status (T1/T2/T3), Source, Symbol, Direction (BULL/BEAR), TriggerID, Level, Liquidity, Quant, Bid, Ask, Delta, Gamma, Vega, Theta, Rho, IV, Volume, P/L, Actions (MOD, REM) |
| Table Footer | Added "N rows. 15.0 LT (In-Day Stat) | 0:27 | Prep est 0.02s | Daily 97% | Week 71.02%" |
| Bottom Buttons | EXECUTE X 99 (green), EXIT ALL (red); Run Scan, Export CSV moved to secondary |
| Right Column | Restructured: TOP TRADE IDEAS, AGENT COMPOSITION, SWARM CONCENSUS PER TIKER, NEWS & PATTERN TRIGGERS, FDI CHECK |
| Footer | RUN SCAN, DEBATE, BROKER, EXECUTE, HELP/DOCS, PAUSE, EMERGENCY STOP; CPU, GPU, RAM, NET, PID |
| Hidden | Selected Symbol Detail, Risk & Order Proposal, Cognitive Intelligence, Equity Curve, ML Flywheel (hidden for mockup fidelity) |

---

## Anything Still Off From Mockup

- **Table data:** Options flow columns (Delta, Gamma, Vega, etc.) use placeholder/derived values; backend may not provide Greeks.
- **Direction:** Mockup uses BULL/BEAR; implementation uses LONG/SHORT in some places; normalized to BULL/BEAR in table.
- **Deployed format:** Mockup "0.7M"; implementation uses portfolio.deployedPercent — may need backend alignment.
- **Mini sidebar:** Mockup sidebar (COMMAND, INTELLIGENCE, etc.) is the main app sidebar; Dashboard has its own 6-icon mini sidebar ( Dash, Signals, Port, Risk, Agents, ML).
- **Layout integration:** Dashboard is rendered inside Layout (Sidebar + Header + StatusFooter); Dashboard has its own full-page layout which may overlap with Layout.

---

## Approval Status

- **Header, toolbar, table structure, right column, footer:** Aligned with mockup
- **Shared nav/header/sidebar:** Not modified (Layout unchanged)
- **Ready for approval:** Yes, with noted data/backend considerations
