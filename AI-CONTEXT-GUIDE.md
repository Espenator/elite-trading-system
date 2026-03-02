# AI Context Guide - Elite Trading System

> Strategies for managing AI context limits when working with this codebase.
> This repo has 100+ files. Feeding everything at once causes "lost in the middle" problems.

## 5 Context Management Strategies

### 1. Repo Map First (Always Start Here)

Before any coding session, feed the AI:
1. `REPO-MAP.md` - Full directory tree with annotations
2. `README.md` - Project overview and current status
3. The specific file(s) you want to modify

### 2. Layered Context Loading

Load context in layers based on the task:

| Task Type | Layer 1 (Always) | Layer 2 (Task) | Layer 3 (If needed) |
|-----------|------------------|----------------|---------------------|
| Frontend fix | REPO-MAP.md | The page .jsx | useApi.js, api.js |
| Backend fix | REPO-MAP.md | The route .py | service .py, schema |
| New feature | REPO-MAP.md + README | Mockup image | Related page + API |
| Bug fix | REPO-MAP.md | Error log | Failing file(s) |
| CI fix | REPO-MAP.md | ci.yml | test_api.py, conftest |

### 3. Bundle Files Script

Use `bundle_files.py` to create a single text block of key files:

```bash
python bundle_files.py
```

This bundles the most important files into a copy-pasteable format with syntax highlighting markers. Edit the `FILES_TO_EXTRACT` list in the script to customize.

### 4. Project State Template

Paste this at the start of every AI session:

```
PROJECT: Elite Trading System
STATUS: CI GREEN (22 tests passing)
STACK: FastAPI + React (Vite) + DuckDB
DATA: Alpaca Markets, Unusual Whales, FinViz (NO yfinance)
BRANCH: main
LAST UPDATE: [date]

RULES:
- No mock data in production components
- All frontend data via useApi() hook
- No yfinance anywhere
- 4-space indentation in Python
- Mockups in docs/mockups-v3/images/ are the source of truth for UI

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

**ML Engine** (isolated module):
- `backend/app/modules/ml_engine/` - Self-contained ML pipeline
- Has own config, trainer, feature pipeline

**OpenClaw** (isolated multi-agent system):
- `backend/app/modules/openclaw/` - 8+ sub-modules
- Has own app.py, config.py, main.py entry points

## File Size Quick Reference

| File | Approximate Lines | Notes |
|------|-------------------|-------|
| Patterns.jsx | ~800 | Largest frontend page |
| DataSourcesMonitor.jsx | ~600 | Data source dashboard |
| signal_engine.py | ~500 | Core signal generation |
| kelly_position_sizer.py | ~400 | Position sizing logic |
| test_api.py | ~300 | Main test suite |
| main.py (backend) | ~200 | FastAPI app setup |

## Common Pitfalls

1. **Don't import yfinance** - Removed from requirements.txt, use Alpaca/FinViz/UW
2. **Don't use mock data** - All components wire to real API endpoints
3. **Python indentation** - Use 4 spaces, never tabs. Run `scripts/fix_indentation.py` if issues
4. **Emoji in JSX** - Use BMP unicode only (e.g. `\u21BB` not `\u{1F504}`)
5. **WebSocket** - Keep catch blocks on single lines to avoid parse errors

---

## Advanced Strategies

### 6. XML Tagging (Crucial for Claude)

Claude models parse structured XML tags better than raw code dumps. Wrap context like this:

```xml
<project_goal>
Refactor the legacy codebase to match the new UI mockups and integrate the OpenClaw agent swarm.
</project_goal>

<current_ui_code>
[Paste bundled UI code here]
</current_ui_code>

<agent_logic_code>
[Paste bundled Python agent code here]
</agent_logic_code>

<instructions>
Compare the UI code to the agent logic and write the missing websocket connection between them.
</instructions>
```

### 7. The "Skeleton & Muscle" Workflow

Use the two helper scripts in sequence:

1. **Skeleton**: Send `REPO-MAP.md` tree + explain your goal. Ask the AI: "Based on this tree, which specific files do you need to see?"
2. **Muscle**: AI replies with 3-4 files. Run `python bundle_files.py` (edit the file list) to grab exactly those files. Feed them back.
3. This ensures the AI holds **only** the exact context it needs.

### 8. Watch for "Context Amnesia"

Stop the conversation immediately if the AI:
- Writes generic boilerplate code
- Suggests libraries you don't use (e.g., yfinance)
- Forgets your data sources (Alpaca/FinViz/UW)
- Starts hallucinating variable names or endpoints

**Recovery**: Copy any good code, save to repo, start a new chat with `project_state.md` to re-initialize.

### 9. Divide & Conquer Sessions

Never mix domains in the same prompt:

| Session | Focus | Feed These Files |
|---------|-------|------------------|
| UI Build | Static React pages | Mockup image + page .jsx + components |
| API Wiring | Connect frontend to backend | Finished UI + useApi.js + route .py |
| Agent Swarm | OpenClaw recursive loops | openclaw/ module + API endpoints |
| Hardware | Deploy to dual-PC RTX setup | OpenClaw config + Ollama settings |

### 10. The project_state.md "Save Point"

Maintain `project_state.md` in the repo root. Paste it at the start of **every new chat**:

> "Read this project state document. Acknowledge you understand the architecture, and then I will give you your first task."

See `project_state.md` for the current version.

