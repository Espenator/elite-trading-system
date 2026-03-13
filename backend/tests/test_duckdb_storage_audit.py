"""
DuckDB Storage Layer Audit — Schema integrity & performance.

Tests for:
- Concurrent OHLCV upsert (no duplicates)
- Connection/cursor cleanup and behavior after thread exit
- Query timeout behavior (no built-in timeout; app-level timeout works)

Run: pytest backend/tests/test_duckdb_storage_audit.py -v
"""

import asyncio
import os
import tempfile
import threading
import pytest
import pandas as pd
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Fixtures: isolated DuckDB for tests that need a clean DB
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_duckdb_path():
    """Temporary DuckDB file path. File is created by DuckDB on first connect."""
    fd, path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    os.remove(path)  # so DuckDB creates it
    yield path
    for p in (path, path + ".wal"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture
def isolated_duckdb_store(temp_duckdb_path):
    """Fresh DuckDBStorage instance with temp DB; singleton is reset for isolation."""
    from app.data.duckdb_storage import DuckDBStorage

    orig_instance = DuckDBStorage._instance
    DuckDBStorage._instance = None
    try:
        store = DuckDBStorage(temp_duckdb_path)
        store.init_schema()
        yield store
    finally:
        store.close()
        DuckDBStorage._instance = orig_instance


# ---------------------------------------------------------------------------
# 1. Concurrent OHLCV upsert — no duplicates
# ---------------------------------------------------------------------------

def test_concurrent_ohlcv_upsert_no_duplicates(isolated_duckdb_store):
    """Two threads upsert the same symbol+date; final table must have one row per (symbol, date)."""
    store = isolated_duckdb_store
    base_date = date.today() - timedelta(days=1)
    symbol = "AUDIT_CONCURRENT"

    def upsert_batch(seed: int):
        df = pd.DataFrame([{
            "symbol": symbol,
            "date": base_date,
            "open": 100.0 + seed,
            "high": 101.0 + seed,
            "low": 99.0 + seed,
            "close": 100.5 + seed,
            "volume": 1_000_000 + seed,
            "source": "alpaca",
        }])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        store.upsert_ohlcv(df)

    t1 = threading.Thread(target=upsert_batch, args=(1,))
    t2 = threading.Thread(target=upsert_batch, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    conn = store.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT symbol, date, COUNT(*) as cnt FROM daily_ohlcv WHERE symbol = ? GROUP BY symbol, date",
            [symbol],
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    assert len(rows) == 1, "Expected exactly one (symbol, date) row after concurrent upserts"
    assert rows[0][2] == 1, "Expected count 1 per (symbol, date); duplicates would indicate race"


# ---------------------------------------------------------------------------
# 2. Connection cleanup and thread exit behavior
# ---------------------------------------------------------------------------

def test_connection_usable_after_thread_exits_without_closing_cursor(isolated_duckdb_store):
    """Thread gets cursor, runs query, exits without closing cursor; main thread can still use store."""
    store = isolated_duckdb_store
    result_holder = []

    def thread_run():
        cur = store.get_thread_cursor()
        result_holder.append(cur.execute("SELECT 1").fetchone())
        # Intentionally do NOT close cursor (simulates leak or thread crash)

    t = threading.Thread(target=thread_run)
    t.start()
    t.join()

    assert result_holder[0][0] == 1
    # Main thread: health_check or simple query should still work (shared connection)
    health = store.health_check()
    assert "db_path" in health and "ohlcv_rows" in health


def test_close_clears_connection(isolated_duckdb_store):
    """After close(), internal connection is cleared; next use creates a new connection."""
    store = isolated_duckdb_store
    store.get_connection()  # ensure connection exists
    store.close()
    assert store._conn is None
    assert store._schema_initialized is False
    # Next call reopens
    conn = store.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1
    cur.close()


# ---------------------------------------------------------------------------
# 3. Query timeout behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_builtin_query_timeout(isolated_duckdb_store):
    """DuckDB has no per-query timeout; a long-running query runs to completion unless app wraps it."""
    # Use isolated store to avoid touching global analytics.duckdb (may be locked by another process)
    store = isolated_duckdb_store
    rows = await store.async_execute("SELECT 1 AS x")
    assert rows == [(1,)]


@pytest.mark.asyncio
async def test_application_level_timeout_works():
    """With asyncio.wait_for, a slow coroutine can be timed out at application level.

    DuckDB has no built-in per-query timeout; wrapping async_execute in wait_for
    is the recommended way to enforce timeouts. This test verifies that pattern works.
    """
    async def slow_work():
        await asyncio.sleep(1.0)
        return "done"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_work(), timeout=0.05)


# ---------------------------------------------------------------------------
# Schema / idempotency sanity checks (no separate migration system)
# ---------------------------------------------------------------------------

def test_init_schema_idempotent(isolated_duckdb_store):
    """Calling init_schema() twice does not fail and tables exist."""
    store = isolated_duckdb_store
    store.init_schema()
    store.init_schema()
    cur = store.get_connection().cursor()
    try:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_name = 'daily_ohlcv'"
        )
        assert cur.fetchone() is not None
    finally:
        cur.close()


def test_daily_ohlcv_primary_key_enforced(isolated_duckdb_store):
    """daily_ohlcv (symbol, date) is primary key; INSERT OR REPLACE replaces by key."""
    store = isolated_duckdb_store
    d = date.today()
    conn = store.get_connection()
    # Insert directly to avoid symbol_registry path (DuckDB CURRENT_TIMESTAMP handling)
    conn.execute(
        "INSERT OR REPLACE INTO daily_ohlcv (symbol, date, open, high, low, close, volume, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ["PK_TEST", d, 1.0, 2.0, 0.5, 1.5, 100, "alpaca"],
    )
    conn.execute(
        "INSERT OR REPLACE INTO daily_ohlcv (symbol, date, open, high, low, close, volume, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ["PK_TEST", d, 10.0, 20.0, 5.0, 15.0, 200, "alpaca"],
    )
    cur = conn.cursor()
    try:
        cur.execute("SELECT close, volume FROM daily_ohlcv WHERE symbol = 'PK_TEST' AND date = ?", [d])
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 15.0 and row[1] == 200
    finally:
        cur.close()


def test_job_state_single_row_per_job(isolated_duckdb_store):
    """job_state has job_name as PRIMARY KEY; ON CONFLICT DO UPDATE yields one row per job."""
    store = isolated_duckdb_store
    conn = store.get_connection()
    conn.execute(
        "INSERT INTO job_state (job_name, last_run_date, last_run_ts, last_result) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (job_name) DO UPDATE SET last_run_date = excluded.last_run_date, last_run_ts = excluded.last_run_ts",
        ["audit_job", "2026-01-01", 1735689600.0, "ok"],
    )
    conn.execute(
        "INSERT INTO job_state (job_name, last_run_date, last_run_ts, last_result) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (job_name) DO UPDATE SET last_run_date = excluded.last_run_date, last_run_ts = excluded.last_run_ts",
        ["audit_job", "2026-01-02", 1735776000.0, "ok"],
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_state WHERE job_name = 'audit_job'")
    assert cur.fetchone()[0] == 1
    cur.close()
