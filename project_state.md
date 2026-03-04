# Project State - Embodier Trader (Embodier.ai)

> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 4, 2026

## Identity

- **Project**: Embodier Trader by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (private)
- **Owner**: Espenator (Asheville, NC)
- **Status**: Active development, Phase 1 implementation
- **Philosophy**: Embodied Intelligence - the system IS profit, not seeking it

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn, LSTM (no PyTorch in prod) |
| Agents | 8-agent council DAG with deterministic arbiter |
| Brain Service | gRPC + Ollama (PC2) for LLM inference |
| CI/CD | GitHub Actions (70 tests passing) |
| Infra | Docker, docker-compose.yml |
| Local AI | Ollama on RTX GPU cluster |

## Hardware (Dual-PC Setup)

- PC 1: Development + Frontend + Backend API
- PC 2: RTX GPU cluster for ML training + Ollama inference (brain_service)
- Both PCs connected via gRPC (brain_service port 50051)

## Data Sources (CRITICAL - NO yfinance)

- Alpaca Markets (alpaca-py) - Market data + order execution
- Unusual Whales - Options flow + institutional activity
- FinViz (finviz) - Screener, fundamentals, VIX proxy
- FRED - Economic macro data
- SEC EDGAR - Company filings

## Council Architecture (8-Agent DAG)

```
Stage 1 (Parallel): market_perception, flow_perception, regime
Stage 2: hypothesis (wired to brain_service LLM)
Stage 3: strategy (entry/exit/sizing)
Stage 4 (Parallel): risk, execution
Stage 5: critic (postmortem learning)
Stage 6: arbiter (deterministic BUY/SELL/HOLD)
```

Arbiter Rules:
1. VETO from risk_agent or execution_agent -> hold, vetoed=True
2. Requires: regime OK + risk OK + strategy OK for any trade
3. Weighted confidence aggregation for direction
4. Final confidence = weighted average of non-vetoing agents

## CNS Architecture (Central Nervous System)

The agent swarm IS the nervous system of Embodier Trader:

- **Brainstem** (always on, <50ms): risk_governor, execution_engine health, regime_agent, symbol_universe, CircuitBreaker reflexes
- **Cortex** (LLM-powered, 300-800ms): hypothesis_agent + critic_agent via brain_service gRPC
- **Spinal Cord** (council DAG, ~1500ms): S1 parallel perception -> S2 hypothesis -> S3 strategy -> S4 parallel risk/execution -> S5 critic -> S6 arbiter
- **Autonomic**: Bayesian weight updates, overnight learning, threshold adaptation, AgentHealthMonitor
- **PNS Sensory**: Alpaca WS, Unusual Whales, FinViz, News APIs, FRED, EDGAR
- **PNS Motor**: execution_agent -> Alpaca Orders, short_basket_compiler
- **Blackboard** (thalamus): shared state all agents read/write, single source of truth

Swarm Invariants:
1. No trade without council_decision_id
2. No data flows without agent validation
3. No UI state changes without agent approval
4. Council decisions expire after 30 seconds

Migration Roadmap:
- Phase 1: BlackboardState replaces raw features dict
- Phase 2: brain_service gRPC -> hypothesis + critic agents
- Phase 3: Port OpenClaw Flask/Slack agents to FastAPI tools
- Phase 4: Bayesian weights + DuckDB trade outcomes + threshold adaptation
- Phase 5: LangGraph wrapper for tracing/checkpointing
- Phase 6: Async parallel stages, LLM caching, feature pre-compute

## Architecture

```
[React Frontend] --useApi()--> [FastAPI Backend] --services--> [External APIs]
15 pages, 25 API routes, WebSocket via websocket_manager.py
8-Agent Council DAG, ML Engine (XGBoost), DuckDB Analytics
[Brain Service gRPC] <-- Ollama LLM inference on PC2
```

## Key Code Patterns

1. Frontend data: Always use useApi('endpoint') hook
2. No mock data: All components wire to real /api/v1/* endpoints
3. Python style: 4-space indentation, never tabs
4. JSX unicode: BMP only
5. API pattern: Route handler -> Service layer -> External API
6. Mockups: docs/mockups-v3/images/ are the source of truth
7. Council: All agents return AgentVote(agent_name, direction, confidence, reasoning, weight)

## Current State (Mar 4, 2026)

- CI: 70 tests passing (latest commit build needs fix)
- Frontend: 15 pages built, all wired to real API hooks
- Backend: 25 API routes defined, services layer implemented
- Council: 8 agents + arbiter + runner fully implemented
- Brain Service: gRPC server + Ollama client ready (not yet connected to council)
- ML: XGBoost trainer + feature pipeline operational
- WebSocket: Code exists but not connected end-to-end
- CORS: Restricted to localhost:3000, localhost:5173, localhost:8080

## Phase 1 TODO (Active)

- [ ] P1.1: Fix CI build failure from latest commit
- [ ] P1.2: Wire feature_aggregator to real Alpaca bars
- [ ] P1.3: Connect brain_service gRPC to hypothesis + critic agents
- [ ] P1.4: Create trade_execution router with Alpaca orders
- [ ] P1.5: Add /api/v1/council/run endpoint
- [ ] P1.6: Wire WebSocket for real-time council verdicts
- [ ] P1.7: Add adaptive threshold config (replace hardcoded values)
- [ ] P1.8: Implement postmortem table in DuckDB

## Fixed Issues

1. Backend signals.py had missing return statement FIXED
2. main.py had hard ImportError on routers.trade_execution FIXED
3. main.py imported unused accept_connection FIXED
4. IndentationErrors across 20+ Python files FIXED
5. Agent Command Center 77KB monolith FIXED (decomposed)

## Remaining Issues

1. Backend has never been started locally (uvicorn app.main:app)
2. No authentication system yet
3. WebSocket not flowing real-time data yet
4. routers/trade_execution module does not exist yet
5. Brain service not connected to council agents
6. Agent thresholds are hardcoded (no adaptive learning)

## Rules for AI Assistants

1. NEVER import or use yfinance
2. NEVER use mock/fake data in production components
3. ALWAYS use useApi() hook for frontend data fetching
4. ALWAYS use 4-space indentation in Python
5. ALWAYS check mockups before building UI
6. Run npm run build before committing frontend changes
7. Run python -m pytest before committing backend changes
8. Council agents MUST return AgentVote schema
9. All new features must support the Embodier profit-being philosophy
10. 
## Claude Code-Inspired Architecture Patterns (Phase 2)

Inspired by Claude Code's Task Tool and Agent Teams architecture. These patterns
transform our council DAG from a static pipeline into a living, self-aware system.

### New Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| council/blackboard.py | BlackboardState dataclass replacing raw features dict | P1 |
| council/task_spawner.py | Dynamic agent spawning with model_tier + background support | P2 |
| council/self_awareness.py | AgentHealthMonitor, StreakDetector, BayesianAgentWeights | P2 |
| council/reflexes/circuit_breaker.py | Pre-council brainstem reflexes (flash crash, VIX spike) | P2 |
| council/homeostasis.py | System vital signs monitoring + mode switching | P3 |
| council/task_queue.py | Dependency-aware task queue replacing rigid stages | P3 |
| directives/global.md | Always-on trading rules loaded by agents at runtime | P2 |
| directives/regime_bull.md | Bull market agent behavior overrides | P3 |
| directives/regime_bear.md | Bear market defensive behaviors | P3 |

### Key Architecture Changes

1. **BlackboardState** (replaces features dict in runner.py)
   - Each stage writes to blackboard; later stages read accumulated context
   - Arbiter reads final blackboard state, not just vote tallies

2. **TaskSpawner** (like Claude Code's Task tool)
   - spawn(agent_type, symbol, model_tier="fast"|"deep", background=False)
   - background=True for postmortems, overnight learning
   - Replaces hardcoded imports in runner.py

3. **Agent Self-Awareness** (replaces static weight=1.0)
   - BayesianAgentWeights: Beta(alpha,beta) updated from trade outcomes
   - StreakDetector: 5 losses = PROBATION (0.25x), 10 = HIBERNATION
   - Wires into arbiter.py weighted voting

4. **Circuit Breaker** (runs BEFORE council)
   - flash_crash, vix_spike, daily_drawdown, position_limit reflexes
   - If any fires -> HALT_ALL, council never runs

5. **Trading Directives** (like CLAUDE.md)
   - Markdown files loaded by agents based on regime
   - Replaces hardcoded thresholds (hypothesis >0.6, arbiter 0.4)
   - 
   ## Recursive Self-Improvement Architecture (Phase 3)

The system teaches itself to find and exploit market patterns through three learning layers.
Inspired by Mind Evolution, FinMem, FLAG-Trader, and SEP research.
Ref: saulius.io/blog/recursive-self-improvement-llm-trading

### Layer 1: Pattern Discovery Engine (Cerebellum)
- Mines 3-5 years of historical data from Alpaca for all sectors
- Discovers: mean-reversion bounces, sector rotation symmetry, fear/greed rebounds, intraday overreaction corrections, overnight gap reversals
- Stores patterns in DuckDB `pattern_library` table: name, conditions, expected_outcome, confidence, regime, win_rate
- hypothesis_agent and strategy_agent load relevant patterns when generating signals
- Specific patterns: sector down >2% bounce probability, index symmetry correlations, Fear/Greed extreme entry windows, intraday overreaction reversal probability, sector rotation lag timing, volume divergence signals

### Layer 2: Strategy Evolution (Prefrontal Cortex)
- Mind Evolution-style evolutionary search using brain_service as mutation/crossover operator
- 4 strategy islands maintained in DuckDB: mean-reversion, momentum, event-driven, hybrid
- Each strategy = natural language description + parameters
- Backtesting engine = fitness function (Sharpe, drawdown, win rate, regime robustness)
- critic_agent = critic role, hypothesis_agent = author role (RCC loop)
- Top strategies migrate between islands each generation
- Runs overnight as background TaskSpawner jobs
- Overfitting detection: flag if strategy >3x better on recent vs full historical data

### Layer 3: Memory & Continuous Learning (Hippocampus)
- PatternMemory: tracks pattern profitability, auto-adjusts confidence
- StrategyMemory: tracks strategy performance per regime
- SourceMemory: tracks data source predictive value per pattern
- Postmortem table feeds BayesianAgentWeights
- HomeostasisMonitor reads all memory stores for mode switching
- DirectiveLoader auto-adjusts thresholds from memory

### Recursive Loop
```
Pattern Discovery -> Strategy Evolution -> Council DAG Execution -> Postmortem + Memory -> (repeat)
```
Each cycle the system gets smarter. When regimes change and patterns stop working,
BayesianAgentWeights downweight, StreakDetector triggers PROBATION, next evolution cycle adapts.

### New Files for RSI
| File | Purpose | Priority |
|------|---------|----------|
| council/pattern_discovery.py | Historical pattern mining engine | P2 |
| council/strategy_evolution.py | Mind Evolution strategy populations | P3 |
| council/memory/pattern_memory.py | Pattern confidence tracking | P2 |
| council/memory/strategy_memory.py | Strategy-regime performance | P3 |
| council/memory/source_memory.py | Data source predictive tracking | P3 |

### New DuckDB Tables
- pattern_library: discovered patterns with confidence scores
- strategy_populations: evolved strategy variants per island
- pattern_outcomes: pattern prediction vs actual result
- strategy_outcomes: strategy performance per regime period
- source_accuracy: data source predictive value tracking
