# ClawBot Panel Design Specification

**Date:** February 24, 2026
**Status:** Implementation Required
**Priority:** HIGH - Heart of the trading system
**Estimated Effort:** 7-8 hours total

---

## Overview

The ClawBot Panel centralizes OpenClaw's swarm intelligence for operator oversight, pulling live candidates via bridge API while visualizing Macro Brain waves and team dynamics to enable strategic interventions.

**Goal:** Elevate from basic candidate list to a **swarm command center** by fusing Macro Brain state, clawbot team visualization, and LLM summaries.

---

## Component Tree Structure

```
ClawBotPanel
|-- Header (persistent regime banner: wave gauge + bias)
|-- Swarm Status (teams counter + spawn controls)
|-- Candidates Table (composite score desc, team tags, click -> TradeExecution prepop)
|-- LLM Flow (alert carousel)
+-- Heatmap Mini (symbols by score/wave bias)
```

---

## 5 Required Features

### Feature 1: Macro Wave Gauge
- **Why:** Visual fear/greed oscillator + regime (always visible at top)
- **Implementation:** Radial chart via Recharts
- **Data Source:** `GET /api/v1/openclaw/macro`
- **Display:** Color-coded (red = fear, green = greed, yellow = neutral), bias multiplier badge (e.g., +1.5x longs)
- **Refresh:** Every 30 seconds via polling
- **Integration:** Persistent in Header.jsx as `<RegimeBanner />`

### Feature 2: Team Provenance
- **Why:** Signals tagged by spawning bots (e.g., "fear_bounce_team: rebound_detector")
- **Implementation:** Table column with chip badges; hover reveals mini agent graph (D3 force-directed)
- **Data Source:** Team metadata from `/api/v1/openclaw/candidates` response (each candidate has `team_id` field)
- **Display:** Color-coded Badge components per team type

### Feature 3: Live Clawbot Status
- **Why:** Active teams count/status (spawning/active/idle)
- **Implementation:** Top bar swarm counter (e.g., "5/8 teams"), clickable to open spawn modal
- **Data Source:** `GET /api/v1/openclaw/swarm-status`
- **Refresh:** Every 15 seconds
- **Display:** Badge showing active/total, team list with status indicators

### Feature 4: Operator Overrides
- **Why:** Spawn/kill teams, bias slider for manual regime adjustment
- **Implementation:** Buttons ("Spawn Fear Team", "Spawn Greed Team", "Kill All") + bias Slider component
- **Data Source:** `POST /api/v1/openclaw/spawn-team` and `POST /api/v1/openclaw/macro/override`
- **Bias Slider:** Range 0.5x to 2.0x, syncs to backend override endpoint

### Feature 5: LLM Flow Alerts
- **Why:** Macro summaries (e.g., "Extreme Greed: Fade shorts recommended")
- **Implementation:** Toast notification carousel, keeps last 5 alerts
- **Data Source:** `ws://localhost:5000/api/v1/openclaw/llm-flow` (WebSocket)
- **Display:** Alert components with severity coloring (high = destructive red)

---

## Header.jsx Regime Banner (Always Visible)

```jsx
// Persistent top bar - add to Header.jsx
<RegimeBanner
  oscillator={macro.oscillator}
  wave={macro.wave_state}
  bias={macro.bias}
/>
```

The RegimeBanner must be integrated into the existing `Header.jsx` component so it persists across all page navigation.

---

## TradeExecution Wiring

On candidate row click, extract entry/stop/target/team and dispatch to TradeExecution modal:

```jsx
window.dispatchEvent(new CustomEvent('openTradeExecution', {
  detail: {
    symbol: candidate.symbol,
    entry: candidate.entry_price,
    stop: candidate.stop_loss,
    target: candidate.target_price,
    team: candidate.team_id,
    score: candidate.composite_score
  }
}));
```

TradeExecution.jsx must listen for this event and prepopulate its form with "Team: fear_bounce" context.

---

## Required API Endpoints (Backend on OpenClaw/PC1)

| Endpoint | Method | Purpose | Status |
|---|---|---|---|
| `/api/v1/openclaw/macro` | GET | Macro Brain state (oscillator, wave_state, bias) | Needs route |
| `/api/v1/openclaw/swarm-status` | GET | Team count/state (spawning/active/idle) | Needs route |
| `/api/v1/openclaw/candidates` | GET | Live candidates with scores + team tags | Exists (bridge) |
| `/api/v1/openclaw/spawn-team` | POST | Spawn/kill clawbot teams | Needs route |
| `/api/v1/openclaw/macro/override` | POST | Bias slider sync | Needs route |
| `/api/v1/openclaw/llm-flow` | WS | LLM summary stream | Needs WebSocket |

---

## Frontend Files to Create/Modify

| File | Action | Description |
|---|---|---|
| `frontend/src/pages/ClawBotPanel.jsx` | CREATE | Full swarm command center (see component tree above) |
| `frontend/src/components/RegimeBanner.jsx` | CREATE | Persistent regime banner with radial gauge |
| `frontend/src/components/Header.jsx` | MODIFY | Add RegimeBanner integration |
| `frontend/src/pages/TradeExecution.jsx` | MODIFY | Add CustomEvent listener for prepopulation |
| `frontend/src/services/openclawService.js` | CREATE | API client for all /openclaw/* endpoints |

---

## Dependencies

- `recharts` - Already in project for charts, use RadialBarChart
- `lucide-react` - Already in project for icons
- `@/components/ui/*` - shadcn/ui components (Card, Button, Slider, Badge, Alert)
- D3 force-directed graph (optional, for team provenance hover)

---

## Acceptance Criteria

- [ ] Macro Wave Gauge renders radial chart with fear/greed coloring
- [ ] RegimeBanner persists in Header across all pages
- [ ] Candidates table shows team provenance badges
- [ ] Row click opens TradeExecution with prepopulated entry/stop/target/team
- [ ] Swarm counter shows active/total teams with spawn/kill controls
- [ ] Bias slider POSTs override to backend
- [ ] LLM alerts display via WebSocket in carousel
- [ ] Heatmap mini shows symbols by score/wave bias
- [ ] All data refreshes on appropriate intervals (15-30s)

---

## Reference

- [RFC: Agent Teams - Coordinated Multi-Agent Orchestration](https://github.com/openclaw/openclaw/discussions/10036)
- [Multi-Agent Swarms: Architecture Guide](https://swapanmanna.com/blog/multi-agent-swarms-advanced-architecture)
