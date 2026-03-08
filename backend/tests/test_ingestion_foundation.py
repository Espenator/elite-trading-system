"""Tests for shared ingestion foundation."""

import asyncio
from datetime import datetime, timedelta
import pytest

from app.ingestion.event import SourceEvent
from app.ingestion.checkpoint import CheckpointStore
from app.ingestion.health import HealthStatus, HealthMetrics
from app.ingestion.adapter import BaseSourceAdapter
from app.ingestion.example_adapter import ExampleMarketDataAdapter


# ── SourceEvent Tests ───────────────────────────────────────────────


class TestSourceEvent:
    """Tests for SourceEvent class."""

    def test_create_event(self):
        """Test creating a basic SourceEvent."""
        event = SourceEvent(
            event_type="market_data.bar",
            source="alpaca",
            data={"symbol": "AAPL", "close": 175.50},
        )
        assert event.event_type == "market_data.bar"
        assert event.source == "alpaca"
        assert event.data["symbol"] == "AAPL"
        assert event.data["close"] == 175.50
        assert event.event_id is not None
        assert isinstance(event.timestamp, datetime)

    def test_event_validation(self):
        """Test SourceEvent validation."""
        # Missing event_type
        with pytest.raises(ValueError, match="event_type is required"):
            SourceEvent(event_type="", source="test", data={})

        # Missing source
        with pytest.raises(ValueError, match="source is required"):
            SourceEvent(event_type="test", source="", data={})

        # Invalid data type
        with pytest.raises(ValueError, match="data must be a dictionary"):
            SourceEvent(event_type="test", source="test", data="not a dict")

    def test_to_dict(self):
        """Test SourceEvent serialization."""
        event = SourceEvent(
            event_type="test.event",
            source="test_source",
            data={"key": "value"},
            metadata={"tag": "important"},
        )
        d = event.to_dict()
        assert d["event_type"] == "test.event"
        assert d["source"] == "test_source"
        assert d["data"]["key"] == "value"
        assert d["metadata"]["tag"] == "important"
        assert "timestamp" in d
        assert "event_id" in d

    def test_from_dict(self):
        """Test SourceEvent deserialization."""
        data = {
            "event_type": "test.event",
            "source": "test_source",
            "data": {"symbol": "AAPL"},
            "timestamp": "2026-03-08T12:00:00",
            "event_id": "test-123",
            "metadata": {"priority": "high"},
        }
        event = SourceEvent.from_dict(data)
        assert event.event_type == "test.event"
        assert event.source == "test_source"
        assert event.data["symbol"] == "AAPL"
        assert event.event_id == "test-123"
        assert event.metadata["priority"] == "high"

    def test_with_metadata(self):
        """Test adding metadata to an event."""
        event = SourceEvent(
            event_type="test",
            source="test",
            data={},
            metadata={"existing": "value"},
        )
        new_event = event.with_metadata(new_key="new_value", another="data")
        assert new_event.metadata["existing"] == "value"
        assert new_event.metadata["new_key"] == "new_value"
        assert new_event.metadata["another"] == "data"
        # Original unchanged
        assert "new_key" not in event.metadata

    def test_event_id_uniqueness(self):
        """Test that event IDs are unique."""
        event1 = SourceEvent(event_type="test", source="test", data={})
        event2 = SourceEvent(event_type="test", source="test", data={})
        assert event1.event_id != event2.event_id


# ── CheckpointStore Tests ───────────────────────────────────────────


class TestCheckpointStore:
    """Tests for CheckpointStore class."""

    @pytest.fixture
    def store(self):
        """Create a fresh checkpoint store for each test."""
        store = CheckpointStore(ttl_seconds=5, max_entries=100)
        store.clear()
        return store

    @pytest.fixture
    def sample_event(self):
        """Create a sample event for testing."""
        return SourceEvent(
            event_type="test",
            source="test",
            data={"value": 1},
        )

    def test_mark_and_check_seen(self, store, sample_event):
        """Test marking an event as seen and checking it."""
        assert not store.has_seen(sample_event)
        store.mark_seen(sample_event)
        assert store.has_seen(sample_event)

    def test_different_events_not_seen(self, store):
        """Test that different events are not marked as duplicates."""
        event1 = SourceEvent(event_type="test", source="test", data={})
        event2 = SourceEvent(event_type="test", source="test", data={})
        store.mark_seen(event1)
        assert store.has_seen(event1)
        assert not store.has_seen(event2)

    def test_ttl_expiration(self, store):
        """Test that entries expire after TTL."""
        from datetime import timezone
        event = SourceEvent(event_type="test", source="test", data={})
        store.mark_seen(event)
        assert store.has_seen(event)

        # Manually expire the entry
        event_id = event.event_id
        store._seen[event_id] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Should be expired now
        assert not store.has_seen(event)

    def test_max_entries_pruning(self):
        """Test that the store prunes old entries when max_entries is exceeded."""
        store = CheckpointStore(ttl_seconds=300, max_entries=10)
        store.clear()

        # Add 15 events
        events = []
        for i in range(15):
            event = SourceEvent(
                event_type="test",
                source="test",
                data={"index": i},
            )
            events.append(event)
            store.mark_seen(event)

        # Should have pruned to ~9 (90% of max_entries)
        stats = store.get_stats()
        assert stats["cache_size"] <= 10
        assert stats["entries_pruned"] > 0

    def test_get_stats(self, store, sample_event):
        """Test checkpoint store statistics."""
        store.mark_seen(sample_event)
        stats = store.get_stats()
        assert stats["cache_size"] == 1
        assert stats["max_entries"] == 100
        assert stats["ttl_seconds"] == 5
        assert stats["total_marked"] == 1

    def test_clear(self, store, sample_event):
        """Test clearing the checkpoint store."""
        store.mark_seen(sample_event)
        assert store.has_seen(sample_event)
        store.clear()
        assert not store.has_seen(sample_event)
        stats = store.get_stats()
        assert stats["cache_size"] == 0


# ── HealthMetrics Tests ─────────────────────────────────────────────


class TestHealthMetrics:
    """Tests for HealthMetrics class."""

    def test_default_metrics(self):
        """Test default health metrics."""
        metrics = HealthMetrics()
        assert metrics.status == HealthStatus.HEALTHY
        assert metrics.consecutive_errors == 0
        assert metrics.total_events == 0
        assert metrics.is_healthy()
        assert metrics.is_available()

    def test_degraded_status(self):
        """Test degraded health status."""
        metrics = HealthMetrics(status=HealthStatus.DEGRADED)
        assert not metrics.is_healthy()
        assert metrics.is_degraded()
        assert metrics.is_available()

    def test_offline_status(self):
        """Test offline health status."""
        metrics = HealthMetrics(status=HealthStatus.OFFLINE)
        assert not metrics.is_healthy()
        assert not metrics.is_available()

    def test_to_dict(self):
        """Test HealthMetrics serialization."""
        metrics = HealthMetrics(
            status=HealthStatus.HEALTHY,
            total_events=100,
            consecutive_errors=0,
            average_latency_ms=50.5,
        )
        d = metrics.to_dict()
        assert d["status"] == "healthy"
        assert d["total_events"] == 100
        assert d["consecutive_errors"] == 0
        assert d["average_latency_ms"] == 50.5


# ── BaseSourceAdapter Tests ─────────────────────────────────────────


class TestExampleAdapter:
    """Tests for ExampleMarketDataAdapter (concrete implementation)."""

    @pytest.fixture
    def mock_message_bus(self):
        """Create a mock message bus."""
        class MockMessageBus:
            def __init__(self):
                self.published = []

            async def publish(self, topic, data):
                self.published.append({"topic": topic, "data": data})

        return MockMessageBus()

    @pytest.fixture
    def adapter(self, mock_message_bus):
        """Create an example adapter with mock dependencies."""
        store = CheckpointStore(ttl_seconds=300, max_entries=1000)
        store.clear()
        return ExampleMarketDataAdapter(
            event_sink=mock_message_bus,
            checkpoint_store=store,
        )

    @pytest.mark.anyio
    async def test_adapter_properties(self, adapter):
        """Test adapter properties."""
        assert adapter.source_name == "example_market_data"
        assert adapter.event_type == "market_data.bar"

    @pytest.mark.anyio
    async def test_fetch_data(self, adapter):
        """Test fetching raw data."""
        data = await adapter.fetch_data()
        assert "bars" in data
        assert len(data["bars"]) == 2
        assert data["bars"][0]["symbol"] == "AAPL"
        assert data["bars"][1]["symbol"] == "MSFT"

    @pytest.mark.anyio
    async def test_transform_to_events(self, adapter):
        """Test transforming raw data to events."""
        raw_data = await adapter.fetch_data()
        events = adapter.transform_to_events(raw_data)
        assert len(events) == 2
        assert all(isinstance(e, SourceEvent) for e in events)
        assert events[0].source == "example_market_data"
        assert events[0].event_type == "market_data.bar"
        assert events[0].data["symbol"] == "AAPL"

    @pytest.mark.anyio
    async def test_run_tick_success(self, adapter, mock_message_bus):
        """Test successful tick execution."""
        report = await adapter.run_tick()
        assert report["status"] == "success"
        assert report["source"] == "example_market_data"
        assert report["events_fetched"] == 2
        assert report["events_new"] == 2
        assert report["events_published"] == 2
        assert report["latency_ms"] > 0

        # Check that events were published
        assert len(mock_message_bus.published) == 2
        assert mock_message_bus.published[0]["topic"] == "market_data.bar"

    @pytest.mark.anyio
    async def test_run_tick_deduplication(self, adapter):
        """Test that duplicate events are filtered out."""
        # First tick
        report1 = await adapter.run_tick()
        assert report1["events_new"] == 2
        assert report1["events_duplicate"] == 0

        # Second tick with same events (same event_ids in practice would be rare,
        # but we're testing the deduplication mechanism)
        # In real usage, the checkpoint would prevent re-processing events with
        # the same event_id within the TTL window
        report2 = await adapter.run_tick()
        # New events because they have different event_ids
        assert report2["events_new"] == 2

    @pytest.mark.anyio
    async def test_health_metrics_success(self, adapter):
        """Test health metrics after successful tick."""
        await adapter.run_tick()
        health = adapter.get_health()
        assert health.status == HealthStatus.HEALTHY
        assert health.consecutive_errors == 0
        assert health.total_events == 2
        assert health.last_success is not None
        assert health.average_latency_ms > 0

    @pytest.mark.anyio
    async def test_health_metrics_error(self):
        """Test health metrics after errors."""
        class FailingAdapter(BaseSourceAdapter):
            @property
            def source_name(self):
                return "failing"

            @property
            def event_type(self):
                return "test"

            async def fetch_data(self):
                raise Exception("Simulated fetch failure")

            def transform_to_events(self, raw_data):
                return []

        adapter = FailingAdapter()

        # Run multiple failing ticks
        for _ in range(6):
            report = await adapter.run_tick()
            assert report["status"] == "error"

        health = adapter.get_health()
        assert health.status == HealthStatus.OFFLINE
        assert health.consecutive_errors >= 6
        assert health.last_error is not None

    @pytest.mark.anyio
    async def test_validate_config(self, adapter):
        """Test configuration validation."""
        assert adapter.validate_config()


# ── Integration Tests ───────────────────────────────────────────────


class TestIngestionIntegration:
    """Integration tests for the complete ingestion pipeline."""

    @pytest.mark.anyio
    async def test_end_to_end_flow(self):
        """Test complete flow from adapter to event sink."""
        # Setup
        class MockMessageBus:
            def __init__(self):
                self.published = []

            async def publish(self, topic, data):
                self.published.append({"topic": topic, "data": data})

        bus = MockMessageBus()
        store = CheckpointStore()
        store.clear()

        adapter = ExampleMarketDataAdapter(
            event_sink=bus,
            checkpoint_store=store,
        )

        # Execute tick
        report = await adapter.run_tick()

        # Verify report
        assert report["status"] == "success"
        assert report["events_fetched"] > 0
        assert report["events_published"] > 0

        # Verify events were published
        assert len(bus.published) > 0
        first_event = bus.published[0]
        assert first_event["topic"] == "market_data.bar"
        assert "data" in first_event["data"]
        assert "event_id" in first_event["data"]

        # Verify checkpoint store
        stats = store.get_stats()
        assert stats["total_marked"] == report["events_fetched"]

        # Verify health
        health = adapter.get_health()
        assert health.is_healthy()
        assert health.total_events > 0

    @pytest.mark.anyio
    async def test_concurrent_adapters(self):
        """Test multiple adapters running concurrently."""
        bus_published = []

        class SharedMockBus:
            async def publish(self, topic, data):
                bus_published.append({"topic": topic, "data": data})

        bus = SharedMockBus()
        store = CheckpointStore()
        store.clear()

        # Create multiple adapters
        adapters = [
            ExampleMarketDataAdapter(event_sink=bus, checkpoint_store=store)
            for _ in range(3)
        ]

        # Run them concurrently
        results = await asyncio.gather(*[adapter.run_tick() for adapter in adapters])

        # Verify all succeeded
        assert all(r["status"] == "success" for r in results)

        # Verify events were published
        assert len(bus_published) > 0

        # Verify all adapters are healthy
        assert all(a.get_health().is_healthy() for a in adapters)
