# Path map — canonical machine paths

**Convention:** Repo-relative paths everywhere in docs. See **PATH-STANDARD.md** for the single source of truth.

This file lists the **canonical absolute paths** per machine. All documentation uses these consistently (no alternate paths).

---

## Canonical repo root by machine

| Machine | Repo root |
|---------|-----------|
| **ESPENMAIN** (PC1) | `C:\Users\Espen\elite-trading-system` |
| **ProfitTrader** (PC2) | `C:\Users\ProfitTrader\elite-trading-system` |
| **Other / CI** | Clone path (e.g. `$env:USERPROFILE\elite-trading-system` or script location) |

---

## Full paths (ESPENMAIN)

| Logical | Path |
|---------|------|
| Repo root | `C:\Users\Espen\elite-trading-system` |
| Backend | `C:\Users\Espen\elite-trading-system\backend` |
| Frontend | `C:\Users\Espen\elite-trading-system\frontend-v2` |
| Council | `C:\Users\Espen\elite-trading-system\backend\app\council` |
| Brain service | `C:\Users\Espen\elite-trading-system\brain_service` |

## Full paths (ProfitTrader)

| Logical | Path |
|---------|------|
| Repo root | `C:\Users\ProfitTrader\elite-trading-system` |
| Backend | `C:\Users\ProfitTrader\elite-trading-system\backend` |
| Frontend | `C:\Users\ProfitTrader\elite-trading-system\frontend-v2` |
| Brain service | `C:\Users\ProfitTrader\elite-trading-system\brain_service` |

**Commands from repo root:** `cd backend`, `cd frontend-v2`, etc. (same on every machine.)

---

## Directory structure (same everywhere)

```
<repo root>/
├── backend/
├── frontend-v2/
├── brain_service/
├── desktop/
├── docs/
├── scripts/
├── directives/
├── data/
├── PATH-STANDARD.md   ← convention
├── PATH-MAP.md        ← this file
└── ...
```

See **REPO-MAP.md** for the full tree.
