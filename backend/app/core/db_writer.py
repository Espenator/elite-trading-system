"""Async batch write queue for DuckDB.

Collects writes and flushes in batches — eliminates per-row lock contention.
Runs as a background asyncio task.

Usage:
    from app.core.db_writer import enqueue_write, start_batch_writer

    # At startup:
    asyncio.create_task(start_batch_writer())

    # In event handlers:
    await enqueue_write("market_bars", {"symbol": "AAPL", "close": 150.0, ...})
"""
import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_write_queue: asyncio.Queue = asyncio.Queue(maxsize=50_000)
_writer_running = False
_writer_task: Optional[asyncio.Task] = None

# Metrics
_stats = {
    "rows_queued": 0,
    "rows_flushed": 0,
    "flush_count": 0,
    "drops": 0,
    "errors": 0,
}


async def enqueue_write(table: str, row: Dict[str, Any]):
    """Non-blocking write. Never blocks the event loop.

    If queue is full (50k backlog), drops with warning.
    """
    try:
        _write_queue.put_nowait((table, row))
        _stats["rows_queued"] += 1
    except asyncio.QueueFull:
        _stats["drops"] += 1
        if _stats["drops"] % 1000 == 1:
            logger.warning("[db_writer] Write queue full — dropping %s row (total drops: %d)",
                           table, _stats["drops"])


async def start_batch_writer():
    """Background task: drain queue in batches of 100 rows, every 500ms.

    DuckDB batch inserts are ~50x faster than single-row inserts.
    """
    global _writer_running
    _writer_running = True
    logger.info("[db_writer] Batch writer started (max_queue=50000, batch=100, flush=500ms)")

    while _writer_running:
        buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Collect up to 100 rows or wait 500ms
        total_rows = 0
        deadline = asyncio.get_event_loop().time() + 0.5
        while total_rows < 100:
            timeout = deadline - asyncio.get_event_loop().time()
            if timeout <= 0:
                break
            try:
                table, row = await asyncio.wait_for(_write_queue.get(), timeout=timeout)
                buffer[table].append(row)
                total_rows += 1
            except asyncio.TimeoutError:
                break
            except asyncio.CancelledError:
                _writer_running = False
                return

        # Flush all buffered rows
        if buffer:
            for table, rows in buffer.items():
                try:
                    await asyncio.to_thread(_flush_to_duckdb, table, rows)
                    _stats["rows_flushed"] += len(rows)
                except Exception as e:
                    _stats["errors"] += 1
                    logger.error("[db_writer] Flush failed for %s (%d rows): %s",
                                 table, len(rows), e)
            _stats["flush_count"] += 1


def _flush_to_duckdb(table: str, rows: List[Dict[str, Any]]):
    """Batch insert rows into DuckDB. Called in thread pool."""
    if not rows:
        return

    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()

        cols = list(rows[0].keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_list = ", ".join(cols)
        values = [tuple(r.get(c) for c in cols) for r in rows]

        conn.executemany(
            f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
            values,
        )
        logger.debug("[db_writer] Flushed %d rows to %s", len(rows), table)
    except Exception as e:
        # Log but don't crash — some tables may not exist yet
        logger.debug("[db_writer] Insert to %s failed: %s", table, e)


def stop_batch_writer():
    """Signal the writer to stop."""
    global _writer_running
    _writer_running = False


def get_writer_stats() -> Dict[str, Any]:
    """Return writer metrics for monitoring."""
    return {
        **_stats,
        "queue_depth": _write_queue.qsize(),
        "queue_max": _write_queue.maxsize,
        "running": _writer_running,
    }
