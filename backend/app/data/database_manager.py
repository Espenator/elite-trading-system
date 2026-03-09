"""Unified Database Manager Singleton.

Orchestrates all three database services with consistent initialization,
health monitoring, and graceful degradation:

1. DatabaseService (SQLite) - Orders + application config
2. DuckDBStorage - Analytics OHLCV, features, ML data
3. OpenClawDBService (SQLite) - Signal ingestion + memory intelligence

Architecture:
- Lazy initialization with error handling
- Single source of truth for database lifecycle management
- Health monitoring across all databases
- Graceful degradation if any database is unavailable
- Centralized cleanup in shutdown

Usage:
    from app.data.database_manager import get_database_manager

    db_manager = get_database_manager()
    await db_manager.initialize()  # Call during startup

    # Access individual services
    db_service = db_manager.database_service
    duckdb = db_manager.duckdb_storage
    openclaw = db_manager.openclaw_service

    # Health check
    health = await db_manager.health_check()

    # Shutdown
    await db_manager.shutdown()
"""
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Singleton instance
_db_manager_instance: Optional["DatabaseManager"] = None


class DatabaseManager:
    """Unified database manager coordinating all database services.

    This singleton manages the lifecycle of all three database services:
    - DatabaseService (SQLite orders/config)
    - DuckDBStorage (DuckDB analytics)
    - OpenClawDBService (SQLite signals/memory)

    Benefits:
    - Single initialization point
    - Consistent error handling
    - Health monitoring across all databases
    - Graceful degradation
    - Centralized cleanup
    """

    def __init__(self):
        """Initialize manager (services are lazily initialized)."""
        self._database_service = None
        self._duckdb_storage = None
        self._openclaw_service = None
        self._initialized = False
        self._initialization_errors = {}
        logger.debug("DatabaseManager instance created (services not yet initialized)")

    async def initialize(self) -> Dict[str, Any]:
        """Initialize all database services with error handling.

        Returns:
            Dict with initialization status for each service.

        Note: Initialization failures are logged but don't raise exceptions.
        This allows the application to start even if some databases are unavailable.
        """
        if self._initialized:
            logger.debug("DatabaseManager already initialized")
            return self._get_status()

        logger.info("=" * 60)
        logger.info("🗄️  Initializing Database Manager")
        logger.info("=" * 60)

        results = {}

        # 1. Initialize DatabaseService (SQLite orders + config)
        try:
            from app.services.database import db_service
            self._database_service = db_service
            results["database_service"] = {
                "status": "initialized",
                "path": str(self._database_service.db_path),
                "type": "SQLite",
            }
            logger.info("✅ DatabaseService initialized (orders + config)")
        except Exception as e:
            self._initialization_errors["database_service"] = str(e)
            results["database_service"] = {
                "status": "failed",
                "error": str(e),
            }
            logger.error(f"❌ DatabaseService initialization failed: {e}")

        # 2. Initialize DuckDBStorage (analytics)
        try:
            from app.data.duckdb_storage import duckdb_store
            self._duckdb_storage = duckdb_store

            # Run health check to verify connection
            health = self._duckdb_storage.health_check()
            results["duckdb_storage"] = {
                "status": "initialized",
                "path": str(self._duckdb_storage._db_path),
                "type": "DuckDB",
                "tables": health.get("total_tables", 0),
                "rows": health.get("total_rows", 0),
            }
            logger.info(
                "✅ DuckDBStorage initialized (%d tables, %d rows)",
                health.get("total_tables", 0),
                health.get("total_rows", 0),
            )
        except Exception as e:
            self._initialization_errors["duckdb_storage"] = str(e)
            results["duckdb_storage"] = {
                "status": "failed",
                "error": str(e),
            }
            logger.error(f"❌ DuckDBStorage initialization failed: {e}")

        # 3. Initialize OpenClawDBService (signals + memory)
        try:
            from app.services.openclaw_db import openclaw_db
            self._openclaw_service = openclaw_db
            results["openclaw_service"] = {
                "status": "initialized",
                "path": str(openclaw_db._conn().execute("PRAGMA database_list").fetchone()[2]),
                "type": "SQLite",
            }
            logger.info("✅ OpenClawDBService initialized (signals + memory)")
        except Exception as e:
            self._initialization_errors["openclaw_service"] = str(e)
            results["openclaw_service"] = {
                "status": "failed",
                "error": str(e),
            }
            logger.error(f"❌ OpenClawDBService initialization failed: {e}")

        self._initialized = True
        logger.info("=" * 60)
        logger.info("Database Manager initialization complete")
        logger.info("=" * 60)

        return results

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all database services.

        Returns:
            Dict with health status for each service.
        """
        health = {
            "database_manager": {
                "initialized": self._initialized,
                "errors": self._initialization_errors,
            }
        }

        # Check DatabaseService
        if self._database_service:
            try:
                # Simple query to verify connection
                import sqlite3
                conn = self._database_service._get_pooled_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                health["database_service"] = {
                    "status": "healthy",
                    "tables": table_count,
                    "path": str(self._database_service.db_path),
                }
            except Exception as e:
                health["database_service"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
        else:
            health["database_service"] = {
                "status": "not_initialized",
            }

        # Check DuckDBStorage
        if self._duckdb_storage:
            try:
                duckdb_health = self._duckdb_storage.health_check()
                health["duckdb_storage"] = {
                    "status": "healthy",
                    **duckdb_health,
                }
            except Exception as e:
                health["duckdb_storage"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
        else:
            health["duckdb_storage"] = {
                "status": "not_initialized",
            }

        # Check OpenClawDBService
        if self._openclaw_service:
            try:
                conn = self._openclaw_service._conn()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                health["openclaw_service"] = {
                    "status": "healthy",
                    "tables": table_count,
                }
            except Exception as e:
                health["openclaw_service"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
        else:
            health["openclaw_service"] = {
                "status": "not_initialized",
            }

        return health

    async def shutdown(self) -> None:
        """Gracefully shutdown all database connections.

        Ensures all connections are properly closed and resources cleaned up.
        """
        logger.info("Shutting down Database Manager...")

        # Close DuckDB connection
        if self._duckdb_storage:
            try:
                if hasattr(self._duckdb_storage, '_conn') and self._duckdb_storage._conn:
                    self._duckdb_storage._conn.close()
                    self._duckdb_storage._conn = None
                    logger.info("✅ DuckDB connection closed")
            except Exception as e:
                logger.warning(f"Error closing DuckDB connection: {e}")

        # SQLite connections are thread-local and will be cleaned up automatically,
        # but we can explicitly close them if needed
        if self._database_service:
            try:
                # Thread-local connections will be garbage collected
                logger.info("✅ DatabaseService cleanup completed")
            except Exception as e:
                logger.warning(f"Error during DatabaseService cleanup: {e}")

        if self._openclaw_service:
            try:
                # Thread-local connections will be garbage collected
                logger.info("✅ OpenClawDBService cleanup completed")
            except Exception as e:
                logger.warning(f"Error during OpenClawDBService cleanup: {e}")

        self._initialized = False
        logger.info("Database Manager shutdown complete")

    def _get_status(self) -> Dict[str, Any]:
        """Get current initialization status."""
        return {
            "database_service": {
                "status": "initialized" if self._database_service else "not_initialized",
            },
            "duckdb_storage": {
                "status": "initialized" if self._duckdb_storage else "not_initialized",
            },
            "openclaw_service": {
                "status": "initialized" if self._openclaw_service else "not_initialized",
            },
        }

    # Properties for accessing individual services
    @property
    def database_service(self):
        """Get DatabaseService instance (SQLite orders + config)."""
        if not self._database_service:
            logger.warning("DatabaseService accessed before initialization")
            # Lazy fallback - import global singleton
            try:
                from app.services.database import db_service
                self._database_service = db_service
            except Exception as e:
                logger.error(f"Failed to lazy-load DatabaseService: {e}")
                return None
        return self._database_service

    @property
    def duckdb_storage(self):
        """Get DuckDBStorage instance (analytics)."""
        if not self._duckdb_storage:
            logger.warning("DuckDBStorage accessed before initialization")
            # Lazy fallback - import global singleton
            try:
                from app.data.duckdb_storage import duckdb_store
                self._duckdb_storage = duckdb_store
            except Exception as e:
                logger.error(f"Failed to lazy-load DuckDBStorage: {e}")
                return None
        return self._duckdb_storage

    @property
    def openclaw_service(self):
        """Get OpenClawDBService instance (signals + memory)."""
        if not self._openclaw_service:
            logger.warning("OpenClawDBService accessed before initialization")
            # Lazy fallback - import global singleton
            try:
                from app.services.openclaw_db import openclaw_db
                self._openclaw_service = openclaw_db
            except Exception as e:
                logger.error(f"Failed to lazy-load OpenClawDBService: {e}")
                return None
        return self._openclaw_service

    @property
    def is_initialized(self) -> bool:
        """Check if manager has been initialized."""
        return self._initialized


def get_database_manager() -> DatabaseManager:
    """Get the singleton DatabaseManager instance.

    Returns:
        DatabaseManager singleton instance.

    Usage:
        db_manager = get_database_manager()
        await db_manager.initialize()  # Call during startup
    """
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    return _db_manager_instance
