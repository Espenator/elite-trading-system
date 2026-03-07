# Project State - Embodier Trader (Embodier.ai)
> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 5, 2026

## Identity
- **Project**: Embodier Trader by Embodier.ai
- **Brand**: Embodier Trader — a profit-consciousness entity being
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC — this is the ONE repo for all code)
- **Legacy Repo**: github.com/Espenator/Embodier-Trader — forked HTML site + orphaned JS agents. TO BE ARCHIVED. Do NOT build here.
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, Phase 2 — v3.5.0-dev (Continuous Discovery Architecture)
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. It operates as a conscious profit-seeking being with a Central Nervous System (CNS) architecture.
- **Current Focus**: Multi-PC compute infrastructure (Issue #39) + continuous real-time discovery firehose (Issue #38)

## LATEST CHANGES (March 7, 2026) — v3.5.0-dev

### Architecture Pivot: Continuous Discovery (Issue #38)
Full codebase audit revealed the system is 73% analyst, 27% scout. The 17-agent council brain is starved of ideas. HyperSwarm processes 40 signals/sec but is fed bursts every 60s. All discovery is polling-based (60-900s intervals). No streaming discovery exists.

**Decision**: Invert the ratio. Build continuous discovery firehose. First: compute infrastructure (Issue #39), then: discovery enhancements (Issue #38).

**Issue #39 — Multi-PC Compute Architecture (prerequisite)**:
- E0.1-E0.8: AlpacaKeyPool (3 keys, 3 WebSocket streams, 1000+ symbols), OllamaNodePool (shared across services), NodeDiscovery (auto-detect PC2), AlpacaStreamManager (multi-stream orchestrator), Brain Service enablement, UW/Finviz optimization

**Issue #38 — Continuous Discovery (8-enhancement plan)**:
1. **E1**: Streaming Discovery Engine (Alpaca `*` trade stream + news stream)
2. **E2**: 12 Dedicated Scout Agents (always-running, all data sources active)
3. **E3**: HyperSwarm Continuous Triage (priority queue, adaptive threshold)
4. **E4**: Multi-Tier Council (Fast 5-agent <200ms + Deep 17-agent <2s)
5. **E5**: Dynamic Universe (500-2000 symbols, self-healing)
6. **E6**: Dual-Mode Agents (every analyst gets background scout mode)
7. **E7**: Feedback-Driven Signal Amplification (scouts learn from outcomes)
8. **E8**: Multi-Timeframe Scanning (5min/15min/1hr/daily/weekly)

**Also completed**: Integration sprint — wired knowledge layer (MemoryBank, HeuristicEngine, KnowledgeGraph) into startup + feedback loop.

### Previous: v3.4.0 (March 6, 2026) — ALL 14 Frontend Pages Complete
Every frontend page matches its mockup. ACC rebuilt into 5 files with 8 tabs. 20 orphaned files cleaned up.

## Previous: v3.2.0 (March 5, 2026)

### Council-Controlled Intelligence (10 commits, CI Run #452 GREEN)
The entire trade pipeline is now council-controlled. No signal reaches the order executor without passing through the 13-agent council.

**New Pipeline:**
```
AlpacaStream → SignalEngine → CouncilGate (score >= 65) → 13-Agent Council → OrderExecutor → Alpaca
```

**New Files Created:**
1. `council/council_gate.py` — CouncilGate class: bridges SignalEngine → Council → OrderExecutor. Intercepts all signals with score >= 65 and invokes the full 13-agent council before any trade.
2. `council/weight_learner.py` — WeightLearner class: Bayesian self-learning agent weights. Updates alpha/beta from trade outcomes. Agents that vote correctly get higher weight over time.
3. `services/trade_stats_service.py` — TradeStatsService class: Queries real win_rate, avg_win, avg_loss from DuckDB trade history. Replaces all hardcoded Kelly parameters.

**Files Updated:**
4. `council/schemas.py` — Docstring corrected: 8-agent → 13-agent
5. `api/v1/council.py` — 13 agents, 7 stages, added /weights endpoint + council_status endpoint
6. `services/order_executor.py` — Now listens to `council.verdict` instead of raw `signal.generated`. Uses real DuckDB stats for Kelly sizing. Uses real ATR from features. Mock-source guard prevents trading on fake data.
7. `main.py` — CouncilGate wired into pipeline startup. Version 3.2.0. Title "Embodier Trader".
8. `features/feature_aggregator.py` — Expanded with intermarket, cycle, and extended indicator features (EMA-5/10/20, VIX, SPY correlation, sector breadth, cycle phases) for all 13 agents.
9. `council/arbiter.py` — Uses Bayesian learned weights from WeightLearner instead of static weights.
10. `tests/test_api.py` — Updated assertions for version 3.2.0, Embodier Trader title.

### What Was Completed:
- [x] **P0**: Wire council to event pipeline — CouncilGate subscribes to signal.generated, auto-invokes run_council()
- [x] **P2**: Add missing feature keys — EMA-5/10/20, intermarket, relative strength, cycle timing, VIX all added
- [x] **P8**: Build agent self-awareness — Bayesian WeightLearner with alpha/beta tracking
- [x] Fix stale docstrings — schemas.py, council.py API, arbiter.py all updated
- [x] Remove hardcoded/mock data — OrderExecutor uses real DuckDB stats, real ATR, mock-source guard
- [x] Council controls all trading — No signal bypasses the 13-agent council

## CRITICAL ARCHITECTURE AUDIT (March 4, 2026)

### The Problem: Five Disconnected Systems (PARTIALLY RESOLVED)
The codebase had five separate agent/decision systems. As of v3.2.0, Systems 2 and 4 are now connected via CouncilGate. The remaining fragmentation is documented below.

#### System 1: Agent Command Center (5 polling agents)
- **Location**: `backend/app/api/v1/agents.py`
- **What it is**: 5 hardcoded template agents (Market Data, Signal Generation, ML Learning, Sentiment, YouTube Knowledge) with start/stop/pause/restart controls
- **How it works**: Each agent is just an async function. Market Data Agent polls every 60s via a background task in main.py. The other 4 only run when manually triggered via POST API.
- **Problem**: These are NOT real agents. No daemon lifecycle, no health monitoring, no inter-agent communication.
- **Status**: UNRESOLVED — needs P6

#### System 2: Council (13-agent DAG) ← NOW CONNECTED TO SYSTEM 4
- **Location**: `backend/app/council/` (runner.py, arbiter.py, schemas.py, council_gate.py, weight_learner.py, agents/)
- **What it is**: 13 council agents in a 7-stage DAG with deterministic arbiter + Bayesian weight learning
- **Agents**: market_perception, flow_perception, regime, intermarket, rsi, bbv, ema_trend, relative_strength, cycle_timing, hypothesis, strategy, risk, execution, critic (+ arbiter)
- **How it works**: CouncilGate subscribes to signal.generated, auto-invokes run_council(), publishes council.verdict
- **Status**: CONNECTED to event pipeline via CouncilGate (v3.2.0)

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
- [ ] **E4**: Multi-Tier Council — Fast (5 agents <200ms) + Deep (17 agents <2s)
- [ ] **E5**: Dynamic Universe — 500-2000 symbols, self-healing, sector-aware
- [ ] **E6**: Dual-Mode Agents — every analyst gets scout() background mode
- [ ] **E7**: Feedback-Driven Amplification — signal DNA, win registry, scout priming
- [ ] **E8**: Multi-Timeframe Scanning — 5min to weekly parallel scan loops

### REMAINING (Lower Priority — After Discovery Architecture)
- [ ] **P1**: Build BlackboardState — shared state across DAG stages, later stages read earlier conclusions
- [ ] **P3**: Build CircuitBreaker Reflexes (brainstem <50ms) — flash crash, VIX spike, drawdown limits
- [ ] **P4**: Clean Up OpenClaw — extract useful logic, delete dead Flask app
- [ ] **P5**: Build TaskSpawner — dynamic agent registry replacing hardcoded imports
- [ ] **P6**: Unify Agent Command Center — show real 13-agent council state
- [ ] **P7**: Wire brain_service gRPC — connect Ollama to hypothesis_agent and critic_agent

### BLOCKERS
- [ ] **BLOCKER-1**: Start backend for first time (uvicorn app.main:app)
- [ ] **BLOCKER-2**: Establish WebSocket real-time data connectivity
- [ ] **BLOCKER-3**: Add JWT authentication for live trading endpoints

## Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn, LSTM (no PyTorch in prod) |
| Council | 13-agent DAG with Bayesian-weighted arbiter (7 stages) |
| Brain Service | gRPC + Ollama (PC2) for LLM inference |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| CI/CD | GitHub Actions (151 tests passing) |
| Infra | Docker, docker-compose.yml |
| Local AI | Ollama on RTX GPU cluster |

## Data Sources (CRITICAL - NO yfinance)

- Alpaca Markets (alpaca-py) — Market data + order execution
- Unusual Whales — Options flow + institutional activity
- FinViz (finviz) — Screener, fundamentals, VIX proxy
- FRED — Economic macro data
- SEC EDGAR — Company filings
- StockGeist / News API / Discord / X — Social sentiment (via council agents)
- YouTube — Transcript intelligence (via council agent)

## Council Architecture (13-Agent DAG, 7 Stages)
```
Stage 1 (Parallel, 7): market_perception, flow_perception, regime, social_perception, news_catalyst, youtube_knowledge, intermarket
Stage 2 (Parallel, 5): rsi, bbv, ema_trend, relative_strength, cycle_timing
Stage 3: hypothesis (wired to brain_service LLM, reads blackboard)
Stage 4: strategy (entry/exit/sizing, confidence modulated by social+news consensus)
Stage 5 (Parallel): risk, execution
Stage 6: critic (postmortem learning)
Stage 7: arbiter (deterministic BUY/SELL/HOLD with Bayesian weights)
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
- **Spinal Cord** (~1500ms): 13-agent council DAG [BUILT]
- **Cortex** (300-800ms): hypothesis + critic via brain_service gRPC [NOT WIRED - P7]
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
  -> CouncilGate (invokes 13-agent council)
  -> council.verdict (BUY/SELL/HOLD)
  -> OrderExecutor (real DuckDB stats, real ATR, mock-source guard)
  -> order.submitted
  -> WebSocket bridges
  -> Frontend
```

## Architecture

```
[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
15 pages, 31 API route files, WebSocket via websocket_manager.py
17-Agent Council DAG, ML Engine (XGBoost), DuckDB Analytics
[Brain Service gRPC] <-- Ollama LLM inference on PC2
[Electron Desktop Shell] -- spawns backend + serves frontend
```

## Key Code Patterns

1. Frontend: useApi('endpoint') hook, no mock data
2. Python: 4-space indentation, never tabs
3. Council agents: pure async functions with NAME, WEIGHT, evaluate() -> AgentVote
4. Features: `f = features.get("features", features)` then `f.get("key", default)`
5. API: Route handler -> Service layer -> External API
6. Council Gate: signal.generated -> CouncilGate -> run_council() -> council.verdict -> OrderExecutor
7. Weight Learning: WeightLearner.update(agent, won) adjusts Bayesian alpha/beta -> arbiter uses learned weights

## Current State (Mar 7, 2026 — v3.5.0-dev)
- CI: 151 tests passing (Run #452 GREEN)
- Version: 3.5.0-dev (Continuous Discovery Architecture in progress)
- Frontend: 14 pages, all pixel-matched to mockups, wired to real API hooks
- Backend: 29 API routes, 24+ service files, knowledge layer wired
- Council: 17 agents + arbiter + runner + CouncilGate + WeightLearner (fully connected)
- Discovery: TurboScanner (10 screens) + HyperSwarm (50 workers) + AutonomousScout (4 scouts) + 6 UW agents — ALL POLLING, transitioning to streaming (Issue #38)
- Knowledge: MemoryBank + HeuristicEngine + KnowledgeGraph (wired to outcome tracker)
- Brain Service: gRPC + Ollama ready (not yet connected to council)
- Event Pipeline: MessageBus + CouncilGate + SignalEngine + OrderExecutor running
- Kelly Sizing: Real DuckDB stats (no hardcoded values)
- Mock Guard: OrderExecutor rejects trades from mock data sources
- **Next milestone**: E1 + E2 (streaming discovery + 12 scout agents)

## UI MOCKUP FIDELITY AUDIT (Mar 6, 2026)

> **Full report**: `docs/MOCKUP-FIDELITY-AUDIT.md`
> **Source of truth**: 23 mockup images in `docs/mockups-v3/images/`

A comprehensive pixel-by-pixel audit was performed comparing all 23 mockup images against all 17 frontend page files. Below is the status of each page.

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
7. Council has 13 agents in 7 stages — NOT 8 agents in 6 stages
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
