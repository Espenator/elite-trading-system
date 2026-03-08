# UI Fidelity Audit Report
## Embodier Trader — Mockup vs Current Render
### Generated: 2026-03-08  |  Methodology: pixel diff (pixelmatch, threshold=10%)

> **Scope**: 14 pages × 3 viewports (1920×1080, 1440×900, 1280×720)  
> **Baselines**: `docs/mockups-v3/images/` (primary canonical mockup per page)  
> **Current screenshots**: `artifacts/ui-screenshots/current/<page>/<viewport>.png`  
> **Diff images**: `artifacts/ui-screenshots/diff/<page>/<viewport>-diff.png`  
> **Machine-readable**: `docs/UI-FIDELITY-AUDIT.json`

---

## Quick Summary

| Result | Count |
|--------|-------|
| ✅ PASS (≤10% mismatch) | 2 |
| ❌ FAIL (>10% mismatch) | 12 |

> **Note on mismatch scores**: Baselines are mockup images at their native design resolution; they are scaled to match the screenshot viewport for comparison. The mismatch percentages reflect layout, color, and content differences — **not rendering bugs** per se. Pages with 15–25% mismatch are typically showing loading states (no backend running in CI) rather than broken layouts.

---

## Mockup → Route Mapping

| # | Mockup File | Route | Page Component | Match Level |
|---|-------------|-------|----------------|-------------|
| 1 | `docs/mockups-v3/images/02-intelligence-dashboard.png` | `/dashboard` | `src/pages/Dashboard.jsx` | ✅ PASS |
| 2 | `docs/mockups-v3/images/01-agent-command-center-final.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` | ❌ FAIL |
| 3 | `docs/mockups-v3/images/05-agent-command-center.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Live Wiring tab) | ❌ FAIL |
| 4 | `docs/mockups-v3/images/05b-agent-command-center-spawn.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Spawn & Scale tab) | ❌ FAIL |
| 5 | `docs/mockups-v3/images/05c-agent-registry.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Registry tab) | ❌ FAIL |
| 6 | `docs/mockups-v3/images/agent command center brain map.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Brain Map tab) | ❌ FAIL |
| 7 | `docs/mockups-v3/images/agent command center node control.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Node Control tab) | ❌ FAIL |
| 8 | `docs/mockups-v3/images/agent command center swarm overview.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Swarm tab) | ❌ FAIL |
| 9 | `docs/mockups-v3/images/realtimeblackbard fead.png` | `/agents` | `src/pages/AgentCommandCenter.jsx` (Blackboard tab) | ❌ FAIL |
| 10 | `docs/mockups-v3/images/04-sentiment-intelligence.png` | `/sentiment` | `src/pages/SentimentIntelligence.jsx` | ❌ FAIL |
| 11 | `docs/mockups-v3/images/09-data-sources-manager.png` | `/data-sources` | `src/pages/DataSourcesMonitor.jsx` | ❌ FAIL |
| 12 | `docs/mockups-v3/images/03-signal-intelligence.png` | `/signal-intelligence-v3` | `src/pages/SignalIntelligenceV3.jsx` | ❌ FAIL |
| 13 | `docs/mockups-v3/images/06-ml-brain-flywheel.png` | `/ml-brain` | `src/pages/MLBrainFlywheel.jsx` | ✅ PASS |
| 14 | `docs/mockups-v3/images/07-screener-and-patterns.png` | `/patterns` | `src/pages/Patterns.jsx` | ❌ FAIL |
| 15 | `docs/mockups-v3/images/08-backtesting-lab.png` | `/backtest` | `src/pages/Backtesting.jsx` | ❌ FAIL |
| 16 | `docs/mockups-v3/images/11-performance-analytics-fullpage.png` | `/performance` | `src/pages/PerformanceAnalytics.jsx` | ❌ FAIL |
| 17 | `docs/mockups-v3/images/10-market-regime-green.png` | `/market-regime` | `src/pages/MarketRegime.jsx` | ❌ FAIL |
| 18 | `docs/mockups-v3/images/10-market-regime-red.png` | `/market-regime` | `src/pages/MarketRegime.jsx` (state variant) | ❌ FAIL |
| 19 | `docs/mockups-v3/images/Active-Trades.png` | `/trades` | `src/pages/Trades.jsx` | ❌ FAIL |
| 20 | `docs/mockups-v3/images/13-risk-intelligence.png` | `/risk` | `src/pages/RiskIntelligence.jsx` | ❌ FAIL |
| 21 | `docs/mockups-v3/images/12-trade-execution.png` | `/trade-execution` | `src/pages/TradeExecution.jsx` | ❌ FAIL |
| 22 | `docs/mockups-v3/images/14-settings.png` | `/settings` | `src/pages/Settings.jsx` | ❌ FAIL |

---

## Per-Page Diff Scores

| Page | 1920×1080 | 1440×900 | 1280×720 | Overall | Priority |
|------|-----------|----------|----------|---------|----------|
| dashboard | 5.50% ✅ | 6.26% ✅ | 6.82% ✅ | **PASS** | P2 |
| ml-brain | 5.71% ✅ | 7.19% ✅ | 7.45% ✅ | **PASS** | P2 |
| risk | 14.97% ❌ | 16.35% ❌ | 15.63% ❌ | FAIL | P2 |
| settings | 15.54% ❌ | 15.89% ❌ | 16.81% ❌ | FAIL | P2 |
| performance | 16.38% ❌ | 17.04% ❌ | 18.28% ❌ | FAIL | P2 |
| trades | 16.85% ❌ | 18.02% ❌ | 18.63% ❌ | FAIL | P2 |
| data-sources | 18.17% ❌ | 18.74% ❌ | 22.48% ❌ | FAIL | P1 |
| trade-execution | 18.58% ❌ | 18.67% ❌ | 19.90% ❌ | FAIL | P1 |
| signal-intelligence | 19.84% ❌ | 21.60% ❌ | 22.96% ❌ | FAIL | P1 |
| patterns | 20.32% ❌ | 21.77% ❌ | 22.97% ❌ | FAIL | P1 |
| agent-command-center | 21.22% ❌ | 21.97% ❌ | 22.71% ❌ | FAIL | P1 |
| backtesting | 21.41% ❌ | 23.32% ❌ | 24.67% ❌ | FAIL | P1 |
| market-regime | 21.84% ❌ | 22.65% ❌ | 23.76% ❌ | FAIL | P1 |
| sentiment-intelligence | 34.08% ❌ | 35.72% ❌ | 35.33% ❌ | FAIL | **P0** |

---

## Screenshot & Diff Artifact Paths

| Page | Baseline | Current (1920×1080) | Diff (1920×1080) |
|------|----------|---------------------|------------------|
| dashboard | `artifacts/ui-screenshots/baseline/dashboard/mockup.png` | `artifacts/ui-screenshots/current/dashboard/1920x1080.png` | `artifacts/ui-screenshots/diff/dashboard/1920x1080-diff.png` |
| agent-command-center | `artifacts/ui-screenshots/baseline/agent-command-center/mockup.png` | `artifacts/ui-screenshots/current/agent-command-center/1920x1080.png` | `artifacts/ui-screenshots/diff/agent-command-center/1920x1080-diff.png` |
| sentiment-intelligence | `artifacts/ui-screenshots/baseline/sentiment-intelligence/mockup.png` | `artifacts/ui-screenshots/current/sentiment-intelligence/1920x1080.png` | `artifacts/ui-screenshots/diff/sentiment-intelligence/1920x1080-diff.png` |
| data-sources | `artifacts/ui-screenshots/baseline/data-sources/mockup.png` | `artifacts/ui-screenshots/current/data-sources/1920x1080.png` | `artifacts/ui-screenshots/diff/data-sources/1920x1080-diff.png` |
| signal-intelligence | `artifacts/ui-screenshots/baseline/signal-intelligence/mockup.png` | `artifacts/ui-screenshots/current/signal-intelligence/1920x1080.png` | `artifacts/ui-screenshots/diff/signal-intelligence/1920x1080-diff.png` |
| ml-brain | `artifacts/ui-screenshots/baseline/ml-brain/mockup.png` | `artifacts/ui-screenshots/current/ml-brain/1920x1080.png` | `artifacts/ui-screenshots/diff/ml-brain/1920x1080-diff.png` |
| patterns | `artifacts/ui-screenshots/baseline/patterns/mockup.png` | `artifacts/ui-screenshots/current/patterns/1920x1080.png` | `artifacts/ui-screenshots/diff/patterns/1920x1080-diff.png` |
| backtesting | `artifacts/ui-screenshots/baseline/backtesting/mockup.png` | `artifacts/ui-screenshots/current/backtesting/1920x1080.png` | `artifacts/ui-screenshots/diff/backtesting/1920x1080-diff.png` |
| performance | `artifacts/ui-screenshots/baseline/performance/mockup.png` | `artifacts/ui-screenshots/current/performance/1920x1080.png` | `artifacts/ui-screenshots/diff/performance/1920x1080-diff.png` |
| market-regime | `artifacts/ui-screenshots/baseline/market-regime/mockup.png` | `artifacts/ui-screenshots/current/market-regime/1920x1080.png` | `artifacts/ui-screenshots/diff/market-regime/1920x1080-diff.png` |
| trades | `artifacts/ui-screenshots/baseline/trades/mockup.png` | `artifacts/ui-screenshots/current/trades/1920x1080.png` | `artifacts/ui-screenshots/diff/trades/1920x1080-diff.png` |
| risk | `artifacts/ui-screenshots/baseline/risk/mockup.png` | `artifacts/ui-screenshots/current/risk/1920x1080.png` | `artifacts/ui-screenshots/diff/risk/1920x1080-diff.png` |
| trade-execution | `artifacts/ui-screenshots/baseline/trade-execution/mockup.png` | `artifacts/ui-screenshots/current/trade-execution/1920x1080.png` | `artifacts/ui-screenshots/diff/trade-execution/1920x1080-diff.png` |
| settings | `artifacts/ui-screenshots/baseline/settings/mockup.png` | `artifacts/ui-screenshots/current/settings/1920x1080.png` | `artifacts/ui-screenshots/diff/settings/1920x1080-diff.png` |

---

## Per-Page Visual Delta Analysis

### P0 — BLOCKING

---

#### sentiment-intelligence — 34–36% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/04-sentiment-intelligence.png`
- **Code**: `src/pages/SentimentIntelligence.jsx`
- **Route**: `/sentiment`
- **Screenshots**: `artifacts/ui-screenshots/current/sentiment-intelligence/`

**Top visual deltas:**
- Layout is structurally different: mockup shows a 3-column grid; code renders a 2-column + sidebar
- Sentiment heatmap (word cloud style) in mockup is absent in current render
- Mock shows "Fear & Greed" gauge as a prominent centerpiece; code has a smaller variant
- Color palette: mockup uses amber/orange for sentiment positive; code uses cyan/emerald
- Typography: mockup uses `1.2rem` section headers; code uses `0.75rem`
- No backend → all data sections show skeleton loaders, adding blank space

**Recommended fixes:**
- File: `src/pages/SentimentIntelligence.jsx` — add the 3-column grid layout (`grid-cols-3`)
- File: `src/pages/SentimentIntelligence.jsx` — implement the word-cloud / sentiment heatmap component (referenced in mockup top-center)
- Ensure Fear & Greed gauge is sized to match `h-48 w-48` as in mockup
- Add `text-amber-400` color variant for positive sentiment indicators

---

### P1 — HIGH

---

#### agent-command-center — 21–23% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/01-agent-command-center-final.png` (+ 7 tab variants)
- **Code**: `src/pages/AgentCommandCenter.jsx`
- **Route**: `/agents`

**Top visual deltas:**
- AGENT HEALTH MATRIX (6×2 dot grid) is present in mockup but rendered as text list in code
- SWARM TOPOLOGY network graph layout differs from mockup; edges have different curve style
- ELO Leaderboard in mockup has a metallic gold/silver/bronze styling; code has plain table
- AGENT RESOURCE MONITOR table column widths differ from mockup
- Tab bar spacing and icon alignment differs

**Recommended fixes:**
- File: `src/pages/AgentCommandCenter.jsx` → Swarm Overview tab — use `grid grid-cols-6 gap-1` for health matrix dots
- File: `src/pages/agent-tabs/` — verify each tab component matches its dedicated mockup
- ELO table: add `bg-gradient-to-r from-yellow-500/20` for top-3 rows

---

#### backtesting — 21–25% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/08-backtesting-lab.png`
- **Code**: `src/pages/Backtesting.jsx`
- **Route**: `/backtest`

**Top visual deltas:**
- Equity curve chart takes up 60% of screen in mockup; current is ~40%
- Strategy comparison table in mockup has color-coded P&L cells; code uses plain text
- Parameter input panel is on the right in mockup; may be below in code
- Run backtest button styling differs (mockup: cyan gradient pill; code may differ)

**Recommended fixes:**
- File: `src/pages/Backtesting.jsx` — resize equity chart container to `h-[360px]` or adjust flex proportions
- Add `text-emerald-400` / `text-red-400` to P&L cells based on sign

---

#### market-regime — 21–24% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/10-market-regime-green.png`
- **Code**: `src/pages/MarketRegime.jsx`
- **Route**: `/market-regime`

**Top visual deltas:**
- Large regime indicator badge (BULL/BEAR/NEUTRAL) in mockup is visually prominent; code version is smaller
- Regime confidence gauge (semicircular) differs in size and proportions
- Historical regime transitions timeline (bottom strip) in mockup; may be absent in code
- Color tokens: mockup uses `green-400` for bull; ensure code uses same

**Recommended fixes:**
- File: `src/pages/MarketRegime.jsx` — increase regime badge to `text-6xl font-black`
- Add historical regime strip at page bottom if missing

---

#### patterns — 20–23% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/07-screener-and-patterns.png`
- **Code**: `src/pages/Patterns.jsx`
- **Route**: `/patterns`

**Top visual deltas:**
- Pattern cards in mockup have mini chart thumbnails; code may show text-only list
- Filter sidebar width differs (mockup: 280px; code may be narrower)
- Pattern confidence bar width/color differs

**Recommended fixes:**
- File: `src/pages/Patterns.jsx` — ensure pattern cards have `w-[280px]` chart thumbnails
- Check `PatternCard` component for `aspect-video` chart placeholder

---

#### signal-intelligence — 19–23% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/03-signal-intelligence.png`
- **Code**: `src/pages/SignalIntelligenceV3.jsx`
- **Route**: `/signal-intelligence-v3`

**Top visual deltas:**
- Scanner results table column alignment differs
- Signal strength bar chart (right panel) proportions differ
- Filter pill row in mockup uses more distinct active/inactive states

**Recommended fixes:**
- File: `src/pages/SignalIntelligenceV3.jsx` — audit table `col-span` grid values vs mockup
- Check active filter pill color: should be `bg-cyan-500` not `bg-cyan-500/20`

---

#### data-sources — 18–22% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/09-data-sources-manager.png`
- **Code**: `src/pages/DataSourcesMonitor.jsx`
- **Route**: `/data-sources`

**Top visual deltas:**
- Source health grid in mockup is 3 columns; code may be 2 columns at some viewports
- Status indicator colors: mockup uses solid green/red dots; code may use semitransparent

**Recommended fixes:**
- File: `src/pages/DataSourcesMonitor.jsx` — use `grid-cols-3` for source cards
- Use `bg-emerald-500` (solid) not `bg-emerald-500/50` for active status dots

---

#### trade-execution — 18–20% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/12-trade-execution.png`
- **Code**: `src/pages/TradeExecution.jsx`
- **Route**: `/trade-execution`

**Top visual deltas:**
- Order entry form layout differs (mockup: 2-column; code may be single column)
- L2 order book columns in mockup are more compact (8px row height vs code's default)
- Execution status badge styling differs

**Recommended fixes:**
- File: `src/pages/TradeExecution.jsx` — add `grid grid-cols-2 gap-4` to order entry section
- L2 rows: use `py-0.5 text-[11px]` for ultra-dense styling

---

### P2 — MEDIUM

---

#### performance — 16–18% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/11-performance-analytics-fullpage.png`
- **Code**: `src/pages/PerformanceAnalytics.jsx`
- **Route**: `/performance`

**Top visual deltas:**
- KPI cards (Sharpe, Max DD, Win Rate, etc.) use different font sizes in mockup vs code
- Equity curve chart in mockup shows drawdown overlay; code may not
- Monthly returns heatmap cell sizes differ

**Recommended fixes:**
- File: `src/pages/PerformanceAnalytics.jsx` — KPI cards: `text-3xl font-black` for main value
- Add drawdown overlay to equity curve (`fill-red-500/20` below baseline)

---

#### trades — 16–19% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/Active-Trades.png`
- **Code**: `src/pages/Trades.jsx`
- **Route**: `/trades`

**Top visual deltas:**
- P&L column should use `text-emerald-400`/`text-red-400` with sign indicator
- Table row hover state uses stronger highlight in mockup

**Recommended fixes:**
- File: `src/pages/Trades.jsx` — P&L cell: add conditional `text-emerald-400` for positive, `text-red-400` for negative

---

#### risk — 14–16% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/13-risk-intelligence.png`
- **Code**: `src/pages/RiskIntelligence.jsx`
- **Route**: `/risk`

**Top visual deltas:**
- Risk gauge needle angle may not match mockup
- Position sizing breakdown chart proportions differ slightly

**Recommended fixes:**
- File: `src/pages/RiskIntelligence.jsx` — minor layout polish; mostly data-driven differences

---

#### settings — 15–17% mismatch ❌
- **Mockup**: `docs/mockups-v3/images/14-settings.png`
- **Code**: `src/pages/Settings.jsx`
- **Route**: `/settings`

**Top visual deltas:**
- Section divider spacing differs (mockup uses 32px gap; code may use 16px)
- Toggle switch size differs (mockup: 48px wide; code uses default)

**Recommended fixes:**
- File: `src/pages/Settings.jsx` — `space-y-8` between sections; toggle: `w-12 h-6`

---

#### dashboard — 5–7% mismatch ✅
- **Status**: PASS — closest fidelity in the app
- Minor pixel-level differences due to:
  - Dynamic data / loading states (no backend)
  - Animation frames captured mid-transition

---

#### ml-brain — 5–7% mismatch ✅
- **Status**: PASS — strong structural match
- Small differences from loading state (no backend pipeline data)

---

## Priority Fix Queue

| Priority | Page | Change | Est. Effort |
|----------|------|--------|-------------|
| P0 | `SentimentIntelligence.jsx` | Add 3-column layout + word-cloud sentiment heatmap | 3–4h |
| P1 | `AgentCommandCenter.jsx` | Health matrix dot grid + ELO gold/silver/bronze styling | 2h |
| P1 | `Backtesting.jsx` | Equity chart height + P&L coloring | 1h |
| P1 | `MarketRegime.jsx` | Regime badge enlargement + historical timeline strip | 1.5h |
| P1 | `Patterns.jsx` | Pattern card chart thumbnails + filter sidebar width | 2h |
| P1 | `SignalIntelligenceV3.jsx` | Active filter pill styling + table column alignment | 1h |
| P1 | `DataSourcesMonitor.jsx` | 3-column source grid + solid status dots | 1h |
| P1 | `TradeExecution.jsx` | 2-column order entry form + L2 row density | 1.5h |
| P2 | `PerformanceAnalytics.jsx` | KPI font sizes + drawdown overlay | 1h |
| P2 | `Trades.jsx` | P&L conditional coloring | 30min |
| P2 | `RiskIntelligence.jsx` | Minor layout polish | 1h |
| P2 | `Settings.jsx` | Section spacing + toggle size | 30min |

---

## Visual Regression Tooling

| Script | Command | Description |
|--------|---------|-------------|
| `ui:run` | `npm run ui:run` | Start Vite dev server on port 3000 |
| `ui:baseline` | `npm run ui:baseline` | Copy mockups to `artifacts/…/baseline/` |
| `ui:screenshot` | `npm run ui:screenshot` | Capture current screenshots at 3 viewports |
| `ui:diff` | `npm run ui:diff` | Run pixel diff, output `diff-report.json` |
| `ui:audit` | `npm run ui:audit` | Run all three steps sequentially |
| Visual regression tests | `npx playwright test e2e/visual-regression.spec.js` | Playwright-based smoke + screenshot suite |

**CI Workflow**: `.github/workflows/ui-fidelity.yml`
- Runs on every PR and push to `main`
- Uploads screenshots + diffs as GitHub Actions artifacts (30-day retention)
- Warn-only by default; set repo variable `STRICT_DIFF=1` to make failures blocking
