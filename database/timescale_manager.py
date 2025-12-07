import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)

class TimescaleDBManager:
    """SQLite-based database manager (replaces TimescaleDB for simplicity)"""
    
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize SQLite database manager"""
        self.config_path = config_path
        self.connection = None
        self._load_config()
        self._initialize_database()
        
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                db_config = config.get('database', {})
                self.db_path = db_config.get('path', 'data/elite_trading.db')
                logger.info(f"Found config at: {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.db_path = 'data/elite_trading.db'
    
    def _initialize_database(self):
        """Initialize SQLite database and create tables"""
        try:
            # Create data directory if it doesn't exist
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Create tables
            self._create_tables()
            
            logger.info(f"OK SQLite database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.connection = None
    
    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.connection.cursor()
        
        # Symbols table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Market data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                horizon TEXT NOT NULL,
                prediction_time DATETIME NOT NULL,
                target_time DATETIME NOT NULL,
                predicted_price REAL,
                confidence REAL,
                actual_price REAL,
                resolved BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Model parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horizon TEXT NOT NULL,
                parameters TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Model weights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horizon TEXT NOT NULL,
                weights TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Options flow table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flow_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.connection.commit()
        logger.info("OK Database tables created")
    
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            if not self.connection:
                return False
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Dict]]:
        """Execute SQL query"""
        try:
            if not self.connection:
                logger.error("Database not connected")
                return None
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                self.connection.commit()
                return None
                
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
    
    def execute_dict_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute query and return results as list of dicts (alias for execute_query)"""
        return self.execute_query(query, params, fetch=True)
    
    def get_symbol_id(self, symbol: str) -> Optional[int]:
        """Get or create symbol ID"""
        try:
            # Try to get existing
            result = self.execute_query("SELECT id FROM symbols WHERE symbol = ?", (symbol,))
            if result and len(result) > 0:
                return result[0]['id']
            
            # Insert new symbol
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO symbols (symbol) VALUES (?)", (symbol,))
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to get symbol ID: {e}")
            return None
    
    def insert_market_data(self, symbol: str, data: Dict) -> bool:
        """Insert market data"""
        query = """
            INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            symbol,
            data.get('timestamp'),
            data.get('open'),
            data.get('high'),
            data.get('low'),
            data.get('close'),
            data.get('volume')
        )
        result = self.execute_query(query, params, fetch=False)
        return result is not None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol"""
        query = """
            SELECT close FROM market_data 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """
        result = self.execute_query(query, (symbol,))
        if result and len(result) > 0:
            return result[0]['close']
        return None
    
    def insert_prediction(self, symbol: str, horizon: str, prediction_data: Dict) -> bool:
        """Insert prediction"""
        query = """
            INSERT INTO predictions (symbol, horizon, prediction_time, target_time, predicted_price, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            symbol,
            horizon,
            prediction_data.get('prediction_time'),
            prediction_data.get('target_time'),
            prediction_data.get('predicted_price'),
            prediction_data.get('confidence')
        )
        result = self.execute_query(query, params, fetch=False)
        return result is not None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

# Global instance
_db_manager = None

def get_db_manager(config_path: str = 'config/config.yaml') -> TimescaleDBManager:
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = TimescaleDBManager(config_path)
    return _db_manager

