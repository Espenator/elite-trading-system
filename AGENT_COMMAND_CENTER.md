# Agent Command Center — Final Design Reference

**Date:** February 24, 2026  
**Status:** FINAL — Production Ready  
**Priority:** HIGH  
**Page Title:** Agent Command Center (NOT "ClawBot Panel" — that name is internal backend only)  
**Mockup:** [Perplexity Thread with Gemini 3.1 Pro Mockup](https://www.perplexity.ai/search/please-help-me-mock-up-this-pa-oAOUc_SeRgiVZXleIb9lBw)

## NAMING CONVENTION

> **CRITICAL:** The UI page title is **"Agent Command Center"**. Do NOT use "ClawBot Panel" anywhere in the user-facing interface. The internal backend module name "openclaw" is fine for API paths and service files, but all UI labels, page titles, nav items, and headers must say **"Agent Command Center"** or **"Command Center"**.

## Overview

The Agent Command Center is the dedicated swarm control interface for the Elite Trader Embodier UI. It centralizes OpenClaw's swarm intelligence for operator oversight, pulling live candidates via bridge API while visualizing Macro Brain waves and team dynamics to enable strategic interventions.

This is NOT the main trading page — it is the operator's dashboard for monitoring and controlling the AI trading swarm.

## Architecture

### Frontend Files (elite-trading-system/frontend-v2/src/)

| File | Location | Purpose |
|------|----------|----------|
| `pages/AgentCommandCenter.jsx` | Main page | Orchestrator container with CSS Grid layout (70/30 split) |
| `components/RegimeBanner.jsx` | Component | Persistent top bar: wave gauge, regime badge, bias multiplier |
| `components/SwarmControls.jsx` | Component | Team counter, spawn buttons, bias slider |
| `components/CandidatesGrid.jsx` | Component | High-density data table with sortable columns |
| `components/LLMFlowAlerts.jsx` | Component | WebSocket-fed alert feed in right sidebar |
| `components/HeatmapMini.jsx` | Component | Symbol treemap colored by composite score |
| `services/openclawService.js` | Service | API client for all 6 OpenClaw endpoints |

### Backend Endpoints (openclaw repo)

| Endpoint | Method | Purpose | Poll Rate |
|----------|--------|---------|----------|
| `/api/v1/openclaw/macro` | GET | Regime oscillator, wave_state, bias multiplier | 30s |
| `/api/v1/openclaw/candidates` | GET | Ranked candidates with scores, team tags | On demand |
| `/api/v1/openclaw/swarm-status` | GET | Active teams count, names, health | 15s |
| `/api/v1/openclaw/spawn-team` | POST | Spawn/kill agent teams | Operator action |
| `/api/v1/openclaw/macro/override` | POST | Override bias multiplier (0.5-2.0) | Operator action |
| `/api/v1/openclaw/llm-flow` | WebSocket | Real-time LLM alerts with severity | Real-time |

## Component Tree

```
AgentCommandCenter
├── RegimeBanner (persistent top bar: wave gauge + bias)
│   └── Polls GET /macro every 30s
├── SwarmControls (teams counter + spawn controls)
│   ├── Polls GET /swarm-status every 15s
│   ├── "Spawn Fear Team" → POST /spawn-team
│   ├── "Spawn Greed Fade" → POST /spawn-team
│   ├── "Spawn Breakout" → POST /spawn-team
│   ├── "Kill All" → POST /spawn-team {action: kill}
│   └── Bias Slider → POST /macro/override (debounced 500ms)
├── CandidatesGrid (composite score desc, team tags)
│   ├── Fetches GET /candidates
│   └── Row Click → TradeExecution modal (prepop entry/stop/target/team)
├── LLMFlowAlerts (right sidebar alert carousel)
│   └── WebSocket /llm-flow (last 5 backlog + real-time)
└── HeatmapMini (symbols by score/wave bias)
    └── Reuses candidates data, no separate fetch
```

## Design System

| Token | Value | Usage |
|-------|-------|-------|
| Background Main | `#0B0E14` | Page background |
| Background Panel | `#0D1117` | Panel/card backgrounds |
| Background Card | `#161B22` | Nested cards, inputs |
| Border | `1px solid #21262D` | All borders, no drop shadows |
| Text Primary | `#E6EDF3` | Main text |
| Text Secondary | `#8B949E` | Labels, timestamps |
| Text Muted | `#484F58` | Disabled, placeholders |
| Accent Teal | `#14B8A6` | Primary actions, active states |
| Accent Blue | `#3B82F6` | Selection, team badges |
| Accent Red | `#EF4444` | Danger, fear, critical alerts |
| Accent Green | `#22C55E` | Success, greed, bullish |
| Accent Amber | `#F59E0B` | Warning, neutral regime |
| Font Numbers | `font-mono` (Roboto Mono) | All prices, scores, metrics |
| Font Labels | Inter / sans-serif | Headers, labels, descriptions |

## Mockup Reference

The final mockup was generated using Gemini 3.1 Pro image generator via Perplexity AI. It shows:

1. **Regime Banner** — Radial gauge at 22 (Extreme Fear), BULL REGIME badge, +1.5x LONGS bias badge, VIX/HY stat pills
2. **Swarm Status** — 5/8 teams active, spawn buttons (Fear/Greed Fade/Breakout), Kill All, bias slider
3. **Candidates Table** — 10 tickers with color-coded scores, direction arrows, entry/stop/target, team tags
4. **LLM Alert Feed** — 5 severity-colored cards (critical/warning/info) with timestamps
5. **Heatmap** — Treemap tiles sized by composite score

See the full Perplexity thread for interactive mockup: [Link](https://www.perplexity.ai/search/please-help-me-mock-up-this-pa-oAOUc_SeRgiVZXleIb9lBw)

## Companion Docs

- **Backend API spec:** `CLAWBOT_PANEL_DESIGN.md` in [openclaw repo](https://github.com/Espenator/openclaw/blob/main/CLAWBOT_PANEL_DESIGN.md)
- **Frontend spec:** `CLAWBOT_PANEL_DESIGN.md` in this repo
- **Oleh handoff:** `OLEH-HANDOFF.md` in this repo
