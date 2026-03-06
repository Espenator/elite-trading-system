# Elite Trading System — Full Frontend↔Backend Integration Plan

## Overview
This plan maps EVERY backend endpoint to its frontend representation and EVERY frontend control to its backend endpoint, ensuring 100% bidirectional coverage. It also identifies pixel-fidelity gaps between mockups and current UI.

---

## PART 1: PIXEL FIDELITY GAPS (Mockup vs Current UI)

### 1.1 AgentCommandCenter — Swarm Overview Tab
**Mockup**: `agent command center swarm overview.png`
**Gaps**:
- [ ] Filter bar needs proper dropdowns: ELO/Status/Win Rate/PnL/Latency/P(win) with real filter logic
- [ ] Status toggles (Running/Paused/Degraded/Spawning) need to filter cards by calling `GET /api/v1/agents` with status filter
- [ ] Sort By buttons (Phase AI/Team AI/Campus Selected) need backend sort support
- [ ] Agent cards need REAL data from backend: ELO scores, win rates, PnL impact, expectancy, profit factor
- [ ] Footer bar (Swarm Health %, Total ELO Pool, Avg Confidence, Consensus Agreement, SNAP Coverage) needs aggregated real data
- [ ] Sparkline in each card needs real signal history data
- [ ] Star ratings need to come from backend agent performance metrics
- [ ] "Next Scheduled Refresh" timer needs to sync with backend tick scheduler

### 1.2 AgentCommandCenter — Brain Map Tab
**Mockup**: `agent command center brain map.png`
**Gaps**:
- [ ] SVG DAG nodes should reflect REAL agent status from `GET /api/v1/agents` and `GET /api/v1/council/status`
- [ ] Connection lines should show real latency from `GET /api/v1/agents/resources`
- [ ] Toolbar buttons (Hierarchical/Force-Directed/Circular, Zoom, Fit, Filter, Layers) are UI-only — need layout toggle logic
- [ ] "Auto-Refresh" toggle needs WebSocket subscription to agents channel
- [ ] Connection Health Matrix (Panel 1) needs data from `GET /api/v1/risk/correlation-matrix` or new endpoint
- [ ] Conference DAG (Panel 2) needs data from `GET /api/v1/agents/conference`
- [ ] Flow Anomaly Detector (Panel 3) needs new backend endpoint or derivation from drift/alerts

### 1.3 AgentCommandCenter — Node Control & HITL Tab
**Mockup**: `agent command center node control.png`
**Gaps**:
- [ ] Agent config table (15 rows) — backend only has 5 tick agents + 13 council agents. Need to show ALL agents
- [ ] Power toggle per agent → `POST /api/v1/agents/{id}/start` and `POST /api/v1/agents/{id}/stop`
- [ ] Weight slider → needs new `PUT /api/v1/council/weights` endpoint to update individual agent weights
- [ ] Confidence Threshold slider → needs new endpoint or extend agent config
- [ ] Temperature slider → needs new endpoint for LLM temperature control
- [ ] Context Window control → needs new endpoint
- [ ] Restart/Pause/Kill buttons → `POST /agents/{id}/restart`, `/pause`, `/stop`
- [ ] Priority badge → needs backend priority field
- [ ] Load bar → real CPU from `GET /api/v1/agents/resources`
- [ ] HITL Ring Buffer visual → needs new `GET /api/v1/agents/hitl-buffer` endpoint
- [ ] Overdue History Log → needs new endpoint or derive from agent alerts
- [ ] HITL Analytics (Buffer Fill, Review Count, Avg Review Time) → needs new HITL stats endpoint

### 1.4 AgentCommandCenter — Blackboard & Comms Tab
**Mockup**: `realtimeblackbard fead.png`
**Gaps**:
- [ ] Real-time Blackboard Feed → needs WebSocket subscription to `blackboard` channel + `GET /api/v1/cns/blackboard/current`
- [ ] WebSocket Channel Monitor table → needs `GET /ws/status` or new channel monitoring endpoint (use `get_channel_info()` from websocket_manager)
- [ ] HITL Ring Buffer items with Approve/Reject/Defer buttons → needs `POST /api/v1/agents/hitl/{id}/approve|reject|defer`
- [ ] Agent Lifecycle Controls (Start All, Stop All, Restart All) → needs batch endpoint or call individual agent endpoints

### 1.5 PerformanceAnalytics Page
**Mockup**: `11-performance-analytics-fullpage.png`
**Gaps**:
- [ ] Top KPI strip (Total Trades, Net PnL, Win Rate, Avg Win, Avg Loss, Profit Factor, Max DD, Sharpe, Expectancy, RR) → `GET /api/v1/performance/summary` + `/risk-metrics`
- [ ] Risk Cockpit grade (A/B/C/D/F) → `GET /api/v1/risk/risk-score`
- [ ] Kelly Criterion display → `GET /api/v1/risk/kelly-sizer`
- [ ] Equity + Drawdown chart → `GET /api/v1/performance/equity`
- [ ] Agent Attribution Leaderboard → needs new `GET /api/v1/agents/attribution` or derive from council weights
- [ ] AI + Bulling Risk chart → `GET /api/v1/risk/risk-score` time series
- [ ] Enhanced Trades Table → `GET /api/v1/performance/trades`
- [ ] ML & Flywheel Engine panel → `GET /api/v1/ml-brain/performance` + `/flywheel-logs`
- [ ] Risk Cockpit Expanded (VaR Gauge, Signal Hit Rate, Market Sentiment) → multiple endpoints
- [ ] Strategy & Signals panel → `GET /api/v1/signals/kelly-ranked`
- [ ] Returns Heatmap Calendar → needs new endpoint or derive from performance/equity

---

## PART 2: BACKEND → FRONTEND MAPPING (Every Backend Feature Must Be Visible)

### 2.1 Agent System (backend/app/api/v1/agents.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /agents` | AgentCommandCenter → all tabs | WIRED (useEffect fetch) |
| `POST /agents/{id}/start` | Swarm Overview → card actions, Node Control → Power toggle | PARTIAL — need per-card buttons |
| `POST /agents/{id}/stop` | Node Control → Power toggle, Kill button | PARTIAL |
| `POST /agents/{id}/pause` | Node Control → Pause button | PARTIAL |
| `POST /agents/{id}/restart` | Node Control → Restart button | PARTIAL |
| `POST /agents/{id}/tick` | NOT VISIBLE — need "Manual Tick" button per agent | MISSING |
| `GET /agents/swarm-topology` | Swarm Overview → topology visualization | WIRED |
| `GET /agents/conference` | Conference & Consensus tab | WIRED |
| `GET /agents/consensus` | PerformanceAnalytics → consensus panel | NEEDS WIRING |
| `GET /agents/teams` | Swarm Overview → team groupings | NEEDS WIRING |
| `GET /agents/drift` | ML Ops tab → drift monitor | WIRED |
| `GET /agents/alerts` | System alerts panel | WIRED |
| `GET /agents/resources` | Brain Map → node CPU/MEM, Node Control → Load bar | NEEDS WIRING |

### 2.2 Council System (backend/app/api/v1/council.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `POST /council/evaluate` | Dashboard → "Run Council" button | WIRED |
| `GET /council/latest` | Dashboard → Council Verdict panel | WIRED |
| `GET /council/status` | Brain Map → DAG stages (13 agents, 7 stages) | NEEDS WIRING |
| `GET /council/weights` | Node Control → Weight sliders (initial values) | NEEDS WIRING |
| `POST /council/weights/reset` | Node Control → "Reset Weights" button | MISSING |

### 2.3 Swarm Intelligence (backend/app/api/v1/swarm.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `POST /swarm/ingest/youtube` | SwarmIntelligence page | WIRED |
| `POST /swarm/ingest/news` | SwarmIntelligence page | WIRED |
| `POST /swarm/ingest/text` | SwarmIntelligence page | WIRED |
| `POST /swarm/ingest/url` | SwarmIntelligence page | WIRED |
| `POST /swarm/ingest/symbols` | SwarmIntelligence page | WIRED |
| `GET /swarm/ingest/feed` | SwarmIntelligence → Knowledge Feed | WIRED |
| `GET /swarm/swarm/status` | SwarmIntelligence → Swarm Status | WIRED |
| `GET /swarm/swarm/results` | SwarmIntelligence → Results | WIRED |
| `GET /swarm/scout/status` | SwarmIntelligence → Scout panel | WIRED |
| `POST /swarm/scout/watchlist` | SwarmIntelligence → Watchlist mgmt | WIRED |
| `POST /swarm/scout/config` | SwarmIntelligence → Scout config | WIRED |
| `GET /swarm/discord/status` | SwarmIntelligence → Discord panel | WIRED |
| `GET /swarm/radar/status` | Dashboard or SwarmIntelligence | NEEDS WIRING |
| `GET /swarm/radar/playbook` | NOT VISIBLE — need Playbook display | MISSING |
| `POST /swarm/radar/inject` | NOT VISIBLE — need "Inject Event" button | MISSING |
| `GET /swarm/correlations/status` | Risk Intelligence or Market Regime | NEEDS WIRING |
| `GET /swarm/correlations/matrix` | Risk Intelligence → Correlation Matrix | NEEDS WIRING |
| `GET /swarm/correlations/rotations` | Market Regime → Sector Rotation | NEEDS WIRING |
| `GET /swarm/correlations/reversions` | Signal Intelligence → Mean Reversion | NEEDS WIRING |
| `GET /swarm/patterns/status` | Patterns page | NEEDS WIRING |
| `GET /swarm/patterns/list` | Patterns page → Pattern list | NEEDS WIRING |
| `GET /swarm/expected-moves/levels` | Signal Intelligence → Expected Moves | NEEDS WIRING |
| `GET /swarm/expected-moves/reversals` | Signal Intelligence → Reversal Zones | NEEDS WIRING |
| `GET /swarm/turbo/status` | SwarmIntelligence → TurboScanner | WIRED |
| `GET /swarm/turbo/signals` | Signal Intelligence → Turbo signals | NEEDS WIRING |
| `GET /swarm/hyper/status` | SwarmIntelligence → HyperSwarm | WIRED |
| `GET /swarm/hyper/results` | SwarmIntelligence → Hyper results | NEEDS WIRING |
| `GET /swarm/hyper/escalations` | SwarmIntelligence → Escalations | NEEDS WIRING |
| `GET /swarm/news/status` | SwarmIntelligence → News Aggregator | WIRED |
| `GET /swarm/news/feed` | NOT VISIBLE — need News Feed display | MISSING |
| `GET /swarm/sweep/status` | SwarmIntelligence → Market Sweep | WIRED |
| `GET /swarm/sweep/screens` | NOT VISIBLE — need Screener results | MISSING |
| `GET /swarm/outcomes/status` | PerformanceAnalytics → Outcome tracking | NEEDS WIRING |
| `GET /swarm/outcomes/kelly` | PerformanceAnalytics → Kelly from outcomes | NEEDS WIRING |
| `GET /swarm/outcomes/open` | Active Trades → tracked positions | NEEDS WIRING |
| `GET /swarm/outcomes/closed` | PerformanceAnalytics → closed trades | NEEDS WIRING |
| `GET /swarm/positions/managed` | Active Trades → managed positions | NEEDS WIRING |
| `GET /swarm/ml/scorer/status` | ML Brain → Live scorer status | NEEDS WIRING |
| `POST /swarm/ml/scorer/reload` | ML Brain → "Reload Model" button | MISSING |
| `GET /swarm/unified/status` | Dashboard → Unified score | NEEDS WIRING |
| `GET /swarm/unified/score/{symbol}` | Signal Intelligence → per-symbol score | NEEDS WIRING |
| `GET /swarm/intelligence/status` | Dashboard → Combined intelligence status | NEEDS WIRING |

### 2.4 Risk System (backend/app/api/v1/risk.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /risk` | Risk Intelligence → main view | WIRED |
| `PUT /risk` | Risk Intelligence → update parameters | WIRED |
| `GET /risk/history` | Risk Intelligence → history chart | WIRED |
| `GET /risk/proposal/{symbol}` | Trade Execution → risk check | WIRED |
| `GET /risk/kelly-sizer` | PerformanceAnalytics → Kelly display | WIRED |
| `POST /risk/kelly-sizer` | Risk Intelligence → Kelly calculator | WIRED |
| `POST /risk/position-sizing` | Trade Execution → position sizing | WIRED |
| `POST /risk/drawdown-check` | Dashboard → drawdown alert | WIRED |
| `GET /risk/drawdown-check` | Risk Intelligence → drawdown status | WIRED |
| `POST /risk/dynamic-stop-loss` | Trade Execution → ATR stop | WIRED |
| `GET /risk/risk-score` | Dashboard + Risk Intelligence | WIRED |
| `GET /risk/var-analysis` | Risk Intelligence → VaR panel | WIRED |
| `GET /risk/risk-gauges` | Risk Intelligence → 12 gauges | WIRED |
| `GET /risk/circuit-breakers` | Risk Intelligence → breakers panel | WIRED |
| `GET /risk/stress-test` | Risk Intelligence → Monte Carlo | WIRED |
| `GET /risk/monte-carlo` | Risk Intelligence → Monte Carlo tab | WIRED |
| `GET /risk/position-var` | Risk Intelligence → Position VaR | WIRED |
| `GET /risk/shield` | Dashboard → Risk Shield card | WIRED |
| `GET /risk/equity-curve` | Risk Intelligence → equity chart | WIRED |
| `GET /risk/correlation-matrix` | Risk Intelligence → correlation heatmap | WIRED |
| `GET /risk/var-histogram` | Risk Intelligence → VaR distribution | NEEDS WIRING |
| `GET /risk/drawdown-episodes` | Risk Intelligence → DD episodes | NEEDS WIRING |
| `POST /risk/emergency/halt` | Risk Intelligence → "EMERGENCY STOP ALL" button | NEEDS WIRING to real handler |
| `POST /risk/emergency/resume` | Risk Intelligence → Resume button | NEEDS WIRING |
| `POST /risk/emergency/flatten` | Risk Intelligence → Flatten All button | NEEDS WIRING |

### 2.5 Performance (backend/app/api/v1/performance.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /performance` | PerformanceAnalytics → main KPIs | WIRED |
| `GET /performance/summary` | PerformanceAnalytics → summary metrics | WIRED |
| `GET /performance/equity` | PerformanceAnalytics → equity chart | WIRED |
| `GET /performance/trades` | PerformanceAnalytics → trades table | WIRED |
| `GET /performance/risk-metrics` | PerformanceAnalytics → Sharpe/Sortino/Kelly | NEEDS WIRING |
| `GET /performance/health` | NOT VISIBLE — add to Settings → System Health | MISSING |

### 2.6 ML Brain (backend/app/api/v1/ml_brain.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /ml-brain/performance` | ML Brain & Flywheel → accuracy chart | WIRED |
| `GET /ml-brain/signals/staged` | ML Brain → staged signals table | WIRED |
| `GET /ml-brain/flywheel-logs` | ML Brain → flywheel log | WIRED |
| `POST /ml-brain/conference/{symbol}` | AgentCommandCenter → Conference tab | NEEDS WIRING |
| `POST /ml-brain/conference/batch` | NOT VISIBLE — batch conference | MISSING |
| `GET /ml-brain/registry/status` | ML Brain → Model Registry panel | NEEDS WIRING |
| `GET /ml-brain/drift/status` | ML Brain → Drift Monitor panel | NEEDS WIRING |
| `GET /ml-brain/lstm/predict/{symbol}` | Signal Intelligence → LSTM prediction | NEEDS WIRING |
| `GET /ml-brain/status` | ML Brain → overall status indicator | NEEDS WIRING |

### 2.7 Signals (backend/app/api/v1/signals.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /signals/` | Signal Intelligence → signal list | WIRED |
| `POST /signals/` | Dashboard → "Run Scan" button | WIRED |
| `GET /signals/{symbol}/technicals` | Signal Intelligence → technicals panel | WIRED |
| `GET /signals/active/{symbol}` | Trade Execution → active signal | WIRED |
| `GET /signals/heatmap` | Signal Intelligence → heatmap | WIRED |
| `GET /signals/kelly-ranked` | PerformanceAnalytics → Strategy & Signals | NEEDS WIRING |

### 2.8 Settings (backend/app/api/v1/settings_routes.py)
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /settings` | Settings page → all fields | WIRED |
| `PUT /settings` | Settings → Save All button | WIRED |
| `GET /settings/{category}` | Settings → category tabs | WIRED |
| `PUT /settings/{category}` | Settings → per-category save | WIRED |
| `POST /settings/reset/{category}` | Settings → Reset Default button | WIRED |
| `POST /settings/validate` | Settings → Validate API Key button | WIRED |
| `POST /settings/test-connection` | Settings → Test Connection button | WIRED |
| `GET /settings/export` | Settings → Export Settings button | WIRED |
| `POST /settings/import` | Settings → Import Settings button | WIRED |
| `GET /settings/audit-log` | Settings → Audit Log tab | WIRED |

### 2.9 Other Backend APIs
| Backend Endpoint | Frontend Location | Status |
|---|---|---|
| `GET /market/indices` | Dashboard → Ticker Strip | WIRED |
| `GET /market/order-book` | Trade Execution → Order Book | STUB — needs real implementation |
| `GET /market/price-ladder` | Trade Execution → Price Ladder | STUB — needs real implementation |
| `GET /alpaca/account` | Trade Execution → account info | WIRED |
| `GET /alpaca/positions` | Active Trades → positions table | WIRED |
| `GET /alpaca/orders` | Active Trades → orders table | WIRED |
| `POST /orders/advanced` | Trade Execution → Advanced Order | WIRED |
| `GET /data-sources/` | Data Sources Monitor | WIRED |
| `GET /sentiment` | Sentiment Intelligence | WIRED |
| `GET /openclaw/regime` | Market Regime → regime state | WIRED |
| `GET /openclaw/macro` | Market Regime → macro data | WIRED |
| `GET /openclaw/sectors` | Market Regime → sector rotation | WIRED |
| `GET /cns/homeostasis/vitals` | Dashboard → CNS Vitals | WIRED |
| `GET /cns/blackboard/current` | Blackboard tab | NEEDS WIRING |
| `GET /cns/postmortems` | Dashboard → Postmortem panel | WIRED |
| `GET /cns/directives` | Settings → Directives editor | WIRED |
| WebSocket `agents` channel | AgentCommandCenter → real-time updates | WIRED |
| WebSocket `risk` channel | Risk Intelligence → real-time | WIRED |
| WebSocket `signals` channel | Signal Intelligence → real-time | WIRED |
| WebSocket `council_verdict` channel | Dashboard → council updates | WIRED |

---

## PART 3: NEW BACKEND ENDPOINTS NEEDED

These endpoints don't exist yet but are required by the mockup UI:

### 3.1 Agent HITL (Human-in-the-Loop) System
```
GET  /api/v1/agents/hitl/buffer          → HITL ring buffer contents
POST /api/v1/agents/hitl/{id}/approve    → Approve HITL item
POST /api/v1/agents/hitl/{id}/reject     → Reject HITL item
POST /api/v1/agents/hitl/{id}/defer      → Defer HITL item
GET  /api/v1/agents/hitl/stats           → HITL analytics (fill %, review count, avg time)
```

### 3.2 Agent Extended Config
```
PUT  /api/v1/agents/{id}/config          → Update agent weight, confidence threshold, temperature, context window, priority
GET  /api/v1/agents/all-config           → Get all agents with full config (for Node Control table)
POST /api/v1/agents/batch/start          → Start all agents
POST /api/v1/agents/batch/stop           → Stop all agents
POST /api/v1/agents/batch/restart        → Restart all agents
```

### 3.3 Agent Attribution
```
GET  /api/v1/agents/attribution          → Per-agent PnL contribution, accuracy, signal count
GET  /api/v1/agents/elo-leaderboard      → ELO scores with history for all agents
```

### 3.4 WebSocket Channel Monitor
```
GET  /api/v1/system/ws-channels          → Channel names, subscriber counts, msg/sec, status
```

### 3.5 Flow Anomaly Detection
```
GET  /api/v1/agents/flow-anomalies       → Detected anomalies in data flow between agents
```

---

## PART 4: IMPLEMENTATION PHASES

### Phase 1: Wire Existing Endpoints (No Backend Changes)
Priority: HIGH — Connect all existing backend data to frontend displays

1. **AgentCommandCenter — Swarm Overview**: Replace hardcoded agent data with `GET /agents` + `/agents/swarm-topology` + `/agents/teams`
2. **AgentCommandCenter — Brain Map**: Wire DAG nodes to `GET /council/status` (13 agents, 7 stages) + `/agents/resources`
3. **AgentCommandCenter — Node Control**: Wire table to `GET /agents` + `/council/weights`, buttons to start/stop/pause/restart
4. **AgentCommandCenter — Blackboard**: Wire feed to `GET /cns/blackboard/current` + WebSocket blackboard channel
5. **PerformanceAnalytics**: Wire KPIs to `/performance/summary` + `/performance/risk-metrics`, equity chart to `/performance/equity`
6. **PerformanceAnalytics**: Wire Kelly to `/risk/kelly-sizer`, Risk Cockpit to `/risk/risk-score`
7. **Risk Intelligence**: Wire emergency buttons to `POST /risk/emergency/{action}`
8. **ML Brain**: Wire registry to `/ml-brain/registry/status`, drift to `/ml-brain/drift/status`

### Phase 2: New Backend Endpoints
Priority: MEDIUM — Build missing endpoints for full HITL + extended agent control

1. Create `agents/hitl` endpoints (buffer, approve/reject/defer, stats)
2. Create `agents/{id}/config` PUT endpoint for weight/threshold/temperature
3. Create `agents/batch/*` endpoints for bulk operations
4. Create `agents/attribution` endpoint from council weight learner data
5. Create `system/ws-channels` endpoint from websocket_manager.get_channel_info()
6. Create `agents/flow-anomalies` endpoint

### Phase 3: Pixel-Perfect UI Polish
Priority: MEDIUM — Match mockups exactly

1. Fine-tune colors, spacing, font sizes, border-radius across all new tabs
2. Add proper loading states, error states, empty states for every panel
3. Ensure responsive grid layouts match mockup proportions
4. Add micro-animations (status dot pulse, sparkline animation, gauge transitions)
5. Match exact mockup typography (font weights, letter spacing, text transforms)

### Phase 4: Real-Time Integration
Priority: HIGH — Make everything live

1. Add WebSocket subscriptions to all Agent Command Center tabs
2. Add auto-refresh intervals for polling endpoints (30s for metrics, 5s for active data)
3. Add optimistic UI updates for control actions (toggle → instant visual + API call)
4. Add toast notifications for successful/failed operations
5. Wire all filter/sort/search controls to actually filter the data

---

## PART 5: COMPLETE CONTROL INVENTORY (Every Button/Slider Must Work)

### AgentCommandCenter Controls
| Control | Current State | Backend Endpoint Needed |
|---|---|---|
| Restart All button | UI only | `POST /agents/batch/restart` (NEW) |
| Stop All button | UI only | `POST /agents/batch/stop` (NEW) |
| Spawn Team button | UI only | Future: spawn agent team |
| Run Conference button | UI only | `POST /council/evaluate` |
| Emergency Kill button | UI only | `POST /risk/emergency/halt` |
| Per-agent Start/Stop/Pause/Restart | UI only | `POST /agents/{id}/start\|stop\|pause\|restart` |
| Per-agent Weight slider | UI only | `PUT /agents/{id}/config` (NEW) |
| Per-agent Confidence slider | UI only | `PUT /agents/{id}/config` (NEW) |
| Per-agent Temperature slider | UI only | `PUT /agents/{id}/config` (NEW) |
| Per-agent Power toggle | UI only | `POST /agents/{id}/start\|stop` |
| Per-agent Priority dropdown | UI only | `PUT /agents/{id}/config` (NEW) |
| HITL Approve/Reject/Defer | UI only | `POST /agents/hitl/{id}/*` (NEW) |
| Filter dropdowns (ELO/Status/WinRate/PnL) | UI only | Client-side filter on `/agents` data |
| Search input | UI only | Client-side search on `/agents` data |
| Auto-Refresh toggle | UI only | Toggle WebSocket subscription |
| Layout buttons (Hierarchical/Force/Circular) | UI only | Client-side layout toggle |

### PerformanceAnalytics Controls
| Control | Current State | Backend Endpoint |
|---|---|---|
| Trading Grade badge | Hardcoded | `GET /performance/risk-metrics` → trading_grade |
| Timeframe selector (1D/1W/1M/3M/1Y) | UI only | Pass to `/performance/equity?tf=` |
| Returns Heatmap Calendar | Hardcoded | Derive from `/performance/trades` |

### Risk Intelligence Controls
| Control | Current State | Backend Endpoint |
|---|---|---|
| EMERGENCY STOP ALL button | UI only | `POST /risk/emergency/halt` |
| Resume Trading button | UI only | `POST /risk/emergency/resume` |
| Flatten All button | UI only | `POST /risk/emergency/flatten` |
| Risk parameter sliders | Connected | `PUT /risk` |
| Circuit breaker toggles | Display only | Need `PUT /risk/circuit-breakers` |

---

## SUMMARY STATISTICS

- **Total Backend Endpoints**: ~120+
- **Currently Wired to Frontend**: ~65 (54%)
- **Needs Wiring (endpoint exists)**: ~35 (29%)
- **Missing (need new endpoint)**: ~20 (17%)
- **Total Frontend Controls**: ~80+
- **Currently Functional**: ~35 (44%)
- **UI-only (need backend wiring)**: ~45 (56%)
- **New Backend Endpoints to Create**: 12-15
- **Pages Needing Work**: All 15 pages need some level of integration work
- **Priority Pages**: AgentCommandCenter (most gaps), PerformanceAnalytics, Risk Intelligence
