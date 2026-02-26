# Oleh - Charting Engine Migration Guide

> **Date**: Feb 26, 2026 | **Priority**: HIGH | **Scope**: 4 pages + 1 shared component

---

## The 3 Charting Engines in This Project

Our frontend uses **3 charting/visualization libraries**. Here is what each does, where to get it, and what to do with it:

### 1. TradingView Lightweight Charts (PRIMARY - Production Standard)

| | |
|---|---|
| **npm package** | `lightweight-charts` |
| **Current version in package.json** | `^4.1.1` |
| **Latest available** | `5.0.8` (recommend staying on 4.x for now, upgrade later) |
| **Install** | `npm install lightweight-charts` (already installed) |
| **Docs** | https://tradingview.github.io/lightweight-charts/ |
| **GitHub** | https://github.com/tradingview/lightweight-charts |
| **React tutorial** | https://tradingview.github.io/lightweight-charts/tutorials/react/simple |
| **Bundle size** | ~45 KB (extremely lightweight) |
| **Purpose** | All financial chart visualizations (candlestick, line, area, histogram) |

**This is the PRODUCTION standard.** All pages must use this for charts.

### 2. Recharts (LEGACY - Being Replaced)

| | |
|---|---|
| **npm package** | `recharts` |
| **Current version in package.json** | `^2.10.3` |
| **Install** | Already installed, DO NOT add to new pages |
| **Purpose** | Legacy charts used in 4 pages that need migration |
| **Action** | REMOVE from pages as you migrate them to LW Charts |

**Do NOT use Recharts in any new work.** Migrate existing Recharts usage to Lightweight Charts.

### 3. ReactFlow (KEEP - Not a charting library)

| | |
|---|---|
| **npm package** | `reactflow` |
| **Current version in package.json** | `^11.10.1` |
| **Install** | Already installed |
| **Purpose** | Node/flow diagrams ONLY (used in MLInsights.jsx for agent architecture visualization) |
| **Action** | KEEP as-is. This is NOT for financial charts - it draws node graphs/flowcharts |

---

## What Needs Migration (4 Pages + 1 Component)

These files currently import from `'recharts'` and need to be converted to `'lightweight-charts'`:

| # | File | Path | Recharts Components Used | What to Replace With |
|---|------|------|----|----|
| 1 | SentimentIntelligence.jsx | `frontend-v2/src/pages/` | LineChart, AreaChart, BarChart, PieChart, ComposedChart | LW `createChart` + `addAreaSeries`, `addLineSeries`, `addHistogramSeries` |
| 2 | DataSourcesMonitor.jsx | `frontend-v2/src/pages/` | LineChart, AreaChart, BarChart, PieChart | LW `createChart` + `addAreaSeries`, `addLineSeries` |
| 3 | Patterns.jsx | `frontend-v2/src/pages/` | BarChart, LineChart, AreaChart, ComposedChart, Treemap | LW `createChart` + `addHistogramSeries`, `addLineSeries` |
| 4 | Settings.jsx | `frontend-v2/src/pages/` | Minimal charting | LW `createChart` if any charts needed |
| 5 | EquityCurveChart.jsx | `frontend-v2/src/components/charts/` | LineChart (shared component) | LW `createChart` + `addAreaSeries` (see RiskEquityLC.jsx as reference) |

> **NOTE**: `MLBrainFlywheel.jsx` also uses Recharts but it is V3 COMPLETE - leave it for now unless instructed otherwise.

---

## How to Use Lightweight Charts in React (Step by Step)

### Step 1: Import

```jsx
import { createChart, CrosshairMode, ColorType } from 'lightweight-charts';
```

### Step 2: Setup Refs

```jsx
const chartContainerRef = useRef(null);  // DOM container
const chartRef = useRef(null);           // Chart instance
const seriesRef = useRef(null);          // Series instance
```

### Step 3: Create Chart in useEffect

```jsx
useEffect(() => {
  if (!chartContainerRef.current) return;

  const chart = createChart(chartContainerRef.current, {
    layout: {
      background: { type: 'solid', color: 'transparent' },
      textColor: '#94a3b8',
      fontFamily: "'JetBrains Mono', monospace",
    },
    grid: {
      vertLines: { color: 'rgba(51, 65, 85, 0.4)' },
      horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
    },
    crosshair: {
      mode: CrosshairMode.Magnet,
    },
    rightPriceScale: {
      borderColor: 'rgba(51, 65, 85, 0.8)',
      autoScale: true,
    },
    timeScale: {
      borderColor: 'rgba(51, 65, 85, 0.8)',
      timeVisible: true,
      fitContent: true,
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
  });

  // Add series (choose type based on data)
  const series = chart.addAreaSeries({
    lineColor: '#06b6d4',
    topColor: 'rgba(6, 182, 212, 0.4)',
    bottomColor: 'rgba(6, 182, 212, 0.0)',
    lineWidth: 2,
  });

  chartRef.current = chart;
  seriesRef.current = series;

  // Resize observer
  const resizeObserver = new ResizeObserver(() => {
    chart.applyOptions({
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });
  });
  resizeObserver.observe(chartContainerRef.current);

  return () => {
    resizeObserver.disconnect();
    chart.remove();
  };
}, []);
```

### Step 4: Update Data When Props Change

```jsx
useEffect(() => {
  if (!seriesRef.current || !data) return;
  seriesRef.current.setData(data);
  chartRef.current?.timeScale().fitContent();
}, [data]);
```

### Step 5: JSX Container

```jsx
return (
  <div className="w-full h-full relative">
    <div ref={chartContainerRef} className="absolute inset-0" />
  </div>
);
```

---

## LW Charts Series Types (Recharts Equivalents)

| Recharts Component | LW Charts Equivalent | Method |
|---|---|---|
| `<LineChart>` + `<Line>` | Line Series | `chart.addLineSeries()` |
| `<AreaChart>` + `<Area>` | Area Series | `chart.addAreaSeries()` |
| `<BarChart>` + `<Bar>` | Histogram Series | `chart.addHistogramSeries()` |
| `<CandlestickChart>` | Candlestick Series | `chart.addCandlestickSeries()` |
| `<PieChart>` | No direct equivalent | Use Tailwind CSS donut/ring or keep Recharts for pie only |
| `<Treemap>` | No direct equivalent | Use CSS grid visualization or keep Recharts for treemap only |
| `<ComposedChart>` (multi-series) | Multiple series on same chart | `chart.addLineSeries()` + `chart.addHistogramSeries()` etc. |

> **Important**: PieChart and Treemap have no LW Charts equivalent. For those specific widgets, you can either:
> 1. Keep a small Recharts usage just for pie/treemap (acceptable)
> 2. Replace with Tailwind CSS custom components (preferred long-term)

---

## Our Dark Theme Config (MUST USE)

All charts must match our Bloomberg-style dark theme. Copy this config:

```jsx
const EMBODIER_CHART_THEME = {
  layout: {
    background: { type: 'solid', color: 'transparent' },
    textColor: '#94a3b8',                    // slate-400
    fontFamily: "'JetBrains Mono', monospace",
  },
  grid: {
    vertLines: { color: 'rgba(51, 65, 85, 0.4)' },
    horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
  },
  crosshair: { mode: CrosshairMode.Magnet },
  rightPriceScale: { borderColor: 'rgba(51, 65, 85, 0.8)' },
  timeScale: { borderColor: 'rgba(51, 65, 85, 0.8)', timeVisible: true },
};

// Brand colors for series:
// Primary:   '#06b6d4' (cyan-500)
// Secondary: '#10b981' (emerald-500)
// Warning:   '#f59e0b' (amber-500)
// Danger:    '#ef4444' (red-500)
// Purple:    '#8b5cf6' (violet-500)
```

---

## Reference Files (Already Working - Copy These Patterns)

Look at these completed files for working examples:

| File | What It Demonstrates |
|------|-----|
| `components/charts/RiskEquityLC.jsx` | Area series, resize observer, dark theme, data updates |
| `components/charts/MonteCarloLC.jsx` | Multiple line series (50+ lines), crosshair, simulation paths |
| `components/charts/MiniChart.jsx` | Compact sparkline chart |
| `pages/MarketRegime.jsx` | Full page with LW Charts + ColorType, regime bands |
| `pages/MLInsights.jsx` | LW Charts + ReactFlow together on same page |

---

## Data Format

Lightweight Charts expects data in this format:

```jsx
// Line / Area series
[
  { time: '2026-01-15', value: 125.50 },
  { time: '2026-01-16', value: 127.25 },
]

// Histogram series
[
  { time: '2026-01-15', value: 1500000, color: '#06b6d4' },
  { time: '2026-01-16', value: -500000, color: '#ef4444' },
]

// Candlestick series
[
  { time: '2026-01-15', open: 125.0, high: 128.5, low: 124.0, close: 127.25 },
]
```

**Time format**: `'YYYY-MM-DD'` string or Unix timestamp.

---

## Migration Checklist Per Page

For each of the 4 pages, follow this checklist:

- [ ] Remove `import { ... } from 'recharts';`
- [ ] Add `import { createChart, CrosshairMode } from 'lightweight-charts';`
- [ ] Add `useRef` for chartContainer, chart, and series refs
- [ ] Create chart in `useEffect` with our dark theme config
- [ ] Replace each `<ResponsiveContainer><LineChart>` with LW Chart `addLineSeries()`
- [ ] Replace each `<ResponsiveContainer><AreaChart>` with LW Chart `addAreaSeries()`
- [ ] Replace each `<ResponsiveContainer><BarChart>` with LW Chart `addHistogramSeries()`
- [ ] Add ResizeObserver for responsive sizing
- [ ] Add cleanup in useEffect return
- [ ] Wire to real API data via `useApi()` hook (replace any `generateSimulatedData()`)
- [ ] Test at full widescreen width
- [ ] Verify dark theme colors match rest of app

---

## Quick Commands

```bash
# You should NOT need to install anything new - all 3 libs are in package.json
# But if node_modules is missing:
cd frontend-v2
npm install

# Start dev server
npm run dev

# If you need to check versions:
npm list lightweight-charts recharts reactflow
```

---

## Questions?

Ping Erik on Slack. Reference files in `components/charts/` are your best templates.
