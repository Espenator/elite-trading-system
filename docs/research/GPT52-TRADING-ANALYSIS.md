I can’t literally “audit every file in the git repo” and directly commit updates from this sub-agent context (I don’t have repository-wide read/write tooling here). What I *can* do right now is: (1) translate the council guidance into a concrete, executable audit + stabilization program, and (2) give you **copy‑paste ready** replacement content for `README.md`, `backend/README.md`, plus new audit/development-plan docs that Oleh can follow tomorrow morning.

Below is exactly what to put in the repo (and what to delete/replace), aligned to the council’s hard-gate sequence.

---

# A) What to do in Git *now* (branch + freeze)

**Policy:** Feature freeze until the audit gates are green.

1) Keep **PR #23 open** (do not merge).
2) Create audit branch off the PR head:

```bash
git fetch origin
git checkout feat/event-driven-messagebus
git pull
git checkout -b audit/2026-03-01-stabilization
git push -u origin audit/2026-03-01-stabilization
```

3) On GitHub: open a new PR  
`audit/2026-03-01-stabilization → main` (or → `feat/event-driven-messagebus` if you want to land audit fixes into the feature branch first).

---

# B) Add these 2 new files (copy/paste)

## 1) `docs/AUDIT-2026-03-01.md` (new)

```md
# AUDIT — 2026-03-01 Stabilization (Feature Freeze)

This repo is in a stabilization window. **No new features** may be merged until the hard gates pass.

## Scope
- Backend bootability (`uvicorn app.main:app`)
- `/health` returns event pipeline status without traceback
- CI green: backend tests + frontend build
- Safety-by-default: shadow mode + explicit live-trading acknowledgement
- Documentation truthfulness: remove stale claims, document actual run steps

## Branch Strategy
- Keep PR #23 open (event-driven pipeline).
- All stabilization work happens on: `audit/2026-03-01-stabilization`.
- Merge order:
  1) Audit branch → main (only after gates pass)
  2) Then merge PR #23 → main
  3) Then ship next features one-at-a-time (RiskShield or frontend WS hook)

## HARD GATES (must pass in order)

### Gate 1 — Backend compile/import + boot + /health
Run locally:

```bash
cd backend

python -m venv .venv
source .venv/bin/activate  # mac/linux
# .venv\Scripts\activate   # windows

pip install -r requirements.txt

# 1) Compile all python
python -m compileall app

# 2) Boot server
uvicorn app.main:app --reload
```

Validate endpoints:

```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/docs >/dev/null
```

PASS if:
- `compileall` succeeds (no SyntaxError/IndentationError)
- uvicorn runs without traceback
- `/health` returns JSON including event pipeline keys

### Gate 2 — CI green (pytest + frontend build)
Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend-v2
npm ci
npm run build
```

PASS if both succeed.

### Gate 3 — Safety-by-default
Requirements:
- Trading auto-execute defaults OFF.
- Paper trading is default.
- Live trading requires explicit acknowledgement env var.

PASS if:
- Without env vars, system is in SHADOW mode and does not submit real orders.
- Attempting live trading without acknowledgement hard-fails (startup or order submission).

### Gate 4 — Docs truth audit + final development plan
Requirements:
- README and backend/README reflect current reality (no contradictory claims).
- Add clear “Tomorrow AM Plan (Oleh)” steps.
- Document env vars for event-driven pipeline and OrderExecutor.

PASS if a new dev can:
- Install deps
- Start backend
- Start frontend
- Understand how to run safe “shadow” mode vs paper execute

## Deliverables
- Fix syntax/indent/import errors
- Minimal regression tests for MessageBus + OrderExecutor gates
- Updated docs: `README.md`, `backend/README.md`, plus `docs/DEVELOPMENT-PLAN-OLEH-2026-03-02.md`

## Known Risk Areas to Audit
- “Two engines problem”: legacy polling loops vs event-driven pipeline (avoid duplicated signals/orders).
- Async lifecycle correctness: start/stop ordering, orphan tasks.
- Topic schema consistency: `market_data.bar`, `signal.generated`, `order.*`.
- Secret hygiene: no keys in logs, `.env` not committed.
```

## 2) `docs/DEVELOPMENT-PLAN-OLEH-2026-03-02.md` (new)

```md
# Oleh — Development Plan (Monday AM) — 2026-03-02

## Goal
Stabilize repo and make it bootable + CI green. **No features** until the audit gates pass.

## 0) Non-negotiables
- Work only on `audit/2026-03-01-stabilization`
- Do not merge PR #23 until audit is complete
- Default mode must remain **SHADOW** (no real orders)

## 1) Checkout + Baseline
```bash
git fetch origin
git checkout audit/2026-03-01-stabilization
git pull
```

## 2) Backend Gate 1 (compile + boot)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m compileall app
uvicorn app.main:app --reload
```

If compile fails:
- Fix IndentationError/tab-space mixing first.
- Fix missing imports / optional deps next.
- Re-run `compileall` until clean.

Validate:
```bash
curl -s http://localhost:8000/health | jq .
```

PASS when `/health` returns JSON and no traceback spam.

## 3) Backend Gate 2 (pytest)
```bash
cd backend
pytest -q
```
If failing:
- Fix tests or adjust brittle assumptions
- Add minimal tests for new core: MessageBus and OrderExecutor safety gates

## 4) Frontend Gate 2 (build)
```bash
cd frontend-v2
npm ci
npm run build
```

## 5) Safety Gate 3 (must be true before any “AUTO” mode)
Confirm these are true:
- Default `AUTO_EXECUTE_TRADES=false`
- `TRADING_MODE` defaults to `paper`
- Live trading requires `I_UNDERSTAND_LIVE_TRADING=true`

## 6) Docs Gate 4 (truth + next steps)
Update:
- `README.md`
- `backend/README.md`
- Ensure they match actual behavior on this branch.

## Definition of Done (tomorrow)
- compileall PASS
- uvicorn boots
- /health OK
- pytest OK
- frontend build OK
- docs updated
- PR #23 still unmerged
```

---

# C) Replace/Rewrite the top of `README.md` (delete stale status)

Your current root README contains a lot of historical claims that drift quickly (and some are contradictory across files). Replace the top “status block” with a **truthy, audit-oriented header**.

## Replace the very top of `README.md` with this

```md
# Elite Trading System (Espenator)

Embodier.ai full-stack trading intelligence platform (React + FastAPI) with an event-driven backend pipeline.

## Current Status (Truth-Checked, 2026-03-01)

We are in a **feature freeze** while stabilizing the repo.

### What exists (implemented)
- Event-driven backend plumbing on PR #23 / branch `feat/event-driven-messagebus`:
  - MessageBus (pub/sub)
  - Alpaca WebSocket streaming service
  - EventDrivenSignalEngine (bar → signal)
  - OrderExecutor (signal → order events; SHADOW by default)
- Frontend: `frontend-v2/` React app with multiple pages wired to REST endpoints.

### What is NOT yet guaranteed
- End-to-end backend boot + CI green on `main` (stabilization in progress).
- Real-time UI updates via WebSocket hooks (not yet the default UX path).

### The Plan
All stabilization work happens on: `audit/2026-03-01-stabilization`
See:
- `docs/AUDIT-2026-03-01.md`
- `docs/DEVELOPMENT-PLAN-OLEH-2026-03-02.md`

## Safety Defaults (Non-Negotiable)
- `AUTO_EXECUTE_TRADES` defaults to `false` (SHADOW mode).
- Paper trading is the default mode.
- Live trading must require explicit acknowledgement (see backend README).
```

### Also remove/adjust these outdated README claims
Search & delete/reword:
- Any absolute statements like “Backend has NEVER been started” (replace with “not yet guaranteed/verified on main; stabilization in progress”).
- Any CI status claims that you cannot guarantee are currently true.
- Any mention of yfinance if it’s removed (align with backend/requirements).

---

# D) Update `backend/README.md` (remove stale deps + add safety rail contract)

Your backend README currently lists **yFinance** in “Data Sources”. If yfinance was removed, that’s stale. Also add a safety section for live trading acknowledgement.

## Patch-style replacement sections

### 1) In “Tech Stack / Data Sources” remove yFinance and add the event-driven pieces

Replace the data sources bullets with:

```md
## Data Sources
- Alpaca Markets (REST + WebSocket via alpaca-py)
- Finviz (screener)
- Unusual Whales (options flow)
- FRED (macro)
- SEC EDGAR (filings)

Note: yfinance is not a required dependency in the current stabilized path.
```

### 2) Add a new section: “Event-Driven Pipeline (MessageBus)”

Add:

```md
## Event-Driven Pipeline (MessageBus)

Backend startup initializes an event-driven pipeline (when enabled/available):

AlpacaStreamService → MessageBus → EventDrivenSignalEngine → OrderExecutor → AlpacaService

Core topics:
- `market_data.bar`
- `signal.generated`
- `order.submitted`
- `order.filled`
- `order.cancelled`

Health endpoint:
- `GET /health` includes `event_pipeline` metrics/status.
```

### 3) Add a new section: “Execution Safety (Shadow / Paper / Live)”

Add:

```md
## Execution Safety (Shadow / Paper / Live)

Default behavior must be SAFE:
- Shadow execution is the default (`AUTO_EXECUTE_TRADES=false`).
- Trading mode defaults to paper.

Recommended live-trading interlock (must be enforced before enabling live):
- `TRADING_MODE=live` requires `I_UNDERSTAND_LIVE_TRADING=true`
- Otherwise startup or order submission should hard-fail.
```

---

# E) “Audit every file” realistically: how Oleh should do it tomorrow

You asked to audit every file; doing that manually is slow. The correct approach is **automated scanning + targeted review**:

Add this checklist to the audit doc or to an issue:

### Repo-wide truth scan commands
From repo root:

```bash
# Find stale dependencies/claims
rg -n "yfinance|torch|PyTorch|paper-api|never been started|CI is PASSING|CI is FAILING" .

# Find dangerous execution toggles / live trading
rg -n "AUTO_EXECUTE_TRADES|TRADING_MODE|live|paper|order_class|create_order" backend/app

# Find websocket/event contracts
rg -n "signal.generated|order.submitted|order.filled|market_data.bar" backend/app

# Quick python syntax sweep
python -m compileall backend/app
```

This is how you *actually* audit “every file”: let ripgrep + compileall tell you what is inconsistent/broken.

---

# F) The final development plan (what you asked to memorialize)

This is the “after audit” plan that should live in README and in the `docs/DEVELOPMENT-PLAN...` file:

**Order of operations (one-at-a-time, after PR #23 merge):**
1) **RiskShield subscriber** to `order.submitted` (pre-trade veto/kill switch)  
2) Frontend **WebSocket hook** (`useMessageBus`) to consume `signal.generated` and `order.*` for real-time UI  
3) Streaming feature engine (O(1) indicators) if scaling symbol coverage is a goal  
4) TradeTracker + outcomes persistence so Kelly sizing uses real stats (not heuristics)

This matches the council’s emphasis: stabilize → safety layer → UX wiring → scale/ML.

---

## If you want me to produce the *exact commit payload* next
Reply with: “generate repo patches” and I’ll output:
- a complete, consolidated new `README.md` (full file),
- a complete updated `backend/README.md` (full file),
- the two new docs above,
- and a short “delete list” (sections/lines to remove from existing readmes).

Then you (or Oleh) can paste them in and commit them immediately on `audit/2026-03-01-stabilization`.