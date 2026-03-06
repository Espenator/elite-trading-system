# Embodier Trader - Status & TODO Update

## Date: March 6, 2026
## Author: Claude (Senior Engineering Partner) + Espen
## Repository: github.com/Espenator/elite-trading-system

---

## EXECUTIVE SUMMARY

A full pixel-by-pixel mockup fidelity audit was completed comparing all **23 mockup images** in `docs/mockups-v3/images/` against all **17 frontend page files** in `frontend-v2/src/pages/`.

**Result**: 9 pages are in good shape, 11 pages need partial fixes, 1 has a structural conflict, and 1 has no mockup target.

**Estimated total fix effort**: 33-47 hours

**Detailed audit report**: `docs/MOCKUP-FIDELITY-AUDIT.md`

---

## WHAT WAS DONE (Mar 6 Session)

- [x] Read and analyzed all 23 mockup images (23 PNG files, 120MB+ total)
- [x] Read and analyzed all 17 frontend page files (850KB+ of JSX)
- [x] Read shared layout components (Layout, Sidebar, Header, Footer, Card, Button, Badge, DataTable, etc.)
- [x] Read Tailwind config, design system doc, global CSS
- [x] Created page-by-page mapping: which mockup maps to which code file
- [x] Identified every structural, component-level, and cosmetic gap
- [x] Generated comprehensive audit report at `docs/MOCKUP-FIDELITY-AUDIT.md`
- [x] Updated `project_state.md` with full fidelity status table
- [x] Created this status doc

---

## MOCKUP → CODE MAPPING (Complete)

### 23 Mockup Images → 17 Page Files

```
MOCKUP                                    → PAGE FILE                      → TAB/VIEW
─────────────────────────────────────────────────────────────────────────────────────
01-agent-command-center-final.png         → AgentCommandCenter.jsx         → Tab 1: Swarm Overview
02-intelligence-dashboard.png             → Dashboard.jsx                  → Main view
03-signal-intelligence.png                → SignalIntelligenceV3.jsx       → Main view
04-sentiment-intelligence.png             → SentimentIntelligence.jsx      → Main view
05-agent-command-center.png               → AgentCommandCenter.jsx         → Tab 4: Live Wiring
05b-agent-command-center-spawn.png        → AgentCommandCenter.jsx         → Tab 3: Spawn & Scale
05c-agent-registry.png                    → AgentCommandCenter.jsx         → Tab 2: Agent Registry
06-ml-brain-flywheel.png                  → MLBrainFlywheel.jsx            → Main view
07-screener-and-patterns.png              → Patterns.jsx                   → Main view
08-backtesting-lab.png                    → Backtesting.jsx                → Main view
09-data-sources-manager.png               → DataSourcesMonitor.jsx         → Main view
10-market-regime-green.png                → MarketRegime.jsx               → GREEN state
10-market-regime-red.png                  → MarketRegime.jsx               → RED state
11-performance-analytics-fullpage.png     → PerformanceAnalytics.jsx       → Main view
12-trade-execution.png                    → TradeExecution.jsx             → Main view
13-risk-intelligence.png                  → RiskIntelligence.jsx           → Main view
14-settings.png                           → Settings.jsx                   → Main view
Active-Trades.png                         → Trades.jsx                     → Main view
agent command center brain map.png        → AgentCommandCenter.jsx         → Tab 9: Brain Map
agent command center node control.png     → AgentCommandCenter.jsx         → Tab 10: Node Control
agent command center swarm overview.png   → SwarmIntelligence.jsx (DUPE)   → ⚠️ CONFLICT
realtimeblackbard fead.png                → AgentCommandCenter.jsx         → Tab 5: Blackboard
(no mockup)                               → CognitiveDashboard.jsx         → ❌ NO TARGET
```

---

## FIDELITY SCORECARD

### 🟢 GOOD (9 pages — need polish only)
These pages have correct structure, correct panels, correct data. Minor CSS/font/spacing tweaks.

| Page | File | Notes |
|------|------|-------|
| Dashboard | `Dashboard.jsx` (83KB) | All 21-col table, right panel, ticker strip, footer present |
| Signal Intelligence V3 | `SignalIntelligenceV3.jsx` (63KB) | 4-column layout, 14 scanners, chart, scoring engine, ML models all correct |
| ML Brain & Flywheel | `MLBrainFlywheel.jsx` (22KB) | KPI strip, charts, inference fleet, learning log correct |
| Screener & Patterns | `Patterns.jsx` (40KB) | Both engine panels, live feed, arsenal, forming detections correct |
| Backtesting Lab | `Backtesting.jsx` (45KB) | All 5 rows, 28 KPIs, 8 charts, trade log correct |
| Data Sources | `DataSourcesMonitor.jsx` (45KB) | Previously verified 100% to mockup 09 |
| Market Regime | `MarketRegime.jsx` (40KB) | Both GREEN/RED states, all panels, footer ticker correct |
| Settings | `Settings.jsx` (48KB) | 5x5 grid of 25 section cards, all controls correct |
| Active Trades | `Trades.jsx` (32KB) | Command strip, positions/orders tables, quick execute correct |

### 🟡 PARTIAL (8 pages — need component/panel additions)

| Page | File | What's Missing |
|------|------|----------------|
| ACC Swarm Overview (Tab 1) | `AgentCommandCenter.jsx` | Health Matrix, Activity Feed, Topology, ELO Leaderboard, Resource Monitor, Conference Pipeline, Drift Monitor, System Alerts, Quick Actions, Team Status, Blackboard Feed (mockup shows 12+ panels, code has card grid) |
| ACC Agent Registry (Tab 2) | `AgentCommandCenter.jsx` | Agent Cards Grid should be removed, table needs more columns, lifecycle bar needs repositioning |
| ACC Live Wiring (Tab 4) | `AgentCommandCenter.jsx` | Dynamic Node Discovery panel missing |
| ACC Blackboard (Tab 5) | `AgentCommandCenter.jsx` | Sub-tab navigation missing |
| ACC Brain Map (Tab 9) | `AgentCommandCenter.jsx` | Node metadata enrichment, toolbar actions, connection animations |
| ACC Node Control (Tab 10) | `AgentCommandCenter.jsx` | HITL detail table, Override History Log, HITL Analytics charts |
| Sentiment | `SentimentIntelligence.jsx` | Heatmap density, scanner matrix dot rendering, emergency alerts |
| Performance Analytics | `PerformanceAnalytics.jsx` | Trading Grade badge positioning, Returns Heatmap verification |
| Trade Execution | `TradeExecution.jsx` | Strike selector chips, order book depth bars |
| Risk Intelligence | `RiskIntelligence.jsx` | Low-res mockup makes exact comparison hard |

### 🔴 CONFLICTS (2 items)

| Issue | Details |
|-------|---------|
| SwarmIntelligence.jsx DUPLICATE | This file at `/swarm-intelligence` duplicates AgentCommandCenter functionality. Either merge into ACC or delete. |
| CognitiveDashboard.jsx NO MOCKUP | Page exists in code but has no corresponding mockup image. Needs a mockup created or should follow design system defaults. |

---

## SHARED LAYOUT FINDINGS

### Sidebar (`components/layout/Sidebar.jsx`)
- 16 navigation items across 5 sections (COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM)
- Expanded: 256px, Collapsed: 64px
- Active item: `bg-primary/30 text-primary` with cyan glow
- ✅ Matches mockup sidebar structure

### Header (`components/layout/Header.jsx`)
- Search bar + CNS status badges + Notifications + User menu
- 64px height, sticky top
- ⚠️ Some pages (Dashboard, ACC, Trades, Market Regime) render their own custom headers INSIDE the page — potential double-header issue

### Shared Card Component
- Uses `rounded-xl` (12px) but design system spec says `rounded-md` (6px)
- Card headers use `text-sm font-semibold text-white` but spec says `text-xs uppercase tracking-wider text-slate-400`
- **Decision needed**: Update Card component OR update design system doc

### Design System Colors (verified in Tailwind config)
- `primary`: #06b6d4 (cyan) ✅
- `success`: #10b981 (green) ✅
- `danger`: #ef4444 (red) ✅
- `warning`: #f59e0b (amber) ✅
- `dark`: #0B0E14 (background) ✅
- `surface`: #111827 (card bg) ✅
- Fonts: Inter + JetBrains Mono ✅ (configured, need to verify loading)

---

## PRIORITY FIX QUEUE

### P0 — Critical (structural mismatches)
| # | Task | Est Hours | Blocked By |
|---|------|-----------|------------|
| P0.1 | ACC Swarm Overview tab: full restructure from card grid to 12-panel command center | 8-12 | — |
| P0.2 | ACC Node Control tab: add HITL detail table, Override History, Analytics charts | 4-6 | — |
| P0.3 | Footer consistency: add matching footer bars to all pages | 2-3 | — |
| P0.4 | SwarmIntelligence.jsx: decide merge/delete, remove duplicate | 1-2 | Espen decision |

### P1 — Medium (missing components)
| # | Task | Est Hours |
|---|------|-----------|
| P1.1 | ACC Swarm Overview: add all 12 missing panels | (included in P0.1) |
| P1.2 | ACC Blackboard: add sub-tab navigation | 1-2 |
| P1.3 | ACC Brain Map: enhance node metadata | 2-3 |
| P1.4 | Sentiment: heatmap density, scanner matrix, emergency alerts | 2-3 |
| P1.5 | Performance Analytics: badge position, returns heatmap | 2-3 |
| P1.6 | Card border-radius standardization | 1 |
| P1.7 | Card header styling standardization | 1 |
| P1.8 | JetBrains Mono font loading | 0.5 |
| P1.9 | Verify no double-header on custom-header pages | 1 |

### P2 — Minor (cosmetic polish)
| # | Task | Est Hours |
|---|------|-----------|
| P2.1 | All pages: font size audit | 2 |
| P2.2 | All pages: color value audit vs design system | 2 |
| P2.3 | Chart styling: grid lines, axes, fills | 2 |
| P2.4 | Score bar proportions on Dashboard | 1 |
| P2.5 | Strike selector chips on Trade Execution | 1 |

**Total: 33-47 hours**

---

## RECOMMENDED EXECUTION ORDER

1. **P0.4** — Decide on SwarmIntelligence.jsx (quick decision, blocks nothing but resolves confusion)
2. **P0.1** — ACC Swarm Overview restructure (biggest gap, most visible page)
3. **P0.2** — ACC Node Control additions (second biggest gap)
4. **P1.6 + P1.7** — Card component standardization (affects all pages, do early)
5. **P1.8** — Font loading (quick win)
6. **P0.3** — Footer consistency (affects all pages)
7. **P1.2-P1.5** — Missing panels per page (can be parallelized)
8. **P2.x** — Polish pass (do last)

---

## FILE REFERENCE

| Document | Path | What It Contains |
|----------|------|------------------|
| **This Status Doc** | `docs/STATUS-AND-TODO-2026-03-06.md` | Current priorities |
| **Full Audit Report** | `docs/MOCKUP-FIDELITY-AUDIT.md` | Per-page gap analysis with fix instructions |
| **Project State** | `project_state.md` | Architecture, roadmap, rules, fidelity table |
| **Design System** | `docs/UI-DESIGN-SYSTEM.md` | Colors, typography, layout rules, Tailwind classes |
| **Mockup Images** | `docs/mockups-v3/images/` | 23 PNG source-of-truth images |

---

## FOR AI ASSISTANTS

When working on UI fidelity fixes:

1. **ALWAYS read the relevant mockup image first** — it's the source of truth
2. **ALWAYS read `docs/UI-DESIGN-SYSTEM.md`** for colors, fonts, spacing rules
3. **ALWAYS read `docs/MOCKUP-FIDELITY-AUDIT.md`** for the specific gaps on the page you're fixing
4. **Match mockup pixel-for-pixel** — if the mockup shows a 6×2 dot grid, code a 6×2 dot grid
5. **Use Tailwind classes from the design system** — don't invent new colors
6. **Test in browser** — `cd frontend-v2 && npm run dev` → verify at target resolution (2560px)
7. **Commit per page** — one page fix per commit for clean history
