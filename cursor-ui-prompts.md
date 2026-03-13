# Cursor UI Prompts — Embodier Trader v5.0.0

> **Purpose**: Pixel-fidelity alignment to mockups, eliminate ALL mock/fallback data, make ALL buttons functional, wire bidirectional data flow.
> **Usage**: Copy-paste each prompt into Cursor with the corresponding page file open.
> Generated March 12, 2026 from full code audit + mockup pixel comparison of all 14 pages.

---

## 1. Sentiment Intelligence (`SentimentIntelligence.jsx`)

**Mockup**: `docs/mockups-v3/images/04-sentiment-intelligence.png`

```
I'm aligning SentimentIntelligence.jsx to pixel fidelity with mockup 04-sentiment-intelligence.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons and controls functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981, red #ef4444, amber #f59e0b, text primary #e2e8f0, text secondary #94a3b8.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 3-column layout:
- LEFT (25%): OpenClaw Agent Swarm panel — agent list with status dots + weight progress bars + auto-discover button
- CENTER (50%): PAS Heatmap (stocks × time grid, bright green→yellow→orange→red cells) + 30-Day Sentiment radar chart (hexagonal, 6 axes, cyan fill) + alert box below
- RIGHT (25%): Trade Signals panel + Prediction Markets cards + Scanner Status Matrix (dot grid with colored status dots)

Ensure the grid matches: `grid-cols-12` with left=col-span-3, center=col-span-5, right=col-span-4.

### ELIMINATE MOCK/FALLBACK DATA
Lines 59-72: `HEATMAP_SYMBOLS` is hardcoded with 12 symbols and percentages. Replace with live data from `useSentiment().heatmap`. If API returns empty, show skeleton loader — never show hardcoded values.

Lines 75-79: `SCANNER_SYMBOLS` is hardcoded with 24 symbols. Replace with live scanner data from `useApi('signals')`.

Lines 82-90: `SENTIMENT_SOURCE_BARS` is hardcoded with 7 sources and colors. Replace with `useSentiment().sourceHealth` which returns real source status.

Line 178: `moodValue = mood?.value ?? 87` — the fallback `87` is fake data. Use `mood?.value ?? null` and render a skeleton/dash when null.

Lines 613-616: Hardcoded market event entries. Replace with live data from `useApi('systemAlerts')` or `useSentiment().signals`.

### MAKE ALL BUTTONS FUNCTIONAL
Lines 367-377: Weight sliders display values but have NO onChange handlers — they're display-only. Wire them to `postAgentOverrideWeight(agentName, alpha, beta)` from useApi.js so the user can actually adjust agent weights. Add a "Save Weights" button that persists changes.

The heatmap grid (lines 469-485) is display-only. Make cells clickable — clicking a symbol should filter the signals panel to show that symbol's signals.

### BIDIRECTIONAL DATA FLOW
- The `useSentiment()` hook is read-only (no POST methods). For the agent weight adjustment, use `postAgentOverrideWeight(agentName, alpha, beta)` and `postAgentOverrideStatus(agentName, action)` from `useApi.js`.
- Auto-discover button (lines 381-388) already calls `sentiment/discover` POST — this is good, keep it.
- Add a "Refresh" button to the radar chart panel header that calls `refetch()` from useSentiment().

Keep all existing useApi hooks and polling intervals. No new mock data. Every component must show live data or a proper loading/empty state.
```

---

## 2. Dashboard (`Dashboard.jsx`)

**Mockup**: `docs/mockups-v3/images/02-intelligence-dashboard.png`

```
I'm aligning Dashboard.jsx (1693 lines) to pixel fidelity with mockup 02-intelligence-dashboard.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons and controls functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981, red #ef4444, amber #f59e0b.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 2-column layout:
- LEFT (60%): Main data table (dense grid, 20+ rows, colored header cells cyan/green/red) — this is the signal intelligence table showing symbol, price, volume, %change, indicators
- RIGHT (40%): KPI strip + circular gauges (3 gauges 0-100%) + horizontal bar charts (agent rankings) + status cards with directional arrows

The top bar has horizontal scrollable tabs for intelligence types. The heatmap (15x8 grid) sits in the right column with green→yellow→orange→red gradient.

### ELIMINATE MOCK/FALLBACK DATA
The dashboard uses multiple `useApi` hooks — audit each one:
- `sigStale`, `sigErr` flags are computed but NEVER RENDERED. The `isStale` return value from each hook should trigger a visual indicator (thin amber top-border on stale panels).
- The MiniEquityCurve (SVG polygon, lines ~393-396) recalculates on every render — wrap in `useMemo(() => {...}, [values])`.
- The HeatmapGrid color interpolation (lines ~657-689) produces dark reds on dark backgrounds. Set minimum brightness: reds #ef4444 minimum. All heatmap text needs `text-shadow: 0 0 2px rgba(0,0,0,0.8)`.

Identify and eliminate every `?? fallbackValue`, `|| defaultArray`, or hardcoded sample data. Replace with proper loading states (skeleton loaders) when data is null.

### MAKE ALL BUTTONS FUNCTIONAL
- The boot screen (lines ~1094-1098) only handles loading. If `sigErr` is true, it falls through silently. Add an error state card with "Retry" button that calls refetch on all hooks.
- Signal table rows should be clickable — clicking should navigate to `/signals?symbol=${symbol}` or open a detail panel.
- KPI cards should animate number changes with 200ms CSS transitions when new data arrives.
- Add clickable column headers for sorting the signal table (by score, symbol, direction, time).

### BIDIRECTIONAL DATA FLOW
- The dashboard is primarily read-only (monitoring view). However, add:
  - "Refresh All" button in header that calls `refetch()` on all hooks simultaneously
  - Signal rows should have a "Send to Council" action that calls `fetchCouncilEvaluate(symbol, '15m', {})` from useApi.js
  - Council verdict polling (`councilLatest`) results should highlight the corresponding signal row with cyan glow (1.5s fade)

Keep all existing useApi hooks. No mock data. Every `?? fallback` with fake numbers must become `?? null` with a proper empty/loading state.
```

---

## 3. Agent Command Center (`AgentCommandCenter.jsx`)

**Mockup**: `docs/mockups-v3/images/01-agent-command-center-final.png`

```
I'm aligning AgentCommandCenter.jsx (237 lines) to pixel fidelity with mockup 01-agent-command-center-final.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, lime green #00FF00, red #FF4444, amber #FFA500.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a dense 4-column layout:
- Col 1 (25%): Agent Health Matrix (3 rows of 4x4 status dots, green/yellow/red circles) + Quick Actions row (Start Agent, Config Team, Emergency Veto red button) + Team Status (pool counts + active agents) + System Alerts (stacked boxes with amber/red left borders)
- Col 2 (25%): Agent Resource Monitor (dense table, dark bg, cyan/green/red text) + Blackboard Feed (scrollable monospace logs, 12px, cyan/red highlights)
- Col 3 (25%): Agent Confidence Pipeline (4 horizontal bars showing stage progression) + Drift Monitor (red/orange dot matrix heatmap)
- Col 4 (25%): Agent Skill Leaderboard (grid with agent names + colored cells) + Performance Metrics (KPI cards with green boxes)

Currently the shell is only 237 lines with 8 tabs. Ensure the tab structure and shell match the mockup's visual density.

### ELIMINATE MOCK/FALLBACK DATA
Lines 88-95: Hardcoded metric fallbacks:
- `cpuAvg` defaults to 47 — replace with live data from `useApi("system/health")`, show "—" when null
- `ramPct` defaults to 31 — same fix
- `gpuPct` defaults to 61 — same fix
- `uptime` defaults to "47d 12h 33m" — same fix

These are passed to sub-components. Ensure all sub-components handle null gracefully (show dash or skeleton).

### MAKE ALL BUTTONS FUNCTIONAL
- KILL SWITCH (lines 142-160): Already functional with POST to `/orders/emergency-stop` — GOOD, keep it.
- Tab navigation (lines 167-182): Already functional — GOOD.
- Agent status dots in the health matrix should be clickable — clicking an agent dot should navigate to that agent's detail tab or show a tooltip with current metrics.

### BIDIRECTIONAL DATA FLOW
Uses 8 `useApi` hooks (agents, system/health, teams, systemAlerts, conference, drift, cnsBlackboard, cnsAgentsHealth) — all are GET-only polling.

Wire bidirectional controls:
- Agent enable/disable: Use `postAgentOverrideStatus(agentName, 'enable'|'disable')` from useApi.js
- Agent weight adjustment: Use `postAgentOverrideWeight(agentName, alpha, beta)` from useApi.js
- These should be accessible from the Overview tab when clicking an agent

Keep all 8 useApi hooks and polling intervals. No mock data.
```

---

## 4. Signal Intelligence V3 (`SignalIntelligenceV3.jsx`)

**Mockup**: `docs/mockups-v3/images/03-signal-intelligence.png`

```
I'm aligning SignalIntelligenceV3.jsx (~2046 lines) to pixel fidelity with mockup 03-signal-intelligence.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons and controls functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981, red #ef4444.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 3-column layout:
- LEFT (20%): Navigation sidebar — agent list with status indicators, scanner modules with checkboxes
- CENTER (50%): Large candlestick OHLC chart (200+ candles, moving average overlays, volume bars below) + Signal data table (8 columns × 12 rows)
- RIGHT (30%): Agent voting dashboard (10×3 grid of agent cards, each shows name + confidence bar) + Circular consensus gauge (buy/sell/hold split)

Agent cards have GREEN borders for buy votes, RED for sell, GRAY for hold. Confidence bars are horizontal fills.

### ELIMINATE MOCK/FALLBACK DATA
Lines 41-59: `FALLBACK_CORE_AGENTS` array with 7 hardcoded agent definitions — ELIMINATE. Use live data from `useApi('agents')`. Show skeleton when null.

Line 60: `FALLBACK_EXTENDED_AGENTS = []` — ELIMINATE. Same API source.

Lines 87-101: `SCANNERS` array with 13 hardcoded scanner definitions — ELIMINATE. Use live data from `useApi('dataSources')` for scanner status.

Replace ALL `FALLBACK_*` constants throughout the file with null checks + skeleton/loading states.

### MAKE ALL BUTTONS FUNCTIONAL
- Chart timeframe buttons (1M, 5M, 15M, 1H, 1D): These appear to be UI-only. Wire each to fetch bar data from the appropriate Alpaca bars endpoint via `useApi('stocks', { endpoint: '/stocks/${symbol}/bars?timeframe=${tf}' })`. Show loading spinner on active button while fetching.
- Scoring formula sliders (ocTaBlend, tiers, regimeMultiplier): Add validation — ocTaBlend 0-100, tiers must be descending. These should persist via settings API: use `saveCategory('scoring')` from `useSettings()`.
- "Send to Council" action on signal rows: Wire to `fetchCouncilEvaluate(symbol, timeframe, {})` from useApi.js.
- Scanner module checkboxes: Should toggle scanner on/off via `postAgentOverrideStatus(scannerName, 'enable'|'disable')`.

### BIDIRECTIONAL DATA FLOW
- Agent voting panel: Display-only currently. Add click-to-detail on each agent card showing that agent's recent vote history.
- Scoring parameters should be readable AND writable via `useSettings()` hook (which supports `updateField` + `saveCategory`).
- ML Model Control panel: Show live values from `useApi('flywheelModels')`. "Retrain" button should call the training API endpoint.
- Auto Execution panel: Show live values from `useSettings()`. Toggle "Auto Execute" should call `updateField('trading', 'auto_execute', value)` then `saveCategory('trading')`.

Keep all existing hooks. No mock data.
```

---

## 5. ML Brain & Flywheel (`MLBrainFlywheel.jsx`)

**Mockup**: `docs/mockups-v3/images/06-ml-brain-flywheel.png`

```
I'm aligning MLBrainFlywheel.jsx (643 lines) to pixel fidelity with mockup 06-ml-brain-flywheel.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows 4 stacked sections:
- TOP (25%): 6 KPI cards in a row — "3" (Models), "91.4%" (Accuracy), "24" (Features), "12" (Win Rate), "OK" (Status), ">70%" (Performance). Each card: dark bg, white/cyan text, outlined borders.
- UPPER-MIDDLE (25%): "Model Performance Tracking" — line/area chart showing accuracy trend over time. Green upward trend with semi-transparent green fill. Y-axis 0-100%, X-axis weekly periods.
- LOWER-MIDDLE (25%): "Stage 5: ML Probability Ranking" — horizontal bar chart for 7 symbols (TICK, AAPL, MSFT, etc.). Green bars, value labels 70-95% on right.
- BOTTOM (25%): Two metric grids side-by-side:
  - Left: "Deployed Inference Fleet" — 4 model cards showing precision values (0.835, 0.851, 0.883, 0.862)
  - Right: "Predicted Learning Log" — colored cell grid showing trade outcomes

### ELIMINATE MOCK/FALLBACK DATA
Lines 21-34: `FALLBACK_KPIS` object — ELIMINATE. Replace with live data from `useApi('flywheelKpis', { pollIntervalMs: 15000 })`. Show "—" for each KPI when null.

Lines 29-33: `FALLBACK_PERFORMANCE`, `FALLBACK_SIGNALS`, `FALLBACK_MODELS`, `FALLBACK_LOGS` — ELIMINATE ALL. Each maps to a specific useApi hook (flywheelPerformance, flywheelSignals, flywheelModels, flywheelLogs).

Lines 38-70: `MiniSparkline` generates RANDOM data with `let v = 50` seed — ELIMINATE random generation. Pass real data arrays from the API hooks. When data is null, show a flat gray line placeholder.

Lines 74-100: `MiniLineSparkline` has same random data issue — same fix.

Lines 357-368: `defaultSignals` with 10 hardcoded signal rows (NVDA, MSTR, AAPL, etc.) — ELIMINATE. Use `useApi('flywheelSignals')` data directly.

Lines 373-380: `defaultModels` with 6 hardcoded ML model definitions — ELIMINATE. Use `useApi('flywheelModels')` data directly.

### MAKE ALL BUTTONS FUNCTIONAL
Lines 396-403: "Retrain Models" button — already has `onClick={handleRetrain}` with async operation. VERIFY it actually calls the training API. If it only sets local state, wire it to the real training endpoint.

Lines 459-461: "Model Matrix" button — NO onClick handler. Wire to navigate to a model comparison view or open a detail modal showing the confusion matrix.

Lines 485-487: "Filter ↓" button in probability ranking — NO onClick handler. Wire to open a dropdown filter for filtering by score tier (Slam Dunk / Strong Go / Watch).

### BIDIRECTIONAL DATA FLOW
All 7 useApi hooks (flywheelKpis, flywheelPerformance, flywheelSignals, flywheelModels, flywheelLogs, flywheelFeatures, mlBrain) are GET-only.

Add write capability:
- "Retrain" button: POST to training endpoint to trigger walk-forward retrain
- ML probability ranking table should support column sorting (click headers)
- Inference Fleet cards: Click to expand showing model details. Add "Promote to Champion" button that calls a model promotion endpoint.

Keep all 7 useApi hooks and polling intervals. No mock data.
```

---

## 6. Screener & Patterns (`Patterns.jsx`)

**Mockup**: `docs/mockups-v3/images/07-screener-and-patterns.png`

```
I'm aligning Patterns.jsx (750 lines) to pixel fidelity with mockup 07-screener-and-patterns.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 3-column layout:
- LEFT (30%): Screening Engine panel — Scanner Agent Cards with enable/disable checkboxes (8 agents listed) + Control toggles (9 toggle options) + Active Scan status log
- CENTER (30%): Pattern Intelligence panel — Pattern Agent cards + Pattern templates (7-8 visible) + Active scan status
- RIGHT (40%): Coverage & Configuration (2-column sub-panel) + Pattern Results overview + Screener Results (4×4 grid of chart thumbnails) + Scanning indicators (green/yellow/red dots)

### ELIMINATE MOCK/FALLBACK DATA
Lines 42-44: `SCANNER_AGENTS = []` — THIS IS EMPTY and the scanner section renders with no agents. Populate from `useApi('agents')` filtered to scanner-type agents. If API returns none, show: "No scanner agents active. Start scanners from Agent Command Center."

Lines 44: `PATTERN_AGENTS = []` — same issue, same fix.

Lines 47-54: `PATTERNS_ARSENAL_DISPLAY` with 6 hardcoded pattern types (Wyckoff, Elliott Wave, etc.) — replace with live data from `useApi('patterns')`.

Lines 56-57: `LLM_MODELS` hardcoded array (GPT-4, Claude 3, Llama 3) — replace with live data from settings API.

Lines 622-626: `FALLBACK_FEED_ENTRIES` with 3 hardcoded feed entries — ELIMINATE. Use live feed from API or show empty state.

Lines 670-672: `FALLBACK_FORMING` with 2 hardcoded detections — ELIMINATE. Use live data from `useApi('patterns')`.

### MAKE ALL BUTTONS FUNCTIONAL — THIS IS THE BIGGEST ISSUE ON THIS PAGE
Lines 409-413: ALL spawn/clone/kill buttons use `console.log` only:
- `"+ Spawn New Scanner Agent"` → `log.info("Spawn scanner agent")` — WIRE to POST `/agents/spawn` endpoint
- `"Clone Agent"` → `log.info("Clone agent")` — WIRE to POST `/agents/clone` endpoint
- `"Spawn Swarm"` → `log.info("Spawn swarm")` — WIRE to POST `/agents/swarm/spawn`
- `"Swarm Templates"` → `log.info("Swarm template")` — WIRE to GET `/agents/swarm/templates` and show template selector modal
- `"Kill All Agents"` → `log.info("Kill all agents")` — WIRE to POST `/agents/kill-all` WITH confirmation modal

Lines 583-586: Same pattern for pattern agent buttons — same fix, wire to real API endpoints.

Lines 68-77: WindowControls (Minimize, Maximize, Close) — REMOVE these entirely. They do nothing and confuse users. Replace with a simple panel title.

### BIDIRECTIONAL DATA FLOW
- Scanner configuration (lines 254-295): Name, Type, Timeframes inputs exist but have no save mechanism. Wire to settings API or agent configuration endpoint.
- Trading Metric Controls (lines 344-405): Sliders and toggles manage local state but never persist. Wire to `useSettings().updateField()` + `saveCategory()`.
- Pattern configuration selects (lines 504-530): Name, LLM Model, Architecture dropdowns — wire to settings persistence.
- ML Metric Controls (lines 534-579): All display-only with no save/apply button. Add "Apply" button that saves via settings API.
- Filter chips at top: Currently single-select. Convert to multi-select with active filter count badge.

Keep useApi hooks for signals and patterns. No mock data.
```

---

## 7. Backtesting Lab (`Backtesting.jsx`)

**Mockup**: `docs/mockups-v3/images/08-backtesting-lab.png`

```
I'm aligning Backtesting.jsx (~2600 lines) to pixel fidelity with mockup 08-backtesting-lab.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 2-column layout:
- LEFT (35%): Parameter panels stacked vertically:
  - Backtest Configuration panel with strategy dropdown (12 strategies)
  - Time Period selector (From/To date pickers)
  - Agent selection checkboxes
  - Risk parameter sliders
  - Broker/Fees configuration
- RIGHT (65%): Results visualization:
  - Equity curve (large green area chart, 400×200px)
  - Return distribution (histogram)
  - Drawdown chart (negative red/orange area)
  - Monthly returns heatmap (12×3 colored grid)
  - Trade distribution (bar chart)
  - Agent consistency gauge
  - Statistical KPI cards
  - Full trade history table (15 rows)

### ELIMINATE MOCK/FALLBACK DATA
Search the entire 2600-line file for ALL instances of:
- `FALLBACK_*` constants — replace each with the corresponding useApi hook data
- Hardcoded backtest scenarios — replace with live results from `useBacktestResults()`
- Hardcoded parameter ranges — replace with live ranges from `useBacktestOptimization()`
- Any `?? [...]` or `?? {...}` patterns with fake numbers — replace with null + loading state

The following specialized hooks are available — ensure ALL are wired:
- `useBacktestResults()` — main results data
- `useBacktestOptimization()` — parameter optimization
- `useBacktestWalkForward()` — walk-forward validation
- `useBacktestMonteCarlo()` — Monte Carlo simulation
- `useBacktestCorrelation()` — correlation analysis
- `useBacktestSectorExposure()` — sector exposure
- `useBacktestDrawdownAnalysis()` — drawdown analysis

### MAKE ALL BUTTONS FUNCTIONAL
- "Run Backtest" button: Must call POST to backtest API with the configured parameters. Show progress bar with percentage, elapsed time, estimated remaining.
- "Cancel" button: Must abort a running backtest.
- Strategy dropdown: Must actually filter/load different strategy configurations.
- Date pickers: Must actually control the date range sent to the API.
- Agent checkboxes: Must filter which agents participate in the backtest.
- Parameter sweep pagination: Add pagination (25 rows/page) with column sorting.
- ReactFlow DAG: Add zoom controls (+/- buttons) and "Fit to view" button.

### BIDIRECTIONAL DATA FLOW
- All parameter controls (strategy, dates, agents, risk sliders) must bidirectionally sync: read defaults from API, allow user changes, and send modified params in the POST request.
- Trade history table: Sortable by clicking column headers.
- Agent contribution chart: Clicking an agent bar should show that agent's individual metrics.
- Equity curve: Add benchmark line (SPY buy-and-hold) for comparison.

Keep all existing hooks and ReactFlow setup. No mock data.
```

---

## 8. Data Sources Monitor (`DataSourcesMonitor.jsx`)

**Mockup**: `docs/mockups-v3/images/09-data-sources-manager.png`

```
I'm aligning DataSourcesMonitor.jsx (849 lines) to pixel fidelity with mockup 09-data-sources-manager.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 2-column layout:
- LEFT (35%): Data Sources Manager list panel:
  - Connectivity status bar (3 indicators: All Sources, Live Sources, OpenClose Bridge)
  - Source list: 12 sources, each row has name + connection status dot (green/red) + last update time + data quality indicator
  - Sources: Alpaca, Finviz, FRED, NewsAPI, Unusual Whales, Benzinga, SqueezeMetrics, Capitol Trades, Senate Stock Watcher
- RIGHT (65%): Configuration/Status detail panel:
  - Currently Connected status display
  - Source configuration form fields (URL, Auth type, Rate Limit)
  - "Test Connection" button (cyan)
  - Source metadata info box

### ELIMINATE MOCK/FALLBACK DATA — THIS IS THE BIGGEST ISSUE ON THIS PAGE
Lines 33-174: `SOURCE_DEFS` is a MASSIVE hardcoded array with 10 data source definitions including fake status, latency, uptime, and sparkline data. ELIMINATE ENTIRELY. Replace with live data from `useApi("dataSources", { pollIntervalMs: 30000 })`. The API should return real connection statuses.

Lines 176-187: `FILTER_CHIPS` hardcoded array — this is OK as static filter definitions, but filter counts should be computed from live data.

Lines 189-196: `SUGGESTED_SERVICES` hardcoded array — this can remain as static suggestions, but make cards functional (see below).

Lines 210-214: `genSparkline()` generates FAKE random sparkline data — ELIMINATE. Use real latency history from the API. Show flat gray line when no history available.

Lines 560-565: "Connection Log" has hardcoded log entries — replace with live connection log from API.

### MAKE ALL BUTTONS FUNCTIONAL — MANY DEAD BUTTONS
Lines 373-384: Row action buttons are NON-FUNCTIONAL:
- "LIVE PING" button for Alpaca — no onClick handler. WIRE to POST `settings/test-connection` with `{ source: 'alpaca' }` via `useSettings().testConnection('alpaca')`.
- "Show" button — no onClick. Wire to expand/select that source in the detail panel.
- "Copy" button — no onClick. Wire to copy API key to clipboard.
- "Rotate" button — no onClick. Wire to API key rotation endpoint.

Lines 537-551: Detail panel action buttons are ALL NON-FUNCTIONAL:
- "Test Connection" (line 537) — WIRE to `useSettings().testConnection(selectedSource)`
- "Save Changes" (line 541) — WIRE to `useSettings().saveCategory('data_sources')`
- "Cancel" (line 545) — WIRE to reset local state to last saved values
- "Reset to Default" (line 548) — WIRE to `useSettings().resetCategory('data_sources')`

Lines 189-196: Suggested Services cards do nothing when clicked. Make them link to the service's signup page in a new tab.

### BIDIRECTIONAL DATA FLOW
Lines 495-525: ALL credential fields are `readOnly` — the user CANNOT edit API keys, secrets, URLs, rate limits, or polling intervals. REMOVE `readOnly` attribute and wire each field to `useSettings().updateField('data_sources', fieldKey, value)`.

Lines 520-523: "Account Type" dropdown is editable but has no save mechanism — wire to settings.

Lines 509-515: "Polling Interval" dropdown is editable but no save — wire to settings.

After any field change, show "Save Changes" / "Discard" buttons. "Save Changes" calls `useSettings().saveCategory('data_sources')`.

Keep useApi dataSources hook. No mock data.
```

---

## 9. Market Regime (`MarketRegime.jsx`)

**Mockup**: `docs/mockups-v3/images/10-market-regime-green.png`, `10-market-regime-red.png`

```
I'm aligning MarketRegime.jsx (~1464 lines) to pixel fidelity with mockups 10-market-regime-green.png and 10-market-regime-red.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827. For GREEN regime: bright green #00FF00 accents. For RED regime: bright red #FF4444 accents.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 3-column layout:
- LEFT (20%): Sidebar navigation
- CENTER (40%): Regime detail panels stacked:
  - Regime State Machine (3×3 transition grid, current state highlighted GREEN or RED)
  - VIX/Macro Chart (candlestick-style, 300×150px)
  - Regime Parameter Panel (13 metrics with toggle controls)
  - Regime Flow (5 connected boxes: signal → open → ATH → risk → decision)
  - Regime Transition History (table, 8 rows with timestamps)
- RIGHT (40%): Performance & Risk panels:
  - Performance Metric cards (87% accuracy, etc.)
  - Sector Rotation (horizontal bar chart, 5 sectors with percentages)
  - Crash Protocol status (green/red indicator)
  - Agent Consensus (5 agents with confidence %, colored by regime)

The top nav shows "Market Regime" + status "GREEN 87%" in bright green (or "RED 83%" in red).

### ELIMINATE MOCK/FALLBACK DATA
Search all ~1464 lines for hardcoded fallback values. The page uses many specialized hooks:
- `useRegimeState()` — current regime detection
- `useMacroState()` — macro indicators
- `useRegimeParams()` — regime parameters
- `useRegimePerformance()` — performance metrics
- `useSectorRotation()` — sector rotation data
- `useRegimeTransitions()` — transition history
- `useMemoryIntelligence()` — memory/learning data
- `useWhaleFlow()` — whale/institutional flow
- `useRiskGauges()` — risk gauge data
- `useBridgeHealth()` — bridge connectivity

Verify ALL hooks are actually called and their data rendered. Replace any `REGIME_COLORS` or other static data objects with dynamic values from hooks.

### MAKE ALL BUTTONS FUNCTIONAL
- Regime state machine cells should be clickable — clicking a state shows details for that regime period.
- Parameter toggle switches: Verify they actually toggle via API (likely `useSettings()` or a regime-specific endpoint).
- Bias Override button: Already has `postBiasOverride(biasMultiplier)` available from useApi.js. Ensure it's wired with a clear label "Manual Regime Override" and a visible countdown timer showing when override expires.
- Sector bars should be clickable for drill-down showing sector-specific stocks and performance.

### BIDIRECTIONAL DATA FLOW
- Regime parameters: Should be readable AND writable. Use settings API for parameter adjustments.
- Bias override: Use `postBiasOverride(biasMultiplier)` for setting override, show active override banner.
- All 10+ hooks are read-only polling. For write operations, use the dedicated POST functions in useApi.js.

Keep all specialized hooks. No mock data.
```

---

## 10. Performance Analytics (`PerformanceAnalytics.jsx`)

**Mockup**: `docs/mockups-v3/images/11-performance-analytics-fullpage.png`

```
I'm aligning PerformanceAnalytics.jsx (~2000+ lines) to pixel fidelity with mockup 11-performance-analytics-fullpage.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF, emerald #10b981.

### MOCKUP LAYOUT (pixel fidelity)
Dense 3-column layout:
- LEFT (20%): KPI sidebar — Open Trades, Net Profit, Profit Factor, Sharpe Ratio, Win Rate, Drawdown metrics
- CENTER (50%): Performance charts stacked:
  - Equity Curve (large green area chart, 400×150px)
  - Win/Loss Chart (area chart cumulative)
  - Agent Attribution (donut chart showing agent contribution %)
  - Returns Distribution (area chart)
  - Monthly Performance Heatmap (12×3 grid)
  - Correlation matrix (colored grid)
- RIGHT (30%): Detailed breakdown:
  - Grade Card ("A: Excellent" in green)
  - Win % (48%), Profit Factor (2.1)
  - Trade Statistics
  - Agent Performance breakdown (3 agents)
  - Enhanced Trades Table (8 rows)
  - Returns heatmap variant

### ELIMINATE MOCK/FALLBACK DATA
Lines 21-33: `FALLBACK_KPI` object with all zero values — ELIMINATE. Use `useApi('performance')` data. Show "—" for each metric when null.

Lines 35-39: `FALLBACK_EQUITY` array with 21 HARDCODED equity points — ELIMINATE. Use `useApi('performanceEquity')` data. Show skeleton chart while loading.

Lines 41+: `agentColors` and other FALLBACK_* arrays — ELIMINATE ALL. Replace with live data from performance hooks.

Search entire file for `|| []`, `|| {}`, `?? 0`, `?? "N/A"` patterns with fake numbers. Each must become proper null handling with loading/empty states.

### MAKE ALL BUTTONS FUNCTIONAL
- Period selector (1D, 5D, 1M, 3M, 1Y): Must actually control the date range sent to the API. Wire each button to refetch performance data with the corresponding time range parameter.
- Agent filter toggles: Must filter which agents appear in attribution.
- Trade history sorting: Column headers must be clickable for sorting.
- "Export Report" button: Wire to generate a downloadable PDF or CSV of current metrics.
- Grade Card sub-grades: Each should be clickable to scroll to its detailed section.

### BIDIRECTIONAL DATA FLOW
- Date range selection: Read defaults from API, allow user changes, refetch with new range.
- Agent attribution: Click an agent row to expand inline showing accuracy by regime, avg confidence, signal count.
- Returns heatmap: Click a cell to see that day's detailed trades.
- All performance hooks are GET-only — write operations go through trade execution or settings hooks.

Keep all existing hooks. No mock data.
```

---

## 11. Trade Execution (`TradeExecution.jsx`)

**Mockup**: `docs/mockups-v3/images/12-trade-execution.png`

```
I'm aligning TradeExecution.jsx (685 lines) to pixel fidelity with mockup 12-trade-execution.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF. Buy orders: green bg/text. Sell orders: red bg/text.

### MOCKUP LAYOUT (pixel fidelity)
The mockup shows a 3-column layout with top KPI bar:
- TOP BAR: Portfolio info (P/L $81,280, 1D PnL +$912,000, Status: OPEN)
- LEFT (30%): Quick Execution buttons (Market, Limit, Bracket) + Multi-Price Loader table (10 rows: symbol, side, qty, price, status) + CSV paste input + Load button
- CENTER-LEFT (20%): Advanced Order Builder — order type selector, side (Buy/Sell), strategy dropdown, condition builder (If/Then logic), parameter fields
- CENTER (25%): Live Order Book — two tables (Bid green / Ask red), mid-price highlighted, spread shown
- RIGHT (25%): News Feed (5 articles with times) + System Status Log (color-coded messages) + Trade Summary

### ELIMINATE MOCK/FALLBACK DATA
Lines 231-247: Fallback price ladder with 20 HARDCODED price rows (base 4449.50) — ELIMINATE. Use `useTradeExecution().priceLadder` which fetches via `tradeExecutionService.getPriceLadder(symbol)`.

Lines 254-267: Fallback order book with hardcoded bid/ask — ELIMINATE. Use `useTradeExecution().orderBook`.

Lines 270-275: Fallback news feed with 4 hardcoded entries — ELIMINATE. Use `useTradeExecution().newsFeed`.

Lines 278-284: Fallback system status with 5 hardcoded entries — ELIMINATE. Use `useTradeExecution().systemStatus`.

Lines 287-290: Fallback positions with 2 hardcoded positions — ELIMINATE. Use `useTradeExecution().positions`.

Lines 92: `STRATEGIES` array with 8 hardcoded option strategies — verify these match what the API returns.

### MAKE ALL BUTTONS FUNCTIONAL
Quick execution buttons (lines 330-359) — ALREADY FUNCTIONAL via `useTradeExecution()` execute methods. Verify they work end-to-end.

Chart timeframe buttons (1M, 5M, 15M, 1H, 1D): These appear UI-only. Wire each to fetch new candle data from Alpaca bars API for the selected timeframe. Show loading spinner on active button.

Replace `window.confirm()` alignment preflight dialog with a custom Aurora-themed modal: dark bg, cyan "Confirm" button, gray "Cancel", showing order details.

Price ladder clicks: Clicking a price level should set it as the limit price in the order builder.

"Close" button (line 635) and "Adjust" button (line 636) — already wired to `closePosition?.()` and `adjustPosition?.()`. Verify the `?.` doesn't silently fail — these must call `useTradeExecution().closePosition(symbol, side)` and `useTradeExecution().adjustPosition(symbol, side)`.

### BIDIRECTIONAL DATA FLOW
The `useTradeExecution()` hook is the MOST bidirectional hook in the app — it supports:
- Read: portfolio, priceLadder, orderBook, positions, newsFeed, systemStatus
- Write: executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell, executeStopLoss, executeAdvancedOrder, closePosition, adjustPosition

Ensure ALL write methods are properly connected. The order form state (`orderForm`, `updateOrderForm`) should sync with the UI fields.

WebSocket integration is already present for real-time updates — verify it's connected and receiving messages.

Keep all existing hooks and WebSocket subscriptions. No mock data.
```

---

## 12. Risk Intelligence (`RiskIntelligence.jsx`)

**Mockup**: `docs/mockups-v3/images/13-risk-intelligence.png`

```
I'm aligning RiskIntelligence.jsx (~1464 lines) to pixel fidelity with mockup 13-risk-intelligence.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF. Low risk: green #10b981. Medium: amber #f59e0b. High: red #ef4444.

### MOCKUP LAYOUT (pixel fidelity)
Dense multi-panel layout:
- Panel 1 (top-left): Risk Configuration — table of 10+ parameters (Max leverage, Position size, Drawdown limit) each with value and indicator
- Panel 2 (top-right): Risk Score Heatmap — 10×10 colored grid, mostly green with yellow/orange cells
- Panel 3 (middle-left): Multi-Agent Risk Scoring — horizontal bars for 5-6 agents, green/yellow/orange by severity
- Panel 4 (middle-right): VaR & Stress Testing — numerical results, scenario analysis (3-5 scenarios)
- Panel 5 (bottom): Risk Score Distribution — horizontal stacked bars, 15-20 risk categories

### ELIMINATE MOCK/FALLBACK DATA
Search entire 1464-line file for all hardcoded fallback data:
- Risk parameter defaults that aren't from API
- Hardcoded correlation matrix values
- Static risk scores
- Any `FALLBACK_*` or `DEFAULT_*` constants with numerical values

Use these hooks (verify all are called):
- `useRiskScore()` — composite risk score
- `useDrawdownCheck()` — drawdown analysis
- `useKellyRanked()` — Kelly criterion rankings

Each null return should show a skeleton loader, never a fake number.

### MAKE ALL BUTTONS FUNCTIONAL
- Risk parameter sliders: Must persist changes via `useSettings().updateField('risk', paramKey, value)` then `saveCategory('risk')`.
- "EMERGENCY STOP ALL" button: Wire to POST `/orders/emergency-stop` with a 3-second countdown confirmation modal: "Flattening all positions in 3... 2... 1..." with cancel option.
- "Run New Sweep" button: Open modal to configure sweep parameters, then call parameter sweep API.
- Correlation matrix cells: Click to drill down showing the two correlated assets' details.
- 90-Day Risk History chart: Click on any point to see that day's risk breakdown.

### BIDIRECTIONAL DATA FLOW
- Risk parameters: Read from `useSettings()`, write via `updateField()` + `saveCategory('risk')`.
- Risk gauge: Display-only (expected) but should show clear labels and units.
- Stress test scenarios: Allow user to configure custom scenarios and run them.
- All risk hooks are GET-only polling. Write operations go through settings hook.

Keep all existing hooks. No mock data.
```

---

## 13. Active Trades (`Trades.jsx`)

**Mockup**: `docs/mockups-v3/images/Active-Trades.png`

```
I'm aligning Trades.jsx (~1553 lines) to pixel fidelity with mockup Active-Trades.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF. Positive P/L: emerald #10b981. Negative: red #ef4444.

### MOCKUP LAYOUT (pixel fidelity)
Full-width data table view:
- TOP: KPI summary cards in a row (Open Trades, Net P/L, Status)
- MAIN: Scrollable data table:
  - Columns: Position, Qty, Entry Price, Current Price, Unrealized PnL, PnL %, Return %, Side, Status, Last Price, Daily P/L, Entry Time, Exit Time, Actions
  - 20+ rows visible, color-coded by P/L direction
  - Each row expandable for full details
- BOTTOM: Summary statistics (Total positions, Total P/L, Win rate, Avg position size)

### ELIMINATE MOCK/FALLBACK DATA
Lines 50-55: Mini sparkline functions with generated/fallback data — wire to real data arrays from the API. When null, show flat gray line.

Search entire 1553-line file for ALL `FALLBACK_*`, `DEFAULT_*`, `sample*`, `mock*` constants. Replace each with the corresponding API data.

The MiniSparkline bar heights (as noted in summary) are NOT properly scaled to [min, max] of actual data — fix scaling to use real data range.

### MAKE ALL BUTTONS FUNCTIONAL
- Column headers: Must be clickable for sorting (ascending/descending toggle). Default: newest first.
- "Close" buttons on position rows: Wire to `useTradeExecution().closePosition(symbol, side)`.
- "Adjust" buttons: Wire to open a modal for modifying stop-loss/take-profit.
- "Flatten All Positions": Add prominent button in header, wire to POST `/orders/emergency-stop` with confirmation modal.
- "Download CSV": Add export button that generates CSV of all trades.
- Position rows should be clickable to expand inline showing entry date, entry price, current price, stop-loss, take-profit, council_decision_id, P&L sparkline since entry.

### BIDIRECTIONAL DATA FLOW
- Table sorting/filtering: Maintained in component state, applied to API data.
- Position actions (Close, Adjust): Write operations via trade execution service.
- Trade history export: Read-only (download).
- Add a tab toggle: "Positions | Orders | History" to consolidate views.

Ensure sticky table headers have bg `bg-[#0f1729]` with bottom border `border-b border-cyan-900/30`. P/L coloring needs colorblind-friendly directional icons: ▲ profit, ▼ loss, ─ flat.

Keep all existing hooks. No mock data.
```

---

## 14. Settings (`Settings.jsx`)

**Mockup**: `docs/mockups-v3/images/14-settings.png`

```
I'm aligning Settings.jsx (~1553 lines) to pixel fidelity with mockup 14-settings.png. The existing code is good — I need to: (1) match the mockup layout exactly, (2) replace ALL hardcoded/fallback data with live API data, (3) make ALL buttons functional, (4) wire FULL bidirectional data flow.

AURORA DARK THEME: bg #0a0e1a, panels #111827, accent cyan #00D9FF. Active toggles: cyan. Inactive: gray. Input focus: cyan border.

### MOCKUP LAYOUT (pixel fidelity)
Dense 2-column layout with collapsible sections:
- LEFT (40%): Settings navigation categories:
  - PLATFORM (6 items), INTELLIGENCE (5), EXECUTION (3), SYSTEM (4)
- RIGHT (60%): Settings detail panels (context-dependent):
  - Display Mode toggle (light/dark radio buttons)
  - Trading Mode (Paper/Live radio buttons)
  - Max Position Size slider (0-100%)
  - Notification toggles (Email, Slack, Telegram)
  - Risk Management (Kelly % slider, leverage slider)
  - API Configuration (masked key/secret fields)
  - Broker Settings (dropdowns)

### VERIFY FULL BIDIRECTIONAL DATA FLOW
The Settings page uses `useSettings()` which is THE MOST COMPLETE bidirectional hook:
- READ: `settings` object (nested by category)
- WRITE: `updateField(category, key, value)` → local state + dirty flag
- SAVE: `saveCategory(category)` → PUT to API
- RESET: `resetCategory(category)` → POST to API
- VALIDATE: `validateKey(provider, apiKey, secretKey)` → POST
- TEST: `testConnection(source)` → POST

VERIFY that EVERY form field actually calls `updateField()` on change. VERIFY that EVERY section has a working "Save" button calling `saveCategory()`. VERIFY that the `dirty` flag is checked and an "Unsaved Changes" banner appears when modified.

### MAKE ALL BUTTONS FUNCTIONAL
- "Save" buttons per section: Must call `saveCategory(category)` for the active section
- "Reset to Defaults": Must call `resetCategory(category)` WITH confirmation dialog showing what will change
- API key "Copy" buttons: Wire to clipboard copy of the FULL (unmasked) key value. Only enable if key is revealed.
- API key "Reveal" toggle (eye icon): Temporarily unmask key for 10 seconds, then re-mask.
- "Test Connection" buttons: Wire to `testConnection(source)` and show result (green check / red X) inline.
- Notification toggles (Slack/Email/Telegram): Show connection status dot (green if valid token, red if invalid, gray if not configured).
- "Import" / "Export" buttons: Wire to `exportSettings()` and `importSettings()`.

### ELIMINATE MOCK/FALLBACK DATA
Verify ALL settings values come from `useSettings().settings` — no hardcoded defaults in the UI. If settings is null (loading), show skeleton loaders for all fields.

### ADDITIONAL PIXEL FIDELITY
- Risk parameter sliders need explicit bounds labels: "Kelly Fraction: 0.05 - 0.50 (current: 0.25)"
- Add tick marks at key values (conservative 0.10, moderate 0.25, aggressive 0.40)
- Add preset row: "Conservative / Moderate / Aggressive" that sets all risk params at once
- LLM model selector should show descriptions: "Claude (Tier 3) — Deep reasoning only: strategy_critic, overnight_analysis"
- Settings sections should have sticky left sidebar for quick navigation between sections

Keep useSettings hook. No mock data.
```

---

## Cross-Cutting: Apply to ALL Pages

```
I'm doing a cross-cutting improvement pass across ALL 14 pages in frontend-v2/src/pages/. These are NOT new features — they're about making existing data flow work correctly.

### 1. Eliminate ALL fallback/mock data patterns

Search every page file for these anti-patterns and replace:
- `?? 87` or `?? 47` or any `?? <number>` → replace with `?? null` + show "—" or skeleton
- `|| []` with sample data arrays → replace with `|| []` + show empty state message
- `FALLBACK_*` constants with fake data → eliminate constant, use null + loading state
- `default*` arrays with hardcoded rows → eliminate, wire to API
- `genSparkline()` or random data functions → replace with real data, flat gray line when null
- `console.log(...)` as button handlers → wire to real API endpoints

### 2. Verify ALL useApi hooks are connected

Each page has specific useApi hooks. For every hook call, verify:
- The endpoint key exists in `config/api.js` (189 endpoints defined)
- The returned `data` is actually rendered (not ignored)
- The `loading` state shows a skeleton loader (not blank space or hardcoded fallback)
- The `error` state shows an inline error with "Retry" button (not silent failure)
- The `isStale` flag triggers a visual amber indicator (thin amber top-border)

### 3. Wire ALL write-capable endpoints

The following POST/PUT functions exist in useApi.js but may not be used on all relevant pages:
- `fetchCouncilEvaluate(symbol, timeframe, context)` — should be on Signal Intelligence, Dashboard
- `postBiasOverride(biasMultiplier)` — should be on Market Regime
- `postAgentOverrideStatus(agentName, action)` — should be on Agent Command Center, Patterns
- `postAgentOverrideWeight(agentName, alpha, beta)` — should be on Agent Command Center, Sentiment
- `putDirective(filename, content)` — should be accessible from Settings or a dedicated page

The `useSettings()` hook supports full CRUD — verify it's used on Settings AND on any page with configurable parameters.

The `useTradeExecution()` hook supports order execution — verify it's used on Trade Execution AND accessible from Dashboard/Signals.

### 4. Color theme consistency

All pages should use these exact colors (from UI-DESIGN-SYSTEM.md):
- bg-primary: #0a0e1a
- bg-panel: #111827
- bg-panel-hover: #1a2332
- accent-cyan: #00D9FF
- accent-emerald: #10b981
- accent-amber: #f59e0b
- accent-red: #ef4444
- accent-purple: #8B5CF6
- text-primary: #e2e8f0
- text-secondary: #94a3b8
- border: rgba(30, 41, 59, 0.5)

Audit each page for hardcoded hex values that don't match this palette. Standardize all color references.

No new mock data. Every component must show live data or a proper loading/empty state.
```
