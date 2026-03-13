# Scheduler Job Resilience & Distributed Locking — Audit Report

**Date:** March 13, 2026  
**Scope:** APScheduler flywheel jobs on PC1; idempotency, failure recovery, startup ordering, distributed locking.

---

## 1. Job registration and cron triggers

| Job ID | Trigger | Schedule | File / Wrapper |
|--------|---------|----------|----------------|
| `daily_outcome_update` | CronTrigger | 18:00 UTC daily | `daily_outcome_update.run` |
| `weekly_walkforward_train` | CronTrigger | Sun 20:00 UTC | `weekly_walkforward_train.run` |
| `champion_challenger_eval` | CronTrigger | Sun 22:00 UTC | `champion_challenger_eval.run` |
| `daily_backfill` | CronTrigger | 09:30 UTC Mon–Fri | `data_ingestion.run_daily_incremental()` |
| `overnight_refresh` | CronTrigger | 05:00 UTC Mon–Fri | `data_ingestion.ingest_macro_data(days=30)` |
| `morning_briefing` | CronTrigger | 09:00 America/New_York Mon–Fri | `morning_briefing_job.run_morning_briefing()` |

**Finding:** All 6 jobs are registered in `backend/app/jobs/scheduler.py` with the correct cron triggers. The 09:30 UTC job invokes `data_ingestion.run_daily_incremental()` (not `backfill_orchestrator.run()`); the startup backfill in `main.py` uses `data_ingestion.run_startup_backfill()` and `BackfillOrchestrator` is only used in that startup path.

---

## 2. Idempotency and `job_state`

- **`daily_outcome_update`:** Uses DuckDB `job_state` table via `_get_state()` / `_save_state()`. Skips if `last_run_date == today`. Survives process restarts.
- **`weekly_walkforward_train`:** Uses in-memory `_last_train_date` only. No DuckDB. Restart or second process can run again the same week.
- **`champion_challenger_eval`:** Idempotent by logic (no challenger → no work), not by `job_state`. Can run multiple times; only evaluates if a candidate exists.
- **`morning_briefing`**, **`daily_backfill`**, **`overnight_refresh`:** No `job_state` or distributed lock. Duplicate runs possible if scheduler fires twice (e.g. two instances).

**Finding:** Only `daily_outcome_update` is fully idempotent across restarts via `job_state`. Other jobs have no persisted idempotency or locking.

---

## 3. Two scheduler instances (dual-PC / no distributed lock)

- Scheduler is started in `main.py` lifespan (step 3b) and runs only on the process that starts it (PC1).
- There is no distributed lock (Redis or DuckDB advisory) before executing a job. If two backend instances run (e.g. PC1 + PC2, or two workers), both would run the same job at the same cron time.

**Finding:** No distributed locking. Recommendation: add a “try-acquire lock per job key” before running (see §9).

---

## 4. Error handling and retry

- Each job is wrapped in a try/except in `scheduler.py`; exceptions are logged and not re-raised. Process keeps running.
- There is no retry (no backoff, no “run again in N minutes”). A failed run is effectively skipped until the next cron.

**Finding:** Failed jobs do not retry; they are logged and skipped until the next scheduled run. No dead-letter queue for failed job outputs.

---

## 5. Job ordering (weekly_walkforward vs daily_outcome)

- **Time order:** `weekly_walkforward_train` Sun 20:00 UTC; `champion_challenger_eval` Sun 22:00 UTC. Eval runs 2 hours after train.
- **Dependency:** `champion_challenger_eval` depends on a candidate from the model registry (from training), not on `daily_outcome_update`. `daily_outcome_update` (18:00 UTC daily) is independent.

**Finding:** Weekly ordering is correct by schedule. There is no explicit dependency of `weekly_walkforward_train` on `daily_outcome_update`; both are independent.

---

## 6. Long-running job timeout

- `_run_daily_backfill()` and `_run_overnight_refresh()` call `data_ingestion.run_daily_incremental()` and `data_ingestion.ingest_macro_data()` with no `asyncio.wait_for()` or timeout.
- `ingest_all()` (used by run_startup_backfill and run_daily_incremental) has no overall timeout; Alpaca/FRED calls use a 60s HTTP timeout per request but the full run can run arbitrarily long.

**Finding:** Backfill and overnight refresh can hang indefinitely if the Alpaca (or other) API is slow or stuck. Recommendation: wrap execution in `asyncio.wait_for(..., timeout=3600)` (or configurable) and mark the job as failed on timeout.

---

## 7. Startup ordering (scheduler vs DuckDB and MessageBus)

- In `main.py` lifespan (run_in_background=False): (1) SQLite init_schema, (2) `duckdb_store.init_schema()`, (3) ML singletons, (4) `_start_event_driven_pipeline()` (MessageBus + subscribers), (5) **3b** `start_scheduler()`.
- Jobs run at their cron times, not at startup, so the first run of any job is after DuckDB and MessageBus are up.

**Finding:** Scheduler starts after DuckDB and the event pipeline (MessageBus). No change required for ordering.

---

## 8. Job status API

- **Endpoint:** `GET /api/v1/flywheel/scheduler` (in `backend/app/api/v1/flywheel.py`) returns `get_scheduler_status()` from `scheduler.py`.
- **Returned:** `enabled`, `running`, and `jobs` (id, name, next_run). No per-job run history (last run, success/failure, duration).

**Finding:** Basic status exists; frontend cannot see “last run,” “failed,” or “running” per job. Enhancement: persist last run result and status (e.g. in `job_state` or a small table) and expose in the API.

---

## 9. Distributed locking strategy

### Option A: Redis-based lock (recommended if Redis is in use)

- Use a key per job and TTL (e.g. `scheduler:lock:{job_id}` with TTL slightly above max job duration).
- Before running a job: `SET key NX EX TTL`; if not acquired, skip run and log.
- PC1 and PC2 (or multiple workers) share the same Redis; only one instance runs each job per window.

**Pros:** Simple, fast, works across machines. **Cons:** Requires Redis (already used for MessageBus on PC1).

### Option B: DuckDB advisory / job_state lock

- Use `job_state` (or a dedicated `scheduler_lock` table) with a row per job: `job_id`, `locked_until` (timestamp), `locked_by` (hostname/instance id).
- Before run: try to insert or update “lock” row (e.g. `locked_until = now + max_duration`) only if not already locked by another instance; use a single DuckDB connection/write lock.
- Both PC1 and PC2 would need to share the same DuckDB file (e.g. on a shared drive or only one writer), which is not the current dual-PC setup.

**Pros:** No extra service. **Cons:** DuckDB is local to each machine; sharing one file across PCs is operationally harder. Better for single-instance idempotency than for true multi-PC locking.

### Recommendation

- **Single PC (current):** Keep `job_state` for `daily_outcome_update`; add `job_state` (or equivalent) for other daily/weekly jobs so each job records `last_run_ts` / `last_run_date` and skips if already run in the same window. This gives idempotency and avoids duplicate work after restarts.
- **Dual-PC / multi-instance:** Use **Redis-based locking** (Option A) so only one instance runs each job per schedule. Implement “try-acquire lock → run → release” (or TTL-based release) in the scheduler wrappers.
- **Timeout:** Add a configurable `asyncio.wait_for` around long-running jobs (e.g. backfill, overnight refresh) and record failure in job state or logs.

---

## 10. Tests added

- **`backend/tests/test_scheduler_resilience.py`**
  - **Idempotency:** `daily_outcome_update` skips second run when state says “already run today” (mocked `_get_state`).
  - **Idempotency:** Asserts `daily_outcome_update` uses DuckDB `job_state` (module structure).
  - **Failure recovery:** Scheduler wrapper catches job exception and does not propagate.
  - **Startup ordering:** `get_scheduler_status()` does not depend on DuckDB/MessageBus being ready; `start_scheduler()` registers 6 jobs when enabled; main lifespan starts scheduler after `duckdb_store.init_schema()`.

---

## 11. Summary table

| Issue | Status | Action |
|-------|--------|--------|
| 6 jobs registered with correct cron | OK | None |
| Idempotency (job_state) | Partial | Only daily_outcome; extend to other jobs or add Redis lock |
| Distributed lock (dual-PC) | Missing | Add Redis lock (or DuckDB if single-DB) |
| Retry on failure | Missing | Optional: retry with backoff or DLQ |
| Job ordering (weekly) | OK | None |
| Long-running timeout | Missing | Add asyncio.wait_for for backfill/refresh |
| Startup ordering | OK | Scheduler after DuckDB + pipeline |
| Job status API (run history) | Partial | Add last_run / status per job |
| Dead-letter queue for failed outputs | Missing | Optional: persist failed run info |
