# Project State - Embodier Trader (Embodier.ai)

> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 4, 2026

## Identity

- **Project**: Embodier Trader by Embodier.ai
- **Brand**: Embodier Trader — a profit-consciousness entity being
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC — this is the ONE repo for all code)
- **Legacy Repo**: github.com/Espenator/Embodier-Trader — forked HTML site + orphaned JS agents. TO BE ARCHIVED. Do NOT build here.
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, Phase 1 implementation
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. It operates as a conscious profit-seeking being with a Central Nervous System (CNS) architecture.

## Hardware (Dual-PC Setup)

- **ESPENMAIN** (PC 1, Primary): Development + Frontend + Backend API
- **Profit Trader** (PC 2, Secondary): RTX GPU cluster for ML training + Ollama inference (brain_service)
- Connected via gRPC (brain_service port 50051)
- **Desktop App**: Electron wrapper with installer (Windows .exe, macOS .dmg, Linux AppImage)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Desktop | Electron 29, electron-builder, PyInstaller |
| Database | DuckDB (WAL mode), SQLite (config/orders) |
| ML | XGBoost, scikit-learn (no PyTorch in prod) |
| Council | 17-agent DAG with deterministic arbiter (7 stages) |
| Brain Service | gRPC + Ollama (PC2) for LLM inference |
| Event Pipeline | MessageBus, Alpaca WebSocket, SignalEngine, OrderExecutor |
| CI/CD | GitHub Actions (316 tests passing) |
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

## Council Architecture (17-Agent DAG, 7 Stages)

```
Stage 1 (Parallel, 7): market_perception, flow_perception, regime, social_perception, news_catalyst, youtube_knowledge, intermarket
Stage 2 (Parallel, 5): rsi, bbv, ema_trend, relative_strength, cycle_timing
Stage 3: hypothesis (wired to brain_service LLM, reads blackboard)
Stage 4: strategy (entry/exit/sizing, confidence modulated by social+news consensus)
Stage 5 (Parallel): risk, execution
Stage 6: critic (postmortem learning)
Stage 7: arbiter (deterministic BUY/SELL/HOLD)
```

Agent Groups:
- **Core (8)**: market_perception, flow_perception, regime, hypothesis, strategy, risk, execution, critic
- **Data-Source Perception (3)**: social_perception (0.7), news_catalyst (0.6), youtube_knowledge (0.4)
- **Technical Analysis (5)**: rsi, bbv, ema_trend, intermarket, relative_strength, cycle_timing

Arbiter Rules:
1. VETO from risk or execution -> hold, vetoed=True
2. Requires regime + risk + strategy OK for any trade
3. Weighted confidence aggregation for direction
4. Execution readiness requires confidence > 0.4 AND execution_ready=True

Agent Schema: `AgentVote(agent_name, direction, confidence, reasoning, veto, veto_reason, weight, metadata)`

## CNS Architecture (Central Nervous System)

The agent swarm IS the nervous system of Embodier Trader:

- **Brainstem** (always on, <50ms): CircuitBreaker reflexes (flash crash, VIX spike, drawdown, position limits) ✅ BUILT
- **Spinal Cord** (~1500ms): 17-agent council DAG via TaskSpawner ✅ BUILT
- **Cortex** (300-800ms): hypothesis + critic via brain_service gRPC ✅ WIRED
- **Thalamus**: BlackboardState shared memory — all agents read/write ✅ BUILT
- **Autonomic**: BayesianAgentWeights, StreakDetector, AgentHealthMonitor ✅ BUILT
- **Homeostasis**: System vital signs monitoring + mode switching (NORMAL/CAUTIOUS/DEFENSIVE/HALTED) ✅ BUILT
- **PNS Sensory**: Alpaca WS, Unusual Whales, FinViz, News APIs, FRED, EDGAR ✅ BUILT
- **PNS Motor**: OrderExecutor -> Alpaca Orders (SHADOW mode) ✅ BUILT
- **Event Bus**: MessageBus pub/sub ✅ BUILT
- **HITL Gate**: Human-in-the-loop approval for high-risk trades ✅ BUILT
- **Feedback Loop**: Outcome resolution + agent weight learning ✅ BUILT
- **Intelligence**: Multi-tier LLM (Perplexity cortex + Ollama brainstem + Claude deep cortex) ✅ BUILT

Swarm Invariants:
1. No trade without council_decision_id
2. No data flows without agent validation
3. No UI state changes without agent approval
4. Council decisions expire after 30 seconds

## Event-Driven Pipeline

```
AlpacaStreamService -> market_data.bar -> EventDrivenSignalEngine
-> signal.generated (score >= 65) -> OrderExecutor -> order.submitted
-> WebSocket bridges -> Frontend
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
6. Mockups: docs/mockups-v3/images/ are the source of truth
7. Desktop: window.embodier API for Electron integration

## Current State (Mar 4, 2026)

- CI: 316 tests passing
- Frontend: 15 pages built (React 18 + Vite), all wired to real API hooks
- Backend: 31 API route files, v3.1.0, starts cleanly with uvicorn
- Council: 17 agents + arbiter + runner (8 core + 3 data-source + 5 technical)
- Brain Service: gRPC server + Ollama client connected to hypothesis + critic agents
- ML: XGBoost trainer + feature pipeline operational, drift detection active
- WebSocket: Connected end-to-end (heartbeat, channels, signal/order/council/risk bridges)
- Event Pipeline: MessageBus -> SignalEngine -> OrderExecutor (SHADOW mode)
- CORS: Restricted to localhost:3000, localhost:5173
- Intelligence: Multi-tier LLM (Perplexity cortex + Ollama brainstem + Claude deep cortex)
- Data Sources: StockGeist, News API, Discord, X/Twitter, YouTube all wired through council spawner
- Desktop: Electron wrapper with splash screen, setup wizard, system tray

## Completed Milestones

- [x] P1.1: CI build fixed — 316 tests passing
- [x] P1.2: Feature aggregator with Alpaca bars
- [x] P1.3: Brain service gRPC connected to hypothesis + critic agents
- [x] P1.4: Trade execution via Alpaca service + order executor
- [x] P1.5: /api/v1/council/evaluate endpoint working
- [x] P1.6: WebSocket wired for council verdicts, signals, orders, risk
- [x] P1.7: Adaptive threshold config via agent_config.py + settings service
- [x] P1.8: Postmortem table in DuckDB with critic agent writing
- [x] P1.9: BlackboardState replaces raw features dict
- [x] P1.10: TaskSpawner dynamic agent creation (17 agents registered)
- [x] P1.11: Circuit breaker brainstem reflexes
- [x] P1.12: Self-awareness (Bayesian weights, streak detection)
- [x] P1.13: Homeostasis system vital signs + mode switching
- [x] P1.14: HITL gate for human approval
- [x] P1.15: Shadow tracker for paper vs live comparison
- [x] P1.16: Data-source perception agents (social, news, youtube) through council spawner
- [x] P1.17: Intelligence orchestrator with multi-tier LLM package
- [x] P1.18: Intelligence cache with background pre-fetch
- [x] P1.19: 5 technical analysis agents (RSI, BBV, EMA, Intermarket, RelStrength, CycleTiming)
- [x] P1.20: Electron desktop app with installer support

## Feature Gap: New Agents Need Feature Data

- ema_trend_agent expects `ind_ema_5/10/20` (aggregator only has ema_9, ema_21)
- intermarket_agent expects `spy_uvxy_correlation`, `vix_current`, `sector_breadth`
- relative_strength_agent expects `peer_percentile_20d`, `excess_return_20d`
- cycle_timing_agent expects `cycle_phase`, `cycle_phase_confidence`
- All default to hold/0.0 until feature_aggregator.py is updated

## Known Limitations

1. Alpaca API keys required for live market data (MOCK mode without)
2. Finviz API key required for stock screener
3. Brain service (PC2 Ollama) optional — graceful degradation to rule-based
4. Social data sources (StockGeist, Discord, X) require individual API keys
5. 5 new technical agents need feature_aggregator updates for real data

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use useApi() hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups before building UI
6. Run npm run build before committing frontend changes
7. Run python -m pytest before committing backend changes
8. Council agents MUST return AgentVote schema
9. Council has 17 agents in 7 stages — NOT 8 or 11 or 13
10. The ONE repo is Espenator/elite-trading-system — do NOT commit to Embodier-Trader
11. Agent pattern: module-level NAME + WEIGHT + async def evaluate() -> AgentVote
12. All new features must support the Embodier profit-being philosophy

## Architecture Files (All Created)

| File | Purpose | Status |
|------|---------|--------|
| council/blackboard.py | BlackboardState dataclass replacing raw features dict | ✅ DONE |
| council/task_spawner.py | Dynamic agent spawning with model_tier + background support | ✅ DONE |
| council/self_awareness.py | AgentHealthMonitor, StreakDetector, BayesianAgentWeights | ✅ DONE |
| council/reflexes/circuit_breaker.py | Pre-council brainstem reflexes (flash crash, VIX spike) | ✅ DONE |
| council/homeostasis.py | System vital signs monitoring + mode switching | ✅ DONE |
| council/hitl_gate.py | Human-in-the-loop approval gate | ✅ DONE |
| council/feedback_loop.py | Outcome resolution + agent weight learning | ✅ DONE |
| council/agents/social_perception_agent.py | Social sentiment via council spawner | ✅ DONE |
| council/agents/news_catalyst_agent.py | News catalyst detection via council spawner | ✅ DONE |
| council/agents/youtube_knowledge_agent.py | YouTube transcript intelligence via council spawner | ✅ DONE |
| council/agents/rsi_agent.py | Multi-timeframe RSI with divergence detection | ✅ DONE |
| council/agents/bbv_agent.py | Bollinger Band mean-reversion + squeeze detection | ✅ DONE |
| council/agents/ema_trend_agent.py | EMA cascade patterns (UT/SU/GU/DT/SD/GD) | ✅ DONE |
| council/agents/intermarket_agent.py | SPY-UVXY/IEF/IWM correlations, VIX, sector breadth | ✅ DONE |
| council/agents/relative_strength_agent.py | Peer ranking, excess returns, momentum | ✅ DONE |
| council/agents/cycle_timing_agent.py | Seasonality, DOW effect, cycle phase detection | ✅ DONE |
| desktop/main.js | Electron desktop app with splash + setup wizard | ✅ DONE |
| directives/global.md | Always-on trading rules loaded by agents at runtime | ✅ DONE |
| directives/regime_bull.md | Bull market agent behavior overrides | ✅ DONE |
| directives/regime_bear.md | Bear market defensive behaviors | ✅ DONE |

## Recursive Self-Improvement Architecture (Phase 3 - Future)

- Layer 1: Pattern Discovery Engine — mines historical data, stores in DuckDB
- Layer 2: Strategy Evolution — Mind Evolution search, 4 strategy islands
- Layer 3: Memory — PatternMemory, StrategyMemory, SourceMemory feed Bayesian weights
- Loop: Pattern Discovery -> Strategy Evolution -> Council -> Postmortem -> (repeat)
