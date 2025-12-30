"""Database service for SQLite operations."""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Database file path
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "trading_orders.db"


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


# Global database service instance
db_service = DatabaseService()

