"""Data storage facade -- bridges app.data.storage imports to the
real DatabaseService in app.services.database.

Exports used across the codebase:
    get_conn()     -> sqlite3.Connection  (thread-local, WAL-mode)
    DB_PATH        -> pathlib.Path to the SQLite file
    init_schema()  -> create tables/indexes on startup

Fixes Issue #11 -- CRITICAL missing module.
"""

import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export DB_PATH from the canonical database service
# ---------------------------------------------------------------------------
try:
    from app.services.database import DB_PATH, DB_DIR
except ImportError:
    # Fallback if database.py hasn't been loaded yet
    DB_DIR = Path(__file__).parent.parent.parent / "data"
    DB_DIR.mkdir(exist_ok=True)
    DB_PATH = DB_DIR / "trading_orders.db"

# ---------------------------------------------------------------------------
# Connection pool (mirrors database.py implementation)
# ---------------------------------------------------------------------------
_BUSY_TIMEOUT_MS = 5000
_thread_local = threading.local()


def get_conn(db_path: str = None) -> sqlite3.Connection:
    """Return a thread-local pooled SQLite connection with WAL mode.

    This is the primary entry point used by:
        - api/v1/status.py
        - api/v1/signals.py
        - modules/ml_engine/trainer.py
        - strategy/backtest.py
    """
    path = db_path or str(DB_PATH)
    conn = getattr(_thread_local, "conn", None)
    conn_path = getattr(_thread_local, "conn_path", None)

    if conn is None or conn_path != path:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
        conn = sqlite3.connect(path)
        conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        _thread_local.conn = conn
        _thread_local.conn_path = path

    return conn


def init_schema() -> None:
    """Create all required tables and indexes.

    Called from main.py lifespan on startup.
    Delegates to DatabaseService._init_database() to stay DRY.
    """
    try:
        from app.services.database import db_service  # noqa: F811
        # db_service.__init__ already calls _init_database()
        logger.info("Schema initialized via DatabaseService (tables + indexes)")
    except Exception as exc:
        logger.warning("init_schema fallback -- manual table creation: %s", exc)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                filled_at TEXT,
                estimated_cost REAL,
                required_margin REAL,
                potential_pnl REAL,
                alpaca_order_id TEXT,
                alpaca_status TEXT,
                alpaca_response TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition_key TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC)")
        conn.commit()
        logger.info("Schema initialized via fallback SQL")
