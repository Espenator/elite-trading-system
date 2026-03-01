# Embodier Trader - UI Design System

> **AUTHORITATIVE REFERENCE** for rendering ALL 14 pages.
> Derived from 6 approved mockup images in `docs/mockups-v3/images/`.
> Every page MUST match this spec exactly. No deviations.

## Approved Mockup Images (Source of Truth)

| # | File | Page | Key Elements |
|---|------|------|--------------|
| 1 | `01-agent-command-center-final.png` | Agent Command Center - Swarm Overview | Health matrix, activity feed, topology, resource monitor, conference pipeline, drift monitor, alerts, blackboard |
| 2 | `03-signal-intelligence.png` | Signal Intelligence V3 | Left sidebar nav, regime banner, stock chart with SMA/patterns, scanner modules, signal table, scoring engine, ML model control |
| 3 | `04-sentiment-intelligence.png` | Sentiment Intelligence | OpenClaw agent swarm, heatmap grid, 30-day sentiment chart, trade signals, radar chart, prediction market, scanner status matrix |
| 4 | `05-agent-command-center.png` | Agent Command Center - Live Wiring | Network topology (5 columns), connection health matrix, node discovery, websocket channels, API route map |
| 5 | `05b-agent-command-center-spawn.png` | Agent Command Center - Spawn & Scale | Spawn orchestrator, OpenClaw control, ML engine, NLP spawn prompt, template grid, custom builder, active agents table |
| 6 | `agent rgistery.png` | Agent Command Center - Agent Registry | Master agent table (20+ cols), agent inspector, config panel, performance metrics, agent logs, SHAP importance, lifecycle controls |

## Color Palette (EXACT)

```css
/* Background */
--bg-primary: #0B0E14;       /* Deep slate - main background */
--bg-card: #111827;           /* Card backgrounds */
--bg-card-alt: #1a1e2f;      /* Slightly lighter card variant */
--bg-input: #0f1219;          /* Input fields, table rows */
--bg-hover: #1e293b;          /* Hover states */
--bg-selected: #164e63;       /* Selected row highlight */

/* Borders */
--border-default: #1e293b;    /* Default card borders */
--border-accent: #06b6d4;     /* Active/focused borders */
--border-subtle: #374151;     /* Subtle dividers */

/* Primary Accent - Cyan/Teal */
--cyan-500: #06b6d4;          /* Primary action, active tabs, links */
--cyan-400: #22d3ee;          /* Hover states, highlights */
--cyan-300: #67e8f9;          /* Light accents */
--cyan-900: #164e63;          /* Muted cyan backgrounds */

/* Success - Green */
--green-500: #10b981;         /* Active, running, healthy, connected */
--green-400: #34d399;         /* Hover green */
--green-900: #064e3b;         /* Muted green background */

/* Warning - Amber */
--amber-500: #f59e0b;         /* Warning states, degraded */
--amber-400: #fbbf24;         /* Hover amber */
--amber-900: #78350f;         /* Muted amber background */

/* Danger - Red */
--red-500: #ef4444;           /* Error, stopped, kill switch */
--red-400: #f87171;           /* Hover red */
--red-900: #7f1d1d;           /* Muted red background */

/* Purple (Intelligence agents) */
--purple-500: #8b5cf6;        /* Execution type agents */
--purple-400: #a78bfa;

/* Pink (Sentiment) */
--pink-500: #ec4899;

/* Text */
--text-primary: #f8fafc;      /* White - primary text */
--text-secondary: #94a3b8;    /* Slate-400 - secondary text */
--text-muted: #64748b;        /* Slate-500 - muted labels */
--text-cyan: #06b6d4;         /* Cyan data values */
--text-green: #10b981;        /* Positive values */
--text-red: #ef4444;          /* Negative values */
--text-amber: #f59e0b;        /* Warning text */
```

## Typography

```css
/* Data/Numbers - ALWAYS monospace */
font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;

/* Headers/Labels - Inter UI */
font-family: 'Inter', system-ui, -apple-system, sans-serif;

/* Size Scale */
--text-xs: 0.65rem;     /* Dense table cells, sparkline labels */
--text-sm: 0.75rem;     /* Table data, secondary info */
--text-base: 0.8125rem; /* Standard text (13px) */
--text-lg: 0.9375rem;   /* Section headers (15px) */
--text-xl: 1.125rem;    /* Card titles (18px) */
--text-2xl: 1.5rem;     /* Page titles */
```

## Layout Patterns

### Global Header Bar (ALL pages)
- Fixed top bar, full width
- Left: Page icon + title + status badges (GREEN/YELLOW/RED)
- Center: System metrics (CPU, RAM, GPU with mini progress bars + %)
- Right: KILL SWITCH button (red, rounded) + "ELITE TRADING SYSTEM"
- Height: ~48px
- Background: slightly darker than --bg-primary

### Tab Navigation (Agent Command Center pages)
- Horizontal tab strip below header
- Active tab: cyan text + underline
- Inactive: muted slate text
- Tabs: Swarm Overview | Agent Registry | Spawn & Scale | Live Wiring Map | Blackboard & Comms | Conference & Consensus | ML Ops | Logs & Telemetry

### Left Sidebar Navigation (Signal Intelligence)
- Width: ~240px
- Sections with ALL CAPS headers: COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM
- Active item: cyan bg highlight with icon
- Icons before each nav item

### Card Component
- Background: --bg-card
- Border: 1px solid --border-default
- Border-radius: 6px (sm)
- Header: ALL CAPS, --text-secondary, font-size --text-sm, letter-spacing 0.05em
- Padding: 12px 16px
- No shadows (flat design)

### Data Tables
- Header row: uppercase, --text-muted, --text-xs
- Rows: alternating --bg-primary / --bg-input
- Hover: --bg-hover
- Selected: --bg-selected with cyan left border
- Dense: row height 28-32px
- Monospace font for ALL data cells

### Progress Bars
- Height: 4-6px
- Track: --border-default
- Fill: gradient from cyan to green (healthy) or amber to red (warning)
- Mini bars inline with metrics

### Status Badges
- RUNNING/ACTIVE: green bg, white text, rounded-full
- PAUSED: amber bg
- STOPPED/ERROR: red bg
- Font: --text-xs, uppercase, font-weight 600

### Buttons
- Primary: cyan bg (#06b6d4), white text, rounded-md
- Danger: red bg, white text (KILL SWITCH, Stop All)
- Warning: amber bg
- Ghost: transparent bg, cyan text, border
- Size: compact (py-1 px-3 text-xs)

## Chart Styles

### Stock Charts (TradingView lightweight-charts)
- Dark background matching --bg-card
- Candlesticks: green up (#10b981), red down (#ef4444)
- SMA lines: SMA20=cyan, SMA50=green, SMA200=amber (dashed)
- Volume: cyan bars (low opacity)
- Pattern annotations: amber dashed lines with labels

### Line Charts (recharts)
- Grid: subtle, --border-subtle
- Lines: cyan primary, green secondary, amber tertiary
- Area fill: 10% opacity of line color
- Axes: --text-muted

### Heatmaps
- Color scale: red (#ef4444) -> amber (#f59e0b) -> green (#10b981)
- Cell borders: 1px --bg-primary (gap effect)
- Text in cells: white, --text-xs, monospace

### Radar/Spider Charts
- Grid: --border-subtle
- Fill: cyan at 20% opacity
- Stroke: cyan

### Gauge/Ring Charts
- Track: --border-default
- Fill: cyan (good), amber (warning), red (critical)
- Center text: large monospace number

## Agent Type Color Coding

| Type | Color | Badge BG |
|------|-------|----------|
| Scanner | Cyan #06b6d4 | cyan-900 |
| Intelligence | Blue #3b82f6 | blue-900 |
| Execution | Purple #8b5cf6 | purple-900 |
| Streaming | Orange #f97316 | orange-900 |
| Sentiment | Pink #ec4899 | pink-900 |
| MLearning | Yellow #eab308 | yellow-900 |
| Conference | Green #10b981 | green-900 |

## Footer Bar (ALL pages)
- Fixed bottom, full width
- Left: WebSocket Connected + API Healthy indicators (green dots)
- Center: 42 agents | LLM Flow 847 | Conference 8/12
- Right: Last Refresh timestamp | Load metrics | Uptime
- Font: --text-xs, monospace
- Background: darker than --bg-primary

## Responsive Behavior
- Target: 2560px widescreen (primary)
- Minimum: 1920px
- Dense grid layouts: CSS Grid with minmax()
- Scrollable panels with thin cyan scrollbars
- No responsive breakpoints below 1440px (desktop-only app)

## Key UI Principles
1. **Maximum data density** - Every pixel carries information
2. **Glass-box transparency** - Show ALL system internals
3. **Institutional aesthetic** - Bloomberg Terminal meets sci-fi command center
4. **Monospace everything** - All numbers, IDs, timestamps in monospace
5. **Neon on dark** - Cyan/amber/red accents on near-black backgrounds
6. **Real-time feel** - Timestamps, blinking dots, live counters everywhere
7. **Recursive self-improvement** - Every page shows flywheel/learning metrics
8. **Every element clickable** - Hotlinked to deeper drill-down data

## Tailwind CSS Classes Reference

```jsx
// Card
<div className="bg-[#111827] border border-slate-700/50 rounded-md p-3">

// Card Header
<h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">

// Data Value
<span className="font-mono text-sm text-cyan-400">

// Table
<table className="w-full text-xs font-mono">
<th className="text-[10px] uppercase text-slate-500 px-2 py-1">
<td className="px-2 py-1 text-slate-300">

// Status Badge
<span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-green-500/20 text-green-400">

// Button Primary
<button className="px-3 py-1 text-xs font-semibold rounded bg-cyan-500 text-white hover:bg-cyan-400">

// Kill Switch
<button className="px-4 py-1.5 text-sm font-bold rounded-full bg-red-500 text-white animate-pulse">

// Page Background
<div className="min-h-screen bg-[#0B0E14] text-slate-200">
```

## Pages Still Needing Mockups (8 of 14)

These pages do NOT have approved mockup images yet.
They MUST be rendered using the exact same design system above.

1. Dashboard (page 4)
2. EV Opportunity Matrix (page 2)
3. Flywheel Console (page 3)
4. Trade Execution (page 6)
5. Performance Analytics (page 7)
6. Risk Intelligence (page 8)
7. Backtesting Engine (page 10)
8. Data Sources Monitor (page 14)

Refer to `docs/mockups-v3/FULL-MOCKUP-SPEC.md` for component specs per page.
