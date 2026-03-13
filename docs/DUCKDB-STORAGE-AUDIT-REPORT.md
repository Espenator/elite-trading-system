# DuckDB Storage Layer — Schema Integrity & Performance Audit

**Date:** March 13, 2026  
**Scope:** `backend/app/data/duckdb_storage.py`, `storage.py`, `feature_store.py`, `alpaca_data.py`, `data_ingestion.py`, `feature_aggregator.py`

---

## 1. Executive Summary

The DuckDB analytics layer is the single source for OHLCV, indicators, options flow, macro data, and trade outcomes. The audit confirmed **correct singleton and write serialization**, **idempotent schema init with column migrations**, and **no duplicate rows under concurrent OHLCV upsert**. Gaps include: **no schema version table**, **no date partitioning**, **no per-query timeout**, **cursor leaks** where `get_thread_cursor()` is used without `close()`, and **DuckDB CURRENT_TIMESTAMP bug** in `ON CONFLICT DO UPDATE` (workaround applied). Recommended changes: add schema versioning, optional partitioning for `daily_ohlcv`, enforce query timeouts at the application layer, close cursors in a single pattern, and consider compression.

---

## 2. Findings by Task

### 2.1 Singleton Pattern — Async Context

- **Implementation:** `DuckDBStorage` uses **double-checked locking** in `__new__` with `_instance_lock = threading.Lock()`. The singleton is created once; subsequent calls with a different `db_path` raise `ValueError`.
- **Async:** Blocking DuckDB calls are offloaded via `asyncio.to_thread()` in `async_execute`, `async_execute_df`, and `async_insert`. The **write lock** (`_write_lock`) is held inside the thread runnable, so async callers do not block the event loop; they serialize on the lock in the thread pool. **Conclusion:** Correct for async: no lock on the event loop, serialized writes in worker threads.

### 2.2 Connection Leaks

- **Single connection:** One process-wide connection is created in `_get_conn()` and reused. `close()` sets `_conn = None` and `_schema_initialized = False`; the next use creates a new connection. No leak of the connection itself.
- **Cursors:** Many call sites use `get_thread_cursor()` and **never close the cursor** (e.g. `feature_store.py`, `feature_aggregator.py`, `daily_outcome_update.py`, `weight_learner.py`, `council.py`, etc.). DuckDB cursors should be closed to avoid resource leaks. **Recommendation:** Prefer context managers or ensure every `get_thread_cursor()` is paired with `cursor.close()` (or use a helper that returns a context manager).

### 2.3 Schema Init — Idempotency and Column Additions

- **Idempotent:** All tables use `CREATE TABLE IF NOT EXISTS`; indexes use `CREATE INDEX IF NOT EXISTS`. Calling `init_schema()` multiple times is safe.
- **Column additions:** The `features` table has a migration loop that runs `ALTER TABLE features ADD COLUMN ...` for `pipeline_version`, `schema_version`, `feature_count`, `feature_hash`, `timeframe` with try/except (ignore if column exists). **Conclusion:** Idempotent and handles additive column migrations for `features`. There is **no schema version table**; migrations are manual ALTERs.

### 2.4 Concurrent Write Contention

- **Write serialization:** All writes go through `_write_lock` (e.g. `upsert_ohlcv`, `upsert_indicators`, `insert_trade_outcome`). Two threads inserting OHLCV simultaneously are serialized; no duplicate (symbol, date) rows. **Test:** `test_concurrent_ohlcv_upsert_no_duplicates` (two threads upsert same symbol+date) confirms exactly one row per (symbol, date).

### 2.5 Query Timeout

- **Current state:** There is **no per-query timeout** in DuckDB or in the storage layer. A slow query can block the thread (and thus, when called via `async_execute`, the thread pool) until it completes.
- **Recommendation:** Apply timeouts at the application layer, e.g. `asyncio.wait_for(duckdb_store.async_execute(...), timeout=30.0)`. **Test:** `test_application_level_timeout_works` confirms that `asyncio.wait_for` can time out a long-running coroutine.

### 2.6 WAL / MVCC

- **Reads:** Read methods use `cursor()` (e.g. `get_training_window`, `get_inference_snapshot`) and do not take the write lock. DuckDB uses MVCC; concurrent reads during a write see a consistent snapshot. **Conclusion:** Concurrent read-during-write is handled correctly by DuckDB.

### 2.7 Table Size Estimate

- **Formula:** 5000 symbols × 252 trading days × 5 years ≈ **6.3M rows** for `daily_ohlcv`.
- **Other tables:** `technical_indicators` and `options_flow` same order of magnitude per (symbol, date). `trade_outcomes` and `job_state` are much smaller. At 6M rows, full table scans on date ranges are still reasonable; **date partitioning** becomes useful as data grows (e.g. 10x).

---

## 3. Key Tables Verified

| Table | Check | Result |
|-------|--------|--------|
| **daily_ohlcv** | (symbol, date) unique, upsert | PRIMARY KEY (symbol, date); `INSERT OR REPLACE` via staging table; no duplicates under concurrency. |
| **technical_indicators** | Columns match feature_aggregator | Schema has rsi_14, macd, sma_*, ema_*, atr_*, bb_*, adx_14, williams_r; feature_aggregator checks `information_schema.columns` and uses only existing columns. |
| **options_flow** | Nullable columns | All columns nullable except symbol, date; app uses _safe_float / COALESCE. |
| **trade_outcomes** | Uniqueness | Uses sequence `trade_outcomes_seq` for `id`; **no order_id column** — consider adding order_id UNIQUE for traceability to Alpaca orders. |
| **job_state** | Idempotency | PRIMARY KEY (job_name); one row per job; `ON CONFLICT (job_name) DO UPDATE` used in daily_outcome_update. Prompt expected (job_name + date); current design is one row per job with last_run_date. |

---

## 4. Expected Issues Confirmed

- **No schema version tracking:** Migrations are manual ALTER TABLE; no `schema_version` table or migration runner.
- **No date-based partitioning:** Large tables are single objects; range scans on date are index-assisted (e.g. `idx_ohlcv_date`) but not partitioned.
- **ThreadPoolExecutor timeout (e.g. 5s in feature_aggregator):** If a DuckDB read runs in a thread and exceeds the future timeout, the thread keeps running until the query finishes; only the caller gets TimeoutError. No deadlock with the write lock unless a write holds the lock for >5s while another thread waits.
- **Feature aggregator column check:** `_get_indicator_features` queries `information_schema.columns` and builds the SELECT dynamically. Fragile if schema changes without code update; acceptable with disciplined schema evolution.
- **No compression configured:** DuckDB default storage; disk grows linearly. Compression can be enabled at connection or table level in future.

---

## 5. Fixes Applied During Audit

1. **DuckDB CURRENT_TIMESTAMP in ON CONFLICT:** DuckDB (as of audit) mis-parses `CURRENT_TIMESTAMP` in `ON CONFLICT ... DO UPDATE SET updated_at = CURRENT_TIMESTAMP`, causing "column named CURRENT_TIMESTAMP" error. **Fix:** Pass timestamp from Python in `_update_symbol_registry_from_ohlcv_impl` and `upsert_symbol_registry` (e.g. `?` placeholder with `datetime.now(timezone.utc)`).

---

## 6. Recommended Schema and Operational Changes

1. **Schema version table**
   - Add `schema_migrations` or `schema_version` (version INT or name VARCHAR, applied_at TIMESTAMP).
   - Run migrations from a directory of SQL or versioned scripts and record applied version.

2. **Partitioning (optional, for scale)**
   - For `daily_ohlcv`, consider partitioning by year or (year, month) when row count grows (e.g. >10M). DuckDB supports partitioning; would require schema evolution and backfill.

3. **Indexes**
   - Existing indexes on date and symbol are in place. For heavy range queries, ensure `(date, symbol)` or `(symbol, date)` match query patterns.

4. **Query timeout**
   - No change in DuckDB itself. Use `asyncio.wait_for(store.async_execute(...), timeout=30.0)` (or configurable) for all user/API-triggered queries.

5. **Cursor lifecycle**
   - Standardize on a single pattern: either a context manager (e.g. `with store.cursor() as cur:`) or document that callers must call `cur.close()`. Refactor high-traffic paths (feature_aggregator, feature_store, council, weight_learner) to close cursors.

6. **Compression**
   - Evaluate DuckDB options (e.g. connection settings or table-level compression) to reduce disk usage for large tables.

7. **trade_outcomes and order_id**
   - Add optional `order_id` (or `alpaca_order_id`) with UNIQUE constraint if each outcome maps 1:1 to an order, for idempotency and traceability.

---

## 7. Deliverables

| Deliverable | Location |
|-------------|----------|
| Test: concurrent OHLCV upsert, no duplicates | `backend/tests/test_duckdb_storage_audit.py::test_concurrent_ohlcv_upsert_no_duplicates` |
| Test: connection usable after thread exits without closing cursor | `test_connection_usable_after_thread_exits_without_closing_cursor` |
| Test: close() clears connection | `test_close_clears_connection` |
| Test: no built-in query timeout | `test_no_builtin_query_timeout` |
| Test: application-level timeout (wait_for) works | `test_application_level_timeout_works` |
| Test: init_schema idempotent | `test_init_schema_idempotent` |
| Test: daily_ohlcv primary key enforced | `test_daily_ohlcv_primary_key_enforced` |
| Test: job_state one row per job | `test_job_state_single_row_per_job` |
| Schema/partitioning/index/compression recommendations | This report, §6 |
| DuckDB CURRENT_TIMESTAMP workaround | `backend/app/data/duckdb_storage.py` (`_update_symbol_registry_from_ohlcv_impl`, `upsert_symbol_registry`) |

Run audit tests:

```bash
cd backend && python -m pytest tests/test_duckdb_storage_audit.py -v
```
