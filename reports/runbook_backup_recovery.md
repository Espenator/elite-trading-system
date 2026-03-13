# Runbook: Backup & Recovery — Embodier Trader

**Version**: 1.0  
**Last updated**: March 12, 2026  
**Scope**: DuckDB backup, recovery after crash, manual position close via Alpaca.

---

## 1. DuckDB backup procedure (daily snapshot)

### 1.1 What to back up

- **DuckDB analytics**: `backend/data/analytics.duckdb`  
  - **Source**: `backend/app/data/duckdb_storage.py` lines 29–31: `DB_DIR = backend/data`, `DUCKDB_PATH = DB_DIR / "analytics.duckdb"`.  
- **SQLite (orders/config)**: `backend/data/trading_orders.db` (and `-wal` if present)  
  - **Source**: `backend/app/data/storage.py` / `database.py` — orders and app config.

If `DATABASE_URL` in config points to another path (e.g. `elite_trading.duckdb`), include that file as well.

### 1.2 Daily backup steps

1. **When**: After market close (e.g. 17:00 ET) or before market open (e.g. 04:00 ET). Prefer a time when the app is idle or backup runs on a copy.  
2. **Stop or quiesce**: For consistency, either stop the backend or ensure no heavy writes (e.g. no bar flush in progress). Optional: use DuckDB’s `EXPORT` or copy the file while the process holds it (copy is safe on Windows/Linux; best if app is stopped).  
3. **Commands** (run from repo root; adjust paths if needed):

```powershell
# From repo root (e.g. C:\Users\Espen\elite-trading-system or PC2 path)
$BACKUP_DIR = ".\artifacts\backups"
$DATE = Get-Date -Format "yyyyMMdd"
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null

# DuckDB analytics
Copy-Item -Path "backend\data\analytics.duckdb" -Destination "$BACKUP_DIR\analytics_$DATE.duckdb" -Force -ErrorAction SilentlyContinue

# SQLite orders DB (include WAL if present)
Copy-Item -Path "backend\data\trading_orders.db" -Destination "$BACKUP_DIR\trading_orders_$DATE.db" -Force -ErrorAction SilentlyContinue
if (Test-Path "backend\data\trading_orders.db-wal") {
  Copy-Item -Path "backend\data\trading_orders.db-wal" -Destination "$BACKUP_DIR\trading_orders_$DATE.db-wal" -Force
}
```

4. **Retention**: Keep at least 7 daily snapshots; then weekly for 4 weeks.  
5. **Off-machine**: Copy backups to another disk or cloud (e.g. OneDrive, S3) per your policy.

### 1.3 Restore procedure (DuckDB / SQLite)

1. Stop the backend.  
2. Replace the live file with the chosen backup:

```powershell
# Restore DuckDB (example: restore yesterday)
Copy-Item -Path ".\artifacts\backups\analytics_20260311.duckdb" -Destination "backend\data\analytics.duckdb" -Force

# Restore SQLite
Copy-Item -Path ".\artifacts\backups\trading_orders_20260311.db" -Destination "backend\data\trading_orders.db" -Force
```

3. Start the backend and verify: health endpoint, one read-only query (e.g. recent bars or orders).  
4. **Note**: Restore is destructive (overwrites current DB). Use only when the live DB is corrupt or lost.

---

## 2. Recovery procedure if main PC crashes during market hours

### 2.1 Goals

- Avoid leaving positions unmanaged.  
- Either bring the app back on the same or another machine, or close positions manually via Alpaca.

### 2.2 If primary PC (ESPENMAIN) is down

1. **Assess**: Can you reach the Alpaca dashboard (app.alpaca.markets) from another device?  
2. **Option A — Manual close (recommended if app is unavailable)**  
   - Log in to Alpaca (paper or live, same account as the app).  
   - Go to **Positions** and close each position, or use **Close all** if available.  
   - See **Section 3** below.  
3. **Option B — Bring app up on secondary PC (ProfitTrader)**  
   - Clone/repo and `.env` on PC2; use same `ALPACA_*` keys as the account you want to control.  
   - Start backend (and optionally frontend).  
   - Use **Risk Shield** or **Emergency Flatten** to liquidate:  
     - `POST /api/v1/risk-shield/emergency-action` with `{"action": "kill_switch"}` (Bearer `API_AUTH_TOKEN`), or  
     - `POST /api/v1/metrics/emergency-flatten` with Bearer token (after auth fix), or  
     - `POST /api/v1/orders/flatten-all` with Bearer token.  
4. **Option C — Restart on same PC**  
   - Restart machine/backend; ensure `TRADING_MODE` and Alpaca keys are correct.  
   - If positions were opened by the app, use the app to flatten or use Alpaca dashboard.

### 2.3 After recovery

- Check Slack **#embodier-trader** for any emergency-flatten or error alerts.  
- Confirm open positions in Alpaca match expectations.  
- Re-enable trading only when satisfied (e.g. unfreeze entries if you had set freeze).

---

## 3. Manual position close procedure (app unresponsive)

Use this when the app is down or you do not trust it (e.g. after a crash or bug).

### 3.1 Prerequisites

- Alpaca account (paper or live) that the app uses.  
- Browser or Alpaca mobile app.

### 3.2 Steps

1. Open **https://app.alpaca.markets** (or paper: https://paper-api.alpaca.markets / Alpaca paper dashboard URL).  
2. Log in with the same account linked to `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`.  
3. Go to **Positions** (or **Portfolio** → Positions).  
4. For each open position:  
   - Click the position.  
   - Choose **Sell** (long) or **Buy to Cover** (short) and submit a **market** order for the full quantity.  
5. If the UI offers **Close all** or **Liquidate all**, you may use it to close every position in one go.  
6. Verify **Positions** is empty (or only intended positions remain).

### 3.3 Test: Can you close all positions from Alpaca if the system fails?

- **Answer**: Yes. Alpaca’s dashboard and API are independent of the Embodier Trader app. As long as you can log in to the correct Alpaca account, you can close all positions manually.  
- **Recommendation**: Once before going live, log in to the **paper** Alpaca account, open a test position (or use one created by the app), then close it from the dashboard to confirm the flow.

---

## 4. Emergency flatten via API (when app is running)

When the app is running and you want to flatten from the API:

| Method | Endpoint | Auth |
|--------|----------|------|
| Risk Shield kill switch | `POST /api/v1/risk-shield/emergency-action` body `{"action": "kill_switch"}` | Bearer `API_AUTH_TOKEN` |
| Order executor flatten | `POST /api/v1/orders/flatten-all` | Bearer `API_AUTH_TOKEN` |
| Metrics emergency flatten | `POST /api/v1/metrics/emergency-flatten?reason=manual` | Bearer `API_AUTH_TOKEN` |

Example (PowerShell):

```powershell
$token = $env:API_AUTH_TOKEN
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orders/flatten-all" -Method POST -Headers @{ Authorization = "Bearer $token" }
```

---

## 5. Backup cadence summary

| Item | Cadence | Location |
|------|---------|----------|
| DuckDB analytics | Daily (after close or before open) | `backend/data/analytics.duckdb` → `artifacts/backups/analytics_YYYYMMDD.duckdb` |
| SQLite orders | Daily (same run) | `backend/data/trading_orders.db` → `artifacts/backups/trading_orders_YYYYMMDD.db` |
| Retention | 7 daily + 4 weekly | Operator-managed |

---

## 6. Document control

- **Owner**: DevOps / operator.  
- **Review**: After any change to DB paths or backup tooling.  
- **Runbook location**: `reports/runbook_backup_recovery.md`.
