"""Test DatabaseManager singleton."""
import pytest


@pytest.mark.asyncio
async def test_database_manager_singleton():
    """Test that get_database_manager returns the same instance."""
    from app.data.database_manager import get_database_manager

    manager1 = get_database_manager()
    manager2 = get_database_manager()

    assert manager1 is manager2, "DatabaseManager should be a singleton"


@pytest.mark.asyncio
async def test_database_manager_initialize():
    """Test database manager initialization."""
    from app.data.database_manager import get_database_manager

    manager = get_database_manager()
    results = await manager.initialize()

    # Check that initialization returns results for all services
    assert "database_service" in results
    assert "duckdb_storage" in results
    assert "openclaw_service" in results

    # At least one service should initialize successfully
    successful = [
        r for r in results.values()
        if r.get("status") == "initialized"
    ]
    assert len(successful) > 0, "At least one database service should initialize"


@pytest.mark.asyncio
async def test_database_manager_health_check():
    """Test database manager health check."""
    from app.data.database_manager import get_database_manager

    manager = get_database_manager()
    await manager.initialize()

    health = await manager.health_check()

    # Check that health check returns status for manager and all services
    assert "database_manager" in health
    assert health["database_manager"]["initialized"] is True


@pytest.mark.asyncio
async def test_database_manager_properties():
    """Test database manager property accessors."""
    from app.data.database_manager import get_database_manager

    manager = get_database_manager()
    await manager.initialize()

    # Test property accessors (should not raise exceptions)
    database_service = manager.database_service
    duckdb_storage = manager.duckdb_storage
    openclaw_service = manager.openclaw_service

    # All should be accessible (may be None if initialization failed)
    assert database_service is not None or manager._initialization_errors.get("database_service")
    assert duckdb_storage is not None or manager._initialization_errors.get("duckdb_storage")
    assert openclaw_service is not None or manager._initialization_errors.get("openclaw_service")


@pytest.mark.asyncio
async def test_database_manager_shutdown():
    """Test database manager shutdown."""
    from app.data.database_manager import get_database_manager

    manager = get_database_manager()
    await manager.initialize()

    # Shutdown should not raise exceptions
    await manager.shutdown()

    # After shutdown, initialized flag should be False
    assert manager.is_initialized is False
