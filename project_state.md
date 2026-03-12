# Project State - Embodier Trader (Embodier.ai)
> Paste this file at the start of every new AI chat session. Say: "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."
> Last updated: March 12, 2026 (v5.0.0 — ALL Phases A+B+C+D+E complete. 1,044 tests passing. CI GREEN.)

## Identity
- **Project**: Embodier Trader by Embodier.ai
- **Brand**: Embodier Trader — a profit-consciousness entity being
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC — this is the ONE repo for all code)
- **Legacy Repo**: github.com/Espenator/Embodier-Trader — forked HTML site + orphaned JS agents. TO BE ARCHIVED. Do NOT build here.
- **Owner**: Espenator (Asheville, NC)
- **Status**: v5.0.0 — ALL Phases A+B+C+D+E complete. Production-ready (~95%).
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. It operates as a conscious profit-seeking being with a Central Nervous System (CNS) architecture.
- **Current Focus**: Council runs 35-agent DAG; 43 API route files (364+ endpoints); 72+ services; 1,044 tests; Bearer auth fail-closed; WebSocket active (25 channels); desktop BUILD-READY; E2E pipeline tested; Slack notifications wired to all trading events. 1,459+ commits. CI GREEN (3 jobs: backend-test + frontend-build + e2e-gate).BUILD-READY; E2E pipeline tested; Slack notifications wired to all trading events.
- **Latest Session Fixes**: Slack notification bridges wired (council.verdict, order.submitted, order.filled, signal.generated, alert.* → Slack channels). Fixed 3 broken Slack imports. Fixed device-config.js .env regeneration bug (hardcoded API key defaults). Fixed weight learner test_symmetric_penalty. All phases (A+B+C+D+E) complete.

## Two-PC Development Setup

Paths: canonical only (see **PATH-STANDARD.md**). No alternate paths in docs.

### PC1: ESPENMAIN (Primary)
| Item | Value |
|------|-------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary — backend API, frontend, DuckDB, trading execution |
| Repo path | `C:\Users\Espen\elite-trading-system` |
| Backend path | `C:\Users\Espen\elite-trading-system\backend` |
| Frontend path | `C:\Users\Espen\elite-trading-system\frontend-v2` |
| Python venv | `C:\Users\Espen\elite-trading-system\backend\venv` |
| Alpaca account | ESPENMAIN — Key 1 (portfolio trading) |

### PC2: ProfitTrader (Secondary)
| Item | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 |
| Role | Secondary — GPU training, ML inference, brain_service (gRPC) |
| Repo path | `C:\Users\ProfitTrader\elite-trading-system` |
| Backend path | `C:\Users\ProfitTrader\elite-trading-system\backend` |
| Frontend path | `C:\Users\ProfitTrader\elite-trading-system\frontend-v2` |
| Python venv | `C:\Users\ProfitTrader\elite-trading-system\backend\venv` |
| Alpaca account | Profit Trader — Key 2 (discovery scanning) |

Both IPs are DHCP-reserved on the AT&T BGW320-505 router (192.168.1.254).

### Ports & URLs
| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs (Swagger) | 8000 | http://localhost:8000/docs |
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Brain Service (gRPC) | 50051 | localhost:50051 |
| Ollama | 11434 | http://localhost:11434 |
| Redis (optional) | 6379 | redis://localhost:6379 |

### External API Services (all in backend/.env, gitignored)

| Service | Env Var | Required? | Status |
|---------|---------|-----------|--------|
| Alpaca (Key 1 — ESPENMAIN) | `ALPACA_API_KEY` | YES (core) | Needs key on this env |
| Alpaca (Key 2 — ProfitTrader) | `ALPACA_KEY_2` | No (discovery) | Needs key on this env |
| Finviz Elite | `FINVIZ_API_KEY` | No | Needs key |
| FRED | `FRED_API_KEY` | No | **CONFIGURED** |
| NewsAPI | `NEWS_API_KEY` | No | **CONFIGURED** |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | No | **CONFIGURED** |
| Perplexity | `PERPLEXITY_API_KEY` | No (LLM tier 2) | Needs key |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | No (LLM tier 3) | Needs key |
| Resend (email) | `RESEND_API_KEY` | No | **CONFIGURED** |
| Benzinga (scraper) | `BENZINGA_EMAIL` / `BENZINGA_PASSWORD` | No | **CONFIGURED** — web scraper |
| SqueezeMetrics (scraper) | `SQUEEZEMETRICS_ENABLED` | No | **CONFIGURED** — public DIX/GEX |
| Capitol Trades (scraper) | — (via UW API) | No | **CONFIGURED** — UW congress + scrape fallback |
| StockGeist | `STOCKGEIST_API_KEY` | No | Not configured |
| YouTube | `YOUTUBE_API_KEY` | No | Not configured |

### Slack Bots (Embodier Trader Workspace)

| Bot | App ID | Purpose |
|-----|--------|---------|
| OpenClaw | A0AF9HSCQ6S | Multi-agent swarm notifications |
| TradingView Alerts | A0AFQ89RVEV | Inbound TradingView webhook alerts |

Slack tokens expire every 12h — refresh at https://api.slack.com/apps. Config in `backend/.env`.

## LATEST STATE (March 12, 2026) — v4.1.0-dev (Phase A Complete)

### Current Architecture Snapshot
- **Council**: 35-agent DAG in 7 stages. All agents are real implementations (not stubs). CouncilGate invokes full council on every signal (score >= 65).
- **Backend**: 43 API route files in api/v1/ (364+ endpoints); 72+ services (incl. subdirs: scouts, llm_clients, channel_agents, firehose_agents, integrations). brain_service wired (hypothesis_agent → gRPC).
- **Tests**: 666+ passing (backend pytest). CI GREEN.
- **Auth**: Bearer token auth, fail-closed for live trading.
- **WebSocket**: Active; 25 channels with token auth, heartbeat (30s/60s). 5 pages wired.
- **Desktop**: Electron app in `desktop/` — BUILD-READY.
- **LLM Intelligence**: 3-tier router — Ollama (routine) → Perplexity (sonar-pro) → Claude. Claude reserved for 6 deep-reasoning tasks.
- **Data Sources**: 10 active (Alpaca, UW, Finviz, FRED, EDGAR, NewsAPI, Benzinga, SqueezeMetrics, Capitol Trades, Senate Stock Watcher).
- **Scouts**: 12 continuous discovery scouts (Phase A1 fixed 5 crashes).
- **Production Readiness**: ~65%. Architecture solid, enforcement gaps identified. Phase A closed critical gaps.
- **CLAUDE.md files**: Root + frontend-v2 + backend + council + brain_service (comprehensive audit March 12).

### Deep Audit Results (March 11, 2026)
A line-by-line audit of the entire codebase found 40 specific issues in 4 categories:
- **10 Profit Killers**: signal gate too aggressive, shorts inverted, cooldown too long, market-only orders, partial fills lost
- **10 Silent Failures**: 3 scouts crash, no data backfill, agents silently return HOLD, weight learner drops 50%+ outcomes
- **10 Unenforced Safeguards**: 9 of 10 circuit breakers advisory-only, regime params ignored, no paper/live safety check
- **10 Intelligence Gaps**: no regime-adaptive thresholds, no confidence calibration, debate not wired to learning

**What IS working well**: All 33+ agents real, Bayesian weights correct, VETO enforced, sub-1s latency, Kelly math sound, 3-tier LLM router, 666 tests GREEN.

**See `PLAN.md` for the complete 5-phase enhancement plan (Phases A-E, 13-18 sessions).**

### Resolved Blockers (no longer blocking)
- Backend startup (uvicorn) — resolved.
- WebSocket connectivity — resolved; bridges active.
- Auth for live trading — Bearer token, fail-closed.
- Frontend-backend wiring — all 14 pages audited and fixed.
- Mock data — all removed, replaced with real data sources.

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

## ROADMAP: Enhancement Plan (from Deep Audit)

### COMPLETED
- [x] Wire Council to Event Pipeline (CouncilGate)
- [x] Add Missing Feature Keys (EMA-5/10/20, intermarket, cycle, VIX, sector breadth)
- [x] Bayesian WeightLearner with trade outcome learning
- [x] Wire brain_service gRPC to hypothesis_agent
- [x] Backend health, mock data removal, frontend wiring (all 14 pages)
- [x] UI controls, Slack notification service, health monitoring
- [x] 28 action buttons verified, 5 missing endpoints added

### Phase A: Stop the Bleeding (P0 — COMPLETE March 11, 2026)
- [x] A1: Fix 5 scout crashes (added missing service methods + singleton getters to 3 services)
- [x] A2: Enhanced startup data backfill (checks daily_ohlcv, not just indicators)
- [x] A3: Wire regime params to order executor (Gate 2b: RED/CRISIS blocks entries)
- [x] A4: Enforce circuit breakers in order executor (Gate 2c: leverage 2x + concentration 25%)
- [x] A5: VIX-based regime fallback (VIX>=40=CRISIS, >=30=RED, >=20=YELLOW, <20=GREEN)
- [x] A6: Paper/live account safety check (forces SHADOW mode on mismatch)
- [x] A7: Fix DuckDB async lock race condition (thread-safe double-checked locking)
- [x] A8: Background loop supervisor/respawn (3 retries + Slack alert)

### Phase B: Unlock Alpha (P0 — remove profit blockers)
- [ ] Calibrate signal gate threshold (regime-adaptive)
- [ ] Fix short signal generation
- [ ] Smart cooldown (regime-adaptive, separate buy/sell)
- [ ] Priority queue for concurrent council evaluations
- [ ] Limit orders for large positions
- [ ] Partial fill re-execution
- [ ] Fix viability gate and portfolio heat check

### Phase C: Sharpen the Brain — COMPLETE (March 12, 2026)
- [x] Fix weight learner (confidence floor 0.20, regime-stratified Beta(α,β), symmetric loss, trade_id matching)
- [x] Confidence calibration (Brier score tracking per agent, 20% penalty for poorly calibrated)
- [x] Wire debate to learning, council decision audit trail (DuckDB tables + API endpoints)
- [x] Fix trade stats R-multiple (actual stop_price, r_multiple_estimated flag)
- [x] Wire homeostasis to position sizing (AGGRESSIVE/NORMAL/DEFENSIVE/HALTED multipliers)
- [x] Regime-adaptive thresholds centralized in config/regime_thresholds.py
- [x] Publish all 5 data sources to MessageBus (FRED, SEC EDGAR, SqueezeMetrics, Benzinga, Capitol Trades)
- [x] Silent failure alerting (alert.agent_failure, alert.data_starvation, alert.council_degraded)
- [x] Activate SelfAwareness Bayesian tracking (Issue #48)
- [x] IntelligenceCache.start() at startup (Issue #49)
- [x] 12 Academic Edge agents in runner.py DAG (Issue #50)
- [x] brain_service gRPC wired to hypothesis_agent (Issue #51)
- [x] Explicit weights for 6 supplemental agents (Issue #52)

### Phase D: Continuous Intelligence (P1)
- [ ] Autonomous daily data backfill
- [ ] Rate limiting framework
- [ ] MessageBus dead-letter queue
- [ ] Scraper resilience

### Phase E: Production Hardening (P2) — COMPLETE
- [x] End-to-end integration test (full pipeline + fill→outcome→weight_learner)
- [x] Emergency flatten with retry + auth + DuckDB pending_liquidations
- [x] Position manager startup sync + GET /api/v1/positions/sync-status
- [x] WebSocket circuit breaker with MessageBus alert
- [x] Comprehensive metrics (council latency percentiles, weight learner stats, queue depth)
- [x] Desktop packaging + Task Scheduler auto-start

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
- Unusual Whales — Options flow, dark pool, congressional trades
- FinViz (finviz) — Screener, fundamentals, VIX proxy
- FRED — Economic macro data
- SEC EDGAR — Company filings
- Benzinga (web scraper) — Earnings calendar + transcripts
- SqueezeMetrics (web scraper) — DIX/GEX dark pool indicators
- Capitol Trades (web scraper + UW API) — Congressional trading disclosures
- Senate Stock Watcher (JSON API) — Secondary congressional trades fallback
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

## Current State (March 12, 2026 — v4.1.0-dev, Phase A Complete)
- CI: 666+ tests passing (backend pytest), GREEN
- Version: 4.1.0-dev. Deep audit + Phase A critical fixes + CLAUDE.md audit complete.
- Production Readiness: ~65%. Critical enforcement gaps closed, scout crashes fixed, safety gates active.
- Frontend: 14 pages, all pixel-matched to mockups, wired to real API hooks, 28 action buttons verified
- Backend: 43 API route files (364+ endpoints), 72+ service files, all mounted and responding
- Council: 35-agent DAG — all agents are real implementations (not stubs). Sub-1s latency.
- Phase A Fixes Applied: Regime enforcement, circuit breakers, paper/live safety, DuckDB lock, background supervisor, scout crashes, data backfill
- Remaining: Signal gate needs calibration; shorts inverted; weight learner too strict; no limit orders
- LLM: 3-tier router (Ollama → Perplexity → Claude); Claude for 6 deep-reasoning tasks only
- Auth: Bearer token, fail-closed for live trading
- Kelly Sizing: Real DuckDB stats; Mock Guard active; R-multiple assumes 2% stop (needs fix)
- Infrastructure: Two-PC LAN, all API keys configured
- Latest commit: f4be8c1 "fix: DuckDB thread-safety segfault + TurboScanner deque slice bug"
- Next Steps: Phase D (continuous intelligence — data backfill, rate limiting, scraper resilience) is the only remaining phase
- Full plan: See PLAN.md (40 specific issues, 5 phases, 10-15 remaining sessions)

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
