# Project State - Embodier Trader (Embodier.ai)
> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 10, 2026

## Identity
- **Project**: Embodier Trader by Embodier.ai
- **Brand**: Embodier Trader — a profit-consciousness entity being
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC — this is the ONE repo for all code)
- **Legacy Repo**: github.com/Espenator/Embodier-Trader — forked HTML site + orphaned JS agents. TO BE ARCHIVED. Do NOT build here.
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development — v4.1.0-dev. Backend startup, WebSocket, and auth blockers resolved.
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. It operates as a conscious profit-seeking being with a Central Nervous System (CNS) architecture.
- **Current Focus**: Council runs 35-agent DAG; 34 API routes; 68+ services; 666 tests passing; Bearer auth fail-closed; WebSocket active (5 pages); desktop BUILD-READY.

## LATEST STATE (March 10, 2026) — v4.1.0-dev

### Current Architecture Snapshot
- **Council**: 35-agent DAG in 7 stages (11 Core + 12 Academic Edge P0–P4 + 6 Supplemental + 3 Debate + 3 others). CouncilGate invokes full council on every signal (score ≥ 65).
- **Backend**: 34 API route files in api/v1/; 68+ services (including llm_clients, data_sources, scanning, trading subdirs). brain_service exists and is wired (hypothesis_agent → gRPC).
- **Tests**: 666 passing (backend pytest). CI GREEN.
- **Auth**: Bearer token auth, fail-closed for live trading.
- **WebSocket**: Active; 5 pages wired (signals, orders, council, market data).
- **Desktop**: Electron app in `desktop/` — BUILD-READY (not in progress).
- **LLM Intelligence**: 3-tier router — Ollama (routine) → Perplexity → Claude. Claude reserved for 6 deep-reasoning tasks: strategy_critic, strategy_evolution, deep_postmortem, trade_thesis, overnight_analysis, directive_evolution.

### Resolved Blockers (no longer blocking)
- Backend startup (uvicorn) — resolved.
- WebSocket connectivity — resolved; bridges active.
- Auth for live trading — Bearer token, fail-closed.

### Historical: v3.2.0 (March 5, 2026) — Council-Controlled Pipeline
Council was expanded to 17 agents; CouncilGate bridged SignalEngine → Council → OrderExecutor. Pipeline is now 35-agent (see Council Architecture below).

## CRITICAL ARCHITECTURE AUDIT (March 4, 2026)

### The Problem: Five Disconnected Systems (PARTIALLY RESOLVED)
The codebase had five separate agent/decision systems. As of v3.2.0, Systems 2 and 4 are now connected via CouncilGate. The remaining fragmentation is documented below.

#### System 1: Agent Command Center (5 polling agents)
- **Location**: `backend/app/api/v1/agents.py`
- **What it is**: 5 hardcoded template agents (Market Data, Signal Generation, ML Learning, Sentiment, YouTube Knowledge) with start/stop/pause/restart controls
- **How it works**: Each agent is just an async function. Market Data Agent polls every 60s via a background task in main.py. The other 4 only run when manually triggered via POST API.
- **Problem**: These are NOT real agents. No daemon lifecycle, no health monitoring, no inter-agent communication.
- **Status**: UNRESOLVED — needs P6

#### System 2: Council (35-agent DAG) ← CONNECTED TO SYSTEM 4
- **Location**: `backend/app/council/` (runner.py, arbiter.py, schemas.py, council_gate.py, weight_learner.py, agents/)
- **What it is**: 35 council agents in a 7-stage DAG with deterministic arbiter + Bayesian weight learning (11 Core + 12 Academic Edge + 6 Supplemental + 3 Debate + 3 others)
- **How it works**: CouncilGate subscribes to signal.generated, auto-invokes run_council(), publishes council.verdict
- **Status**: CONNECTED to event pipeline via CouncilGate; all 35 agents wired in runner DAG

#### System 3: OpenClaw (copied Flask/Slack multi-agent system)
- **Location**: `backend/app/modules/openclaw/` (9 subdirectories)
- **What it is**: Entire separate trading system copy-pasted from archived openclaw repo.
- **Problem**: Mostly dead code. Need to extract useful pieces or delete.
- **Status**: UNRESOLVED — needs P4

#### System 4: Event-Driven Pipeline (real-time trading) ← NOW CONNECTED TO SYSTEM 2
- **Location**: `backend/app/core/message_bus.py`, `services/signal_engine.py`, `services/order_executor.py`
- **What it is**: MessageBus -> AlpacaStreamService -> EventDrivenSignalEngine -> CouncilGate -> OrderExecutor
- **How it works**: Starts automatically in main.py lifespan. OrderExecutor now listens to council.verdict (not raw signal.generated).
- **Status**: CONNECTED to Council via CouncilGate (v3.2.0)

#### System 5: CNS Architecture (DESIGNED, PARTIALLY BUILT)
- **What it is**: The VISION — BlackboardState, TaskSpawner, CircuitBreaker, Self-Awareness, Homeostasis
- **What's built**: Bayesian WeightLearner (P8), CouncilGate pipeline (P0)
- **What's remaining**: BlackboardState (P1), CircuitBreaker (P3), TaskSpawner (P5)

## ROADMAP: Unification into CNS Architecture

### COMPLETED
- [x] **P0**: Wire Council to Event Pipeline — CouncilGate bridges SignalEngine → Council → OrderExecutor
- [x] **P2**: Add Missing Feature Keys — EMA-5/10/20, intermarket, cycle, VIX, sector breadth
- [x] **P8**: Agent Self-Awareness — Bayesian WeightLearner with trade outcome learning
- [x] Fix stale docstrings in council files and status endpoint

### NEW PRIORITY: Continuous Discovery Architecture (Issue #38)
- [ ] **E1**: Streaming Discovery Engine — Alpaca `*` trade/news streams, dynamic universe
- [ ] **E2**: 12 Dedicated Scout Agents — all data sources active, always running
- [ ] **E3**: HyperSwarm Continuous Triage — priority queue, adaptive threshold
- [ ] **E4**: Multi-Tier Council — Fast (5 agents <200ms) + Deep (35 agents <2s)
- [ ] **E5**: Dynamic Universe — 500-2000 symbols, self-healing, sector-aware
- [ ] **E6**: Dual-Mode Agents — every analyst gets scout() background mode
- [ ] **E7**: Feedback-Driven Amplification — signal DNA, win registry, scout priming
- [ ] **E8**: Multi-Timeframe Scanning — 5min to weekly parallel scan loops

### REMAINING (Lower Priority — After Discovery Architecture)
- [ ] **P1**: Build BlackboardState — shared state across DAG stages, later stages read earlier conclusions
- [ ] **P3**: Build CircuitBreaker Reflexes (brainstem <50ms) — flash crash, VIX spike, drawdown limits
- [ ] **P4**: Clean Up OpenClaw — extract useful logic, delete dead Flask app
- [ ] **P5**: Build TaskSpawner — dynamic agent registry replacing hardcoded imports
- [ ] **P6**: Unify Agent Command Center — show real 35-agent council state
- [x] **P7**: Wire brain_service gRPC — connect Ollama to hypothesis_agent (DONE)

### BLOCKERS — ALL RESOLVED
- [x] **BLOCKER-1**: Start backend for first time (uvicorn app.main:app) — RESOLVED
- [x] **BLOCKER-2**: Establish WebSocket real-time data connectivity — RESOLVED (5 pages wired)
- [x] **BLOCKER-3**: Authentication for live trading — RESOLVED (Bearer token, fail-closed)

## Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn, LSTM (no PyTorch in prod) |
| Council | 35-agent DAG with Bayesian-weighted arbiter (7 stages) |
| Brain Service | gRPC + Ollama (PC2) for LLM inference |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| CI/CD | GitHub Actions (666 tests passing, backend pytest) |
| Infra | Docker, docker-compose.yml, Redis (where used) |
| Local AI | Ollama on RTX GPU cluster; 3-tier router (Ollama → Perplexity → Claude) |
| Auth | Bearer token, fail-closed for live trading |
| Desktop | Electron (desktop/) — BUILD-READY |

## Data Sources (CRITICAL - NO yfinance)

- Alpaca Markets (alpaca-py) — Market data + order execution
- Unusual Whales — Options flow + institutional activity
- FinViz (finviz) — Screener, fundamentals, VIX proxy
- FRED — Economic macro data
- SEC EDGAR — Company filings
- StockGeist / News API / Discord / X — Social sentiment (via council agents)
- YouTube — Transcript intelligence (via council agent)

## Council Architecture (35-Agent DAG, 7 Stages)
```
Stage 1 (Parallel): perception + Academic Edge P0/P1/P2 (13 agents)
Stage 2 (Parallel): technical + data enrichment (8 agents)
Stage 3 (Parallel): hypothesis + layered_memory_agent
Stage 4: strategy
Stage 5 (Parallel): risk, execution, portfolio_optimizer_agent
Stage 6: critic; Stage 7: arbiter (deterministic BUY/SELL/HOLD with Bayesian weights)
```

Agent Groups:
- **Core (8)**: market_perception, flow_perception, regime, hypothesis, strategy, risk, execution, critic
- **Data-Source Perception (3)**: social_perception (0.7), news_catalyst (0.6), youtube_knowledge (0.4)
- **Technical Analysis (5)**: rsi, bbv, ema_trend, intermarket, relative_strength, cycle_timing

Arbiter Rules:
1. VETO from risk or execution -> hold, vetoed=True
2. Requires regime + risk + strategy OK for any trade
3. Bayesian-weighted confidence aggregation for direction
4. Execution readiness requires confidence > 0.4 AND execution_ready=True

Agent Schema: `AgentVote(agent_name, direction, confidence, reasoning, veto, veto_reason, weight, metadata)`

## CNS Architecture (Central Nervous System)
- **Brainstem** (<50ms): CircuitBreaker reflexes [TO BUILD - P3]
- **Spinal Cord** (~1500ms): 35-agent council DAG [BUILT]
- **Cortex** (300-800ms): hypothesis + critic via brain_service gRPC [WIRED]
- **Thalamus**: BlackboardState shared memory [TO BUILD - P1]
- **Autonomic**: Bayesian WeightLearner [BUILT - P8] — learns from trade outcomes
- **PNS Sensory**: Alpaca WS, Unusual Whales, FinViz, FRED, EDGAR [BUILT — transitioning to streaming]
- **Discovery Layer**: StreamingDiscoveryEngine + 12 Scout Agents + Dynamic Universe [PLANNED — Issue #38]
- **PNS Motor**: OrderExecutor -> Alpaca Orders (via council.verdict) [BUILT]
- **Event Bus**: MessageBus pub/sub [BUILT]
- **Council Gate**: SignalEngine → Council → OrderExecutor bridge [BUILT - P0]

## Event-Driven Pipeline (BUILT — v3.2.0)
```
AlpacaStreamService
  -> market_data.bar
  -> EventDrivenSignalEngine
  -> signal.generated (score >= 65)
  -> CouncilGate (invokes 35-agent council)
  -> council.verdict (BUY/SELL/HOLD)
  -> OrderExecutor (real DuckDB stats, real ATR, mock-source guard)
  -> order.submitted
  -> WebSocket bridges
  -> Frontend
```

## Architecture

```
[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
14 pages, 34 API route files, WebSocket active (5 pages), Bearer auth fail-closed
35-Agent Council DAG, ML Engine (XGBoost), DuckDB Analytics, Redis where used
[Brain Service gRPC] <-- Ollama LLM inference on PC2; 3-tier router (Ollama → Perplexity → Claude)
[Electron Desktop — desktop/] BUILD-READY, spawns backend + serves frontend
```

## Key Code Patterns

1. Frontend: useApi('endpoint') hook, no mock data
2. Python: 4-space indentation, never tabs
3. Council agents: pure async functions with NAME, WEIGHT, evaluate() -> AgentVote
4. Features: `f = features.get("features", features)` then `f.get("key", default)`
5. API: Route handler -> Service layer -> External API
6. Council Gate: signal.generated -> CouncilGate -> run_council() -> council.verdict -> OrderExecutor
7. Weight Learning: WeightLearner.update(agent, won) adjusts Bayesian alpha/beta -> arbiter uses learned weights

## Current State (March 10, 2026 — v4.1.0-dev)
- CI: 666 tests passing (backend pytest), GREEN
- Version: 4.1.0-dev. Backend startup, WebSocket, and auth blockers resolved.
- Frontend: 14 pages, all pixel-matched to mockups, wired to real API hooks
- Backend: 34 API routes (brain, triage, ingestion firehose, awareness, etc. mounted), 68+ service files (incl. subdirs)
- Council: 35-agent DAG + arbiter + runner + CouncilGate + WeightLearner; brain_service wired to hypothesis_agent
- LLM: 3-tier router (Ollama → Perplexity → Claude); Claude for 6 deep-reasoning tasks only
- Auth: Bearer token, fail-closed for live trading
- WebSocket: Active; 5 pages wired (signals, orders, council, market data)
- Desktop: `desktop/` — BUILD-READY (Electron)
- Discovery: TurboScanner + HyperSwarm + AutonomousScout + UW agents — polling; streaming planned (Issue #38)
- Knowledge: MemoryBank + HeuristicEngine + KnowledgeGraph (wired to outcome tracker)
- Event Pipeline: MessageBus + CouncilGate + SignalEngine + OrderExecutor running
- Kelly Sizing: Real DuckDB stats (no hardcoded values); Mock Guard: OrderExecutor rejects mock-source trades

## UI MOCKUP FIDELITY AUDIT (Mar 6, 2026)

> **Full report**: `docs/MOCKUP-FIDELITY-AUDIT.md`
> **Source of truth**: 23 mockup images in `docs/mockups-v3/images/`

A comprehensive pixel-by-pixel audit was performed comparing all 23 mockup images against all 14 frontend page files. Below is the status of each page.

### Page Fidelity Status

| Page | Mockup(s) | Route | File | Match | Effort |
|------|-----------|-------|------|-------|--------|
| Dashboard | `02-intelligence-dashboard.png` | `/dashboard` | `Dashboard.jsx` | 🟢 GOOD | Polish only |
| ACC Swarm Overview | `01-agent-command-center-final.png` | `/agents` tab 1 | `AgentCommandCenter.jsx` | 🔴 MAJOR GAP | 8-12h rewrite |
| ACC Agent Registry | `05c-agent-registry.png` | `/agents` tab 2 | `AgentCommandCenter.jsx` | 🟡 PARTIAL | 3-4h fixes |
| ACC Spawn & Scale | `05b-agent-command-center-spawn.png` | `/agents` tab 3 | `AgentCommandCenter.jsx` | 🟢 GOOD | Polish only |
| ACC Live Wiring | `05-agent-command-center.png` | `/agents` tab 4 | `AgentCommandCenter.jsx` | 🟡 PARTIAL | 2-3h fixes |
| ACC Blackboard | `realtimeblackbard fead.png` | `/agents` tab 5 | `AgentCommandCenter.jsx` | 🟡 PARTIAL | 2h fixes |
| ACC Brain Map | `agent command center brain map.png` | `/agents` tab 9 | `AgentCommandCenter.jsx` | 🟡 PARTIAL | 2-3h fixes |
| ACC Node Control | `agent command center node control.png` | `/agents` tab 10 | `AgentCommandCenter.jsx` | 🟡 PARTIAL | 4-6h missing panels |
| Signal Intelligence | `03-signal-intelligence.png` | `/signal-intelligence-v3` | `SignalIntelligenceV3.jsx` | 🟢 GOOD | Polish only |
| Sentiment | `04-sentiment-intelligence.png` | `/sentiment` | `SentimentIntelligence.jsx` | 🟡 PARTIAL | 2-3h fixes |
| ML Brain & Flywheel | `06-ml-brain-flywheel.png` | `/ml-brain` | `MLBrainFlywheel.jsx` | 🟢 GOOD | Polish only |
| Screener & Patterns | `07-screener-and-patterns.png` | `/patterns` | `Patterns.jsx` | 🟢 GOOD | Polish only |
| Backtesting Lab | `08-backtesting-lab.png` | `/backtest` | `Backtesting.jsx` | 🟢 GOOD | Polish only |
| Data Sources | `09-data-sources-manager.png` | `/data-sources` | `DataSourcesMonitor.jsx` | 🟢 CLOSE | Verified DONE |
| Market Regime | `10-market-regime-green/red.png` | `/market-regime` | `MarketRegime.jsx` | 🟢 CLOSE | Verified DONE |
| Performance Analytics | `11-performance-analytics-fullpage.png` | `/performance` | `PerformanceAnalytics.jsx` | 🟡 PARTIAL | 3-4h fixes |
| Trade Execution | `12-trade-execution.png` | `/trade-execution` | `TradeExecution.jsx` | 🟡 PARTIAL | 2-3h fixes |
| Risk Intelligence | `13-risk-intelligence.png` | `/risk` | `RiskIntelligence.jsx` | 🟡 PARTIAL | 2-3h fixes |
| Settings | `14-settings.png` | `/settings` | `Settings.jsx` | 🟢 GOOD | Polish only |
| Active Trades | `Active-Trades.png` | `/trades` | `Trades.jsx` | 🟢 CLOSE | Verified DONE |
| Cognitive Telemetry | ❌ NO MOCKUP | `/cognitive-dashboard` | `CognitiveDashboard.jsx` | ❓ No target | Needs mockup |
| Swarm Intelligence | ⚠️ DUPLICATE of ACC | `/swarm-intelligence` | `SwarmIntelligence.jsx` | 🔴 CONFLICT | Merge or delete |

### Priority Fix Queue

**P0 (Critical — structure wrong):**
1. ACC Swarm Overview: mockup shows 12+ dense panels, code has simple card grid → full restructure
2. ACC Node Control: missing HITL detail table, Override History, Analytics charts
3. Footer consistency: some pages have footers, some don't. Design system requires footer on ALL pages
4. SwarmIntelligence.jsx: duplicates ACC at separate route → decision needed: merge or delete

**P1 (Medium — missing panels/components):**
5. ACC sub-tabs and missing panels across multiple tabs
6. Sentiment: heatmap density, scanner matrix dots, emergency alerts
7. Performance Analytics: Trading Grade badge position, Returns Heatmap
8. Card `border-radius` standardization (`rounded-md` per design system vs `rounded-xl` in code)
9. Card header styling (ALL CAPS text-xs slate-400 per design system)
10. JetBrains Mono font loading

**P2 (Minor — cosmetic polish):**
11. All pages: font sizes, bar proportions, chart colors, slider styling

**Total estimated effort: 33-47 hours**

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use useApi() hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. Council agents MUST return AgentVote schema
6. The ONE repo is Espenator/elite-trading-system — do NOT commit to Embodier-Trader
7. Council has 35 agents in 7 stages — see Council Architecture section
8. Read CRITICAL ARCHITECTURE AUDIT section before making changes
9. Agent pattern: module-level NAME + WEIGHT + async def evaluate() -> AgentVote
10. VETO_AGENTS = {"risk", "execution"} — only these can veto
11. REQUIRED_AGENTS = {"regime", "risk", "strategy"} — must vote non-hold for trade
12. New agents should NOT have veto power
13. CouncilGate is the bridge — signals go through council before OrderExecutor
14. Discovery must be CONTINUOUS, not periodic — new scouts use streaming/event patterns (Issue #38)
15. All discovery agents publish to MessageBus `swarm.idea` topic
16. The council brain can handle 40+ signals/sec — feed it continuously, not in bursts

- Layer 1: Pattern Discovery Engine — mines historical data, stores in DuckDB
- Layer 2: Strategy Evolution — Mind Evolution search, 4 strategy islands
- Layer 3: Memory — PatternMemory, StrategyMemory, SourceMemory feed Bayesian weights
- Loop: Pattern Discovery -> Strategy Evolution -> Council -> Postmortem -> WeightLearner.update() -> (repeat)
