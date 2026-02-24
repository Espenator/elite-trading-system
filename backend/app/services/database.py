"""Database service for SQLite operations (orders + app config)."""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

# Database file path
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "trading_orders.db"


def _get_conn():
    return sqlite3.connect(DB_PATH)


class DatabaseService:
    """Service for managing SQLite database operations."""
    
    def __init__(self, db_path: str = None):
        """Initialize database service."""
        self.db_path = db_path or str(DB_PATH)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN alpaca_order_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN alpaca_status TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN alpaca_response TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

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
        conn.commit()
        conn.close()
    
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        estimated_cost = estimated_cost or (quantity * price)
        required_margin = required_margin or (estimated_cost * 0.5)
        potential_pnl = potential_pnl or (estimated_cost * 0.02)
        
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
        conn.close()
        
        return self.get_order_by_id(order_id)
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get order by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get recent orders, limited to specified count."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM orders
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_orders(self) -> List[Dict]:
        """Get all orders."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """Update order status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        filled_at = datetime.now().isoformat() if status == 'Filled' else None
        
        cursor.execute("""
            UPDATE orders
            SET status = ?, filled_at = ?
            WHERE id = ?
        """, (status, filled_at, order_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

    # --- Config (settings, risk, strategy_controls) ---
    def get_config(self, key: str, default: Any = None) -> Any:
        """Load JSON config by key. Returns default if missing."""
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return default

    def set_config(self, key: str, value: Any) -> None:
        """Save JSON config by key."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        conn.commit()
        conn.close()

    # --- Alert rules ---
    def get_alert_rules(self) -> List[Dict]:
        """Return all alert rules (id, name, condition, enabled)."""
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, condition_key, enabled FROM alert_rules ORDER BY id")
        rows = cur.fetchall()
        conn.close()
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alert_rules")
        if cur.fetchone()[0] > 0:
            conn.close()
            return
        for r in default_rules:
            cur.execute(
                "INSERT INTO alert_rules (name, condition_key, enabled) VALUES (?, ?, ?)",
                (r["name"], r["condition"], 1 if r.get("enabled", True) else 0),
            )
        conn.commit()
        conn.close()

    def update_alert_rule_enabled(self, rule_id: int, enabled: bool) -> Optional[Dict]:
        """Set enabled for a rule. Returns updated rule or None if not found."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE alert_rules SET enabled = ? WHERE id = ?", (1 if enabled else 0, rule_id))
        if cur.rowcount == 0:
            conn.close()
            return None
        conn.commit()
        cur.execute("SELECT id, name, condition_key, enabled FROM alert_rules WHERE id = ?", (rule_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "condition": row[2], "enabled": bool(row[3])}


# Global database service instance
db_service = DatabaseService()

