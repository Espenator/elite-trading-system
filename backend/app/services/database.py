"""Database service for SQLite operations (orders + app config).

Enhancements (Feb 26, 2026 - Intelligence Council Audit):
- WAL journal mode for concurrent read/write
- busy_timeout to prevent 'database is locked' errors
- Connection pooling via thread-local storage
- Indexes on symbol and created_at for query performance
- Context manager for safe connection handling
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


# Database file path
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "trading_orders.db"

# Connection pool settings
_BUSY_TIMEOUT_MS = 5000
_thread_local = threading.local()


def _get_pooled_conn(db_path: str = None) -> sqlite3.Connection:
    """Get a thread-local pooled connection with WAL mode and busy_timeout.
    
    Each thread reuses its own connection, reducing overhead from
    creating new connections on every call.
    """
    path = db_path or str(DB_PATH)
    conn = getattr(_thread_local, 'conn', None)
    conn_path = getattr(_thread_local, 'conn_path', None)
    
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


@contextmanager
def _db_cursor(db_path: str = None, row_factory=None):
    """Context manager for database operations with proper error handling.
    
    Usage:
        with _db_cursor(row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute('SELECT ...')
            rows = cursor.fetchall()
    """
    conn = _get_pooled_conn(db_path)
    if row_factory:
        conn.row_factory = row_factory
    else:
        conn.row_factory = None
    cursor = conn.cursor()
    try:
        yield conn, cursor
    except Exception:
        conn.rollback()
        raise


class DatabaseService:
    """Service for managing SQLite database operations.
    
    Uses WAL mode, connection pooling, and proper indexing
    for production-grade SQLite performance.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize database service."""
        self.db_path = db_path or str(DB_PATH)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables, indexes, and PRAGMAs if they don't exist."""
        with _db_cursor(self.db_path) as (conn, cursor):
            # Create orders table
            cursor.execute("""
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
            
            # Add new columns if they don't exist (for existing databases)
            for col in ['alpaca_order_id TEXT', 'alpaca_status TEXT', 'alpaca_response TEXT']:
                try:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            # Performance indexes (P0 fix from council audit)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_symbol
                ON orders (symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_created_at
                ON orders (created_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status
                ON orders (status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_symbol_created
                ON orders (symbol, created_at DESC)
            """)
            
            # App config: key-value store for settings, risk, strategy_controls (JSON)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Alert rules
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    condition_key TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
            """)

            # Persistent idempotency for jobs (restart-safe; no in-memory-only keys)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_idempotency (
                    job_name TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (job_name, idempotency_key)
                )
            """)

            conn.commit()
    
    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        quantity: int,
        price: float,
        estimated_cost: float = None,
        required_margin: float = None,
        potential_pnl: float = None,
        alpaca_order_id: str = None,
        alpaca_status: str = None,
        alpaca_response: str = None
    ) -> Dict:
        """Create a new order."""
        with _db_cursor(self.db_path) as (conn, cursor):
            now = datetime.now().isoformat()
            if estimated_cost is None:
                estimated_cost = quantity * price
            if required_margin is None:
                required_margin = estimated_cost * 0.5
            if potential_pnl is None:
                potential_pnl = 0.0
            
            # Map Alpaca status to our status
            status = 'Pending'
            if alpaca_status:
                if alpaca_status in ['filled', 'partially_filled']:
                    status = 'Filled'
                elif alpaca_status == 'canceled':
                    status = 'Cancelled'
                elif alpaca_status == 'rejected':
                    status = 'Rejected'
                else:
                    status = 'Pending'
            
            cursor.execute("""
                INSERT INTO orders (
                    symbol, order_type, side, quantity, price, status,
                    created_at, estimated_cost, required_margin, potential_pnl,
                    alpaca_order_id, alpaca_status, alpaca_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, order_type, side, quantity, price, status,
                now, estimated_cost, required_margin, potential_pnl,
                alpaca_order_id, alpaca_status, alpaca_response
            ))
            
            order_id = cursor.lastrowid
            conn.commit()
        
        return self.get_order_by_id(order_id)
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get order by ID."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get recent orders, limited to specified count."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM orders
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_all_orders(self) -> List[Dict]:
        """Get all orders."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """Update order status."""
        with _db_cursor(self.db_path) as (conn, cursor):
            filled_at = datetime.now().isoformat() if status == 'Filled' else None
            
            cursor.execute("""
                UPDATE orders
                SET status = ?, filled_at = ?
                WHERE id = ?
            """, (status, filled_at, order_id))
            
            success = cursor.rowcount > 0
            conn.commit()
        
        return success
    
    # --- Config (settings, risk, strategy_controls) ---
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Load JSON config by key. Returns default if missing."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
        
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return default
    
    def set_config(self, key: str, value: Any) -> None:
        """Save JSON config by key."""
        with _db_cursor(self.db_path) as (conn, cursor):
            cursor.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )
            conn.commit()

    # --- Job idempotency (durable; restart-safe) ---

    def get_idempotency_run(self, job_name: str, idempotency_key: str) -> Optional[str]:
        """Return completed_at timestamp if this job+key already ran, else None."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute(
                "SELECT completed_at FROM job_idempotency WHERE job_name = ? AND idempotency_key = ?",
                (job_name, idempotency_key),
            )
            row = cursor.fetchone()
        return row[0] if row else None

    def set_idempotency_run(self, job_name: str, idempotency_key: str) -> None:
        """Record that this job+key completed (idempotent: same key skips on next run)."""
        now = datetime.now().isoformat()
        with _db_cursor(self.db_path) as (conn, cursor):
            cursor.execute(
                """INSERT OR REPLACE INTO job_idempotency (job_name, idempotency_key, completed_at, created_at)
                   VALUES (?, ?, ?, ?)""",
                (job_name, idempotency_key, now, now),
            )
            conn.commit()

    # --- Alert rules ---
    
    def get_alert_rules(self) -> List[Dict]:
        """Return all alert rules (id, name, condition, enabled)."""
        with _db_cursor(self.db_path, row_factory=sqlite3.Row) as (conn, cursor):
            cursor.execute("SELECT id, name, condition_key, enabled FROM alert_rules ORDER BY id")
            rows = cursor.fetchall()
        
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "condition": r["condition_key"],
                "enabled": bool(r["enabled"]),
            }
            for r in rows
        ]
    
    def ensure_alert_rules_seeded(self, default_rules: List[Dict]) -> None:
        """If no rules exist, insert defaults."""
        with _db_cursor(self.db_path) as (conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM alert_rules")
            if cursor.fetchone()[0] > 0:
                return
            for r in default_rules:
                cursor.execute(
                    "INSERT INTO alert_rules (name, condition_key, enabled) VALUES (?, ?, ?)",
                    (r["name"], r["condition"], 1 if r.get("enabled", True) else 0),
                )
            conn.commit()
    
    def update_alert_rule_enabled(self, rule_id: int, enabled: bool) -> Optional[Dict]:
        """Set enabled for a rule. Returns updated rule or None if not found."""
        with _db_cursor(self.db_path) as (conn, cursor):
            cursor.execute("UPDATE alert_rules SET enabled = ? WHERE id = ?", (1 if enabled else 0, rule_id))
            if cursor.rowcount == 0:
                return None
            conn.commit()
            cursor.execute("SELECT id, name, condition_key, enabled FROM alert_rules WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
        
        if not row:
            return None
        return {"id": row[0], "name": row[1], "condition": row[2], "enabled": bool(row[3])}


# Global database service instance
db_service = DatabaseService()
