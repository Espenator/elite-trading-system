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

## CRITICAL ARCHITECTURE AUDIT (March 4, 2026)

### The Problem: Five Disconnected Systems

The codebase currently contains FIVE separate agent/decision systems that were built at different times and DO NOT talk to each other. Understanding this fragmentation is essential before making any changes.

#### System 1: Agent Command Center (5 polling agents)
- **Location**: `backend/app/api/v1/agents.py`
- **What it is**: 5 hardcoded template agents (Market Data, Signal Generation, ML Learning, Sentiment, YouTube Knowledge) with start/stop/pause/restart controls
- **How it works**: Each agent is just an async function. Market Data Agent polls every 60s via a background task in main.py. The other 4 only run when manually triggered via POST API.
- **Problem**: These are NOT real agents. No daemon lifecycle, no health monitoring, no inter-agent communication.

#### System 2: Council (13-agent DAG)
- **Location**: `backend/app/council/` (runner.py, arbiter.py, schemas.py, agents/)
- **What it is**: 13 council agents in a 7-stage DAG with deterministic arbiter
- **Agents (8 original)**: market_perception, flow_perception, regime, hypothesis, strategy, risk, execution, critic
- **Agents (6 new, Mar 4 2026)**: rsi, bbv, ema_trend, intermarket, relative_strength, cycle_timing
- **How it works**: On-demand only via POST to `/api/v1/council/evaluate`. No automatic trigger.
- **Problem**: Council is an island. No connection to System 1 or System 4.

#### System 3: OpenClaw (copied Flask/Slack multi-agent system)
- **Location**: `backend/app/modules/openclaw/` (9 subdirectories)
- **What it is**: Entire separate trading system copy-pasted from archived openclaw repo.
- **Problem**: Mostly dead code. Need to extract useful pieces or delete.

#### System 4: Event-Driven Pipeline (real-time trading)
- **Location**: `backend/app/core/message_bus.py`, `services/signal_engine.py`, `services/order_executor.py`
- **What it is**: MessageBus -> AlpacaStreamService -> EventDrivenSignalEngine -> OrderExecutor
- **How it works**: Starts automatically in main.py lifespan. <1s latency.
- **Problem**: Runs independently of Council. Makes trading decisions without consulting 13-agent council.

#### System 5: CNS Architecture (DESIGNED, NOT BUILT)
- **What it is**: The VISION — BlackboardState, TaskSpawner, CircuitBreaker, Self-Awareness, Homeostasis
- **Problem**: None of these files exist yet. This is where the codebase SHOULD be heading.

### Stale Documentation Warnings
- `council/__init__.py` says "8-Agent" — actually 13
- `council/schemas.py` says "8-agent" — actually 13
- `api/v1/council.py` says "8-agent" and GET /status returns old 8-agent/6-stage config
- REPO-MAP.md does not list council/ directory

### Feature Gap: New Agents Get No Real Data
- ema_trend_agent expects `ind_ema_5/10/20` (aggregator only has ema_9, ema_21)
- intermarket_agent expects `spy_uvxy_correlation`, `vix_current`, `sector_breadth`
- relative_strength_agent expects `peer_percentile_20d`, `excess_return_20d`
- cycle_timing_agent expects `cycle_phase`, `cycle_phase_confidence`
- All default to hold/0.0 until feature_aggregator.py is updated

## ROADMAP: Unification into CNS Architecture

### P0: Wire Council to Event Pipeline (HIGHEST PRIORITY)
- Subscribe to `signal.generated` on MessageBus
- Auto-invoke `run_council()` when score >= threshold
- OrderExecutor listens to `council.verdict` for trade decisions

### P1: Build BlackboardState
- Create `council/blackboard.py` — shared state across DAG stages
- Later stages read earlier conclusions, not just raw features

### P2: Add Missing Feature Keys to feature_aggregator.py
- EMA-5/10/20, intermarket correlations, relative strength, cycle timing, VIX

### P3: Build CircuitBreaker Reflexes (brainstem)
- `council/reflexes/circuit_breaker.py` — flash crash, VIX spike, drawdown limits
- Runs pre-council on every bar, <50ms

### P4: Clean Up OpenClaw
- Extract useful scorer/scanner logic, delete dead Flask app and unreachable modules
- Clean up disconnected `core/api/` at repo root

### P5: Build TaskSpawner
- Dynamic agent registry replacing hardcoded imports in runner.py

### P6: Unify Agent Command Center
- Show real 13-agent council state instead of 5 fake template agents

### P7: Wire brain_service gRPC
- Connect Ollama to hypothesis_agent and critic_agent

### P8: Agent Self-Awareness (Bayesian weights)
- BayesianAgentWeights, StreakDetector, AgentHealthMonitor

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18 (Vite), Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn, LSTM (no PyTorch in prod) |
| Council | 13-agent DAG with deterministic arbiter (7 stages) |
| Brain Service | gRPC + Ollama (PC2) for LLM inference |
| Event Pipeline | MessageBus, Alpaca WebSocket, SignalEngine, OrderExecutor |
| CI/CD | GitHub Actions (70 tests passing) |
| Infra | Docker, docker-compose.yml |
| Local AI | Ollama on RTX GPU cluster |

## Hardware (Dual-PC Setup)
- PC 1: Development + Frontend + Backend API
- PC 2: RTX GPU cluster for ML training + Ollama inference (brain_service)
- Connected via gRPC (brain_service port 50051)

## Data Sources (CRITICAL - NO yfinance)
- Alpaca Markets (alpaca-py) — Market data + order execution
- Unusual Whales — Options flow + institutional activity
- FinViz (finviz) — Screener, fundamentals, VIX proxy
- FRED — Economic macro data
- SEC EDGAR — Company filings

## Council Architecture (13-Agent DAG, 7 Stages)

```
Stage 1 (Parallel): market_perception, flow_perception, regime, intermarket
Stage 2 (Parallel): rsi, bbv, ema_trend, relative_strength, cycle_timing
Stage 3: hypothesis (wired to brain_service LLM)
Stage 4: strategy (entry/exit/sizing)
Stage 5 (Parallel): risk, execution
Stage 6: critic (postmortem learning)
Stage 7: arbiter (deterministic BUY/SELL/HOLD)
```

Arbiter Rules:
1. VETO from risk or execution -> hold, vetoed=True
2. Requires regime + risk + strategy OK for any trade
3. Weighted confidence aggregation for direction
4. Execution readiness requires confidence > 0.4 AND execution_ready=True

Agent Schema: `AgentVote(agent_name, direction, confidence, reasoning, veto, veto_reason, weight, metadata)`

## CNS Architecture (Central Nervous System)

- **Brainstem** (<50ms): CircuitBreaker reflexes [TO BUILD - P3]
- **Spinal Cord** (~1500ms): 13-agent council DAG [BUILT]
- **Cortex** (300-800ms): hypothesis + critic via brain_service gRPC [NOT WIRED - P7]
- **Thalamus**: BlackboardState shared memory [TO BUILD - P1]
- **Autonomic**: Bayesian weights, overnight learning [TO BUILD - P8]
- **PNS Sensory**: Alpaca WS, Unusual Whales, FinViz, FRED, EDGAR [BUILT]
- **PNS Motor**: OrderExecutor -> Alpaca Orders [BUILT]
- **Event Bus**: MessageBus pub/sub [BUILT]

## Event-Driven Pipeline (BUILT)

```
AlpacaStreamService -> market_data.bar -> EventDrivenSignalEngine
-> signal.generated (score >= 65) -> OrderExecutor -> order.submitted
-> WebSocket bridges -> Frontend
```

## Key Code Patterns
1. Frontend: useApi('endpoint') hook, no mock data
2. Python: 4-space indentation, never tabs
3. Council agents: pure async functions with NAME, WEIGHT, evaluate() -> AgentVote
4. Features: `f = features.get("features", features)` then `f.get("key", default)`
5. API: Route handler -> Service layer -> External API

## Current State (Mar 4, 2026)
- CI: 70 tests passing
- Frontend: 15 pages, all wired to real API hooks
- Backend: 25 API routes, services layer implemented
- Council: 13 agents + arbiter + runner (expanded from 8 on Mar 4)
- Brain Service: gRPC + Ollama ready (not yet connected)
- Event Pipeline: MessageBus + SignalEngine + OrderExecutor running
- Feature Gap: 6 new agents need feature_aggregator updates

## Phase 1 TODO
- [ ] P0: Wire council to event pipeline
- [ ] P1: Build BlackboardState
- [ ] P2: Add missing feature keys
- [ ] P3: Build CircuitBreaker reflexes
- [ ] P4: Clean up OpenClaw
- [ ] P5: Build TaskSpawner
- [ ] P6: Unify Agent Command Center
- [ ] P7: Wire brain_service gRPC
- [ ] P8: Build agent self-awareness
- [ ] Fix stale docstrings (council files + status endpoint)

## Rules for AI Assistants
1. NEVER import or use yfinance
2. NEVER use mock/fake data in production
3. ALWAYS use useApi() hook for frontend data
4. ALWAYS use 4-space indentation in Python
5. Council agents MUST return AgentVote schema
6. The ONE repo is Espenator/elite-trading-system — do NOT commit to Embodier-Trader
7. Council has 13 agents in 7 stages — NOT 8 agents in 6 stages
8. Read CRITICAL ARCHITECTURE AUDIT section before making changes
9. Agent pattern: module-level NAME + WEIGHT + async def evaluate() -> AgentVote

## Recursive Self-Improvement (Phase 3 - Future)
- Layer 1: Pattern Discovery Engine — mines historical data, stores in DuckDB
- Layer 2: Strategy Evolution — Mind Evolution search, 4 strategy islands
- Layer 3: Memory — PatternMemory, StrategyMemory, SourceMemory feed Bayesian weights
- Loop: Pattern Discovery -> Strategy Evolution -> Council -> Postmortem -> (repeat)
