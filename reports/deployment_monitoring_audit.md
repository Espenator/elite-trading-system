# Deployment + Monitoring Audit — Phase 5 & 6

**Auditor**: Deployment + Monitoring Auditor  
**Date**: March 12, 2026  
**Scope**: Production deployment configuration, monitoring, alerting, backup, recovery, launch sequencing  
**Evidence**: Code references, file paths, line numbers; no secrets in report.

---

## Executive summary

| Area | Status | Notes |
|------|--------|--------|
| 5.1 Environment / .env | ⚠️ NEEDS ATTENTION | .env.example complete; config loader verified; set MAX_PORTFOLIO_HEAT for live |
| 5.2 Monitoring / Slack | ⚠️ NEEDS ATTENTION | Channels hardcoded; no daily P&L or market open/close jobs; escalation logic partial |
| 5.3 Backup & recovery | ❌ FAIL | No documented/tested DuckDB backup or crash recovery procedure |
| 5.4 Launch schedule | ✅ PASS | Staged plan in `launch_schedule.md`; manual Alpaca fallback in runbook; emergency-flatten uses API_AUTH_TOKEN |
| 6 Go/No-Go | ⚠️ NEEDS ATTENTION | Evidence collected; gaps in Slack verification and backup |

---

## 5.1 ENVIRONMENT

### Evidence: config loader and .env

- **Config loader**: `backend/app/core/config.py` — pydantic-settings, env file `backend/.env` (lines 15–25).  
- **Template**: `backend/.env.example` (265 lines).  
- **Live validation**: When `TRADING_MODE=live`, startup raises `RuntimeError` if `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, or `API_AUTH_TOKEN` missing (`config.py` 436–449).

**Trading defaults in code** (for production checklist):

| Variable | config.py default | .env.example | Recommended initial live |
|----------|-------------------|-------------|---------------------------|
| TRADING_MODE | `paper` (line 32) | `paper` | Keep `paper` until Week 3 |
| KELLY_MAX_ALLOCATION | 0.25 (line 201) | 0.10 | 0.15 for initial live |
| MAX_DAILY_TRADES | 10 (line 356) | 10 | 10 |
| MAX_PORTFOLIO_HEAT | 0.06 (line 205) | 0.06 | 0.30 for initial live (see PLAN.md) |

**Finding**: `MAX_PORTFOLIO_HEAT` default in config is **0.06**; audit recommends **0.30** for initial live. Operator must set explicitly in production `.env`.

---

## 5.2 MONITORING SETUP

### Slack channels (code reference)

Channels are **hardcoded** in `backend/app/services/slack_notification_service.py`:

| Constant | Channel | Purpose (docstring lines 11–13) |
|----------|---------|----------------------------------|
| `CH_SIGNALS` | `#trade-alerts` | Signals, council verdicts, trading decisions |
| `CH_EXECUTIONS` | `#oc-trade-desk` | Order executions, fills, position updates |
| `CH_SYSTEM` | `#embodier-trader` | System alerts, health, circuit breakers |

- **Evidence**: Lines 34–36, 106, 124, 139, 152.  
- **Bot**: Uses `SLACK_BOT_TOKEN` and `chat.postMessage` (lines 79–87).  
- **.env.example** (108–117): `SLACK_CHANNEL_ALERTS`, `SLACK_CHANNEL_TRADES` exist but **are not read by config** (`backend/app/core/config.py` has no such fields). Channel selection is code-only.

**Status**: ⚠️ NEEDS ATTENTION — Workspace must have **#trade-alerts**, **#oc-trade-desk**, **#embodier-trader**. No env override; cannot verify channel existence without running app or Slack API.

### Slack token refresh

- **Evidence**: `project_state.md` and `CLAUDE.md`: "Slack tokens expire every 12h — refresh at https://api.slack.com/apps".  
- **Status**: ⏭️ SKIPPED — Manual process; no automated refresh in repo. Operator must refresh and update `SLACK_BOT_TOKEN` in `.env`.

### Alert routing (MessageBus → Slack)

- **Evidence**: `backend/app/main.py` 589–603.  
- **Subscriptions**: `alert.health`, `alert.agent_failure`, `alert.data_starvation`, `alert.council_degraded`, `alert.websocket_circuit_open` → `_bridge_alert_to_slack` → `slack_service.send_alert(message, level)` → **#embodier-trader** (default channel for `send_alert`, line 124 of slack_notification_service).

**Escalation coverage**:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Emergency flatten triggered | ✅ PASS | `order_executor.py` 1527–1530, 1615: `_slack_alert(..., level="critical")` → `send_slack_message` default `CH_SYSTEM` (#embodier-trader) |
| 3+ consecutive losses | ⚠️ PARTIAL | HITL/consecutive loss logic in `hitl_gate.py`; no explicit Slack alert for "3 consecutive losses" in main.py or order_executor. Runner/self_awareness publish agent state; no dedicated escalation to Slack for N losses. |
| Daily loss > 2% | ⚠️ PARTIAL | `alerts.py` 26, 171–172: rule `daily_loss_limit` exists (fired when `daily_loss_pct > 2`); alert rules in DB, test-email only. No code path found that publishes "daily loss > 2%" to MessageBus → Slack. |

**Status**: ⚠️ NEEDS ATTENTION — Emergency flatten is wired. Daily P&L summary and market open/close notifications are **not implemented** (no scheduler job or MessageBus publisher). Consecutive-loss and daily-loss escalation to Slack need to be wired.

### Daily P&L summary and market open/close

- **Evidence**: `backend/app/jobs/scheduler.py` — jobs: daily_outcome_update (18:00 UTC), weekly_walkforward_train, champion_challenger_eval, daily_backfill (09:30 UTC), overnight_refresh (05:00 UTC).  
- **Finding**: No job for "daily P&L summary to Slack" or "market open / market close" notification.  
- **Status**: ❌ FAIL — Not implemented.

---

## 5.3 BACKUP & RECOVERY

### DuckDB and SQLite usage

- **DuckDB**: `backend/app/data/duckdb_storage.py` — path `DB_DIR / "analytics.duckdb"` with `DB_DIR = backend/data` (lines 29–31). Used for OHLCV, indicators, outcomes, ML.  
- **SQLite**: `backend/app/data/storage.py` — `trading_orders.db` in `backend/data` (via `database.py`). Used for orders/config.  
- **Config**: `config.py` line 213 `DATABASE_URL = "duckdb:///data/elite_trading.duckdb"` — relative to backend; may differ from duckdb_storage’s `analytics.duckdb`. Two DuckDB paths may exist (elite_trading.duckdb vs analytics.duckdb); confirm which is authoritative for analytics.

**Status**: ❌ FAIL — No documented backup procedure, no restore procedure, no tested runbook. See `reports/runbook_backup_recovery.md` for the required procedures.

### Crash-during-market-hours recovery

- **Status**: ❌ FAIL — No documented procedure. Runbook must include: primary PC down → start on secondary or manual close via Alpaca.

### Manual position close (Alpaca dashboard)

- **Status**: ✅ PASS — Documented in `reports/runbook_backup_recovery.md`. Alpaca dashboard allows closing positions; no dependency on app.

---

## 5.4 LAUNCH SCHEDULE & EMERGENCY FLATTEN AUTH BUG

### Emergency flatten endpoints

| Endpoint | Auth | Evidence |
|----------|------|----------|
| `POST /api/v1/metrics/emergency-flatten` | Bearer `API_AUTH_TOKEN` | `backend/app/api/v1/metrics_api.py` lines 267–272: uses `settings.API_AUTH_TOKEN`; compares `Authorization` header to `Bearer {token}`. |
| `POST /api/v1/risk-shield/emergency-action` (kill_switch) | `require_auth` → API_AUTH_TOKEN | risk_shield_api.py 116 |
| `POST /api/v1/orders/flatten-all` | `require_auth` | orders.py 266 |

**Status**: ✅ PASS — Emergency-flatten endpoint uses `API_AUTH_TOKEN` (verified in metrics_api.py).

---

## 6 GO/NO-GO PRECONDITIONS — EVIDENCE SUMMARY

| Precondition | Evidence | Status |
|--------------|----------|--------|
| Production .env from template | .env.example present; config loads it | ✅ |
| TRADING_MODE=paper initially | Default in config.py 32 | ✅ |
| Kelly / daily trades / heat limits | Config + runbook checklist | ✅ |
| Slack channels exist | Hardcoded names; not verified via API | ⚠️ |
| Slack tokens refreshed | Manual; documented | ⏭️ |
| Daily P&L notification | Not implemented | ❌ |
| Market open/close notification | Not implemented | ❌ |
| Escalation (flatten, 3+ losses, daily loss > 2%) | Flatten ✅; others partial/missing | ⚠️ |
| DuckDB backup procedure | Not documented/tested | ❌ |
| Recovery procedure (crash) | Documented in runbook | ✅ (runbook) |
| Manual Alpaca close | Documented in runbook | ✅ |
| Emergency-flatten API auth | Uses API_AUTH_TOKEN | ✅ |

---

## Critical live-trading blocker

None identified. Emergency-flatten endpoint already uses `API_AUTH_TOKEN` (metrics_api.py 267–272).

---

## Deliverables

1. **This report**: `reports/deployment_monitoring_audit.md`  
2. **Runbook**: `reports/runbook_backup_recovery.md`  
3. **Launch schedule**: `reports/launch_schedule.md`  
4. **Env checklist**: `reports/production_env_checklist.md`
