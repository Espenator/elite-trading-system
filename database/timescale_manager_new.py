import os, logging, yaml, psycopg2
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
from psycopg2 import pool, extras

logger = logging.getLogger(__name__)

class TimescaleDBManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self.db_config = self.config.get('database', {})
        self.connection_pool = None
        self.pool_min_conn = self.db_config.get('pool_min_connections', 2)
        self.pool_max_conn = self.db_config.get('pool_max_connections', 20)
        self.host = self.db_config.get('host', 'localhost')
        self.port = self.db_config.get('port', 5432)
        self.database = self.db_config.get('database', 'elite_trading')
        self.user = self.db_config.get('user', 'postgres')
        self.password = self.db_config.get('password')
        self.last_health_check = None
        self.is_healthy = False
        logger.info(f"TimescaleDB Manager initialized - {self.host}:{self.port}/{self.database}")
    
    def _find_config(self):
        for path in ['config/config.yaml', '../config/config.yaml', os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')]:
            if os.path.exists(path):
                logger.info(f"Found config at: {path}")
                return path
        raise FileNotFoundError("config.yaml not found")
    
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {'database': {'host': 'localhost', 'port': 5432, 'database': 'elite_trading', 'user': 'postgres', 'password': None}}
    
    def initialize_pool(self):
        try:
            if self.connection_pool:
                return True
            logger.info(f"Initializing connection pool ({self.pool_min_conn}-{self.pool_max_conn} connections)...")
            params = {'minconn': self.pool_min_conn, 'maxconn': self.pool_max_conn, 'host': self.host, 'port': self.port, 'database': self.database, 'user': self.user, 'connect_timeout': 10}
            if self.password and self.password.strip():
                params['password'] = self.password
            self.connection_pool = pool.ThreadedConnectionPool(**params)
            test = self.connection_pool.getconn()
            if test:
                self.connection_pool.putconn(test)
                logger.info("Connection pool initialized successfully")
                self.is_healthy = True
                return True
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self.is_healthy = False
            return False
    
    @contextmanager
    def get_connection(self):
        if not self.connection_pool:
            self.initialize_pool()
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory) if cursor_factory else conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Cursor error: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query, params=None, fetch=True):
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall() if fetch else None
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
    
    def execute_dict_query(self, query, params=None):
        try:
            with self.get_cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except:
            return None
    
    def execute_many(self, query, data):
        if not data:
            return True
        try:
            with self.get_cursor() as cursor:
                extras.execute_batch(cursor, query, data, page_size=1000)
            return True
        except:
            return False
    
    def health_check(self):
        try:
            result = self.execute_query("SELECT 1")
            self.is_healthy = result is not None
            return self.is_healthy
        except:
            self.is_healthy = False
            return False
    
    def get_symbol_id(self, ticker):
        result = self.execute_query("SELECT symbol_id FROM symbols WHERE ticker = %s", (ticker.upper(),))
        return result[0][0] if result else None
    
    def insert_symbol(self, ticker, company_name=None, sector=None, is_tracked=True):
        existing = self.get_symbol_id(ticker)
        if existing:
            return existing
        result = self.execute_query("INSERT INTO symbols (ticker, company_name, sector, is_tracked) VALUES (%s, %s, %s, %s) ON CONFLICT (ticker) DO UPDATE SET last_updated = NOW() RETURNING symbol_id", (ticker.upper(), company_name, sector, is_tracked))
        return result[0][0] if result else None
    
    def get_active_symbols(self, tracked_only=True):
        query = "SELECT * FROM symbols WHERE is_active = TRUE" + (" AND is_tracked = TRUE" if tracked_only else "") + " ORDER BY ticker"
        return self.execute_dict_query(query) or []
    
    def get_database_stats(self):
        return {}
    
    def close_pool(self):
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None
    
    def __del__(self):
        self.close_pool()

_db_manager_instance = None

def get_db_manager():
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = TimescaleDBManager()
        _db_manager_instance.initialize_pool()
    return _db_manager_instance
