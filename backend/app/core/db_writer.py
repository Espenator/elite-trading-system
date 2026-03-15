"""Async batch write queue for DuckDB.

Collects writes and flushes in batches — eliminates per-row lock contention.
Runs as a background asyncio task. Uses the existing duckdb_store connection
pool (thread-safe) rather than opening a separate connection.

Usage:
    from app.core.db_writer import enqueue_write, start_batch_writer

    # At startup:
    asyncio.create_task(start_batch_writer())

    # In event handlers (non-blocking):
    await enqueue_write("signals_log", {"symbol": "AAPL", "score": 78, ...})
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_write_queue: Optional[asyncio.Queue] = None
_writer_running = False
_QUEUE_MAX = 50_000
_BATCH_SIZE = 100
_FLUSH_INTERVAL = 0.5  # seconds


def _get_queue() -> asyncio.Queue:
    """Lazy-init the write queue (must be created inside an event loop)."""
    global _write_queue
    if _write_queue is None:
        _write_queue = asyncio.Queue(maxsize=_QUEUE_MAX)
    return _write_queue


async def enqueue_write(table: str, row: Dict[str, Any]) -> None:
    """Non-blocking write. Never blocks the event loop.

    If queue is full (50k backlog), drops with warning.
    """
    q = _get_queue()
    try:
        q.put_nowait((table, row))
    except asyncio.QueueFull:
        logger.warning("[db_writer] Write queue full — dropping %s row", table)


async def start_batch_writer() -> None:
    """Background task: drain queue in batches, flush via duckdb_store.

    DuckDB batch inserts are ~50x faster than single-row inserts.
    """
    global _writer_running
    if _writer_running:
        logger.warning("[db_writer] Already running — skipping duplicate start")
        return
    _writer_running = True

    logger.info("[db_writer] Batch writer started (batch=%d, interval=%.1fs)", _BATCH_SIZE, _FLUSH_INTERVAL)
    q = _get_queue()

    while True:
        buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        total_rows = 0

        # Collect up to BATCH_SIZE rows or wait FLUSH_INTERVAL
        deadline = asyncio.get_event_loop().time() + _FLUSH_INTERVAL
        while total_rows < _BATCH_SIZE:
            timeout = deadline - asyncio.get_event_loop().time()
            if timeout <= 0:
                break
            try:
                table, row = await asyncio.wait_for(q.get(), timeout=timeout)
                buffer[table].append(row)
                total_rows += 1
            except asyncio.TimeoutError:
                break
            except asyncio.CancelledError:
                _writer_running = False
                return

        # Flush all buffered rows
        for table, rows in buffer.items():
            if not rows:
                continue
            try:
                await asyncio.to_thread(_flush_to_duckdb, table, rows)
            except Exception as e:
                logger.error("[db_writer] Flush failed for %s (%d rows): %s", table, len(rows), e)


def _flush_to_duckdb(table: str, rows: List[Dict[str, Any]]) -> None:
    """Sync flush — runs in thread pool via asyncio.to_thread."""
    if not rows:
        return
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_list = ", ".join(cols)
        values = [tuple(r.get(c) for c in cols) for r in rows]
        with duckdb_store._lock:
            conn.executemany(
                f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
                values,
            )
        logger.debug("[db_writer] Flushed %d rows to %s", len(rows), table)
    except Exception as e:
        logger.error("[db_writer] DuckDB write error for %s: %s", table, e)


def stop_batch_writer() -> None:
    """Signal the writer to stop (for graceful shutdown)."""
    global _writer_running
    _writer_running = False
