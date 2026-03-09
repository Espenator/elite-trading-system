"""
Tests for Ingestion Framework

Tests for BaseSourceAdapter, CheckpointStore, AdapterRegistry, and IngestionScheduler.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.models.source_event import SourceEvent
from app.data.checkpoint_store import CheckpointStore
from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.registry import AdapterRegistry
from app.services.ingestion.scheduler import IngestionScheduler


# ==================== Fixtures ====================

@pytest.fixture
def temp_checkpoint_db():
    """Create a temporary checkpoint database"""
    # Create a temp file path but don't create the file itself
    # DuckDB will create the file when it connects
    fd, db_path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)  # Close the file descriptor
    os.remove(db_path)  # Remove the empty file so DuckDB can create it
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    # Also cleanup WAL file if it exists
    wal_path = db_path + ".wal"
    if os.path.exists(wal_path):
        os.remove(wal_path)


@pytest.fixture
def checkpoint_store(temp_checkpoint_db):
    """Create a CheckpointStore instance"""
    return CheckpointStore(temp_checkpoint_db)


@pytest.fixture
def mock_message_bus():
    """Create a mock message bus"""
    bus = Mock()
    bus.publish = AsyncMock()
    return bus


# ==================== Test SourceEvent Model ====================

def test_source_event_creation():
    """Test SourceEvent model creation"""
    event = SourceEvent(
        source="test_source",
        source_kind="test_kind",
        topic="test.topic",
        symbol="AAPL",
        occurred_at=datetime.utcnow()
    )
    assert event.source == "test_source"
    assert event.source_kind == "test_kind"
    assert event.topic == "test.topic"
    assert event.symbol == "AAPL"
    assert event.event_id is not None
    assert event.schema_version == "1.0"


def test_source_event_with_payload():
    """Test SourceEvent with payload_json"""
    event = SourceEvent(
        source="test_source",
        source_kind="test_kind",
        occurred_at=datetime.utcnow(),
        payload_json={"key": "value", "number": 42}
    )
    assert event.payload_json["key"] == "value"
    assert event.payload_json["number"] == 42


# ==================== Test CheckpointStore ====================

def test_checkpoint_store_initialization(checkpoint_store):
    """Test CheckpointStore initializes schema"""
    # Store should be ready to use
    checkpoint = checkpoint_store.get_checkpoint("nonexistent")
    assert checkpoint is None


def test_checkpoint_save_and_retrieve(checkpoint_store):
    """Test saving and retrieving checkpoints"""
    checkpoint_store.save_checkpoint(
        adapter_name="test_adapter",
        source_key="test_key",
        last_cursor="cursor_123",
        batch_id="batch_456",
        status="success",
        row_count=100
    )

    checkpoint = checkpoint_store.get_checkpoint("test_adapter")
    assert checkpoint is not None
    assert checkpoint["adapter_name"] == "test_adapter"
    assert checkpoint["source_key"] == "test_key"
    assert checkpoint["last_cursor"] == "cursor_123"
    assert checkpoint["batch_id"] == "batch_456"
    assert checkpoint["status"] == "success"
    assert checkpoint["row_count"] == 100


def test_checkpoint_update(checkpoint_store):
    """Test updating existing checkpoint"""
    # Save initial checkpoint
    checkpoint_store.save_checkpoint(
        adapter_name="test_adapter",
        batch_id="batch_1",
        status="success",
        row_count=50
    )

    # Update checkpoint
    checkpoint_store.save_checkpoint(
        adapter_name="test_adapter",
        batch_id="batch_2",
        status="success",
        row_count=75
    )

    checkpoint = checkpoint_store.get_checkpoint("test_adapter")
    assert checkpoint["batch_id"] == "batch_2"
    assert checkpoint["row_count"] == 75


def test_checkpoint_get_all(checkpoint_store):
    """Test getting all checkpoints"""
    checkpoint_store.save_checkpoint("adapter1", status="success", row_count=10)
    checkpoint_store.save_checkpoint("adapter2", status="success", row_count=20)
    checkpoint_store.save_checkpoint("adapter3", status="failed", row_count=0)

    all_checkpoints = checkpoint_store.get_all_checkpoints()
    assert len(all_checkpoints) == 3
    assert any(c["adapter_name"] == "adapter1" for c in all_checkpoints)
    assert any(c["adapter_name"] == "adapter2" for c in all_checkpoints)
    assert any(c["adapter_name"] == "adapter3" for c in all_checkpoints)


def test_checkpoint_clear(checkpoint_store):
    """Test clearing a checkpoint"""
    checkpoint_store.save_checkpoint("test_adapter", status="success", row_count=10)
    assert checkpoint_store.get_checkpoint("test_adapter") is not None

    checkpoint_store.clear_checkpoint("test_adapter")
    assert checkpoint_store.get_checkpoint("test_adapter") is None


# ==================== Test BaseSourceAdapter ====================

class MockAdapter(BaseSourceAdapter):
    """Mock adapter for testing"""

    def get_source_name(self):
        return "mock_adapter"

    def get_source_kind(self):
        return "mock"

    async def validate_credentials(self):
        return True

    async def fetch_incremental(self, last_cursor=None, last_timestamp=None):
        # Return mock events
        return [
            SourceEvent(
                source=self.get_source_name(),
                source_kind=self.get_source_kind(),
                topic="mock.event",
                symbol="TEST",
                occurred_at=datetime.utcnow(),
                payload_json={"test": "data"}
            )
        ]


@pytest.mark.asyncio
async def test_adapter_ingest(checkpoint_store, mock_message_bus):
    """Test adapter ingest method"""
    adapter = MockAdapter(checkpoint_store, mock_message_bus)

    result = await adapter.ingest()

    assert result["status"] == "success"
    assert result["row_count"] == 1
    assert result["adapter_name"] == "mock_adapter"

    # Check checkpoint was saved
    checkpoint = checkpoint_store.get_checkpoint("mock_adapter")
    assert checkpoint is not None
    assert checkpoint["status"] == "success"
    assert checkpoint["row_count"] == 1


@pytest.mark.asyncio
async def test_adapter_health_check(checkpoint_store, mock_message_bus):
    """Test adapter health check"""
    adapter = MockAdapter(checkpoint_store, mock_message_bus)

    # Run ingestion first
    await adapter.ingest()

    # Check health
    health = await adapter.health_check()
    assert health["adapter_name"] == "mock_adapter"
    assert health["source_kind"] == "mock"
    assert health["credentials_valid"] is True
    assert health["last_checkpoint"] is not None


@pytest.mark.asyncio
async def test_adapter_start_stop(checkpoint_store, mock_message_bus):
    """Test adapter start/stop lifecycle"""
    adapter = MockAdapter(checkpoint_store, mock_message_bus)

    assert adapter.is_running() is False

    await adapter.start()
    assert adapter.is_running() is True

    await adapter.stop()
    assert adapter.is_running() is False


# ==================== Test AdapterRegistry ====================

@pytest.mark.asyncio
async def test_adapter_registry_initialization(checkpoint_store, mock_message_bus):
    """Test AdapterRegistry initialization"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    adapters = registry.get_all_adapters()
    assert len(adapters) == 6  # 6 adapters
    assert "finviz" in adapters
    assert "fred" in adapters
    assert "unusual_whales" in adapters
    assert "sec_edgar" in adapters
    assert "openclaw" in adapters
    assert "alpaca_stream" in adapters


@pytest.mark.asyncio
async def test_adapter_registry_get_adapter(checkpoint_store, mock_message_bus):
    """Test getting specific adapter from registry"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    finviz_adapter = registry.get_adapter("finviz")
    assert finviz_adapter is not None
    assert finviz_adapter.get_source_name() == "finviz"

    nonexistent = registry.get_adapter("nonexistent")
    assert nonexistent is None


@pytest.mark.asyncio
async def test_adapter_registry_stats(checkpoint_store, mock_message_bus):
    """Test registry statistics"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    stats = registry.get_registry_stats()
    assert stats["total_adapters"] == 6
    assert stats["running_adapters"] == 0  # None started yet
    assert stats["stopped_adapters"] == 6
    assert len(stats["adapter_names"]) == 6


# ==================== Test IngestionScheduler ====================

@pytest.mark.asyncio
async def test_scheduler_initialization(checkpoint_store, mock_message_bus):
    """Test IngestionScheduler initialization"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    scheduler = IngestionScheduler(registry)
    assert scheduler.is_running() is False


@pytest.mark.asyncio
async def test_scheduler_schedule_adapter(checkpoint_store, mock_message_bus):
    """Test scheduling an adapter"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    scheduler = IngestionScheduler(registry)

    # Schedule finviz adapter
    scheduler.schedule_adapter("finviz")

    jobs = scheduler.get_scheduled_jobs()
    assert len(jobs) >= 1
    assert any("finviz" in job["id"] for job in jobs)


@pytest.mark.asyncio
async def test_scheduler_schedule_all(checkpoint_store, mock_message_bus):
    """Test scheduling all adapters"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    scheduler = IngestionScheduler(registry)
    scheduler.schedule_all_adapters()

    jobs = scheduler.get_scheduled_jobs()
    # Should have 5 scheduled jobs (not alpaca_stream which is continuous)
    assert len(jobs) == 5


@pytest.mark.asyncio
async def test_scheduler_start_stop(checkpoint_store, mock_message_bus):
    """Test scheduler lifecycle"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    scheduler = IngestionScheduler(registry)
    scheduler.schedule_all_adapters()

    scheduler.start()
    assert scheduler.is_running() is True

    scheduler.stop()
    assert scheduler.is_running() is False


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_full_ingestion_workflow(checkpoint_store, mock_message_bus):
    """Test complete ingestion workflow"""
    # Create registry and scheduler
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    # Mock the finviz adapter's fetch method to avoid real API calls
    finviz_adapter = registry.get_adapter("finviz")
    finviz_adapter.fetch_incremental = AsyncMock(return_value=[
        SourceEvent(
            source="finviz",
            source_kind="screener",
            topic="finviz.screener",
            symbol="AAPL",
            occurred_at=datetime.utcnow(),
            payload_json={"price": 150.00}
        )
    ])

    # Run ingestion
    result = await registry.run_adapter("finviz")

    assert result["status"] == "success"
    assert result["row_count"] == 1

    # Verify checkpoint was saved
    checkpoint = checkpoint_store.get_checkpoint("finviz")
    assert checkpoint is not None
    assert checkpoint["status"] == "success"


@pytest.mark.asyncio
async def test_health_check_all_adapters(checkpoint_store, mock_message_bus):
    """Test health checking all adapters"""
    registry = AdapterRegistry(checkpoint_store, mock_message_bus)
    registry.initialize_adapters()

    health_checks = await registry.health_check_all()

    assert len(health_checks) == 6
    for health in health_checks:
        assert "adapter_name" in health
        assert "source_kind" in health
        assert "is_running" in health
