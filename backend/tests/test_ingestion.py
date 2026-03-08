"""Tests for data ingestion adapters."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from app.models.source_event import SourceEvent
from app.data.checkpoint_store import CheckpointStore
from app.services.ingestion.base import BaseSourceAdapter, AdapterHealth
from app.services.ingestion.adapter_registry import AdapterRegistry, get_adapter_registry
from app.services.ingestion.finviz_adapter import FinvizAdapter
from app.services.ingestion.fred_adapter import FredAdapter
from app.services.ingestion.unusual_whales_adapter import UnusualWhalesAdapter
from app.services.ingestion.sec_edgar_adapter import SecEdgarAdapter
from app.services.ingestion.openclaw_adapter import OpenClawAdapter


# Test SourceEvent model
def test_source_event_creation():
    """Test creating a SourceEvent."""
    event = SourceEvent(
        event_id="test_123",
        source="test_source",
        event_type="test_type",
        event_time=datetime.utcnow(),
        symbol="AAPL",
        data={"key": "value"},
        metadata={"meta": "data"}
    )

    assert event.event_id == "test_123"
    assert event.source == "test_source"
    assert event.event_type == "test_type"
    assert event.symbol == "AAPL"
    assert event.data["key"] == "value"
    assert event.metadata["meta"] == "data"


def test_source_event_optional_fields():
    """Test SourceEvent with optional fields."""
    event = SourceEvent(
        event_id="test_456",
        source="test",
        event_type="type",
        event_time=datetime.utcnow()
    )

    assert event.symbol is None
    assert event.data == {}
    assert event.metadata == {}
    assert event.ingested_at is not None


# Test CheckpointStore
@pytest.fixture
def checkpoint_store():
    """Create a CheckpointStore for testing."""
    with patch('app.data.checkpoint_store.DuckDBManager') as mock_db:
        mock_instance = Mock()
        mock_instance.execute = Mock()
        mock_instance.query = Mock(return_value=[])
        mock_db.return_value = mock_instance
        store = CheckpointStore(db_manager=mock_instance)
        yield store


def test_checkpoint_store_save(checkpoint_store):
    """Test saving a checkpoint."""
    checkpoint_store.save_checkpoint(
        adapter_id="test_adapter",
        last_event_id="event_123",
        last_event_time=datetime.utcnow(),
        checkpoint_data={"key": "value"}
    )

    # Verify execute was called
    assert checkpoint_store.db.execute.called


def test_checkpoint_store_get_missing(checkpoint_store):
    """Test getting a checkpoint that doesn't exist."""
    checkpoint_store.db.query.return_value = []
    result = checkpoint_store.get_checkpoint("nonexistent")
    assert result is None


def test_checkpoint_store_get_existing(checkpoint_store):
    """Test getting an existing checkpoint."""
    now = datetime.utcnow()
    checkpoint_store.db.query.return_value = [[
        "test_adapter",
        "event_123",
        now,
        '{"key": "value"}',
        now
    ]]

    result = checkpoint_store.get_checkpoint("test_adapter")
    assert result is not None
    assert result["adapter_id"] == "test_adapter"
    assert result["last_event_id"] == "event_123"


# Test BaseSourceAdapter
class TestAdapter(BaseSourceAdapter):
    """Test implementation of BaseSourceAdapter."""

    def __init__(self, **kwargs):
        super().__init__(adapter_id="test_adapter", **kwargs)
        self.fetch_called = False

    async def fetch_events(self, since=None):
        self.fetch_called = True
        return [
            SourceEvent(
                event_id="test_1",
                source="test",
                event_type="test",
                event_time=datetime.utcnow(),
                symbol="AAPL",
                data={"test": "data"}
            )
        ]

    def get_topic(self):
        return "test.topic"


@pytest.mark.asyncio
async def test_adapter_run():
    """Test running an adapter."""
    with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
        mock_bus_instance = AsyncMock()
        mock_bus.return_value = mock_bus_instance

        adapter = TestAdapter()
        count = await adapter.run()

        assert count == 1
        assert adapter.fetch_called
        assert mock_bus_instance.publish.called


@pytest.mark.asyncio
async def test_adapter_run_with_checkpoint():
    """Test adapter run uses checkpoint."""
    with patch('app.data.checkpoint_store.DuckDBManager'):
        checkpoint_store = CheckpointStore()
        checkpoint_store.get_checkpoint = Mock(return_value={
            "last_event_time": datetime(2026, 1, 1)
        })
        checkpoint_store.save_checkpoint = Mock()

        with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
            mock_bus_instance = AsyncMock()
            mock_bus.return_value = mock_bus_instance

            adapter = TestAdapter(checkpoint_store=checkpoint_store)
            await adapter.run()

            assert checkpoint_store.get_checkpoint.called
            assert checkpoint_store.save_checkpoint.called


def test_adapter_health():
    """Test adapter health status."""
    adapter = TestAdapter()
    health = adapter.get_health()

    assert isinstance(health, AdapterHealth)
    assert health.adapter_id == "test_adapter"
    assert not health.is_healthy  # No successful run yet


@pytest.mark.asyncio
async def test_adapter_health_after_run():
    """Test adapter health after successful run."""
    with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
        mock_bus_instance = AsyncMock()
        mock_bus.return_value = mock_bus_instance

        adapter = TestAdapter()
        await adapter.run()

        health = adapter.get_health()
        assert health.is_healthy
        assert health.last_success is not None
        assert health.events_ingested == 1


# Test AdapterRegistry
def test_adapter_registry_register():
    """Test registering an adapter."""
    registry = AdapterRegistry()
    adapter = TestAdapter()

    registry.register(adapter)

    assert "test_adapter" in registry.get_adapter_ids()
    assert registry.get("test_adapter") == adapter


def test_adapter_registry_get_all():
    """Test getting all adapters."""
    registry = AdapterRegistry()
    adapter1 = TestAdapter()

    registry.register(adapter1)

    all_adapters = registry.get_all()
    assert len(all_adapters) == 1
    assert adapter1 in all_adapters


@pytest.mark.asyncio
async def test_adapter_registry_run_adapter():
    """Test running a specific adapter via registry."""
    with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
        mock_bus_instance = AsyncMock()
        mock_bus.return_value = mock_bus_instance

        registry = AdapterRegistry()
        adapter = TestAdapter()
        registry.register(adapter)

        count = await registry.run_adapter("test_adapter")

        assert count == 1
        assert adapter.fetch_called


@pytest.mark.asyncio
async def test_adapter_registry_run_all():
    """Test running all adapters."""
    with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
        mock_bus_instance = AsyncMock()
        mock_bus.return_value = mock_bus_instance

        registry = AdapterRegistry()
        adapter = TestAdapter()
        registry.register(adapter)

        results = await registry.run_all()

        assert "test_adapter" in results
        assert results["test_adapter"] == 1


def test_adapter_registry_health():
    """Test getting health status from registry."""
    registry = AdapterRegistry()
    adapter = TestAdapter()
    registry.register(adapter)

    health = registry.get_health("test_adapter")

    assert "test_adapter" in health
    assert isinstance(health["test_adapter"], AdapterHealth)


def test_adapter_registry_health_summary():
    """Test getting health summary."""
    registry = AdapterRegistry()
    adapter = TestAdapter()
    registry.register(adapter)

    summary = registry.get_health_summary()

    assert summary["total_adapters"] == 1
    assert summary["healthy_adapters"] == 0  # No successful run yet
    assert summary["unhealthy_adapters"] == 1
    assert "adapters" in summary


# Test specific adapters
@pytest.mark.asyncio
async def test_finviz_adapter():
    """Test Finviz adapter fetch."""
    with patch('app.services.ingestion.finviz_adapter.FinvizService') as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_intraday_screen = AsyncMock(return_value=[
            {"Ticker": "AAPL", "Price": "150.00"}
        ])
        mock_service.return_value = mock_instance

        adapter = FinvizAdapter()
        adapter.finviz = mock_instance

        events = await adapter.fetch_events()

        assert len(events) > 0
        assert all(e.source == "finviz" for e in events)


@pytest.mark.asyncio
async def test_fred_adapter():
    """Test FRED adapter fetch."""
    with patch('app.services.ingestion.fred_adapter.FredService') as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_latest_value = AsyncMock(return_value={
            "date": "2026-03-08",
            "value": "15.5"
        })
        mock_service.return_value = mock_instance

        adapter = FredAdapter()
        adapter.fred = mock_instance

        events = await adapter.fetch_events()

        assert len(events) > 0
        assert all(e.source == "fred" for e in events)
        assert all(e.event_type == "economic_indicator" for e in events)


@pytest.mark.asyncio
async def test_unusual_whales_adapter():
    """Test Unusual Whales adapter fetch."""
    with patch('app.services.ingestion.unusual_whales_adapter.UnusualWhalesService') as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_flow_alerts = AsyncMock(return_value=[
            {"ticker": "AAPL", "premium": 250000}
        ])
        mock_instance.get_congress_trades = AsyncMock(return_value=[])
        mock_instance.get_insider_trades = AsyncMock(return_value=[])
        mock_instance.get_darkpool_flow = AsyncMock(return_value=[])
        mock_service.return_value = mock_instance

        adapter = UnusualWhalesAdapter()
        adapter.uw = mock_instance

        events = await adapter.fetch_events()

        assert len(events) > 0
        assert all(e.source == "unusual_whales" for e in events)


@pytest.mark.asyncio
async def test_sec_edgar_adapter():
    """Test SEC Edgar adapter fetch."""
    with patch('app.services.ingestion.sec_edgar_adapter.SecEdgarService') as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_recent_forms = AsyncMock(return_value=[
            {"ticker": "AAPL", "accessionNumber": "0001234567", "filingDate": "2026-03-08"}
        ])
        mock_service.return_value = mock_instance

        adapter = SecEdgarAdapter()
        adapter.edgar = mock_instance

        events = await adapter.fetch_events()

        # Should fetch multiple form types
        assert mock_instance.get_recent_forms.call_count >= len(adapter.form_types)


@pytest.mark.asyncio
async def test_openclaw_adapter():
    """Test OpenClaw adapter fetch."""
    with patch('app.services.ingestion.openclaw_adapter.OpenClawBridgeService') as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_regime = AsyncMock(return_value={"regime": "bull"})
        mock_instance.get_top_candidates = AsyncMock(return_value=[
            {"symbol": "AAPL", "score": 0.95}
        ])
        mock_instance.get_whale_flow = AsyncMock(return_value=[])
        mock_service.return_value = mock_instance

        adapter = OpenClawAdapter()
        adapter.openclaw = mock_instance

        events = await adapter.fetch_events()

        assert len(events) >= 2  # At least regime + 1 candidate
        assert all(e.source == "openclaw" for e in events)


# Test error handling
@pytest.mark.asyncio
async def test_adapter_run_error_handling():
    """Test adapter handles errors gracefully."""

    class ErrorAdapter(BaseSourceAdapter):
        async def fetch_events(self, since=None):
            raise ValueError("Test error")

        def get_topic(self):
            return "test.topic"

    adapter = ErrorAdapter(adapter_id="error_adapter")

    with pytest.raises(ValueError):
        await adapter.run()

    health = adapter.get_health()
    assert not health.is_healthy
    assert health.last_error is not None


@pytest.mark.asyncio
async def test_registry_run_adapter_not_found():
    """Test running non-existent adapter raises error."""
    registry = AdapterRegistry()

    with pytest.raises(ValueError, match="Adapter not found"):
        await registry.run_adapter("nonexistent")


def test_adapter_reset_checkpoint():
    """Test resetting adapter checkpoint."""
    with patch('app.data.checkpoint_store.DuckDBManager'):
        checkpoint_store = CheckpointStore()
        checkpoint_store.delete_checkpoint = Mock()

        adapter = TestAdapter(checkpoint_store=checkpoint_store)
        adapter.reset_checkpoint()

        assert checkpoint_store.delete_checkpoint.called


# Test global registry
def test_get_adapter_registry_singleton():
    """Test that get_adapter_registry returns singleton."""
    registry1 = get_adapter_registry()
    registry2 = get_adapter_registry()

    assert registry1 is registry2


@pytest.mark.asyncio
async def test_adapter_publishes_to_message_bus():
    """Test that adapter publishes events to message bus."""
    with patch('app.services.ingestion.base.get_message_bus') as mock_bus:
        mock_bus_instance = AsyncMock()
        mock_bus_instance.publish = AsyncMock()
        mock_bus.return_value = mock_bus_instance

        adapter = TestAdapter()
        await adapter.run()

        # Verify publish was called with correct topic
        mock_bus_instance.publish.assert_called()
        call_args = mock_bus_instance.publish.call_args
        assert call_args[0][0] == "test.topic"  # First arg is topic
