# CLAUDE.md — Embodier Trader (Elite Trading System)
# This file is read automatically by Claude Code at session start.
# Last updated: March 12, 2026 — v4.1.0-dev (Phase A complete)

## 1. Identity

- **Name**: Embodier Trader v4.1.0-dev — an AI-powered trading intelligence platform by Embodier.ai
- **Repo**: github.com/Espenator/elite-trading-system (PUBLIC)
- **Owner**: Espenator (Espen Schiefloe, Asheville NC)
- **Philosophy**: Embodied Intelligence — the system IS profit, not seeking it. A conscious profit-seeking being with a Central Nervous System (CNS) architecture.
- **Local Path**: `C:\Users\Espen\elite-trading-system`

## 2. Quick Reference

**Paths:** Use **repo-relative** paths everywhere (e.g. `backend/`, `frontend-v2/`). See `PATH-STANDARD.md` for the single source of truth. Machine-specific absolute paths: `PATH-MAP.md`.

### PC1: ESPENMAIN (Primary)
| Item | Value |
|------|-------|
| Hostname | ESPENMAIN |
| LAN IP | 192.168.1.105 |
| Role | Primary — backend API, frontend, DuckDB, trading execution |
| Repo root | Workspace root. Canonical: ESPENMAIN `C:\Users\Espen\elite-trading-system`, ProfitTrader `C:\Users\ProfitTrader\elite-trading-system`. See PATH-STANDARD.md. |
| Backend | `backend/` |
| Frontend | `frontend-v2/` |
| Python venv | `backend/venv` |
| Alpaca account | ESPENMAIN (paper trading) — Key 1 |

### PC2: ProfitTrader (Secondary)
| Item | Value |
|------|-------|
| Hostname | ProfitTrader |
| LAN IP | 192.168.1.116 |
| Role | Secondary — GPU training, ML inference, brain_service (gRPC) |
| Repo root | Workspace root on PC2 (see PATH-STANDARD.md) |
| Alpaca account | Profit Trader (discovery) — Key 2 |

| Metric | Value |
|--------|-------|
| Version | v4.1.0-dev |
| Tests | 982+ passing (pytest), CI GREEN |
| Council agents | 35 (7-stage DAG) |
| Backend services | 72+ (incl. subdirs) |
| API route files | 43 in api/v1/ (364+ endpoints) |
| Frontend pages | 14 (React 18 + Vite) |
| Data sources | 10 (Alpaca, UW, Finviz, FRED, EDGAR, NewsAPI, Benzinga, SqueezeMetrics, Capitol Trades, Senate Stock Watcher) |
| Discovery scouts | 12 (continuous, not polling) |
| Production readiness | ~85% (Phase A+B+C complete, D-E pending) |
| Commits | 1,424+ |

## 3. Architecture Overview — CNS Layers

| CNS Layer | Speed | Component | Status |
|-----------|-------|-----------|--------|
| Brainstem | <50ms | `reflexes/circuit_breaker.py` — auto-protective reflexes | Gate 2c enforced (leverage 2x, concentration 25%) |
| Spinal Cord | ~1500ms | 35-agent council DAG (7 parallel stages) | BUILT — all agents are real implementations |
| Cortex | 300-800ms | 3-tier LLM: Ollama → Perplexity → Claude | WIRED — hypothesis + critic via brain gRPC |
| Thalamus | — | `blackboard.py` shared memory across DAG stages | BUILT |
| Autonomic | nightly | WeightLearner Bayesian Beta(α,β) + scheduler jobs | BUILT — confidence floor too strict (0.5) |
| PNS Sensory | real-time | Alpaca WS, UW, FinViz, FRED, EDGAR, NewsAPI | BUILT — 5 sources don't publish to MessageBus |
| Discovery | streaming | 12 Scout Agents (continuous, Issue #38) | BUILT — Phase A fixed 5 scout crashes |
| PNS Motor | — | OrderExecutor → Alpaca (via council.verdict) | BUILT — Gate 2b regime + Gate 2c circuit breakers |

## 4. Directory Structure

```
C:\Users\Espen\elite-trading-system\
├── backend/                        # FastAPI backend (Python 3.11)
│   ├── app/
│   │   ├── main.py                 # 44 router registrations, 6-phase lifespan startup
│   │   ├── api/v1/                 # 43 route files (364+ endpoints)
│   │   ├── council/                # 35-agent DAG + 15 orchestration files
│   │   │   ├── agents/             # 32 agent files (35 registered agents)
│   │   │   ├── debate/             # debate_engine, scorer, utils
│   │   │   ├── regime/             # bayesian_regime
│   │   │   ├── reflexes/           # circuit_breaker
│   │   │   ├── runner.py           # 7-stage DAG orchestrator (29.4 KB)
│   │   │   ├── arbiter.py          # Bayesian-weighted BUY/SELL/HOLD
│   │   │   ├── schemas.py          # AgentVote + DecisionPacket
│   │   │   ├── council_gate.py     # Signal → Council bridge
│   │   │   └── weight_learner.py   # Bayesian Beta(α,β) learning
│   │   ├── services/               # 72+ service modules
│   │   │   ├── scouts/             # 12 discovery scouts
│   │   │   ├── llm_clients/        # ollama, perplexity, claude
│   │   │   ├── channel_agents/     # 6 channel agents + orchestrator
│   │   │   ├── firehose_agents/    # 4 firehose ingest agents
│   │   │   ├── integrations/       # 6 data source adapters
│   │   │   └── (68+ top-level services)
│   │   ├── core/                   # MessageBus, security, config
│   │   ├── data/                   # DuckDB storage + init_schema()
│   │   ├── features/               # feature_aggregator.py
│   │   ├── jobs/                   # scheduler, daily_outcome, walkforward
│   │   ├── modules/                # openclaw/, ml_engine/
│   │   └── websocket_manager.py    # 25 channels, token auth, heartbeat
│   └── tests/                      # 666+ tests passing
├── frontend-v2/                    # React 18 + Vite + TailwindCSS
│   └── src/
│       ├── pages/                  # 14 route pages
│       ├── hooks/                  # useApi, useSentiment, useSettings, useTradeExecution
│       ├── config/api.js           # 189 endpoint definitions
│       ├── services/               # websocket.js, tradeExecutionService.js
│       └── components/             # dashboard/ (6), layout/ (5), ui/ (9)
├── brain_service/                  # gRPC LLM inference (PC2 RTX GPU)
│   ├── server.py, ollama_client.py, models.py
│   └── proto/                      # Protobuf definitions
├── desktop/                        # Electron desktop app (BUILD-READY)
├── directives/                     # Trading directives (global.md, regime_*.md)
├── docs/                           # Architecture, mockups, audits
│   ├── mockups-v3/images/          # 23 UI mockups (source of truth)
│   └── architecture/               # 4 skill-sharing documents
├── scripts/                        # Deployment utilities
├── CLAUDE.md                       # THIS FILE — auto-loaded by Claude Code
├── PLAN.md                         # 5-phase enhancement plan (A-E)
├── project_state.md                # Session context (read first)
└── docker-compose.yml              # Full stack deployment
```

## 5. Trade Pipeline

**Rules (CRITICAL):** Paths = repo-relative; no mock data; all frontend via `useApi()`; no yfinance; 4-space indent; agents return `AgentVote`; VETO_AGENTS = risk/execution only; CouncilGate required; continuous discovery; scouts → `swarm.idea`; one repo; no secrets in commits; dashboard inside `<Layout />`. See PATH-STANDARD.md.

```
AlpacaStreamService
  → market_data.bar (MessageBus)
  → EventDrivenSignalEngine (feature computation + ML scoring)
  → signal.generated (score >= 65)
  → CouncilGate (invokes 35-agent council)
      → Stage 1: Perception + Academic Edge (13 agents, parallel)
      → Stage 2: Technical + Data Enrichment (8 agents, parallel)
      → Stage 3: Hypothesis + Memory (2 agents, parallel)
      → Stage 4: Strategy (1 agent)
      → Stage 5: Risk + Execution + Portfolio (3 agents, parallel)
      → Stage 5.5: Debate + Red Team (3 agents)
      → Stage 6: Critic (1 agent)
      → Stage 7: Arbiter (Bayesian-weighted BUY/SELL/HOLD)
  → council.verdict
  → OrderExecutor (Gate 2b regime → Gate 2c breakers → Kelly sizing → Heat → Viability → market/limit/TWAP)
  → order.submitted
  → WebSocket bridges → Frontend
```

## 6. Council Architecture (35 Agents, 7 Stages)

### Core (11 Agents)

| Agent | File | Weight | Stage |
|-------|------|--------|-------|
| Market Perception | market_perception_agent.py | 1.0 | 1 |
| Flow Perception | flow_perception_agent.py | 0.8 | 1 |
| Regime | regime_agent.py | 1.2 | 1 |
| Social Perception | social_perception_agent.py | 0.7 | 1 |
| News Catalyst | news_catalyst_agent.py | 0.6 | 1 |
| YouTube Knowledge | youtube_knowledge_agent.py | 0.4 | 1 |
| Hypothesis | hypothesis_agent.py | 0.9 | 3 |
| Strategy | strategy_agent.py | 1.1 | 4 |
| Risk | risk_agent.py | 1.5 | 5 |
| Execution | execution_agent.py | 1.3 | 5 |
| Critic | critic_agent.py | 0.5 | 6 |

### Academic Edge (12 Agents)

| Agent | File | Weight | Stage |
|-------|------|--------|-------|
| GEX / Options Flow | gex_agent.py | 0.9 | 1 |
| Insider Filing | insider_agent.py | 0.85 | 1 |
| FinBERT Sentiment | finbert_sentiment_agent.py | 0.75 | 1 |
| Earnings Tone NLP | earnings_tone_agent.py | 0.8 | 1 |
| Dark Pool | dark_pool_agent.py | 0.7 | 1 |
| Macro Regime | macro_regime_agent.py | 1.0 | 1 |
| Supply Chain | supply_chain_agent.py | 0.7 | 2 |
| 13F Institutional | institutional_flow_agent.py | 0.7 | 2 |
| Congressional | congressional_agent.py | 0.6 | 2 |
| Portfolio Optimizer | portfolio_optimizer_agent.py | 0.8 | 5 |
| Layered Memory | layered_memory_agent.py | 0.6 | 3 |
| Alternative Data | alt_data_agent.py | 0.5 | post |

### Supplemental (6 Agents)

| Agent | File | Stage |
|-------|------|-------|
| RSI | rsi_agent.py | 2 |
| BBV | bbv_agent.py | 2 |
| EMA Trend | ema_trend_agent.py | 2 |
| Intermarket | intermarket_agent.py | 1 |
| Relative Strength | relative_strength_agent.py | 2 |
| Cycle Timing | cycle_timing_agent.py | 2 |

### Debate & Adversarial (3 Agents)

| Agent | File | Stage |
|-------|------|-------|
| Bull Debater | bull_debater.py | 5.5 |
| Bear Debater | bear_debater.py | 5.5 |
| Red Team | red_team_agent.py | 5.5 |

### Orchestration (15 files in council/)

| File | Purpose |
|------|---------|
| runner.py (29.4 KB) | 7-stage parallel DAG orchestrator |
| weight_learner.py (14.8 KB) | Bayesian Beta(α,β) self-learning weights |
| hitl_gate.py (12.0 KB) | Human-in-the-loop approval gate |
| blackboard.py (11.1 KB) | Shared memory state across stages |
| self_awareness.py (10.8 KB) | System metacognition |
| task_spawner.py (10.7 KB) | Dynamic agent registry |
| overfitting_guard.py (9.4 KB) | ML overfitting detection |
| data_quality.py (9.0 KB) | Data quality scoring |
| council_gate.py (8.9 KB) | Signal → Council → OrderExecutor bridge |
| shadow_tracker.py (8.0 KB) | Shadow portfolio (paper vs live) |
| schemas.py (7.6 KB) | AgentVote + DecisionPacket |
| feedback_loop.py (7.5 KB) | Post-trade feedback |
| homeostasis.py (6.3 KB) | System stability + auto-healing |
| arbiter.py (6.4 KB) | Bayesian-weighted BUY/SELL/HOLD |
| agent_config.py (5.4 KB) | Settings-driven thresholds |

## 7. Key Code Patterns

```python
# AgentVote schema — ALL agents MUST return this
@dataclass
class AgentVote:
    agent_name: str
    direction: str          # "buy" | "sell" | "hold"
    confidence: float       # 0.0 – 1.0
    reasoning: str
    veto: bool = False
    veto_reason: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    blackboard_ref: str = ""
```

```javascript
// Frontend: ALWAYS use useApi hook — no direct fetch, no mock data
const { data, loading, error } = useApi('councilLatest', { pollIntervalMs: 15000 });
```

```python
# Agent pattern: module-level NAME + WEIGHT + async evaluate() → AgentVote
NAME = "my_agent"
WEIGHT = 0.8

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    f = features.get("features", features)
    return AgentVote(agent_name=NAME, direction="buy", confidence=0.75,
                     reasoning="...", weight=WEIGHT)
```

```python
# Event pipeline
# signal.generated → CouncilGate → run_council() → council.verdict → OrderExecutor
# VETO_AGENTS = {"risk", "execution"}
# REQUIRED_AGENTS = {"regime", "risk", "strategy"}
```

## 8. Swarm Invariants

1. **No trade without** `council_decision_id` — every order must trace to a council verdict
2. **No data without** agent validation — feature aggregator checks data quality
3. **No UI mutation without** agent approval — frontend reads only, never writes trading state
4. **Decisions expire** after 30 seconds — stale verdicts cannot execute
5. **No yfinance** — ever. Use Alpaca/FinViz/UW
6. **No mock data** in production components — all data via real API endpoints

## 9. LLM Intelligence — 3-Tier Router

| Tier | Provider | Tasks | Cost |
|------|----------|-------|------|
| 1 (Local) | Ollama on RTX GPU (PC2) | Routine agent tasks, hypothesis generation | Free |
| 2 (Search) | Perplexity (sonar-pro) | Web search + synthesis for news analysis | Moderate |
| 3 (Deep) | Claude | 6 deep-reasoning tasks ONLY | Higher |

**Claude-reserved tasks**: `strategy_critic`, `strategy_evolution`, `deep_postmortem`, `trade_thesis`, `overnight_analysis`, `directive_evolution`

**Brain Service**: gRPC server on port 50051, runs on PC2 (ProfitTrader, 192.168.1.116). Primary consumer: `hypothesis_agent.py`. Client: `services/brain_client.py`.

## 10. Data Sources

| Source | Env Var | Library/Method | Data |
|--------|---------|----------------|------|
| Alpaca Markets | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | alpaca-py | OHLCV bars, quotes, orders, streaming |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | REST API (httpx) | Options flow, dark pool, congressional |
| Finviz Elite | `FINVIZ_API_KEY` | finviz lib | Screener, fundamentals, sector data |
| FRED | `FRED_API_KEY` | fredapi | Macro indicators, yield curves, VIX |
| SEC EDGAR | `SEC_EDGAR_USER_AGENT` | REST API (httpx) | Insider transactions, 13F filings |
| NewsAPI | `NEWS_API_KEY` | REST API | Breaking news headlines |
| Benzinga | `BENZINGA_EMAIL` / `BENZINGA_PASSWORD` | Web scraper (httpx) | Earnings calendar + transcripts |
| SqueezeMetrics | `SQUEEZEMETRICS_ENABLED` | Web scraper (httpx) | DIX/GEX dark pool indicators |
| Capitol Trades | via UW API + scraper | httpx | Congressional trade disclosures |
| Senate Stock Watcher | — (JSON API) | httpx | Secondary congressional fallback |

All sources degrade gracefully if keys are missing.

## 11. Infrastructure — Dual-PC Setup

| Item | PC1: ESPENMAIN | PC2: ProfitTrader |
|------|----------------|-------------------|
| Hostname | ESPENMAIN | ProfitTrader |
| LAN IP | 192.168.1.105 | 192.168.1.116 |
| Role | Backend API, frontend, DuckDB, trading | GPU training, ML inference, brain_service |
| Repo path | `C:\Users\Espen\elite-trading-system` | `C:\Users\ProfitTrader\elite-trading-system` |
| Python venv | `backend\venv` | `backend\venv` |
| Alpaca account | Key 1 (portfolio trading) | Key 2 (discovery scanning) |

**Ports**: Backend 8000, Frontend 5173, Brain gRPC 50051, Ollama 11434, Redis 6379

Both IPs DHCP-reserved on AT&T BGW320-505 router (192.168.1.254). Connected via gRPC.

## 12. API Keys (env var names only — values in backend/.env)

| Category | Variables |
|----------|-----------|
| Alpaca | `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL`, `ALPACA_KEY_2`, `ALPACA_SECRET_2` |
| Data Sources | `FINVIZ_API_KEY`, `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `SEC_EDGAR_USER_AGENT` |
| Scrapers | `BENZINGA_EMAIL`, `BENZINGA_PASSWORD`, `SQUEEZEMETRICS_ENABLED` |
| LLM | `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`, `LOCAL_LLM_MODEL` |
| Brain | `BRAIN_SERVICE_URL`, `BRAIN_HOST`, `BRAIN_PORT` |
| Notifications | `SLACK_BOT_TOKEN`, `RESEND_API_KEY`, `TELEGRAM_BOT_TOKEN` |
| Auth | `API_AUTH_TOKEN`, `FERNET_KEY` |
| Trading | `TRADING_MODE`, `KELLY_MAX_ALLOCATION`, `MAX_PORTFOLIO_HEAT`, `MAX_DAILY_TRADES` |

Full template: `backend/.env.example`

## 13. Testing

```bash
cd backend
python -m pytest --tb=short -q       # Run all 666+ tests
python -m pytest tests/test_api.py -v # Run specific test file
```

- **Framework**: pytest with conftest.py monkey-patching DuckDB to in-memory
- **CI/CD**: GitHub Actions — `backend-test` (pytest) + `frontend-build` (npm build) + `e2e-gate`
- **Risk params validated at CI**: Kelly=0.25, Max Risk=0.02, Max Drawdown=0.15

## 14. Common Commands

```powershell
# Backend (Terminal 1 on ESPENMAIN)
cd C:\Users\Espen\elite-trading-system\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Terminal 2 on ESPENMAIN)
cd C:\Users\Espen\elite-trading-system\frontend-v2
npm run dev

# Brain Service (Terminal on ProfitTrader)
cd C:\Users\ProfitTrader\elite-trading-system\brain_service
python server.py

# One-click launchers
.\start-embodier.ps1          # PowerShell
.\launch.bat                  # Windows batch

# Docker (full stack)
docker-compose up -d

# Tests
cd backend && python -m pytest --tb=short -q
```

Or from repo root: `.\start-embodier.ps1` (launcher derives paths from script location).

## 15. Current TODO — Enhancement Plan

See `PLAN.md` for full details (40 issues, 5 phases, 13-18 sessions).

| Phase | Name | Status | Summary |
|-------|------|--------|---------|
| A | Stop the Bleeding | **COMPLETE** | Scout crashes fixed, regime enforcement, circuit breakers, safety gates, DuckDB lock, supervisor |
| B | Unlock Alpha | **COMPLETE** | Regime-adaptive gate, independent short scoring, buy/sell cooldowns, priority queue, limit/TWAP orders, partial fills, DuckDB viability, last_equity heat |
| C | Sharpen the Brain | **COMPLETE** | Weight learner fix, Brier calibration, regime-adaptive thresholds, audit trail, silent alerts |
| D | Continuous Intelligence | **COMPLETE** | Backfill orchestrator, rate limiter registry, DLQ resilience, circuit breakers, session scanner scheduling |
| E | Production Hardening | NOT STARTED | E2E test, emergency flatten, desktop packaging |

### Top Issues Blocking Profits

1. ~~Signal gate threshold 65 filters 20-40% of profitable signals~~ **FIXED** (Phase B — regime-adaptive: 55/65/75)
2. ~~Short signals inverted — `100 - blended` blocks bearish setups~~ **FIXED** (Phase B — independent short composite)
3. ~~Weight learner drops 50%+ of outcomes due to 0.5 confidence floor~~ **FIXED** (Phase C — floor 0.20, regime-stratified, trade_id matching)
4. ~~Only market orders — pays full bid-ask spread~~ **FIXED** (Phase B — market/limit/TWAP by notional)
5. ~~Partial fills never re-executed — 60-80% fill rate silently~~ **FIXED** (Phase B — 3 retries, market remainder)

### What IS Working Well (Do NOT Break)

1. All 35 council agents are real implementations (not stubs)
2. Bayesian weight updates are mathematically correct
3. VETO agents (risk, execution) properly enforced
4. Event-driven architecture achieves sub-1s council latency
5. Kelly criterion implementation is mathematically sound
6. 3-tier LLM router (Ollama → Perplexity → Claude)
7. 950+ tests passing, CI GREEN
8. HITL gate, bracket orders, shadow tracking all working

## 16. Coding Rules for AI Sessions

1. **Read `project_state.md` first** in every new session
2. **Never use yfinance** — removed from requirements, use Alpaca/FinViz/UW
3. **Never add mock/dummy data** — all data via real API endpoints
4. **Council agents must return `AgentVote`** schema from `council/schemas.py`
5. **All frontend data via `useApi()` hook** — never raw fetch or hardcoded values
6. **Python 4-space indentation** — never tabs
7. **Bearer token auth** on all live trading endpoints (`API_AUTH_TOKEN`)
8. **DuckDB connection pooling only** — never raw connections, use `get_conn()` from `data/storage.py`
9. **MessageBus for all inter-service communication** — no direct service-to-service calls for events
10. **Run tests before and after changes** — `cd backend && python -m pytest --tb=short -q`
11. **VETO_AGENTS = {"risk", "execution"}** — no other agent can veto
12. **CouncilGate bridges signals to council** — do NOT bypass
13. **Discovery must be continuous** — no polling-based scanners (Issue #38)
14. **Scouts publish to `swarm.idea`** topic on MessageBus
15. **ONE repo** — all code in Espenator/elite-trading-system
16. **No secrets in committed files** — all keys in `.env` (gitignored)
17. **Dashboard route inside `<Layout />`** wrapper in App.jsx

## 17. Files to Read First

1. `project_state.md` — Current state snapshot (paste into AI sessions)
2. `CLAUDE.md` — This file (auto-loaded by Claude Code)
3. `PLAN.md` — 5-phase enhancement plan with 40 specific issues
4. `REPO-MAP.md` — Complete file inventory
5. `README.md` — Public-facing overview with architecture diagrams

### Key Files for Common Tasks

| Task | Read these files |
|------|-----------------|
| Frontend page fix | `App.jsx`, the page `.jsx`, `useApi.js`, `api.js` |
| Backend API fix | The route in `api/v1/`, the service in `services/` |
| Council/agent fix | `council/runner.py`, `council/arbiter.py`, `council/schemas.py`, agent file |
| Pipeline fix | `council_gate.py`, `signal_engine.py`, `order_executor.py` |
| WebSocket fix | `websocket_manager.py`, `frontend-v2/src/services/websocket.js` |
| Sidebar/layout fix | `Layout.jsx`, `Sidebar.jsx`, `App.jsx` |
| Auth fix | `core/security.py`, `backend/.env` |
| Git push/pull setup | `docs/GIT-PUSH-SETUP.md`, `scripts/set-git-remote-from-token.ps1`, `.github-token` or `GITHUB_TOKEN` |

## Slack Bots

| Bot | App ID | Purpose |
|-----|--------|---------|
| OpenClaw | A0AF9HSCQ6S | Multi-agent swarm notifications |
| TradingView Alerts | A0AFQ89RVEV | Inbound TradingView webhook alerts |

Slack tokens expire every 12h — refresh via Slack API console.
