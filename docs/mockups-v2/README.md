# Embodier Trader V2 - UI Mockups & Implementation Guide

## For Oleh - Frontend Implementation Spec

> **Phase**: Mockup Approval -> React/Tailwind Code -> FastAPI Backend
> **Aesthetic**: Institutional Glass-Box Command Center
> **Colors**: `#0B0E14` (bg), `#06B6D4` (cyan active), `#F59E0B` (amber warning), `#EF4444` (red danger)
> **Fonts**: Monospace data fonts (JetBrains Mono / Fira Code)

---

## Frontend Charting Tech Stack

| Component | Library | Why |
|---|---|---|
| Candlesticks & Price Feeds | `lightweight-charts` (TradingView) | Unbeatable Canvas perf for WebSocket data |
| Agent Buy/Sell Overlays | React/Tailwind (absolute pos) | Use `timeToCoordinate()` + `priceToCoordinate()` API |
| SHAP Bars & Win Rates | `recharts` | Native React, dark-mode friendly |
| Agent Swarm Brain Map | `reactflow` | Industry-standard draggable DAG nodes |
| Flywheel Ring Buffer | `recharts` (circular) | Progress rings + line charts |

### The Coordinate Mapping Secret Sauce
TradingView Lightweight Charts renders on Canvas. To overlay React components:
1. Render plain TV chart
2. Use `timeToCoordinate()` and `priceToCoordinate()` to get X/Y pixels
3. Render custom Tailwind UI components with absolute positioning on top
4. This gives TV performance + React/Tailwind hyper-interactivity

---

## MOCKUP 1 V2: Agent Command Center (The Interactive Brain Map)

**Perplexity Link**: See generated mockup in project Perplexity thread

### Layout: Widescreen 2560px+, full-bleed, 3-pane horizontal scroll

#### LEFT PANE (40%) - Swarm Node Graph (ReactFlow)
- Interactive DAG of active agents
- Nodes: MACRO BRAIN (center), LLM Analyst, Fear Bounce, Greed Fade, Breakout, Composite Scorer, Ensemble ML, Risk Governor, Sentiment Sensor, Technical Pattern Scout, Macroeconomic Oracle, Order Execution Bot
- **HOTLINK**: Every node is clickable -> slides open Node Control Panel
- **Node Control Panel** (glass overlay):
  - Agent Temperature slider (0.0-2.0)
  - Context Window Size slider (2K-128K)
  - Model Hot-Swap dropdown (Gemini 3.1 Pro / Local Ollama Llama-3-8B / GPT-4o / Claude 3.5)
  - Red **KILL & RESPAWN** emergency button
- ON/OFF glow rings on each node
- Directed edges with animated data flow arrows

#### CENTER PANE (40%) - Live Consensus Feed (WebSocket)
- Streaming signal cards: NVDA +2.3 EV, TSLA -1.1 EV, AMD +1.8 EV, META -0.9 EV, GOOGL +3.1 EV
- Each card: ticker, direction arrow, EV score, confidence %, agent agreement
- Buttons: **APPROVE** (green), **REJECT** (red), **OVERRIDE** (amber)
- **HOTLINK**: Blue `Decision Trace ID: 0x7f3a...` -> click pauses stream, shows raw JSON payload from Phase 1 Bridge
- Filter bar: LONG ONLY / SHORT ONLY / ALL
- Sort: BY EV / BY CONFIDENCE / BY RECENCY

#### RIGHT PANE (20%) - Swarm Bias & Override
- Bear/Bull Consensus donut gauge
- **CAPITAL ALLOCATION THROTTLE**: Massive vertical slider 0%-100% (current: 72%)
- Mini sparklines: VIX, SPX, USD (all clickable to expand)
- CONFIGURE ALERTS button

#### Header & Footer
- Header: `EMBODIER TRADER - AGENT COMMAND CENTER V2` | FLYWHEEL CYCLE #47 | RECURSIVE SELF-IMPROVEMENT badge
- Footer: `FLYWHEEL ACTIVE | PAIRS: 142/200 | ADAPTER: v0.47 | LAST SYNC: 0.4s ago | SYSTEM LOAD: 34% | MODE: AUTONOMOUS TRADING`

---

## MOCKUP 2 V2: EV Opportunity Matrix (Deep Drill-Down)

**Perplexity Link**: See generated mockup in project Perplexity thread

### Layout: Bloomberg-style data grid, infinite horizontal scroll

#### THE EV GRID (Full width)
- Ranked by: `EV = (Win% * AvgWin) - (Loss% * AvgLoss) - Costs`
- Columns: RANK, SYMBOL, EV SCORE, SHAP CONTRIBUTION BARS, OPPORTUNITY, VOLATILITY, MOMENTUM, FLOW, SENTIMENT, RISK GRADE
- Rows: #1 NVDA +2.75, #2 AMD +2.12, #3 TSLA +1.86, #4 AAPL +1.30, #5 GOOGL +0.95
- **HOTLINK**: SHAP segments clickable -> modal shows Etherscan/SolanaFM transaction hashes
- Top bar: BULL/BEAR regime badge, REFRESH SCAN, EXPORT CSV buttons

#### Position Sizing & Execution Drawer (Expanded on row click)
- **Kelly Sizing Modifier**: [0.5x] [1.0x] [1.5x] buttons
- Calculated Position Size: `$3,450`
- **AGENT VETO**: Checkboxes per agent vote. Uncheck to exclude -> EV dynamically recalculates
- AUTO-STOP LOSS toggle
- **EXECUTE TRADE** (green) / **SEND TO PAPER** (amber) buttons

#### Right Sidebar - Selected Trade Deep-Dive
- Feature Importance Waterfall chart (Recharts)
- Mini price chart with entry/exit zones (lightweight-charts)
- Risk Governor approval status

#### Footer
- `LAST SCAN: 14:32:01 EST | NEXT SCAN: 2m 15s | TOTAL CANDIDATES: 847 | FLYWHEEL CYCLE #47`

---

## MOCKUP 3 V2: Flywheel Console (The Mutation Chamber)

**Perplexity Link**: See generated mockup in project Perplexity thread

### Layout: Split-screen. Left = Autopsy Feed, Right = Training Ring Buffer
### THIS IS WHERE RECURSIVE SELF-IMPROVEMENT BECOMES TANGIBLE

#### LEFT PANE (55%) - Post-Trade Autopsy Feed
- Scrollable closed trade cards
- Winners: faint green border | Losers: red border
- Each card: Symbol, Direction, Entry/Exit, P&L, AI reasoning (collapsed), SHAP factor bars
- **HOTLINK**: `Model Version: v2.4.1` blue link -> GitHub commit / openclaw_db.py snapshot
- HITL Buttons: **APPROVE** (thumbs up), **REJECT** (thumbs down), **OVERRIDE** (amber)
- On REJECT -> **DIAGNOSE & PENALIZE** block expands:
  - Dropdown: `Reason for Failure` (Stop Hunt, Whale Manipulation, News Event, Overfitting)
  - SEVERITY slider (1-10)
  - **PUSH PENALTY TO LoRA** cyan button -> tags JSON in SQLite as negative DPO example

#### RIGHT PANE (45%) - HITL Ring Buffer & Training Dashboard
- Training Buffer: 142/200 circular progress ring
- Win Rate Trend: Line chart (Recharts) over 20 flywheel cycles (55% -> 68%)
- LoRA Adapter Version History table (v0.45 RETIRED 67.2%, v0.46 ACTIVE 68.5%, v0.47 PENDING)
- Agent Accuracy bars: Volatile 72%, Trending 85%, Ranging 55%, News Event 62%
- **TRIGGER LOCAL RE-TRAIN**: Massive cyan pulsing button (forces OpenClaw weight update)
- **ROLLBACK TO v0.46**: Amber warning button

#### Footer
- `DPO PAIRS TODAY: 12 approved, 3 rejected, 2 overrides | NEXT AUTO-TRAIN: 58 pairs | Memory: 4.1GB/8GB | RTX 4090 READY`

---

## Wiring Map: Mockup Component -> Backend API

| UI Component | API Endpoint | Backend Module |
|---|---|---|
| Agent Node Graph | `GET /api/v1/agents/topology` | `openclaw/config.py` |
| Node Control Panel (temp/ctx/model) | `PATCH /api/v1/agents/{id}/config` | `openclaw/llm_client.py` |
| KILL & RESPAWN | `POST /api/v1/agents/{id}/respawn` | `openclaw/llm_client.py` |
| Live Consensus Feed | `WS /api/v1/signals/stream` | `openclaw_bridge_service.py` |
| Decision Trace ID -> JSON | `GET /api/v1/traces/{trace_id}` | `openclaw/db_logger.py` |
| Capital Throttle slider | `PATCH /api/v1/risk/throttle` | `risk_shield_api.py` |
| EV Grid data | `GET /api/v1/ev-matrix` | `openclaw/composite_scorer.py` |
| SHAP -> Etherscan | `GET /api/v1/shap/{signal_id}/sources` | `openclaw/whale_tracker.py` |
| Kelly Sizing calc | `POST /api/v1/position-size` | `openclaw/risk_governor.py` |
| Agent Veto recalc | `POST /api/v1/ev-recalc` | `openclaw/composite_scorer.py` |
| Execute Trade | `POST /api/v1/trades/execute` | `openclaw/order_executor.py` |
| Post-Trade Autopsy | `GET /api/v1/trades/closed` | `openclaw/performance_tracker.py` |
| APPROVE/REJECT/OVERRIDE | `POST /api/v1/flywheel/feedback` | `openclaw/memory.py` |
| Diagnose & Penalize | `POST /api/v1/flywheel/penalize` | `openclaw/lora_trainer.py` |
| Push Penalty to LoRA | `POST /api/v1/flywheel/dpo-pair` | `openclaw/lora_trainer.py` |
| Trigger Local Re-Train | `POST /api/v1/flywheel/train` | `openclaw/lora_trainer.py` |
| Rollback Adapter | `POST /api/v1/flywheel/rollback` | `openclaw/lora_trainer.py` |
| Training Buffer status | `GET /api/v1/flywheel/buffer` | `openclaw/memory.py` |
| LoRA Version History | `GET /api/v1/flywheel/versions` | `openclaw/lora_trainer.py` |

---

## Next Steps
1. **Oleh Review**: Review V2 mockups and this implementation spec
2. **Phase 2**: Write `SwarmConsensusDrawer.tsx` and `FlywheelFeedback.tsx` React components
3. **Phase 3**: Write `openclaw_bridge_service.py` FastAPI WebSocket router
4. **Wire up**: Connect all API endpoints listed above
