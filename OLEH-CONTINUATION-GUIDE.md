# Oleh Continuation Guide - Elite Trading System Frontend-v2

## Recent Changes (What Was Done)

### 1. Chart Component Stubs Created
Two new stub components were added to `frontend-v2/src/components/charts/`:

- **RiskEquityLC.jsx** - Placeholder for lightweight-charts equity curve
  - Accepts `data`, `height`, `showBenchmark`, `timeframe` props
  - Currently renders mini bar-chart placeholder
  - TODO: Wire up with `createChart()` from lightweight-charts library

- **MonteCarloLC.jsx** - Placeholder for Monte Carlo simulation chart
  - Accepts `data`, `height`, `showPercentiles` props
  - Shows percentile color legend (5th through 95th)
  - TODO: Wire up with lightweight-charts AreaSeries for percentile bands

### 2. RiskIntelligence.jsx Imports Fixed
- Uncommented `import RiskEquityLC` (line 25)
- Uncommented `import MonteCarloLC` (line 26)
- Both imports now resolve to the stub files above

### 3. JSX Usage Blocks Still Commented
In `RiskIntelligence.jsx`, the JSX that renders these charts is still wrapped in `{/* ... */}` comments. To activate them:

**Portfolio Equity Chart (~line 160-165):**
Find and uncomment the block that uses `<RiskEquityLC data={histData} height={220} />`

**Monte Carlo Chart (~line 170-180):**
Find and uncomment the block that uses `<MonteCarloLC data={mcData} height={220} />`

## What Needs To Be Done Next

### Priority 1: Wire Up Chart Components with lightweight-charts
1. Install lightweight-charts: `npm install lightweight-charts`
2. In `RiskEquityLC.jsx`: Replace placeholder with `createChart()` + LineSeries
3. In `MonteCarloLC.jsx`: Replace placeholder with `createChart()` + multiple AreaSeries
4. Uncomment the JSX blocks in `RiskIntelligence.jsx` that render these charts

### Priority 2: Verify All Page Imports Compile
Pages to verify compile cleanly:
- `Dashboard.jsx` - 717 lines, imports look clean
- `Signals.jsx` - 683 lines, imports look clean
- `RiskIntelligence.jsx` - 480 lines, imports now fixed
- `EquityCurveChart.jsx` - Already using useApi with portfolio data

### Priority 3: API Integration
All pages use `useApi()` hook to fetch from backend. Verify these endpoints:
- `/api/v1/risk` - Risk metrics (Alpaca account data)
- `/api/v1/portfolio` - Portfolio positions
- `/api/v1/alerts` - Alert data
- `/api/v1/performance` - Equity history + Monte Carlo data
- `/api/v1/signals` - OpenClaw signal data

## File Structure Reference

```
frontend-v2/src/
  components/
    charts/
      EquityCurveChart.jsx   (working - uses useApi)
      MiniChart.jsx          (working)
      RiskEquityLC.jsx       (STUB - needs lightweight-charts)
      MonteCarloLC.jsx       (STUB - needs lightweight-charts)
      RiskHistoryChart.jsx   (working)
    ui/                      (Card, Button, TextField, etc.)
  pages/
    Dashboard.jsx            (clean)
    RiskIntelligence.jsx     (imports fixed, JSX blocks to uncomment)
    Signals.jsx              (clean)
    ... other pages
  hooks/
    useApi.js                (centralized API fetching)
  config/
    api.js                   (getApiUrl helper)
```

## Quick Start
```bash
cd frontend-v2
npm install
npm run dev
```

Then visit http://localhost:5173 to see the app.
