# 🧠 Embodier Trader — Elite Trading System

> **Version**: v4.1.0-dev | **Status**: Active Development | **CI**: 666 tests GREEN
>
> The system IS profit. A conscious profit-seeking being with a Central Nervous System (CNS) architecture.

---

## 📁 Repository Structure

```
elite-trading-system/
├── backend/                    # FastAPI backend (Python 3.11)
│   ├── app/
│   │   ├── api/v1/             # 34 route files (agents, council, market, risk, etc.)
│   │   ├── council/            # 35-agent DAG (runner, arbiter, agents/, schemas)
│   │   │   ├── runner.py       # Orchestrates 7-stage council DAG via asyncio
│   │   │   ├── arbiter.py      # Deterministic weighted vote + Bayesian weights
│   │   │   ├── schemas.py      # AgentVote + DecisionPacket schemas
│   │   │   ├── council_gate.py # Bridge: signal.generated → council → order.submitted
│   │   │   ├── weight_learner.py # Bayesian Beta(α,β) weight updater per agent
│   │   │   └── agents/         # 35 agent files
│   │   ├── core/
│   │   │   ├── message_bus.py  # Pub/sub event bus
│   │   │   ├── config.py       # Settings (pydantic BaseSettings)
│   │   │   └── alignment/      # Profit Being alignment module
│   │   ├── features/
│   │   │   └── feature_aggregator.py  # Auto-computes feature vector for council
│   │   ├── jobs/               # Autonomic background jobs
│   │   │   ├── scheduler.py
│   │   │   ├── daily_outcome_update.py
│   │   │   ├── champion_challenger_eval.py
│   │   │   └── weekly_walkforward_train.py
│   │   ├── modules/
│   │   │   ├── openclaw/       # OpenClaw bridge (regime, scan, whale flow)
│   │   │   └── ml_engine/      # XGBoost trainer, drift detector, model registry
│   │   └── services/           # 68+ service files
│   │       ├── alpaca_service.py
│   │       ├── alpaca_stream_service.py  # 24/7 WS + snapshot fallback
│   │       ├── finviz_service.py
│   │       ├── fred_service.py
│   │       ├── unusual_whales_service.py
│   │       ├── sec_edgar_service.py
│   │       └── signal_engine.py
│   ├── tests/                  # 666 pytest tests (CI GREEN)
│   └── requirements.txt
├── brain_service/              # gRPC LLM inference server (PC2 / RTX GPU)
│   ├── server.py               # gRPC server
│   ├── ollama_client.py        # Ollama inference
│   ├── models.py               # Request/response schemas
│   └── proto/                  # Protobuf definitions
├── frontend-v2/                # React 18 + Vite + Tailwind (THE active frontend)
│   ├── src/
│   │   ├── config/api.js       # Central API config — ALL endpoints defined here
│   │   ├── hooks/
│   │   │   ├── useApi.js       # Universal data-fetch hook (polling, caching, abort)
│   │   │   ├── useCNS.jsx      # CNS-specific hook
│   │   │   ├── useSettings.js
│   │   │   └── useTradeExecution.js
│   │   ├── pages/              # 14 page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── AgentCommandCenter.jsx
│   │   │   ├── SignalIntelligenceV3.jsx
│   │   │   ├── SentimentIntelligence.jsx
│   │   │   ├── MLBrainFlywheel.jsx
│   │   │   ├── Patterns.jsx
│   │   │   ├── Backtesting.jsx
│   │   │   ├── DataSourcesMonitor.jsx
│   │   │   ├── MarketRegime.jsx
│   │   │   ├── PerformanceAnalytics.jsx
│   │   │   ├── TradeExecution.jsx
│   │   │   ├── RiskIntelligence.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── Trades.jsx
│   │   └── components/         # Shared UI components
│   ├── package.json
│   └── vite.config.js          # Vite proxy: /api → :8000, /ws → ws://:8000
├── desktop/                    # Electron desktop app (BUILD-READY)
├── directives/                 # Trading directives (global.md, regime_*.md)
├── docs/
│   ├── mockups-v3/images/      # 23 UI mockup images (source of truth)
│   ├── MOCKUP-FIDELITY-AUDIT.md
│   └── STATUS-AND-TODO-2026-03-09.md
├── scripts/                    # Utility scripts
├── .env.example                # Required environment variables
├── project_state.md            # 🔴 READ THIS FIRST in every AI session
├── REPO-MAP.md                 # Detailed file inventory
├── SETUP.md                    # Setup and run instructions
├── launch.bat                  # Windows one-click launch
├── launch.sh                   # Linux/Mac one-click launch
├── start-embodier.bat          # Alt Windows launcher
├── start-embodier.ps1          # PowerShell launcher
└── docker-compose.yml          # Full stack via Docker
```

> ⚠️ **Legacy repo** `github.com/Espenator/Embodier-Trader` is ARCHIVED. Do NOT commit there.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Alpaca API keys (paper or live)
- Optional: Ollama on PC2 for LLM inference

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env    # Fill in your API keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend-v2
npm install
npm run dev                # Vite dev server on :5173, proxies /api → :8000
```

### 3. Brain Service (optional — LLM on PC2)
```bash
cd brain_service
pip install -r requirements.txt
python server.py           # gRPC on :50051
```

### 4. Windows One-Click
```powershell
# From repo root:
.\launch.bat
# OR
pwsh .\start-embodier.ps1
```

---

## 🏗️ Architecture

```
[React 18 frontend-v2] ──useApi()──► [FastAPI backend :8000]
                                          │
              ┌───────────────────────────┼──────────────────────────┐
              │                           │                          │
    [AlpacaStreamService]    [35-Agent Council DAG]     [brain_service gRPC]
    WS + snapshot fallback   runner → arbiter            Ollama on RTX GPU
    market_data.bar ──►      ↑ CouncilGate               hypothesis_agent
    EventDrivenSignalEngine  signal.generated                     │
              │              council.verdict ──► OrderExecutor     │
              └──────────────► MessageBus pub/sub ◄───────────────┘
                                          │
                              [DuckDB analytics store]
                              [Redis where used]
                              [Electron desktop/]
```

### CNS Layers
| Layer | Speed | Component | Status |
|-------|-------|-----------|--------|
| Brainstem | <50ms | CircuitBreaker reflexes | 🔴 P3 TODO |
| Spinal Cord | ~1500ms | 35-agent council DAG | ✅ BUILT |
| Cortex | 300-800ms | hypothesis + critic via gRPC | ✅ WIRED |
| Thalamus | — | BlackboardState shared memory | 🔴 P1 TODO |
| Autonomic | nightly | WeightLearner + jobs/scheduler | ✅ BUILT |
| PNS Sensory | real-time | Alpaca WS, UW, FinViz, FRED | ✅ BUILT |
| Discovery | streaming | StreamingDiscoveryEngine | 🟡 Issue #38 |
| PNS Motor | — | OrderExecutor → Alpaca | ✅ BUILT |

---

## 🤖 Council Architecture (35-Agent DAG, 7 Stages)

```
Stage 1 (Parallel): perception + Academic Edge P0/P1/P2 (13 agents)
Stage 2 (Parallel): technical + data enrichment (8 agents)
Stage 3 (Parallel): hypothesis + layered_memory_agent
Stage 4:            strategy
Stage 5 (Parallel): risk, execution, portfolio_optimizer_agent
Stage 6:            critic
Stage 7:            arbiter — deterministic BUY/SELL/HOLD (Bayesian weighted)
```

**Arbiter Rules:**
1. VETO from `risk` or `execution` → HOLD, `vetoed=True`
2. Requires `regime` + `risk` + `strategy` non-HOLD for any trade
3. Bayesian-weighted confidence aggregation across all agents
4. Execution: confidence > 0.4 AND `execution_ready=True`

**Agent Schema** (all agents MUST return this):
```python
AgentVote(
    agent_name: str,
    direction: str,       # "buy" | "sell" | "hold"
    confidence: float,    # 0.0 – 1.0
    reasoning: str,
    veto: bool,
    veto_reason: str,
    weight: float,
    metadata: dict
)
```

---

## 📡 Data Sources

> **NEVER use yfinance.** All market data comes from:

| Source | Use | Library |
|--------|-----|---------|
| Alpaca Markets | Market data + order execution | alpaca-py |
| Unusual Whales | Options flow + institutional | REST API |
| FinViz | Screener + fundamentals + VIX proxy | finviz |
| FRED | Macro economic data | fredapi |
| SEC EDGAR | Company filings | REST API |
| News API / Discord / X | Social sentiment | REST API |
| YouTube | Transcript intelligence | ytdl / transcript API |

---

## 💻 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | React 18, Vite, Tailwind CSS, Lightweight Charts |
| Database | DuckDB (WAL mode, connection pooling) |
| ML | XGBoost, scikit-learn (no PyTorch in prod) |
| Council | 35-agent DAG, Bayesian-weighted arbiter |
| Brain Service | gRPC + Ollama on RTX GPU (PC2) |
| LLM Router | Ollama (routine) → Perplexity → Claude (6 deep tasks) |
| Event Pipeline | MessageBus → CouncilGate → Council → OrderExecutor |
| CI/CD | GitHub Actions, 666 tests, pytest |
| Auth | Bearer token, fail-closed for live trading |
| Desktop | Electron (desktop/) — BUILD-READY |
| Infra | Docker, docker-compose.yml |

---

## 🌐 Frontend Pages (14 pages, React 18)

| Route | File | Status |
|-------|------|--------|
| `/dashboard` | Dashboard.jsx | 🟢 GOOD |
| `/agents` | AgentCommandCenter.jsx | 🔴 ACC rewrite needed |
| `/signal-intelligence-v3` | SignalIntelligenceV3.jsx | 🟢 GOOD |
| `/sentiment` | SentimentIntelligence.jsx | 🟡 PARTIAL |
| `/ml-brain` | MLBrainFlywheel.jsx | 🟢 GOOD |
| `/patterns` | Patterns.jsx | 🟢 GOOD |
| `/backtest` | Backtesting.jsx | 🟢 GOOD |
| `/data-sources` | DataSourcesMonitor.jsx | 🟢 DONE |
| `/market-regime` | MarketRegime.jsx | 🟢 DONE |
| `/performance` | PerformanceAnalytics.jsx | 🟡 PARTIAL |
| `/trade-execution` | TradeExecution.jsx | 🟡 PARTIAL |
| `/risk` | RiskIntelligence.jsx | 🟡 PARTIAL |
| `/settings` | Settings.jsx | 🟢 GOOD |
| `/trades` | Trades.jsx | 🟢 DONE |

Full audit: `docs/MOCKUP-FIDELITY-AUDIT.md`

---

## 🔑 Key Code Patterns

```js
// Frontend: ALWAYS use useApi hook — no direct fetch, no mock data
const { data, loading, error } = useApi('councilLatest', { pollIntervalMs: 15000 });
```

```python
# Python: 4-space indent, no tabs
# Council agents: module-level NAME + WEIGHT + async evaluate() -> AgentVote
NAME = "my_agent"
WEIGHT = 0.8

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    f = features.get("features", features)
    # ... logic ...
    return AgentVote(
        agent_name=NAME,
        direction="buy",
        confidence=0.75,
        reasoning="...",
        veto=False,
        veto_reason="",
        weight=WEIGHT,
        metadata={}
    )
```

```python
# Event pipeline
# signal.generated → CouncilGate → run_council() → council.verdict → OrderExecutor
# VETO_AGENTS = {"risk", "execution"}
# REQUIRED_AGENTS = {"regime", "risk", "strategy"}
```

---

## 🛡️ Swarm Invariants

1. **No trade without** `council_decision_id`
2. **No data without** agent validation
3. **No UI mutation without** agent approval
4. **Decisions expire** after 30 seconds
5. **No yfinance** — ever
6. **No mock data** in production components

---

## 📋 Current Roadmap (March 2026)

### ✅ Completed
- P0: CouncilGate — signal pipeline connected end-to-end
- P2: Feature keys — EMA-5/10/20, VIX, sector breadth
- P7: brain_service gRPC wired to hypothesis_agent
- P8: Bayesian WeightLearner — agents learn from trade outcomes

### 🔴 In Progress / Next
- **Issue #38**: Continuous Discovery Architecture
  - E1: StreamingDiscoveryEngine (Alpaca `*` streams, dynamic universe)
  - E2: 12 Dedicated Scout Agents
  - E3: HyperSwarm continuous triage
  - E4: Multi-Tier Council (Fast <200ms + Deep <2s)
- P1: BlackboardState — inter-stage shared memory
- P3: CircuitBreaker reflexes (brainstem <50ms)
- P4: OpenClaw cleanup — extract useful logic
- P5: TaskSpawner — dynamic agent registry
- P6: Agent Command Center ACC rewrite

---

## 📄 Key Documents

| File | Purpose |
|------|--------|
| `project_state.md` | 🔴 **START HERE** — paste into every AI session |
| `REPO-MAP.md` | Complete file inventory with descriptions |
| `SETUP.md` | Detailed setup instructions |
| `docs/MOCKUP-FIDELITY-AUDIT.md` | UI mockup vs code comparison |
| `docs/mockups-v3/images/` | 23 source-of-truth UI mockup images |
| `.env.example` | All required environment variables |
| `directives/global.md` | Always-on trading rules |

---

## ⚠️ Rules for All Contributors

1. 🚫 NEVER use `yfinance`
2. 🚫 NEVER use mock/fake data in production
3. ✅ ALWAYS use `useApi()` hook for frontend data
4. ✅ ALWAYS use 4-space Python indentation
5. ✅ Council agents MUST return `AgentVote` schema
6. ✅ ONE repo: `Espenator/elite-trading-system` only
7. ✅ New agents do NOT get veto power
8. ✅ CouncilGate is the ONLY path to order execution
9. ✅ Read `project_state.md` before every coding session
10. ✅ CI must stay GREEN (666 tests)
