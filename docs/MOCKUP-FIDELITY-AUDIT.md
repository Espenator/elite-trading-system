# MOCKUP → CODE FIDELITY AUDIT
## Embodier Trader — Full Page-by-Page Analysis
### Generated: 2026-03-06

> **Goal**: Every app page must be a pixel-perfect mirror of its corresponding mockup image.
> This audit maps every mockup to its code file, identifies every gap, and provides fix instructions.

---

## TABLE OF CONTENTS

1. [Mockup-to-Page Mapping](#mapping)
2. [Per-Page Gap Analysis](#gap-analysis)
3. [Shared Layout Gaps](#shared-gaps)
4. [Priority Fix Queue](#priority-queue)
5. [Estimated Effort](#effort)

---

## 1. MOCKUP → PAGE MAPPING {#mapping}

| # | Mockup Image | Page File | Route | Match Level |
|---|---|---|---|---|
| 1 | `01-agent-command-center-final.png` | `AgentCommandCenter.jsx` → Swarm Overview tab | `/agents` | 🟡 PARTIAL |
| 2 | `02-intelligence-dashboard.png` | `Dashboard.jsx` | `/dashboard` | 🟢 GOOD |
| 3 | `03-signal-intelligence.png` | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | 🟢 GOOD |
| 4 | `04-sentiment-intelligence.png` | `SentimentIntelligence.jsx` | `/sentiment` | 🟡 PARTIAL |
| 5 | `05-agent-command-center.png` | `AgentCommandCenter.jsx` → Live Wiring Map tab | `/agents` | 🟡 PARTIAL |
| 6 | `05b-agent-command-center-spawn.png` | `AgentCommandCenter.jsx` → Spawn & Scale tab | `/agents` | 🟡 PARTIAL |
| 7 | `05c-agent-registry.png` | `AgentCommandCenter.jsx` → Agent Registry tab | `/agents` | 🟡 PARTIAL |
| 8 | `06-ml-brain-flywheel.png` | `MLBrainFlywheel.jsx` | `/ml-brain` | 🟢 GOOD |
| 9 | `07-screener-and-patterns.png` | `Patterns.jsx` | `/patterns` | 🟢 GOOD |
| 10 | `08-backtesting-lab.png` | `Backtesting.jsx` | `/backtest` | 🟢 GOOD |
| 11 | `09-data-sources-manager.png` | `DataSourcesMonitor.jsx` | `/data-sources` | 🟢 CLOSE |
| 12 | `10-market-regime-green.png` | `MarketRegime.jsx` | `/market-regime` | 🟢 CLOSE |
| 13 | `10-market-regime-red.png` | `MarketRegime.jsx` | `/market-regime` | 🟢 CLOSE |
| 14 | `11-performance-analytics-fullpage.png` | `PerformanceAnalytics.jsx` | `/performance` | 🟡 PARTIAL |
| 15 | `12-trade-execution.png` | `TradeExecution.jsx` | `/trade-execution` | 🟡 PARTIAL |
| 16 | `13-risk-intelligence.png` | `RiskIntelligence.jsx` | `/risk` | 🟡 PARTIAL |
| 17 | `14-settings.png` | `Settings.jsx` | `/settings` | 🟢 GOOD |
| 18 | `Active-Trades.png` | `Trades.jsx` | `/trades` | 🟢 CLOSE |
| 19 | `agent command center brain map.png` | `AgentCommandCenter.jsx` → Brain Map tab | `/agents` | 🟡 PARTIAL |
| 20 | `agent command center node control.png` | `AgentCommandCenter.jsx` → Node Control tab | `/agents` | 🟡 PARTIAL |
| 21 | `agent command center swarm overview.png` | `SwarmIntelligence.jsx` OR `AgentCommandCenter.jsx` Swarm tab | `/agents` or `/swarm-intelligence` | 🔴 DUPLICATE CONFLICT |
| 22 | `realtimeblackbard fead.png` | `AgentCommandCenter.jsx` → Blackboard & Comms tab | `/agents` | 🟡 PARTIAL |
| 23 | `10-active-trades.html` | `Trades.jsx` (HTML reference mockup) | `/trades` | N/A (HTML) |

### PAGES WITH NO MOCKUP (code exists, no visual target):
- `CognitiveDashboard.jsx` (`/cognitive-dashboard`) — No corresponding mockup image
- `SwarmIntelligence.jsx` (`/swarm-intelligence`) — Overlaps with ACC Swarm Overview

---

## 2. PER-PAGE GAP ANALYSIS {#gap-analysis}

---

### PAGE 1: Dashboard (`02-intelligence-dashboard.png`)
**File**: `Dashboard.jsx` (83KB, ~1955 lines)
**Match Level**: 🟢 GOOD — Core structure matches, minor refinements needed

#### WHAT THE MOCKUP SHOWS:
- Top: "EMBODIER TRADER" header with hex logo, ticker strip scrolling market data
- Left: 6-icon mini sidebar (Dash, Signals, Portfolio, Risk, Agents, ML)
- Center: Sort pill filters (15 options) + timeframe selector + massive signals table (~21 columns) with colored score bars per row
- Right (~32%): Swarm Consensus bars, Signal Strength bar chart, Regime Donut + Top Trades Donut, Selected Symbol Detail (composite breakdown, technical grid 2×4, SHAP drivers), Risk & Order Proposal (L2 order book), Cognitive Intelligence, Equity Curve sparkline, ML Flywheel Pipeline
- Bottom: Action buttons (Spawn Agent, Flatten All, Emergency Stop) + system status

#### WHAT THE CODE RENDERS:
✅ Header with HexagonLogo, TickerStrip (16 symbols), regime/score/risk/sentiment badges, KPI row
✅ Left sidebar with 6 icon buttons
✅ Center: 15 Sort Pills, Timeframe selector, Main Signals Table (21 columns)
✅ Right panel: Swarm Consensus, SignalBarChart, Regime/TopTrades Donuts, Detail Panel, SHAP Drivers, L2 Order Book, Cognitive section, Equity Curve, Flywheel Pipeline
✅ Footer: Spawn Agent, Flatten All, Emergency Stop + WS/API dots

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 1.1 | Score bar widths in table may not match mockup proportions | Minor | Compare bar gradient CSS to mockup colors — ensure `bg-gradient-to-r from-cyan-500 to-emerald-500` fills correctly proportional |
| 1.2 | Ticker strip scroll speed may differ | Minor | Tune animation duration CSS |
| 1.3 | Right panel section order may need verification | Minor | Visually verify in browser that sections stack in same order as mockup |
| 1.4 | Need to verify EXACT font sizes match design system (0.65rem for dense cells) | Minor | Audit all `text-[Xpx]` classes |

**VERDICT**: Dashboard is the closest match. Needs pixel-polish, not structural changes.

---

### PAGE 2: Agent Command Center — Swarm Overview (`01-agent-command-center-final.png`)
**File**: `AgentCommandCenter.jsx` → Tab 1 (Swarm Overview)
**Match Level**: 🟡 PARTIAL — Layout structure differs significantly

#### WHAT THE MOCKUP SHOWS:
Dense 12-column command center layout:
- **Top-left**: AGENT HEALTH MATRIX (6×2 grid of colored health dots with legend: Scanner, Intelligence, Execution, Streaming, Sentiment, MLearning, Conference; States: Active, Idle, Warning, Error, Stopped)
- **Top-left below**: QUICK ACTIONS (Restart All, Stop All, Spawn Team, Run Conference, Emergency Kill buttons)
- **Below Quick Actions**: TEAM STATUS (team names with status badges and agent counts)
- **Top-center**: LIVE AGENT ACTIVITY FEED (timestamped log of agent actions)
- **Top-right**: SWARM TOPOLOGY (network graph with colored nodes)
- **Below topology**: Agent ELO Leaderboard (rank table)
- **Mid-center**: AGENT RESOURCE MONITOR (table: Agent, CPU, MEM, Requests/s, Throughput, Status)
- **Mid-right**: CONFERENCE PIPELINE (Researcher → RiskOfficer → Adversary → Arbitrator flow)
- **Below pipeline**: LAST CONFERENCE (AAPL #941 result with verdict and confidence ring)
- **Bottom-left**: SYSTEM ALERTS (color-coded alert rows: RED, AMBER, INFO)
- **Bottom-center**: BLACKBOARD LIVE FEED (topic/message table)
- **Bottom-right**: DRIFT MONITOR (agent drift detection indicators)
- **Footer bar**: WebSocket/API status, agent counts, LLM Flow, Conference stats, uptime

#### WHAT THE CODE RENDERS (Tab 1 — Swarm Overview):
⚠️ Filter bar (ELO/Status/Win Rate/PnL dropdowns + Running/Paused/Degraded/Spawning toggles)
⚠️ 4-column agent card grid (each with ELO, Win Rate, PnL, sparkline)
⚠️ Footer bar (Swarm Health %, Total ELO, Avg Confidence)

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 2.1 | **MISSING: Agent Health Matrix** — 6×2 dot grid not present | 🔴 HIGH | Add AgentHealthMatrix component with type-colored dots and legend |
| 2.2 | **MISSING: Quick Actions panel** — no Restart All/Stop All/Spawn Team/Run Conference/Emergency Kill button group | 🔴 HIGH | Add Quick Actions card with 5 action buttons |
| 2.3 | **MISSING: Team Status panel** — no team names/badges/counts | 🟡 MEDIUM | Add Team Status card pulling from agents grouped by team |
| 2.4 | **MISSING: Live Agent Activity Feed** — no timestamped action log | 🔴 HIGH | Add scrollable feed using LiveActivityFeed component (already defined in code but not rendered in tab 1) |
| 2.5 | **MISSING: Swarm Topology visualization** — no network graph with colored nodes | 🔴 HIGH | Add SVG/canvas topology using ReactFlow or custom SVG. Nodes colored by agent type |
| 2.6 | **MISSING: Agent ELO Leaderboard table** | 🟡 MEDIUM | Add table: Rank, Agent, ELO, Win% |
| 2.7 | **MISSING: Agent Resource Monitor table** | 🟡 MEDIUM | Add table: Agent, CPU%, MEM MB, Requests/s, Throughput, Status |
| 2.8 | **MISSING: Conference Pipeline flow** | 🟡 MEDIUM | Add horizontal flow diagram: Researcher → RiskOfficer → Adversary → Arbitrator |
| 2.9 | **MISSING: Last Conference panel** | 🟡 MEDIUM | Add panel showing latest conference result with verdict donut |
| 2.10 | **MISSING: System Alerts panel** | 🟡 MEDIUM | Add color-coded alert rows (RED/AMBER/INFO) |
| 2.11 | **MISSING: Blackboard Live Feed table** | 🟡 MEDIUM | Add BlackboardLiveFeed (component exists but not in tab 1) |
| 2.12 | **MISSING: Drift Monitor panel** | 🟡 MEDIUM | Add drift detection indicators |
| 2.13 | **Layout wrong**: Code uses card grid; mockup uses dense multi-panel 12-col grid | 🔴 HIGH | Restructure entire tab 1 layout to match the 3-column dense panel layout from mockup |
| 2.14 | **Footer bar incomplete**: Missing LLM Flow count, Conference stats | 🟡 MEDIUM | Add LLM Flow, Conference 8/12 to footer |

**VERDICT**: Major structural rewrite needed. The current Swarm Overview is a card grid; the mockup is a dense command center with 12+ distinct panels. NOTE: The newer mockup `agent command center swarm overview.png` shows the card grid layout — need to decide which is canonical.

---

### PAGE 3: Agent Command Center — Agent Registry (`05c-agent-registry.png`)
**File**: `AgentCommandCenter.jsx` → Tab 2 (Agent Registry)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Header: Same ACC header with tabs, "Agent Registry" tab active
- Left (~60%): MASTER AGENT TABLE with 20+ columns (Agent, Status, Type, PID, ELO, Accuracy, Win%, Signals, CPU, MEM, KB, Heap, Subs, Latency, Last Active, etc.), row selection highlight, toolbar with buttons (Bulk Start, Bulk Reset, Bulk Restart, Stop, Type dropdown)
- Right (~40%): AGENT INSPECTOR panel with:
  - Agent name + RUNNING badge
  - Configuration section (model, interval, subscribers, etc.) + Apply Changes/Reset buttons
  - Performance Metrics (Requests/s, Avg Latency, Error Rate, Success Rate, Signals, Queue Depth)
  - Agent Logs (filtered terminal)
  - SHAP Feature Importance (5 horizontal bars)
  - LIFECYCLE CONTROLS BAR at bottom (donut %, Start/Stop, Auto-Restart checkbox, Max Restarts, Cooldown)

#### WHAT THE CODE RENDERS:
✅ Master Agent Table with 16 columns
✅ Agent Inspector Panel (right sidebar) with config, performance, logs, SHAP, lifecycle
⚠️ Agent Cards Grid (3-col) — NOT in mockup

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 3.1 | Code has Agent Cards Grid between table and inspector — mockup doesn't | 🟡 MEDIUM | Remove or hide the agent cards grid, make table + inspector the only content |
| 3.2 | Table has 16 columns; mockup shows ~20+ | 🟡 MEDIUM | Add missing columns: PID, KB, Heap, more granular stats |
| 3.3 | Lifecycle Controls Bar positioning — mockup shows it as full-width bottom bar | 🟡 MEDIUM | Move lifecycle controls from inspector panel to a separate full-width bar |
| 3.4 | Inspector panel width — mockup ~40%, code 380px fixed | Minor | Make inspector responsive ~40% instead of fixed width |

---

### PAGE 4: Agent Command Center — Spawn & Scale (`05b-agent-command-center-spawn.png`)
**File**: `AgentCommandCenter.jsx` → Tab 3 (Spawn & Scale)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Top row (4 panels): Agent Spawn & Swarm Orchestrator | OpenClaw Swarm Control (gauge) | ML Engine & Flywheel | Trading Conference & Auto-Scale
- Center: NATURAL LANGUAGE SPAWN PROMPT (large text input + EXECUTE PROMPT button)
- Mid: QUICK-SPAWN TEMPLATE GRID (10 template cards in 5×2 grid)
- Bottom-left: CUSTOM AGENT BUILDER (form: Agent Name, Type, Data Sources, Risk Interval slider, Temperature slider, Kill Condition)
- Bottom-right: ACTIVE SPAWNED AGENTS TABLE (10 columns)

#### WHAT THE CODE RENDERS:
✅ 4 top panels with config, gauge, ML metrics, conference metrics
✅ NLP spawn prompt with Execute button
✅ 10 template cards in grid
✅ Custom Agent Builder form
✅ Active Spawned Agents table

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 4.1 | Template grid layout — mockup shows 5×2 cards with icons; verify card icons match | Minor | Verify each of the 10 templates has correct icon from mockup |
| 4.2 | OpenClaw Swarm Control gauge styling — mockup shows bright cyan semicircle | Minor | Verify gauge arc styling matches |
| 4.3 | Custom Agent Builder — slider styling may differ | Minor | Compare slider visual to mockup |

**VERDICT**: Good structural match. Mostly cosmetic alignment needed.

---

### PAGE 5: Agent Command Center — Live Wiring Map (`05-agent-command-center.png`)
**File**: `AgentCommandCenter.jsx` → Tab 4 (Live Wiring Map)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Full-width SVG network diagram with 5 columns of connected nodes:
  - EXTERNAL SOURCES (Alpaca API, Finviz, Unusual Whales, FRED, SEC, Discord, Reddit, X/Twitter, YouTube)
  - AGENT (Signal Generation Agent, ML Learning Agent, Sentiment Agent, Streaming Agent)
  - PROCESSING ENGINES (signal_engine.py, ml_engine.py, etc.)
  - STORAGE/DATABASES (DuckDB, knowledge_base, model_registry, etc.)
  - FRONTEND/INTERFACES (AgentCommandCenter.js, Backtesting.js, Patterns.js, etc.)
- Right panel: CONNECTION HEALTH MATRIX (6×6 green/yellow/red), DYNAMIC NODE DISCOVERY table, WEBSOCKET CHANNELS, API ROUTE MAP

#### WHAT THE CODE RENDERS:
✅ SVG network diagram with 5 columns of nodes and connecting lines
✅ Right panel with Connection Health Matrix, WebSocket Channels, API Route Status
⚠️ Node discovery panel not present in code

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 5.1 | **MISSING: Dynamic Node Discovery panel** | 🟡 MEDIUM | Add node discovery table showing recently detected nodes |
| 5.2 | SVG line colors/curvature may not match mockup exactly | Minor | Compare line gradients and path curvature |
| 5.3 | Node icons/colors may differ | Minor | Verify each node has correct icon and type-color |

---

### PAGE 6: Agent Command Center — Brain Map (`agent command center brain map.png`)
**File**: `AgentCommandCenter.jsx` → Tab 9 (Brain Map)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Toolbar: Hierarchical/Force-Directed/Circular toggles, Zoom +/-, Fit, Filter, Layer, Status, Agent, Highlight Path, Source to Frontend, Auto-Refresh toggle, Snapshot buttons
- Main: 5-layer DAG with animated connections between layers, each node showing agent name, status badge, confidence, last action, latency
- Bottom: 3 panels — CONNECTION HEALTH MATRIX (8×8), CONFERENCE DAG, FLOW ANOMALY DETECTOR

#### WHAT THE CODE RENDERS:
✅ Toolbar with layout toggles, zoom, fit, filter, layer buttons
✅ 5-layer DAG SVG (9 sources → 5 agents → 8 processing → 5 storage → 1 frontend)
✅ Bottom panels: Connection Health Matrix, Conference DAG, Flow Anomaly Detector

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 6.1 | Toolbar buttons may be missing: "Source to Frontend" highlight button, Auto-Refresh toggle | Minor | Add missing toolbar actions |
| 6.2 | Node detail richness — mockup shows confidence %, last action, latency per node | 🟡 MEDIUM | Enhance node rendering to show more metadata |
| 6.3 | Connection line animation — mockup shows animated dashes | Minor | Add CSS `stroke-dasharray` animation |

---

### PAGE 7: Agent Command Center — Node Control (`agent command center node control.png`)
**File**: `AgentCommandCenter.jsx` → Tab 10 (Node Control & HITL)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Header: "MAIN CONTENT — TWO MAJOR SECTIONS SPLIT HORIZONTALLY"
- Top half: Agent Config Table (Agent Name, Power toggle, Weight slider, Conf Threshold, State, Temperature, Context Window, Controls, Priority, Load bar, Acc%, Reach/Trades)
- Bottom half: HITL RING BUFFER VISUAL (large semicircle gauge with Buffer % + stats) + HITL Ring Buffer Table (right) with Timestamp, Agent Source, Action Type, Symbol, Confidence, Reasoning Summary, Max Impact, Urgency, Timer, Review Actions
- Bottom panels: OVERRIDE HISTORY LOG, Flow to agentConfig chart, HITL ANALYTICS charts (Buffer Write Rate, Approval Latency, Review Distribution)

#### WHAT THE CODE RENDERS:
✅ Agent Config Table with power toggles, weight sliders, threshold sliders, state badges, temperature sliders
✅ HITL Ring Buffer Visual (semicircle gauge with stats)
⚠️ Missing: HITL Ring Buffer detail table, Override History Log, HITL Analytics charts

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 7.1 | **MISSING: HITL Ring Buffer detail table** with Timestamp, Agent Source, Action Type, Symbol, Confidence, Reasoning | 🔴 HIGH | Add scrollable table below gauge |
| 7.2 | **MISSING: Override History Log** | 🟡 MEDIUM | Add timestamped log of overrides |
| 7.3 | **MISSING: HITL Analytics charts** (Buffer Write Rate, Approval Latency, Review Distribution) | 🟡 MEDIUM | Add 3 mini charts |

---

### PAGE 8: Agent Command Center — Blackboard & Comms (`realtimeblackbard fead.png`)
**File**: `AgentCommandCenter.jsx` → Tab 5 (Blackboard & Comms)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Sub-tab navigation: Overview | Agents | Signal Control | LiveFlyup | Grid | Market
- Main: REAL-TIME BLACKBOARD FEED (large terminal-style log)
- Right: WEBSOCKET CHANNEL MONITOR table + HITL RING BUFFER + AGENT LIFECYCLE CONTROLS

#### WHAT THE CODE RENDERS:
✅ Real-time Blackboard Feed terminal
✅ WebSocket Channel Monitor table
✅ HITL Ring Buffer
✅ Agent Lifecycle Controls
⚠️ Missing sub-tab navigation

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 8.1 | **MISSING: Sub-tab navigation** (Overview/Agents/Signal Control/LiveFlyup/Grid/Market) | 🟡 MEDIUM | Add secondary tab bar within Blackboard & Comms tab |

---

### PAGE 9: Signal Intelligence V3 (`03-signal-intelligence.png`)
**File**: `SignalIntelligenceV3.jsx` (63KB)
**Match Level**: 🟢 GOOD

#### WHAT THE MOCKUP SHOWS:
- Left sidebar navigation (standard Embodier sidebar with sections)
- Header toolbar: "SIGNAL_INTELLIGENCE_V3" + badges
- Regime Banner: "BULL_TREND REGIME" with HMM confidence
- 4-column grid: Scanners | Chart + Signal Table | Scoring Engine + Intelligence Modules | External Sensors + Execution Controls + ML Models
- Bottom status bar: agents, DB, signals, hit rate, WS, time

#### WHAT THE CODE RENDERS:
✅ All 4 columns with correct content distribution
✅ 14 scanner modules with toggles/weights
✅ Candlestick chart with SMA overlays
✅ Signal data table (6 columns)
✅ Global Scoring Engine with SHAP weights
✅ 9 Intelligence Modules
✅ External Sensors + Execution Controls + ML Model Control
✅ Bottom status bar

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 9.1 | Sidebar: Mockup shows the full left sidebar nav; code relies on Layout.jsx sidebar | Minor | Verify Layout sidebar matches mockup sidebar exactly (section headers, icon list, active highlight) |
| 9.2 | Chart ENTRY/TARGET/STOP price lines may need styling verification | Minor | Verify horizontal price line colors match |
| 9.3 | Extended Swarm section shows "93 agents" — verify all render correctly | Minor | Test with real data |

**VERDICT**: Very close match. Minor styling verification needed.

---

### PAGE 10: Sentiment Intelligence (`04-sentiment-intelligence.png`)
**File**: `SentimentIntelligence.jsx` (32KB)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Ultrawide curved display view (the mockup was rendered on a curved monitor)
- Left: OpenClaw Agent Swarm (agent list with weights), Sentiment Sources chart
- Center: PAS Regime Banner, Sentiment Heatmap (color-coded grid), 30-Day Sentiment chart, Trade Signals
- Right: Prediction Market (2 cards), Spider/Radar chart, Scanner Status Matrix (colored dot grid), Divergence Alerts (amber warning cards), Emergency Alerts

#### WHAT THE CODE RENDERS:
✅ Left: OpenClaw Agent Swarm card (6 agents), Sentiment Sources chart
✅ Center: PAS Regime Banner, Sentiment Heatmap, 30-Day Sentiment, Divergence Alerts
✅ Right: Trade Signals, 2× Prediction Market cards, Multi-Factor Radar Chart, Scanner Status Matrix

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 10.1 | Heatmap: Mockup shows VERY dense color-coded grid with thin cell borders; verify CSS matches | 🟡 MEDIUM | Ensure heatmap cells are `text-[10px] font-mono` with 1px gap borders |
| 10.2 | Scanner Status Matrix: Mockup shows large dot grid (maybe 12×8); code shows table | 🟡 MEDIUM | Verify dot matrix rendering (should be colored circles not text) |
| 10.3 | Radar chart: Mockup shows 8-factor spider; code does 8 factors — verify polygon fill opacity | Minor | Check SVG polygon `fill-opacity` matches cyan 20% from design system |
| 10.4 | **MISSING: Emergency Alert cards** (amber warning cards at bottom-center in mockup) | 🟡 MEDIUM | These may be part of divergence alerts but styled differently in mockup |

---

### PAGE 11: ML Brain & Flywheel (`06-ml-brain-flywheel.png`)
**File**: `MLBrainFlywheel.jsx` (22KB)
**Match Level**: 🟢 GOOD

#### WHAT THE MOCKUP SHOWS:
- Header: "ML Brain & Flywheel" with sidebar nav
- KPI strip (6 boxes): Active Models (3), Walk Forward Accuracy (91.4%), Stage 3 Ignitions (24), Flywheel Cycles, Feature Store (OK), Win Rate Threshold (>70%)
- Left: Model Performance Tracking chart (line graph)
- Right: Stage 4: ML Probability Ranking table
- Bottom-left: Deployed Inference Fleet (6 model cards, 2×3 grid)
- Bottom-right: Flywheel Learning Log (scrollable text log)

#### WHAT THE CODE RENDERS:
✅ 6 KPI cards in strip
✅ Model Performance Tracking with Lightweight Charts
✅ ML Probability Ranking table
✅ Deployed Inference Fleet as card grid
✅ Flywheel Learning Log

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 11.1 | Model cards layout — mockup shows 3×2 grid; verify code uses same | Minor | Verify `grid-cols-3` for model cards |
| 11.2 | FeatureImportanceChart and FlywheelCycleSVG defined but NOT rendered | 🟡 MEDIUM | The mockup doesn't show these either, but they're dead code — consider adding or removing |
| 11.3 | KPI strip — verify exact values and label formatting match mockup | Minor | Compare text formatting |

**VERDICT**: Good match. Minimal changes needed.

---

### PAGE 12: Screener & Patterns (`07-screener-and-patterns.png`)
**File**: `Patterns.jsx` (40KB)
**Match Level**: 🟢 GOOD

#### WHAT THE MOCKUP SHOWS:
- Header: "SCREENER AND PATTERNS" with sidebar
- Top-left: SCREENING ENGINE (Scanner Agent Card + Trading Metric Controls sliders)
- Top-right: PATTERN INTELLIGENCE (Pattern Agent Card + ML Metric Controls)
- Bottom row (3 panels): Consolidated Live Feed | Pattern Arsenal | Forming Detections
- Action buttons: Spawn New Scanner Agent, Clone Agent, Power Scans, Spawn Template, Kill All Agents (for both engines)

#### WHAT THE CODE RENDERS:
✅ All sections present with correct titles
✅ Scanner Agent Card + metric sliders
✅ Pattern Agent Card + ML controls
✅ Consolidated Live Feed, Pattern Arsenal, Forming Detections
✅ All spawn/kill action buttons

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 12.1 | Verify slider label formatting matches mockup exactly | Minor | Check slider text alignment |
| 12.2 | Forming Detections — mockup shows mini chart thumbnails; code has MiniChart sparklines | Minor | Verify sparkline rendering |

**VERDICT**: Very close match.

---

### PAGE 13: Backtesting Lab (`08-backtesting-lab.png`)
**File**: `Backtesting.jsx` (45KB)
**Match Level**: 🟢 GOOD

#### WHAT THE MOCKUP SHOWS:
- Extremely dense layout with 5 rows of panels:
- Row 1: Config | Parameter Sweeps | OpenClaw Swarm Integration
- Row 2: Performance KPI Mega Strip (28 KPIs in 2 rows)
- Row 3: Equity Curve | Parallel Run Manager | Trade P&L Distribution | Rolling Sharpe | Walk-Forward Analysis
- Row 4: Market Regime Performance | Monte Carlo (50 paths) | Parameter Optimization Heatmap | Strategy Builder (ReactFlow)
- Row 5: Trade-by-Trade Log | Run History | OpenClaw Swarm Consensus

#### WHAT THE CODE RENDERS:
✅ All 5 rows with correct panel distribution
✅ 28 KPI boxes in 2 rows of 14
✅ All charts: Equity Curve, P&L Distribution, Rolling Sharpe, Walk-Forward, Monte Carlo, Heatmap, ReactFlow
✅ Trade log, Run History, Swarm Consensus

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 13.1 | KPI box coloring — verify green/amber/red thresholds match mockup | Minor | Compare values |
| 13.2 | Monte Carlo chart — verify 50-path rendering matches mockup | Minor | Test with data |
| 13.3 | Strategy Builder ReactFlow — verify node types match mockup | Minor | Compare node shapes |

**VERDICT**: Excellent match. The most dense page and it's well-implemented.

---

### PAGE 14: Data Sources Manager (`09-data-sources-manager.png`)
**File**: `DataSourcesMonitor.jsx` (45KB)
**Match Level**: 🟢 CLOSE

#### WHAT THE MOCKUP SHOWS:
- Header: "DATA_SOURCES_MANAGER" with WS/API status indicators
- Top metrics bar: Connected count, System Health %, Ingestion rate, OpenClaw Bridge status
- AI-powered search input
- Provider chips + Filter tabs (ALL, Brokerage, Data, etc.)
- Source table: Finviz (Screener), Unusual Whales (Options Flow), Alpaca (Market Data), FRED (Macro), SEC EDGAR, Stockgeist, News API, Discord, X/Twitter, YouTube — each with icon, name, category, status, latency, uptime, sparkline, count
- Right panel: Credential Panel (API Key, Base URL, WebSocket URL, Rate Limit, Polling, Account Type, Test Connection)
- Footer: Supplier Heartbeat bar

#### WHAT THE CODE RENDERS:
✅ All above sections implemented
✅ Credential Panel with all fields
✅ Supplier Heartbeat bar
✅ Sparklines in table

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 14.1 | "VERSION A: SPLIT VIEW LAYOUT" text in mockup header — remove from code if present | Minor | Cosmetic |
| 14.2 | Source row icons — verify each source has correct icon (llama for Alpaca, chart for Finviz, etc.) | Minor | Verify icon mapping |

**VERDICT**: Very close. Previously marked as "DONE" and it shows.

---

### PAGE 15: Market Regime (`10-market-regime-green.png` + `10-market-regime-red.png`)
**File**: `MarketRegime.jsx` (40KB)
**Match Level**: 🟢 CLOSE

#### WHAT THE MOCKUP SHOWS (GREEN state):
- Header: "Market Regime" + GREEN 87% badge + Risk Score: 34 healthy + timeframe selector
- KPI strip (10): VIX, HY Spread, Yield Curve, Fear & Greed, Hurst, VELEZ SLAM, Oscillator, Bias Mult, Risk Score, Crash Proto
- Row 1: Regime State Machine (2×2 grid) | VIX+Macro Chart (dual-line)
- Row 2: Regime Parameter Panel | Performance Matrix (3×3) | Sector Rotation (horizontal bars)
- Row 3: Regime Flow (pipeline diagram) | Crash Protocol (5 triggers) | Agent Consensus
- Row 4: Regime Transition History (table) + Bias Multiplier slider
- Footer ticker: SPY, QQQ, DIA, VIX, IWM

#### WHAT THE CODE RENDERS:
✅ All sections present and structured correctly
✅ Regime State Machine 2×2 grid
✅ VIX+Macro dual-line chart with thresholds
✅ Parameter Panel with editable fields
✅ Performance Matrix (3 metrics × 3 regimes)
✅ Sector Rotation bars
✅ Regime Flow pipeline
✅ Crash Protocol (5 triggers with ARMED/OFF toggles)
✅ Agent Consensus list
✅ Transition History table
✅ Bias Multiplier slider
✅ Footer ticker

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 15.1 | RED state: Verify all elements change correctly when regime is RED (mockup shows `*New Box*` annotations, BLOCKED labels) | 🟡 MEDIUM | Test with RED regime data; verify Regime Flow shows BLOCKED/HALTED in red |
| 15.2 | Crash Protocol — verify pulsing red dot when TRIGGERED | Minor | Check CSS animation on active triggers |
| 15.3 | "EXACT" labels visible on mockup left edge — these are annotations, not UI elements | N/A | Ignore |

**VERDICT**: Very close. Previously marked as "DONE".

---

### PAGE 16: Performance Analytics (`11-performance-analytics-fullpage.png`)
**File**: `PerformanceAnalytics.jsx` (60KB)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Header: "Performance Analytics" with sidebar + Trading Grade badge (top-right)
- KPI strip (10): Total Trades, Net P&L, Win Rate, Avg Win, Avg Loss, Profit Factor, Max DD, Sharpe, Expectancy, R:R
- Left column: Risk Cockpit (Grade hero circle + Sharpe/Sortino/Calmar), Kelly Criterion, Agent Attribution Leaderboard, Risk/Reward + Expectancy bar chart
- Center column: Equity + Drawdown chart, Enhanced Trades Table
- Right column: AI + Rolling Risk (concentric rings, rolling Sharpe, P/L by Symbol), Attribution + Agent ELO table, Returns Heatmap Calendar
- Bottom row (4 panels): ML & Flywheel Engine | Risk Cockpit Expanded | Strategy & Signals | (4th panel visible but details unclear)

#### WHAT THE CODE RENDERS:
✅ All sections structurally present
✅ KPI strip (10 cards)
✅ Risk Cockpit with SVG Grade circle
✅ Kelly Criterion panel
✅ Equity + Drawdown chart
✅ Enhanced Trades Table
✅ AI + Rolling Risk panels
✅ Agent Attribution + ELO
✅ Bottom row panels

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 16.1 | Trading Grade badge positioning — mockup shows large green circle badge at top-right corner | 🟡 MEDIUM | Verify badge size/position matches |
| 16.2 | Returns Heatmap Calendar — mockup shows colored monthly grid; verify code generates same | 🟡 MEDIUM | Verify 13-cell grid (Jan-Dec + YTD) with correct green/red coloring |
| 16.3 | Bottom 4th panel — mockup shows content but details unclear | Minor | Need to zoom into mockup |
| 16.4 | AI Concentric Rings — verify SVG dual-ring layout matches mockup (inner ring lighter, outer darker) | Minor | Compare ring proportions |

---

### PAGE 17: Trade Execution (`12-trade-execution.png`)
**File**: `TradeExecution.jsx` (31KB)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Header: "TRADE EXECUTION" with Portfolio value, Daily P/L, Status: ELITE, Latency
- Quick Execution: Market Buy (green), Market Sell (red), Limit Buy, Limit Sell, Stop Loss — 5 buttons
- Left column: Multi-Price Ladder (scrollable price table with size bars)
- Center: Advanced Order Builder (Symbol, Strategy: Iron Condor, Call/Put selectors, Quantity, Limit, Execute button) + Live Order Book (Bid/Size/Total table with depth bars)
- Right: Price Charts (candlestick) + News Feed (timestamped entries)
- Bottom: Live Positions table + System Status Log

#### WHAT THE CODE RENDERS:
✅ All sections present
✅ Quick Execution buttons with keyboard shortcuts
✅ Multi-Price Ladder
✅ Advanced Order Builder with strategy selection
✅ Live Order Book
✅ Price Charts (Lightweight Charts)
✅ News Feed
✅ Live Positions + System Status Log

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 17.1 | Order Builder — mockup shows Call/Put strike selector chips in a row; verify code renders chips | 🟡 MEDIUM | Verify strike selection UI matches |
| 17.2 | Live Order Book — mockup shows green bid bars and red ask bars; verify depth visualization | Minor | Check bar gradient colors |
| 17.3 | Price Ladder — mockup shows row 10 highlighted in bright green; verify selected row styling | Minor | Check `--bg-selected` color |

---

### PAGE 18: Risk Intelligence (`13-risk-intelligence.png`)
**File**: `RiskIntelligence.jsx` (58KB)
**Match Level**: 🟡 PARTIAL

#### WHAT THE MOCKUP SHOWS:
- Header: "RISK_INTELLIGENCE" with LIVE badge, grade letter, score, timeframe selector
- Row 1: Risk Configuration (8 items) | Parameter Sweeps (10 KPIs + equity bar chart) | Realtime Risk Detail (8 progress bars)
- Row 2: Stop-Loss Command (9 safety checks + Emergency buttons) | Correlation Matrix (color heatmap) | Volatility Regime Monitor (4 semicircle gauges) | AI Agent Risk Monitors (6 progress bars) | Position Sizing (Kelly bars)
- Row 3: Risk Rules Engine (full-width table)
- Row 4: 90-Day Risk History (full-width bar chart)
- Agent Self-Awareness panel

#### WHAT THE CODE RENDERS:
✅ All sections present
✅ Header with grade, score, status, timeframe, refresh
✅ Risk Configuration, Parameter Sweeps, Realtime Risk Detail
✅ Stop-Loss Command with safety checks
✅ Correlation Matrix heatmap
✅ Volatility gauges, AI monitors, Position Sizing
✅ Risk Rules Engine table
✅ 90-Day Risk History
✅ Agent Self-Awareness panel

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 18.1 | Mockup image resolution is low — hard to verify exact match | Minor | Need higher-res mockup for pixel comparison |
| 18.2 | Correlation matrix cell colors — verify green-to-red gradient matches | Minor | Compare color scale |
| 18.3 | Emergency buttons — mockup shows EMERGENCY STOP ALL prominently in red | Minor | Verify button size/prominence |

---

### PAGE 19: Settings (`14-settings.png`)
**File**: `Settings.jsx` (47KB)
**Match Level**: 🟢 GOOD

#### WHAT THE MOCKUP SHOWS:
- Header: "SYSTEM CONFIGURATION" with SAVE ALL button
- Dense 5×5 grid (25 section cards): Identity & Locale, Trading Mode, Position Sizing, Risk Limits, Circuit Breakers, Brokerage Connections, Data Feed API Keys, Data Source Priority, Ollama LLM, Ollama Models, ML Models, Scanning Config, Pipeline Adjustments, Agent Switches, Backup & System, Trade Management, Order Execution, Notifications, Security & Auth, OpenClaw Bridge, Appearance, Market Data, Notification Channels, Alignment Engine, System/Audit Log
- Footer: Export/Import/Reset buttons + SAVE ALL CHANGES

#### WHAT THE CODE RENDERS:
✅ All 25 sections in 5×5 grid
✅ Correct section titles and content
✅ SAVE ALL button top-right
✅ Footer with Export/Import/Reset/Save
✅ Expandable Audit Log

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 19.1 | Section numbering — mockup shows "1. Intelligence Dashboard", "2. Agent Command Center" etc. in left sidebar; code shows sidebar via Layout | Minor | Sidebar is handled by Layout.jsx |
| 19.2 | Verify all 25 section titles match mockup exactly | Minor | Cross-check titles |

**VERDICT**: Good match. Settings was well-implemented.

---

### PAGE 20: Active Trades (`Active-Trades.png`)
**File**: `Trades.jsx` (32KB)
**Match Level**: 🟢 CLOSE

#### WHAT THE MOCKUP SHOWS:
- Top command strip (cyan bar): Title, NAV value, Daily P&L, Margin Avail, Buying Power, Regime badge, Trade Mode
- POSITIONS table: Symbol, Side, Qty, Avg Entry, Price, Mkt Value, Unrealized P&L, Realized P&L, Cost Basis, Delta, Theta, Gamma, Vega, IV, Daily Range Vol, Sparkline, Actions
- ORDERS table: Order ID, Time, Symbol, Type, Qty, YTD/Day, Limit Price, Stop Price, Status, Execution Time, Avg Fill, Legs, Actions (with profit target/stop loss badges)
- Bottom: Quick Execute bar

#### WHAT THE CODE RENDERS:
✅ Command strip with metrics
✅ Positions table (16 columns)
✅ Orders table (17 columns)
✅ Quick Execute bar
✅ Filter inputs, status cycling, Close Losers, Flatten All, Cancel All

#### GAPS TO FIX:
| # | Gap | Severity | Fix |
|---|---|---|---|
| 20.1 | Positions table — mockup shows Greeks columns (Delta, Theta, Gamma, Vega, IV); code may not include all | 🟡 MEDIUM | Verify all Greek columns are present |
| 20.2 | Orders — mockup shows profit target/stop loss badges in Actions column | Minor | Verify bracket order badges render |
| 20.3 | Sparklines in positions — mockup shows mini price charts per row | Minor | Verify sparklines render |

---

### PAGE 21: SwarmIntelligence.jsx — DUPLICATE CONFLICT
**File**: `SwarmIntelligence.jsx` (32KB)
**Route**: `/swarm-intelligence`
**Mockup**: `agent command center swarm overview.png` shows agent card grid layout

#### CONFLICT:
This page renders a SEPARATE "Agent Command Center" with its OWN:
- Header bar (same as ACC)
- 8-tab navigation (same as ACC)
- Master Agent Table + Agent Inspector
- Lifecycle Controls Bar

This is a DUPLICATE of `AgentCommandCenter.jsx` but at a different route. The mockup `agent command center swarm overview.png` shows the card grid layout that matches this page better than the main ACC Swarm Overview tab.

#### RESOLUTION NEEDED:
| # | Issue | Recommendation |
|---|---|---|
| 21.1 | SwarmIntelligence.jsx duplicates ACC functionality | 🔴 DECIDE: Merge into ACC or keep as separate view |
| 21.2 | Route `/swarm-intelligence` has no dedicated mockup | 🔴 DECIDE: Use `agent command center swarm overview.png` as target |
| 21.3 | If keeping both, the ACC Swarm Overview tab should match mockup `01` and SwarmIntelligence should match mockup `21` | Clarify intent |

---

### PAGE 22: CognitiveDashboard.jsx — NO MOCKUP
**File**: `CognitiveDashboard.jsx` (15KB)
**Route**: `/cognitive-dashboard`
**Mockup**: ❌ NONE

This page exists in code but has no corresponding mockup image. It renders:
- "COGNITIVE TELEMETRY" header
- 6 KPI cards
- Mode Distribution donut, Latency Profile bars, Explore vs Exploit outcomes
- 4 sparkline time series
- Recent Evaluations table

#### ACTION NEEDED:
| # | Issue | Recommendation |
|---|---|---|
| 22.1 | No mockup exists for this page | 🟡 DECIDE: Create a mockup, or remove the page, or accept it as-is with design system styling |

---

## 3. SHARED LAYOUT GAPS {#shared-gaps}

### Sidebar Navigation
| # | Gap | Severity | Fix |
|---|---|---|---|
| S.1 | Sidebar uses `rounded-xl` styling throughout; some mockups show sharper card edges | Minor | Compare border-radius between mockups and code |
| S.2 | Sidebar section headers — mockup shows ALL CAPS; code uses `uppercase tracking-wider` | Minor | Verify font weight and color match `--text-secondary` |
| S.3 | Active nav item — mockup `03` shows cyan background highlight; code uses `bg-primary/30` | Minor | Verify opacity level matches |
| S.4 | Sidebar width — mockup shows ~240px expanded; code uses `w-64` (256px) | Minor | 16px difference, likely acceptable |
| S.5 | Some mockups (01, 05) show NO left sidebar — ACC uses a full-width layout | 🟡 MEDIUM | ACC pages may need to suppress/collapse sidebar automatically |

### Header Bar
| # | Gap | Severity | Fix |
|---|---|---|---|
| H.1 | Global header shows Search + CNS status + Notifications; some mockup pages show different headers | 🟡 MEDIUM | Dashboard, ACC, Market Regime, Trades have CUSTOM headers overriding the global one |
| H.2 | Pages like ACC render their own header bar inside the page; the global header may stack on top | 🟡 MEDIUM | Verify no double-header issue |

### Footer Bar
| # | Gap | Severity | Fix |
|---|---|---|---|
| F.1 | Mockup `01` shows detailed footer (WS, API, agents, LLM Flow, Conference, uptime); global Layout has no footer | 🔴 HIGH | Each page implements its own footer — verify they all match mockup style |
| F.2 | Some pages have footers (ACC, Dashboard, Market Regime); some don't (ML Brain, Patterns) | 🟡 MEDIUM | Add consistent footer to all pages per design system spec |

### Design System Alignment
| # | Gap | Severity | Fix |
|---|---|---|---|
| D.1 | Card corners: Design system says `rounded-md` (6px); shared Card component uses `rounded-xl` (12px) | 🟡 MEDIUM | Standardize to one — mockups show subtle rounding closer to `rounded-md` |
| D.2 | Card headers: Design system says ALL CAPS `text-xs tracking-wider text-slate-400`; some pages use `text-sm font-semibold text-white` | 🟡 MEDIUM | Audit all card headers for consistency |
| D.3 | Table header style: Design system says `text-[10px] uppercase text-slate-500`; DataTable uses `text-xs text-cyan-400 uppercase` | Minor | Cyan vs slate-500 for table headers — mockups show cyan |
| D.4 | JetBrains Mono font — verify it's loaded (in tailwind config but needs @import or font-face) | 🟡 MEDIUM | Check index.html or CSS for font import |

---

## 4. PRIORITY FIX QUEUE {#priority-queue}

### 🔴 P0 — Critical (Structure Wrong)
1. **ACC Swarm Overview tab** — Complete restructure to match mockup `01` (12+ panels vs current card grid)
2. **ACC Node Control tab** — Add HITL detail table, Override History Log, HITL Analytics charts
3. **Footer consistency** — Add per-page footer bars matching design system spec
4. **SwarmIntelligence.jsx duplicate** — Decide: merge into ACC or give distinct purpose

### 🟡 P1 — Medium (Missing Panels/Components)
5. ACC Swarm Overview: Add Health Matrix, Activity Feed, Topology, ELO Leaderboard, Resource Monitor, Conference Pipeline, Drift Monitor, System Alerts, Quick Actions, Team Status, Blackboard Feed
6. ACC Blackboard tab: Add sub-tab navigation
7. ACC Brain Map: Enhance node metadata (confidence, latency, last action)
8. Sentiment: Verify heatmap density, scanner status matrix dot rendering, emergency alerts
9. Performance Analytics: Verify Trading Grade badge position, Returns Heatmap, AI rings
10. Active Trades: Verify Greeks columns present
11. Card corner radius standardization (`rounded-md` vs `rounded-xl`)
12. Card header styling standardization (ALL CAPS, text-xs, slate-400)
13. JetBrains Mono font loading verification
14. ACC header stacking issue — custom page headers vs global header

### 🟢 P2 — Minor (Cosmetic Polish)
15. Dashboard: Score bar proportions, ticker scroll speed
16. Signal Intelligence: Chart price line colors, sidebar active highlight
17. All pages: Font size audit (0.65rem for dense cells)
18. All pages: Color value audit against design system CSS variables
19. Market Regime: RED state testing (BLOCKED labels, pulsing dots)
20. Trade Execution: Strike selector chips, order book depth bars
21. All charts: Grid line colors, axis text colors

---

## 5. ESTIMATED EFFORT {#effort}

| Priority | Item | Effort |
|---|---|---|
| P0.1 | ACC Swarm Overview restructure | 8-12 hours |
| P0.2 | ACC Node Control additions | 4-6 hours |
| P0.3 | Footer consistency | 2-3 hours |
| P0.4 | SwarmIntelligence resolution | 1-2 hours (decision + redirect) |
| P1 (all) | Missing panels + styling fixes | 12-16 hours |
| P2 (all) | Cosmetic polish | 6-8 hours |
| **TOTAL** | | **33-47 hours** |

---

## APPENDIX: File Sizes for Reference

| File | Size | Lines (est) | Complexity |
|---|---|---|---|
| AgentCommandCenter.jsx | 160KB | ~2000+ | 🔴 Massive — 11 tabs |
| Dashboard.jsx | 83KB | ~1955 | 🔴 Dense — main hub |
| PerformanceAnalytics.jsx | 60KB | ~1200 | 🟡 Large |
| SignalIntelligenceV3.jsx | 63KB | ~1083 | 🟡 Large |
| RiskIntelligence.jsx | 58KB | ~1100 | 🟡 Large |
| Settings.jsx | 48KB | ~900 | 🟡 Large |
| Backtesting.jsx | 45KB | ~900 | 🟡 Large |
| DataSourcesMonitor.jsx | 45KB | ~900 | 🟡 Large |
| MarketRegime.jsx | 40KB | ~800 | 🟡 Medium |
| Patterns.jsx | 40KB | ~800 | 🟡 Medium |
| Trades.jsx | 32KB | ~650 | 🟢 Medium |
| SwarmIntelligence.jsx | 32KB | ~650 | 🟢 Medium |
| SentimentIntelligence.jsx | 32KB | ~650 | 🟢 Medium |
| TradeExecution.jsx | 31KB | ~620 | 🟢 Medium |
| MLBrainFlywheel.jsx | 22KB | ~440 | 🟢 Small |
| CognitiveDashboard.jsx | 15KB | ~300 | 🟢 Small |

---

*Generated by Claude — Senior Engineering Audit for Embodier.ai*
*Mockup Source of Truth: `docs/mockups-v3/images/`*
