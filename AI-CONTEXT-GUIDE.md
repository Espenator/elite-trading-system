# AI Context Guide - Embodier Trader (Elite Trading System)
> Strategies for managing AI context limits when working with this codebase.
> This repo has 100+ files. Feeding everything at once causes "lost in the middle" problems.
> Last updated: March 5, 2026 — v3.2.0

## Quick Start for AI Sessions

**Always start every new AI chat by pasting `project_state.md` and saying:**
> "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."

This gives the AI the full architecture, rules, and current state in one shot.

## 5 Context Management Strategies

### 1. Repo Map First (Always Start Here)

Before any coding session, feed the AI:
1. `project_state.md` - Full project state, architecture, rules, and roadmap
2. `README.md` - Project overview and current status
3. The specific file(s) you want to modify

### 2. Layered Context Loading

Load context in layers based on the task:

| Task Type | Layer 1 (Always) | Layer 2 (Task) | Layer 3 (If needed) |
|-----------|------------------|----------------|---------------------|
| Frontend fix | project_state.md | The page .jsx | useApi.js, api.js |
| Backend fix | project_state.md | The route .py | service .py, schema |
| Council fix | project_state.md | The agent .py | arbiter.py, schemas.py, runner.py |
| Pipeline fix | project_state.md | council_gate.py | signal_engine.py, order_executor.py |
| New feature | project_state.md + README | Mockup image | Related page + API |
| Bug fix | project_state.md | Error log | Failing file(s) |
| CI fix | project_state.md | ci.yml | test_api.py, conftest |

### 3. Bundle Files Script

Use `bundle_files.py` to create a single text block of key files:

```bash
python bundle_files.py
```

This bundles the most important files into a copy-pasteable format with syntax highlighting markers. Edit the `FILES_TO_EXTRACT` list in the script to customize.

### 4. Project State Template

Paste this at the start of every AI session:

```
PROJECT: Embodier Trader (Elite Trading System)
VERSION: 3.2.0
STATUS: CI GREEN (151 tests passing)
STACK: FastAPI + React (Vite) + DuckDB
DATA: Alpaca Markets, Unusual Whales, FinViz, FRED, SEC EDGAR (NO yfinance)
COUNCIL: 13-agent DAG in 7 stages with Bayesian weight learning
PIPELINE: AlpacaStream -> SignalEngine -> CouncilGate -> 13-Agent Council -> OrderExecutor -> Alpaca
BRANCH: main
LAST UPDATE: [date]
RULES:
  - No mock data in production components
  - All frontend data via useApi() hook
  - No yfinance anywhere
  - 4-space indentation in Python
  - Council agents MUST return AgentVote schema
  - VETO_AGENTS = {"risk", "execution"} only
  - CouncilGate bridges signals to council — do NOT bypass
  - ONE repo: Espenator/elite-trading-system
CURRENT TASK: [describe what you want to do]
FILES TO MODIFY: [list specific files]
```

### 5. Domain Boundaries

The codebase has clear boundaries. Stay within one domain per session:

**Frontend Pages** (each self-contained):
- `frontend-v2/src/pages/*.jsx` - Each page is independent
- Data comes from `useApi('endpoint')` hook
- UI components from `components/ui/`

**Backend API Routes** (each maps to a service):
- `backend/app/api/v1/*.py` - Route handlers
- `backend/app/services/*.py` - Business logic
- Pattern: route calls service, service calls external API

**Council** (13-agent DAG + intelligence layer):
- `backend/app/council/agents/*.py` - 13 agent modules
- `backend/app/council/runner.py` - 7-stage DAG orchestrator
- `backend/app/council/arbiter.py` - Deterministic arbiter with Bayesian weights
- `backend/app/council/council_gate.py` - Pipeline bridge (signal -> council -> order)
- `backend/app/council/weight_learner.py` - Bayesian self-learning weights
- `backend/app/council/schemas.py` - AgentVote + DecisionPacket

**Event Pipeline** (real-time trading):
- `backend/app/core/message_bus.py` - Pub/sub event bus
- `backend/app/services/signal_engine.py` - Signal scoring
- `backend/app/services/order_executor.py` - Council-controlled order execution
- `backend/app/services/trade_stats_service.py` - Real DuckDB stats for Kelly

**ML Engine** (isolated module):
- `backend/app/modules/ml_engine/` - Self-contained ML pipeline
- Has own config, trainer, feature pipeline

**OpenClaw** (legacy — to be cleaned up):
- `backend/app/modules/openclaw/` - Dead code, needs P4 cleanup

## File Size Quick Reference

| File | Approximate Lines | Notes |
|------|-------------------|-------|
| Patterns.jsx | ~800 | Largest frontend page |
| DataSourcesMonitor.jsx | ~600 | Data source dashboard |
| signal_engine.py | ~500 | Core signal generation |
| kelly_position_sizer.py | ~400 | Position sizing logic |
| order_executor.py | ~350 | Council-controlled order execution |
| test_api.py | ~300 | Main test suite |
| main.py (backend) | ~200 | FastAPI app setup |
| arbiter.py | ~200 | Deterministic arbiter + Bayesian weights |
| council_gate.py | ~100 | Signal -> Council -> Order bridge |
| weight_learner.py | ~80 | Bayesian alpha/beta learning |

## Common Pitfalls

1. **Don't import yfinance** - Removed from requirements.txt, use Alpaca/FinViz/UW
2. **Don't use mock data** - All components wire to real API endpoints
3. **Python indentation** - Use 4 spaces, never tabs
4. **Don't bypass CouncilGate** - All signals must go through the 13-agent council
5. **Agent votes** - Must return AgentVote schema from council/schemas.py
6. **Veto power** - Only risk and execution agents can veto
7. **Emoji in JSX** - Use BMP unicode only (e.g. `\u21BB` not `\u{1F504}`)
8. **WebSocket** - Keep catch blocks on single lines to avoid parse errors
9. **GitHub editor** - Use clipboard paste method for multi-line edits to avoid auto-indent issues

---

## Advanced Strategies

### 6. XML Tagging (Crucial for Claude)

Claude models parse structured XML tags better than raw code dumps. Wrap context like this:

```xml
<project_goal>
Refactor the council arbiter to use Bayesian weights from WeightLearner.
</project_goal>

<council_code>
[Paste arbiter.py, weight_learner.py, schemas.py here]
</council_code>

<pipeline_code>
[Paste council_gate.py, order_executor.py here]
</pipeline_code>

<instructions>
Update the arbiter to query WeightLearner for current weights before aggregation.
</instructions>
```

### 7. The "Skeleton & Muscle" Workflow

Use the two helper scripts in sequence:

1. **Skeleton**: Send `project_state.md` + explain your goal. Ask the AI: "Based on this project state, which specific files do you need to see?"
2. **Muscle**: AI replies with 3-4 files. Run `python bundle_files.py` (edit the file list) to grab exactly those files. Feed them back.
3. This ensures the AI holds **only** the exact context it needs.

### 8. Watch for "Context Amnesia"

Stop the conversation immediately if the AI:
- Writes generic boilerplate code
- Suggests libraries you don't use (e.g., yfinance)
- Forgets your data sources (Alpaca/FinViz/UW)
- Starts hallucinating variable names or endpoints
- Suggests bypassing the council for direct order execution
- Proposes mock data or hardcoded values

**Recovery**: Copy any good code, save to repo, start a new chat with `project_state.md` to re-initialize.

### 9. Divide & Conquer Sessions

Never mix domains in the same prompt:

| Session | Focus | Feed These Files |
|---------|-------|------------------|
| UI Build | Static React pages | Mockup image + page .jsx + components |
| API Wiring | Connect frontend to backend | Finished UI + useApi.js + route .py |
| Council | Agent intelligence | council/ agents + arbiter + schemas |
| Pipeline | Event flow | council_gate.py + signal_engine.py + order_executor.py |
| Brain Service | LLM inference | brain_client.py + hypothesis_agent.py + critic_agent.py |
| Hardware | Deploy to dual-PC RTX setup | Docker config + Ollama settings |

### 10. The project_state.md "Save Point"

Maintain `project_state.md` in the repo root. Paste it at the start of **every new chat**:

> "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."

See `project_state.md` for the current version.
