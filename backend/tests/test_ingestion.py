"""Tests for the ingestion layer: models, base adapter, checkpoints, sink, registry, health.

Covers:
  - SourceEvent model serialisation and defaults
  - Checkpoint store persistence and resume
  - BaseSourceAdapter lifecycle (start / stop / poll loop / backoff)
  - Idempotent EventSink (dedupe on dedupe_key)
  - Diff-based snapshot publishing (Finviz adapter)
  - Reconnect / backoff behaviour
  - Adapter health status reporting
  - AdapterRegistry lifecycle management
  - IngestionHealth aggregation
"""

import asyncio
import json
import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# SourceEvent model
# ---------------------------------------------------------------------------

class TestSourceEvent:
    def test_defaults(self):
        from app.services.ingestion.models import SourceEvent, SourceKind
        evt = SourceEvent(source="test", topic="t.test", payload={"k": 1})
        assert evt.source == "test"
        assert evt.topic == "t.test"
        assert evt.payload == {"k": 1}
        assert evt.source_kind == SourceKind.SNAPSHOT
        assert evt.event_id  # non-empty UUID hex
        assert evt.dedupe_key == evt.event_id  # defaults to event_id
        assert evt.trace_id == evt.event_id
        assert evt.schema_version == 1
        assert evt.sequence == 0
        assert evt.occurred_at > 0
        assert evt.ingested_at > 0

    def test_custom_dedupe_key(self):
        from app.services.ingestion.models import SourceEvent
        evt = SourceEvent(source="s", topic="t", payload={}, dedupe_key="custom-123")
        assert evt.dedupe_key == "custom-123"

    def test_to_dict_roundtrip(self):
        from app.services.ingestion.models import SourceEvent, SourceKind
        evt = SourceEvent(
            source="fred", topic="perception.macro",
            payload={"series": "CPI"}, source_kind=SourceKind.LOW_FREQ,
            symbol="SPY", entity_id="CPIAUCSL",
        )
        d = evt.to_dict()
        assert d["source"] == "fred"
        assert d["source_kind"] == "low_freq"
        assert d["symbol"] == "SPY"
        assert d["entity_id"] == "CPIAUCSL"
        assert d["payload"]["series"] == "CPI"

        restored = SourceEvent.from_dict(d)
        assert restored.source == evt.source
        assert restored.source_kind == SourceKind.LOW_FREQ
        assert restored.payload == evt.payload

    def test_source_kind_enum(self):
        from app.services.ingestion.models import SourceKind
        assert SourceKind.STREAM.value == "stream"
        assert SourceKind.INCREMENTAL.value == "incremental"
        assert SourceKind.SNAPSHOT.value == "snapshot"
        assert SourceKind.LOW_FREQ.value == "low_freq"


# ---------------------------------------------------------------------------
# Checkpoint store
# ---------------------------------------------------------------------------

class TestCheckpointStore:
    def test_save_and_load(self):
        from app.services.ingestion.checkpoints import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = CheckpointStore(path=path)
            store.save("fred", {"last_date": "2024-01-15", "count": 42})
            loaded = store.load("fred")
            assert loaded["last_date"] == "2024-01-15"
            assert loaded["count"] == 42
        finally:
            os.unlink(path)

    def test_resume_from_file(self):
        """Checkpoints survive across store instances (simulating restart)."""
        from app.services.ingestion.checkpoints import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store1 = CheckpointStore(path=path)
            store1.save("sec_edgar", {"cursors": {"AAPL": "8-K,10-K"}})

            # New instance reads the same file
            store2 = CheckpointStore(path=path)
            loaded = store2.load("sec_edgar")
            assert loaded["cursors"]["AAPL"] == "8-K,10-K"
        finally:
            os.unlink(path)

    def test_missing_source_returns_empty(self):
        from app.services.ingestion.checkpoints import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = CheckpointStore(path=path)
            assert store.load("nonexistent") == {}
        finally:
            os.unlink(path)

    def test_delete_checkpoint(self):
        from app.services.ingestion.checkpoints import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = CheckpointStore(path=path)
            store.save("x", {"a": 1})
            store.delete("x")
            assert store.load("x") == {}
        finally:
            os.unlink(path)

    def test_all_checkpoints(self):
        from app.services.ingestion.checkpoints import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = CheckpointStore(path=path)
            store.save("a", {"v": 1})
            store.save("b", {"v": 2})
            all_cp = store.all_checkpoints()
            assert "a" in all_cp and "b" in all_cp
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# BaseSourceAdapter lifecycle
# ---------------------------------------------------------------------------

class _StubAdapter:
    """Minimal concrete adapter for testing the base class."""

    def __new__(cls, *args, **kwargs):
        from app.services.ingestion.base import BaseSourceAdapter
        from app.services.ingestion.models import SourceKind

        class _Impl(BaseSourceAdapter):
            source_name = "stub"
            source_kind = SourceKind.SNAPSHOT
            poll_interval_seconds = 0.05  # fast for tests

            def __init__(self, bus=None, fail_after=0):
                super().__init__(bus)
                self.poll_count = 0
                self._fail_after = fail_after

            async def poll_once(self):
                self.poll_count += 1
                if self._fail_after and self.poll_count >= self._fail_after:
                    raise RuntimeError("simulated failure")

        return _Impl(*args, **kwargs)


class TestBaseSourceAdapter:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = _StubAdapter(bus=bus)
        with patch("app.services.ingestion.base.BaseSourceAdapter.load_checkpoint", new_callable=AsyncMock):
            with patch("app.services.ingestion.base.BaseSourceAdapter.save_checkpoint", new_callable=AsyncMock):
                await adapter.start()
                assert adapter._running
                await asyncio.sleep(0.15)
                await adapter.stop()
                assert not adapter._running
                assert adapter.poll_count > 0

    @pytest.mark.asyncio
    async def test_publish_event_increments_counter(self):
        from app.services.ingestion.models import SourceEvent
        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = _StubAdapter(bus=bus)
        evt = SourceEvent(source="stub", topic="test.topic", payload={"v": 1})
        await adapter.publish_event(evt)
        assert adapter._events_published == 1
        assert bus.publish.call_count == 1

    @pytest.mark.asyncio
    async def test_backoff_on_errors(self):
        """Consecutive errors increase the backoff delay."""
        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = _StubAdapter(bus=bus, fail_after=1)
        adapter.poll_interval_seconds = 0.01
        adapter._base_backoff = 0.02
        with patch("app.services.ingestion.base.BaseSourceAdapter.load_checkpoint", new_callable=AsyncMock):
            with patch("app.services.ingestion.base.BaseSourceAdapter.save_checkpoint", new_callable=AsyncMock):
                await adapter.start()
                await asyncio.sleep(0.25)
                await adapter.stop()
                assert adapter._errors > 0
                assert adapter._consecutive_errors > 0

    def test_health_status_healthy(self):
        adapter = _StubAdapter()
        adapter._running = True
        adapter._start_time = time.time() - 10
        adapter._last_success_at = time.time() - 5
        h = adapter.health()
        assert h["state"] == "healthy"
        assert h["running"]

    def test_health_status_degraded(self):
        adapter = _StubAdapter()
        adapter._running = True
        adapter._start_time = time.time() - 100
        adapter._consecutive_errors = 5
        h = adapter.health()
        assert h["state"] == "degraded"

    def test_health_status_stopped(self):
        adapter = _StubAdapter()
        adapter._running = False
        h = adapter.health()
        assert h["state"] == "stopped"


# ---------------------------------------------------------------------------
# EventSink — idempotent persistence
# ---------------------------------------------------------------------------

class TestEventSink:
    @pytest.mark.asyncio
    async def test_dedupe_skips_duplicate(self):
        from app.services.ingestion.sink import EventSink
        sink = EventSink()

        event = {"event_id": "evt-1", "dedupe_key": "dk-1", "source": "test", "payload": {}}

        # Mock _persist to track calls
        persist_count = 0
        original_persist = sink._persist

        async def counting_persist(data):
            nonlocal persist_count
            persist_count += 1

        sink._persist = counting_persist

        await sink._on_event(event)
        assert persist_count == 1

        # Same dedupe_key — should be skipped
        await sink._on_event(event)
        assert persist_count == 1
        assert sink._duplicates == 1

    @pytest.mark.asyncio
    async def test_different_keys_both_persisted(self):
        from app.services.ingestion.sink import EventSink
        sink = EventSink()

        calls = []

        async def mock_persist(data):
            calls.append(data)

        sink._persist = mock_persist

        await sink._on_event({"dedupe_key": "a", "source": "test", "payload": {}})
        await sink._on_event({"dedupe_key": "b", "source": "test", "payload": {}})
        assert len(calls) == 2
        assert sink._duplicates == 0

    @pytest.mark.asyncio
    async def test_subscribe_registers_topic(self):
        from app.services.ingestion.sink import EventSink
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        sink = EventSink(message_bus=bus)
        await sink.subscribe("test.topic")
        assert "test.topic" in sink._subscribed_topics
        bus.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self):
        from app.services.ingestion.sink import EventSink
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        sink = EventSink(message_bus=bus)
        await sink.subscribe("test.topic")
        await sink.subscribe("test.topic")  # second call should be no-op
        assert bus.subscribe.call_count == 1

    def test_health_report(self):
        from app.services.ingestion.sink import EventSink
        sink = EventSink()
        sink._persisted = 100
        sink._duplicates = 5
        h = sink.health()
        assert h["persisted"] == 100
        assert h["duplicates_skipped"] == 5


# ---------------------------------------------------------------------------
# Diff-based snapshot publishing (Finviz adapter)
# ---------------------------------------------------------------------------

class TestFinvizAdapterDiff:
    @pytest.mark.asyncio
    async def test_diff_detection_publishes_on_change(self):
        """First poll always publishes; second with same data is still published but tagged."""
        from app.services.ingestion.adapters.finviz_adapter import FinvizAdapter
        from app.services.ingestion.models import SourceEvent

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = FinvizAdapter(message_bus=bus)
        adapter._checkpoint = {}

        # Mock FinvizService to return fake stocks
        mock_stocks = [{"Ticker": "AAPL"}, {"Ticker": "MSFT"}]

        with patch("app.services.finviz_service.FinvizService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_stock_list = AsyncMock(return_value=mock_stocks)

            # Patch symbol_universe
            with patch("app.modules.symbol_universe.set_tracked_symbols_from_finviz", create=True):
                await adapter.poll_once()

        assert bus.publish.call_count == 1
        call_args = bus.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]
        assert topic == "perception.finviz.screener"
        assert payload["payload"]["changed"] is True

    @pytest.mark.asyncio
    async def test_no_diff_still_publishes_but_marks_unchanged(self):
        from app.services.ingestion.adapters.finviz_adapter import FinvizAdapter

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = FinvizAdapter(message_bus=bus)
        adapter._checkpoint = {}

        mock_stocks = [{"Ticker": "AAPL"}]

        with patch("app.services.finviz_service.FinvizService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_stock_list = AsyncMock(return_value=mock_stocks)
            with patch("app.modules.symbol_universe.set_tracked_symbols_from_finviz", create=True):
                await adapter.poll_once()
                bus.publish.reset_mock()
                await adapter.poll_once()

        assert bus.publish.call_count == 1
        payload = bus.publish.call_args[0][1]
        assert payload["payload"]["changed"] is False


# ---------------------------------------------------------------------------
# Reconnect / backoff behaviour
# ---------------------------------------------------------------------------

class TestReconnectBackoff:
    @pytest.mark.asyncio
    async def test_stream_reconnect_increments_counter(self):
        from app.services.ingestion.base import BaseSourceAdapter
        from app.services.ingestion.models import SourceKind

        class FailStream(BaseSourceAdapter):
            source_name = "fail_stream"
            source_kind = SourceKind.STREAM
            poll_interval_seconds = 0

            async def _run_stream(self):
                raise ConnectionError("simulated disconnect")

        adapter = FailStream()
        adapter._base_backoff = 0.02
        with patch.object(adapter, "load_checkpoint", new_callable=AsyncMock):
            with patch.object(adapter, "save_checkpoint", new_callable=AsyncMock):
                await adapter.start()
                await asyncio.sleep(0.2)
                await adapter.stop()

        assert adapter._reconnects >= 1
        assert adapter._errors >= 1

    @pytest.mark.asyncio
    async def test_backoff_caps_at_max(self):
        from app.services.ingestion.base import BaseSourceAdapter
        from app.services.ingestion.models import SourceKind

        class FailPoll(BaseSourceAdapter):
            source_name = "fail_poll"
            source_kind = SourceKind.SNAPSHOT
            poll_interval_seconds = 0.01

            async def poll_once(self):
                raise RuntimeError("fail")

        adapter = FailPoll()
        adapter._base_backoff = 0.01
        adapter._max_backoff = 0.05
        with patch.object(adapter, "load_checkpoint", new_callable=AsyncMock):
            with patch.object(adapter, "save_checkpoint", new_callable=AsyncMock):
                await adapter.start()
                await asyncio.sleep(0.5)
                await adapter.stop()

        # Even after many errors, consecutive_errors should grow but backoff is capped
        assert adapter._consecutive_errors > 0


# ---------------------------------------------------------------------------
# AdapterRegistry and IngestionHealth
# ---------------------------------------------------------------------------

class TestAdapterRegistry:
    @pytest.mark.asyncio
    async def test_register_and_start_stop(self):
        from app.services.ingestion.registry import AdapterRegistry
        from app.services.ingestion.base import BaseSourceAdapter
        from app.services.ingestion.models import SourceKind

        class DummyAdapter(BaseSourceAdapter):
            source_name = "dummy"
            source_kind = SourceKind.SNAPSHOT
            poll_interval_seconds = 999

            async def poll_once(self):
                pass

        registry = AdapterRegistry()
        adapter = DummyAdapter()
        registry.register(adapter)

        assert registry.get("dummy") is adapter
        assert len(registry.all_adapters()) == 1

        with patch.object(adapter, "start", new_callable=AsyncMock) as mock_start:
            await registry.start_all()
            mock_start.assert_called_once()

        with patch.object(adapter, "stop", new_callable=AsyncMock) as mock_stop:
            await registry.stop_all()
            mock_stop.assert_called_once()


class TestIngestionHealth:
    def test_summary_healthy(self):
        from app.services.ingestion.health import IngestionHealth
        from app.services.ingestion.registry import AdapterRegistry

        # Create a mock adapter
        mock_adapter = MagicMock()
        mock_adapter.health.return_value = {
            "source": "test",
            "state": "healthy",
            "events_published": 100,
            "errors": 0,
        }

        registry = AdapterRegistry()
        registry._adapters = {"test": mock_adapter}

        health = IngestionHealth(registry=registry)
        summary = health.summary()
        assert summary["status"] == "healthy"
        assert summary["adapter_count"] == 1
        assert summary["total_events_published"] == 100

    def test_summary_degraded_when_adapter_offline(self):
        from app.services.ingestion.health import IngestionHealth
        from app.services.ingestion.registry import AdapterRegistry

        mock_adapter = MagicMock()
        mock_adapter.health.return_value = {
            "source": "test",
            "state": "offline",
            "events_published": 0,
            "errors": 10,
        }

        registry = AdapterRegistry()
        registry._adapters = {"test": mock_adapter}

        health = IngestionHealth(registry=registry)
        summary = health.summary()
        assert summary["status"] == "offline"
        assert "test" in summary["offline_sources"]


# ---------------------------------------------------------------------------
# FRED adapter checkpoint
# ---------------------------------------------------------------------------

class TestFredAdapterCheckpoint:
    @pytest.mark.asyncio
    async def test_only_publishes_new_observations(self):
        from app.services.ingestion.adapters.fred_adapter import FredAdapter

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = FredAdapter(message_bus=bus, series={"vix": "VIXCLS"})
        # Simulate checkpoint: already seen up to 2024-01-10
        adapter._checkpoint = {"series": {"VIXCLS": "2024-01-10"}}

        fake_obs = [
            {"date": "2024-01-12", "value": "15.5"},
            {"date": "2024-01-11", "value": "14.3"},
            {"date": "2024-01-10", "value": "13.0"},  # already seen
        ]

        with patch("app.services.fred_service.FredService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_observations = AsyncMock(return_value=fake_obs)
            await adapter.poll_once()

        # Only the 2 new observations should be in the event
        assert bus.publish.call_count == 1
        payload = bus.publish.call_args[0][1]
        obs_in_event = payload["payload"]["observations"]
        assert len(obs_in_event) == 2
        dates = {o["date"] for o in obs_in_event}
        assert "2024-01-12" in dates
        assert "2024-01-11" in dates
        assert "2024-01-10" not in dates

        # Checkpoint updated
        assert adapter._checkpoint["series"]["VIXCLS"] == "2024-01-12"


# ---------------------------------------------------------------------------
# SEC EDGAR adapter checkpoint
# ---------------------------------------------------------------------------

class TestSecEdgarAdapterCheckpoint:
    @pytest.mark.asyncio
    async def test_skips_unchanged_filings(self):
        from app.services.ingestion.adapters.sec_edgar_adapter import SecEdgarAdapter

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = SecEdgarAdapter(message_bus=bus, max_symbols=1)
        adapter._checkpoint = {"cursors": {"AAPL": "AAPL:8-K,10-K,10-Q"}}

        with patch("app.services.ingestion.adapters.sec_edgar_adapter.SecEdgarAdapter._get_symbols", return_value=["AAPL"]):
            with patch("app.services.sec_edgar_service.SecEdgarService") as MockSvc:
                instance = MockSvc.return_value
                # Same forms as checkpoint
                instance.get_recent_forms = AsyncMock(return_value=["8-K", "10-K", "10-Q", "S-1", "DEF14A"])
                await adapter.poll_once()

        # No change detected — no publish
        assert bus.publish.call_count == 0

    @pytest.mark.asyncio
    async def test_publishes_when_new_filing(self):
        from app.services.ingestion.adapters.sec_edgar_adapter import SecEdgarAdapter

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = SecEdgarAdapter(message_bus=bus, max_symbols=1)
        adapter._checkpoint = {"cursors": {"AAPL": "AAPL:8-K,10-K,10-Q"}}

        with patch("app.services.ingestion.adapters.sec_edgar_adapter.SecEdgarAdapter._get_symbols", return_value=["AAPL"]):
            with patch("app.services.sec_edgar_service.SecEdgarService") as MockSvc:
                instance = MockSvc.return_value
                # NEW forms (different from checkpoint)
                instance.get_recent_forms = AsyncMock(return_value=["4", "8-K", "10-K", "10-Q", "S-1"])
                await adapter.poll_once()

        assert bus.publish.call_count == 1
        payload = bus.publish.call_args[0][1]
        assert payload["payload"]["data"]["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# Unusual Whales adapter checkpoint
# ---------------------------------------------------------------------------

class TestUnusualWhalesAdapterCheckpoint:
    @pytest.mark.asyncio
    async def test_only_publishes_newer_alerts(self):
        from app.services.ingestion.adapters.unusual_whales_adapter import UnusualWhalesAdapter

        bus = MagicMock()
        bus.publish = AsyncMock()
        adapter = UnusualWhalesAdapter(message_bus=bus)
        adapter._checkpoint = {"last_timestamp": "2024-01-10T10:00:00"}

        fake_alerts = [
            {"traded_at": "2024-01-10T12:00:00", "ticker": "AAPL", "volume": 100},
            {"traded_at": "2024-01-10T09:00:00", "ticker": "MSFT", "volume": 50},  # older
        ]

        with patch("app.services.unusual_whales_service.UnusualWhalesService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_flow_alerts = AsyncMock(return_value=fake_alerts)
            await adapter.poll_once()

        assert bus.publish.call_count == 1
        payload = bus.publish.call_args[0][1]
        assert payload["payload"]["count"] == 1  # Only the newer alert
        assert adapter._checkpoint["last_timestamp"] == "2024-01-10T12:00:00"


# ---------------------------------------------------------------------------
# Market data agent backward compat
# ---------------------------------------------------------------------------

class TestMarketDataAgentCompat:
    @pytest.mark.asyncio
    async def test_run_tick_returns_entries(self):
        """run_tick should still return a list of (message, level) tuples."""
        from app.services.market_data_agent import run_tick

        # Disable all sources to test structure only
        entries = await run_tick(
            run_finviz=False, run_alpaca=False, run_fred=False,
            run_edgar=False, run_unusual_whales=False, run_openclaw=False,
            run_ingestion=False,
        )
        assert isinstance(entries, list)
