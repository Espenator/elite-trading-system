# Path standard — Embodier Trader

**Single source of truth for file paths** across Claude, Cursor, Comet, Perplexity, ESPENMAIN, ProfitTrader, and the git repo.

**Repo**: [github.com/Espenator/elite-trading-system](https://github.com/Espenator/elite-trading-system)

---

## 1. Golden rule

**In all shared docs, code comments, and AI context: use paths relative to the repo root.**

- ✅ `backend/app/main.py`
- ✅ `frontend-v2/src/App.jsx`
- ✅ `backend/app/council/runner.py`
- ❌ `C:\Users\Espen\elite-trading-system\backend\...`

**Repo root** = the directory that contains `backend/`, `frontend-v2/`, `CLAUDE.md`. In docs we use repo-relative paths only; see the canonical machine table below when you need an absolute path.

---

## 2. Logical locations (repo-relative)

Use these names in docs and when talking to AI. All are relative to repo root.

| Logical name    | Path from repo root        | Purpose                    |
|-----------------|----------------------------|----------------------------|
| **backend**     | `backend/`                 | FastAPI app, venv, tests   |
| **frontend**    | `frontend-v2/`             | React/Vite app             |
| **council**     | `backend/app/council/`    | 35-agent DAG, runner, arbiter |
| **api**         | `backend/app/api/v1/`      | REST route modules         |
| **services**    | `backend/app/services/`   | Business logic             |
| **brain_service** | `brain_service/`        | gRPC + Ollama              |
| **desktop**     | `desktop/`                 | Electron app               |
| **docs**        | `docs/`                    | Documentation              |
| **scripts**     | `scripts/`                 | Utility scripts            |
| **directives**  | `directives/`              | Trading rules (global.md)  |
| **data**        | `data/`                    | DuckDB, local data         |

Examples:
- “Backend entry” → `backend/app/main.py`
- “Council runner” → `backend/app/council/runner.py`
- “Frontend config” → `frontend-v2/src/config/api.js`

---

## 3. Instructions for AI (Claude, Cursor, Comet, Perplexity)

When editing or referring to files:

1. **Assume workspace root = repo root.** The path you are given (e.g. in Cursor) is the repo root; don’t hardcode `C:\Users\...` or `/Users/...`.
2. **Use repo-relative paths** in suggestions, comments, and docs: `backend/...`, `frontend-v2/...`.
3. **In Quick Start / run commands**, use “from repo root” and then `cd backend`, `cd frontend-v2`, etc., or use `.\backend\...` so it works regardless of where the repo is cloned.

---

## 3b. CRITICAL: Primary vs stale copy (ESPENMAIN / this machine)

On this machine there are **two** clones of the repo. Only the **primary** must be used to run services.

| Copy | Path | Use |
|------|------|-----|
| **PRIMARY** | `C:\Users\Espen\elite-trading-system` | **Use this.** Backend → 8000, Frontend → 5173. All dev and service starts. |
| **STALE** | `C:\Users\Espen\Dev\elite-trading-system` | **Do not run services from here.** Causes port conflicts (8004/5176), DuckDB locks, and fights the primary. |

- **Do NOT** start backend, frontend, or any dev servers from the Dev copy.
- **Do NOT** run both copies at the same time.
- When starting services, use **only** the primary path: `C:\Users\Espen\elite-trading-system\backend` (port 8000) and `C:\Users\Espen\elite-trading-system\frontend-v2` (port 5173).

---

## 4. Canonical machine paths (for humans and scripts)

When you need an absolute path (e.g. terminal, shortcuts), use the canonical path for that machine. All documentation uses these consistently.

| Machine      | Canonical repo root |
|-------------|----------------------|
| **ESPENMAIN** (PC1) | `C:\Users\Espen\elite-trading-system` |
| **ProfitTrader** (PC2) | `C:\Users\ProfitTrader\elite-trading-system` |
| **Other / CI** | Path where the repo is cloned (e.g. `$env:USERPROFILE\elite-trading-system`) |

- Scripts that need the repo root should derive it from script location (e.g. parent of `scripts/`) or use an env var `REPO_ROOT`; fallback for ESPENMAIN is `C:\Users\Espen\elite-trading-system`.

---

## 5. Where path info lives

| Document        | Role |
|-----------------|------|
| **PATH-STANDARD.md** (this file) | Convention and logical names. No absolute paths. |
| **PATH-MAP.md**                 | Canonical full paths per machine (same as table in §4). |
| **CLAUDE.md**                   | Points here; Quick Start uses repo-relative and “from repo root”. |
| **README.md** / **project_state.md** | Use repo-relative paths; one short “Machine paths” table if needed. |

---

## 6. Scripts and env

- **Launchers** (e.g. `start-embodier.ps1`): already use `$Root = Split-Path -Parent $MyInvocation.MyCommand.Path` and `Join-Path $Root "backend"` — no absolute path to repo.
- **Other scripts** that need the repo: take repo root as parameter, or assume they are run from repo root, or read `REPO_ROOT` from env.
- Optional: set `REPO_ROOT` in your shell profile or environment if scripts need an absolute repo path; otherwise they derive it from script location (e.g. parent of `scripts/`).

---

*Last updated: March 2026. Update this file when adding new top-level dirs or changing the convention.*
