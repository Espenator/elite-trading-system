# Project State — Embodier Trader (Elite Trading System)

**For AI agents: Read this file first in every new session.** Paste it into the chat and acknowledge you understand the architecture before taking on tasks.

**Last updated:** March 12, 2026 | **Version:** v5.0.0 | **Phases:** A+B+C+D+E complete

---

## 1. Identity & status

| Item | Value |
|------|--------|
| **Project** | Embodier Trader by Embodier.ai |
| **Repo** | github.com/Espenator/elite-trading-system (PUBLIC — single source of code) |
| **Owner** | Espenator (Asheville, NC) |
| **Version** | v5.0.0 |
| **Status** | Production-ready (~95%); all phases A–E complete |
| **Philosophy** | Embodied Intelligence — the system IS profit; Central Nervous System (CNS) architecture |

---

## 2. Current state summary

### What's working

- **Council**: 35-agent DAG in 7 stages; all agents real implementations; sub-1s latency; CouncilGate bridges signals to council; Bayesian arbiter; weight learner with regime-stratified updates (confidence floor 0.20).
- **Event pipeline**: AlpacaStreamService → market_data.bar → EventDrivenSignalEngine → signal.generated (regime-adaptive threshold) → CouncilGate → council.verdict → OrderExecutor (Gates 2b/2c, Kelly, market/limit/TWAP) → order.submitted → WebSocket → frontend.
- **Backend**: 43 API route files in `backend/app/api/v1/` (364+ endpoints); 72+ services; DuckDB WAL + pooling; Bearer auth fail-closed on live trading.
- **Frontend**: 14 pages in `frontend-v2/src/pages/`; all use `useApi()`; no mock data; pixel-matched to mockups.
- **Tests**: 977+ passing (pytest); CI GREEN.
- **LLM**: 3-tier router (Ollama → Perplexity → Claude); brain_service gRPC wired to hypothesis_agent; Claude reserved for 6 deep-reasoning tasks.
- **Data sources**: 10 active (Alpaca, Unusual Whales, Finviz, FRED, EDGAR, NewsAPI, Benzinga, SqueezeMetrics, Capitol Trades, Senate Stock Watcher); scouts publish to MessageBus.
- **Safety**: 10 circuit breakers enforced (Gate 2c); regime params enforced (Gate 2b); paper/live safety check; emergency flatten with retry + auth.

### What's broken / known issues

| Issue | Severity | Notes |
|-------|----------|--------|
| Agent Command Center (5 template agents) | Low | Not council agents; no daemon lifecycle; P6 backlog. |
| OpenClaw module | Low | Copied Flask/Slack system; mostly dead code; P4 backlog. |
| Some data sources not publishing to MessageBus | Medium | Per architectural review: SEC EDGAR, SqueezeMetrics, Benzinga, Capitol Trades fetch but don't publish; council blind to that data until Phase C wiring. |
| MessageBus DLQ memory-only | Low | 500 entries; no persistent replay. |
| Scout backpressure at 60% queue | Low | May throttle during high-signal periods. |

### What's next

- No blocking phases. Optional: improve ACC/OpenClaw, persistent DLQ, more data sources → MessageBus.
- See `PLAN.md` for full 40-issue history; all critical items resolved.

---

## 3. File path & naming conventions

### Paths (mandatory)

- **Use repo-relative paths only** in docs, comments, and AI context.
- Examples: `backend/app/main.py`, `frontend-v2/src/App.jsx`, `backend/app/council/runner.py`.
- Do **not** use machine-specific absolute paths (e.g. `C:\Users\...`) in shared docs. See `PATH-STANDARD.md` and `PATH-MAP.md` for canonical machine paths.

### Naming

- **API routes**: `backend/app/api/v1/<domain>.py` (e.g. `council.py`, `signals.py`). Prefix in `main.py`: `/api/v1/<path>`.
- **Council agents**: `backend/app/council/agents/<name>_agent.py`; module-level `NAME` and `WEIGHT`; `async def evaluate(features, context) -> AgentVote`.
- **Services**: `backend/app/services/<service_name>.py`; subdirs: `scouts/`, `llm_clients/`, `channel_agents/`, `firehose_agents/`, `integrations/`.
- **Frontend pages**: `frontend-v2/src/pages/<PageName>.jsx`; routes in `App.jsx`; sidebar in `Sidebar.jsx`.
- **Config**: `backend/.env` (gitignored); `backend/.env.example` template. Root `.env.example` for desktop/launchers.

### Test conventions

- **Backend**: `backend/tests/`; pytest; `conftest.py` monkey-patches DuckDB to in-memory. Run: `cd backend && python -m pytest --tb=short -q`.
- **Naming**: `test_<module>_<behavior>.py` or `test_<feature>.py`.
- **CI**: GitHub Actions run pytest + frontend build. Keep tests GREEN (977+).

---

## 4. Key code patterns

### Council agents (all must follow)

```python
# council/agents/<name>_agent.py
from app.council.schemas import AgentVote

NAME = "my_agent"
WEIGHT = 0.8

async def evaluate(features: dict, context: dict = None) -> AgentVote:
    f = features.get("features", features)
    # ... logic ...
    return AgentVote(
        agent_name=NAME,
        direction="buy",   # "buy" | "sell" | "hold"
        confidence=0.75,
        reasoning="...",
        veto=False,
        veto_reason="",
        weight=WEIGHT,
        metadata={},
    )
```

- **VETO_AGENTS** = `{"risk", "execution"}` — only these can set `veto=True`.
- **REQUIRED_AGENTS** = `{"regime", "risk", "strategy"}` — must vote non-hold for any trade.

### Frontend data

- **Always** use `useApi('endpointKey')` from `hooks/useApi.js`. Endpoint keys and URLs live in `frontend-v2/src/config/api.js`. No raw `fetch`, no mock data in production.

### Event pipeline

- `signal.generated` → CouncilGate → `run_council()` → `council.verdict` → OrderExecutor. Do not bypass CouncilGate.
- MessageBus: `get_message_bus()` or `MessageBus.get_instance()`; `publish(topic, payload)`; `subscribe(topic, handler)`.

### DuckDB

- Use `from app.data.storage import get_conn` only. No raw DuckDB connections elsewhere. Thread-safe pooling; double-checked locking in place.

---

## 5. Two-PC architecture

| PC | Hostname | LAN IP | Role |
|----|----------|--------|------|
| PC1 | ESPENMAIN | 192.168.1.105 | Backend API, frontend, DuckDB, trading execution (Alpaca Key 1) |
| PC2 | ProfitTrader | 192.168.1.116 | GPU training, ML inference, brain_service gRPC (Alpaca Key 2) |

- **Ports**: Backend 8000, Frontend 5173, Brain gRPC 50051, Ollama 11434, Redis 6379.
- **Paths**: Repo root on ESPENMAIN `C:\Users\Espen\elite-trading-system`; on ProfitTrader `C:\Users\ProfitTrader\elite-trading-system` (see PATH-MAP.md).

---

## 6. Counts (match README / CLAUDE.md)

| Area | Count |
|------|--------|
| Frontend pages | 14 |
| Backend API route files | 43 (`backend/app/api/v1/`) |
| Backend services | 72+ (incl. subdirs) |
| Council agents | 35 (7-stage DAG) |
| Council orchestration files | 15 |
| Tests | 977+ |

---

## 7. Critical rules (do not break)

1. **No yfinance** — use Alpaca/FinViz/Unusual Whales only.
2. **No mock data** in production; all data via real API/MessageBus.
3. **Council agents** must return `AgentVote` from `council/schemas.py`.
4. **CouncilGate** is the only path from signals to council to OrderExecutor.
5. **New agents** do not get veto power.
6. **Paths** in docs/code: repo-relative only.
7. **Python**: 4-space indentation; DuckDB via `get_conn()` only.
8. **Frontend**: data via `useApi()`; dashboard and all pages inside `<Layout />`.

---

## 8. Where to look for common tasks

| Task | Primary files |
|------|----------------|
| Add/fix API endpoint | `backend/app/api/v1/<domain>.py`, `main.py` (include_router) |
| Add/fix council agent | `council/agents/<name>_agent.py`, `council/runner.py`, `council/agent_config.py`, registry |
| Change trade pipeline | `council_gate.py`, `signal_engine.py`, `order_executor.py`, `message_bus.py` |
| Change frontend page | `frontend-v2/src/pages/<Page>.jsx`, `App.jsx`, `config/api.js`, `useApi.js` |
| Risk/execution gates | `order_executor.py`, `circuit_breaker.py`, `reflexes/` |
| Weights & learning | `weight_learner.py`, `feedback_loop.py`, `arbiter.py` |

---

## 9. Document index

| Document | Purpose |
|----------|---------|
| **project_state.md** (this file) | Single source of truth for AI agents; read first. |
| **CLAUDE.md** | Auto-loaded by Claude; quick reference, rules, paths. |
| **README.md** | Project overview, Quick Start, architecture, key docs. |
| **docs/API-REFERENCE.md** | All 43 API routes by domain (method, path, auth). |
| **docs/COUNCIL-ARCHITECTURE.md** | 35-agent DAG, weights, debate, how to add an agent. |
| **docs/RUNBOOK.md** | Operations: start/stop, health, emergency flatten, API keys. |
| **PATH-STANDARD.md** | Repo-relative path convention. |
| **PATH-MAP.md** | Canonical absolute paths per machine. |
| **PLAN.md** | 5-phase enhancement plan (A–E); historical issues. |
| **REPO-MAP.md** | File inventory. |

---

*End of project_state.md. Acknowledge you have read and understood this before requesting code changes.*
