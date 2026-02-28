# CRITICAL: Backend Python Indentation Fix Guide

**Priority:** BLOCKER - CI cannot pass until this is resolved
**Assigned to:** Oleh
**Due:** Monday, March 2, 2026
**Created:** February 28, 2026 by Espen

---

## Problem Summary

Nearly every Python file in `backend/app/api/v1/` has **broken indentation**. Class fields, function bodies, and code blocks have inconsistent spacing (some lines at 0 spaces, some at 4, some at 8 where they should all be at 4). This causes `IndentationError: unexpected indent` on import, which means **the backend cannot start and CI fails on every push**.

### Root Cause

The Phase 9-12 commits appear to have been generated/pasted with corrupted whitespace. The code logic is correct but the indentation is scrambled throughout.

### Current CI Status

- **backend-test:** FAILING - `IndentationError` in `flywheel.py` line 37 (after fixing `strategy.py`, `risk.py`, `orders.py`, `signals.py`, `backtest_routes.py`, `backtest_engine.py`, `kelly_position_sizer.py`)
- **frontend-build:** FAILING (separate issue)
- **Files already fixed:** `strategy.py` (full rewrite), `risk.py` (line 470), `orders.py`, `signals.py`, `backtest_routes.py`, `backtest_engine.py`
- **Files still broken:** `flywheel.py` + likely 15-20 more files

---

## Fix Instructions (Step by Step)

### Step 1: Clone and Setup

```bash
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
pip install autopep8
```

### Step 2: Scan for ALL Errors

```bash
python scripts/fix_indentation.py --scan
```

This will output every file with syntax/indentation errors. Example output:
```
Scanning 45 Python files under backend/...
======================================================================
  FAIL  backend/app/api/v1/flywheel.py
         -> IndentationError: unexpected indent
  FAIL  backend/app/api/v1/market.py
         -> IndentationError: unexpected indent
  ...
======================================================================
Results: 20 OK, 25 FAILED out of 45 files
```

### Step 3: Auto-Fix with autopep8

```bash
python scripts/fix_indentation.py --fix --check
```

This runs `autopep8 --aggressive --aggressive` on every file, then verifies they compile.

### Step 4: Manual Review (if autopep8 can't fix everything)

For files that autopep8 can't fix (badly scrambled indentation), you'll need to manually fix them. The pattern is always the same:

**Problem:** Class fields or function body lines have wrong indentation:
```python
class MyModel(BaseModel):
    field_a: str = None        # 4 spaces - correct
field_b: int = 0               # 0 spaces - WRONG
        field_c: float = None  # 8 spaces - WRONG
    field_d: bool = True       # 4 spaces - correct
```

**Fix:** All class fields must be at 4 spaces, all function body lines at 4 spaces, nested blocks at 8, etc.:
```python
class MyModel(BaseModel):
    field_a: str = None     # 4 spaces
    field_b: int = 0        # 4 spaces
    field_c: float = None   # 4 spaces
    field_d: bool = True    # 4 spaces
```

### Step 5: Verify and Push

```bash
# Final verification
python scripts/fix_indentation.py --scan

# If all pass, commit and push
git add -A
git commit -m "fix: batch-fix all Python indentation errors across backend"
git push origin main
```

### Step 6: Verify CI

Check https://github.com/Espenator/elite-trading-system/actions - the backend-test job should now pass.

---

## Known Affected Files

These files in `backend/app/api/v1/` are confirmed or highly likely to have indentation issues:

| File | Status | Notes |
|------|--------|-------|
| `strategy.py` | FIXED | Full rewrite done 2/28 |
| `risk.py` | PARTIALLY FIXED | Line 470 fixed, may have more |
| `orders.py` | PARTIALLY FIXED | Earlier fixes applied |
| `signals.py` | PARTIALLY FIXED | Line 63 fixed |
| `backtest_routes.py` | PARTIALLY FIXED | Earlier fixes applied |
| `backtest_engine.py` | PARTIALLY FIXED | service file |
| `kelly_position_sizer.py` | PARTIALLY FIXED | service file |
| `flywheel.py` | BROKEN | Current CI blocker, 540 lines |
| `agents.py` | LIKELY BROKEN | Phase 9-12 file |
| `alerts.py` | LIKELY BROKEN | Phase 9-12 file |
| `data_sources.py` | LIKELY BROKEN | Phase 9-12 file |
| `market.py` | LIKELY BROKEN | Phase 9-12 file |
| `ml_brain.py` | LIKELY BROKEN | Phase 9-12 file |
| `openclaw.py` | LIKELY BROKEN | Phase 9-12 file |
| `patterns.py` | LIKELY BROKEN | Phase 9-12 file |
| `performance.py` | LIKELY BROKEN | Phase 9-12 file |
| `portfolio.py` | LIKELY BROKEN | Phase 9-12 file |
| `quotes.py` | LIKELY BROKEN | Phase 9-12 file |
| `risk_shield_api.py` | LIKELY BROKEN | Phase 9-12 file |
| `sentiment.py` | LIKELY BROKEN | Phase 9-12 file |
| `settings_routes.py` | LIKELY BROKEN | Phase 9-12 file |
| `status.py` | LIKELY BROKEN | Phase 9-12 file |
| `stocks.py` | LIKELY BROKEN | Phase 9-12 file |
| `system.py` | LIKELY BROKEN | Phase 9-12 file |
| `training.py` | LIKELY BROKEN | Phase 9-12 file |
| `youtube_knowledge.py` | LIKELY BROKEN | Phase 9-12 file |

Also check `backend/app/services/`, `backend/app/schemas/`, and `backend/app/models/` directories.

---

## Alternative: VS Code Quick Fix

If autopep8 doesn't fully fix a file:
1. Open the file in VS Code
2. Press `Ctrl+Shift+P` > "Format Document"
3. Select Python formatter (autopep8 or black)
4. Save

Or use black for more aggressive formatting:
```bash
pip install black
black backend/ --line-length 120
```

---

## After Fixing Indentation

Once CI passes, continue with the remaining tasks from `docs/STATUS-AND-TODO-2026-02-27.md`:
1. Fix `main.py` lifespan bug (move risk_monitor_task creation, fix WS add/remove)
2. Delete `ScreenerAndPatterns.jsx` (orphan empty file)
3. Align `hourly-scanner.yml` (Python 3.11 + alpaca-py)
4. Proceed with the wiring plan
