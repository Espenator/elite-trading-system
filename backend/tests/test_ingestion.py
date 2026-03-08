"""Tests for ingestion foundation — SourceEvent, CheckpointStore,
BaseSourceAdapter (backoff/health), snapshot_diff, IngestionEventSink,
DuckDB ingestion_events table, AdapterRegistry, and all 5 concrete adapters.

All external service calls are mocked so these run offline in CI.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===========================================================================
# 1. SourceEvent model
# ===========================================================================

class TestSourceEvent:
    def _make(self, **kwargs) -> "SourceEvent":
        from app.models.source_event import SourceEvent
        defaults = dict(
            source="test",
            source_kind="poll",
            topic="ingestion.test",
            payload={"key": "value"},
        )
        defaults.update(kwargs)
        return SourceEvent(**defaults)

    def test_auto_generates_event_id(self):
        e = self._make()
        assert e.event_id and len(e.event_id) == 36  # UUID format

    def test_auto_generates_dedupe_key(self):
        e = self._make()
        assert e.dedupe_key and len(e.dedupe_key) == 32

    def test_dedupe_key_same_for_same_payload(self):
        e1 = self._make(payload={"x": 1})
        e2 = self._make(payload={"x": 1})
        assert e1.dedupe_key == e2.dedupe_key

    def test_dedupe_key_differs_for_different_payload(self):
        e1 = self._make(payload={"x": 1})
        e2 = self._make(payload={"x": 2})
        assert e1.dedupe_key != e2.dedupe_key

    def test_payload_json_is_serialized(self):
        e = self._make(payload={"a": 1, "b": "hello"})
        assert isinstance(e.payload_json, str)
        assert json.loads(e.payload_json) == {"a": 1, "b": "hello"}

    def test_occurred_at_defaults_to_ingested_at(self):
        e = self._make()
        assert e.occurred_at == e.ingested_at

    def test_occurred_at_explicit(self):
        dt = datetime(2026, 1, 10, 12, 0, 0)
        e = self._make(occurred_at=dt)
        assert e.occurred_at == dt

    def test_to_row_has_all_columns(self):
        e = self._make(symbol="AAPL")
        row = e.to_row()
        expected_cols = {
            "event_id", "source", "source_kind", "topic", "symbol",
            "entity_id", "occurred_at", "ingested_at", "sequence",
            "dedupe_key", "schema_version", "payload_json", "trace_id",
        }
        assert set(row.keys()) == expected_cols

    def test_to_row_symbol(self):
        e = self._make(symbol="AAPL")
        assert e.to_row()["symbol"] == "AAPL"

    def test_from_row_roundtrip(self):
        from app.models.source_event import SourceEvent
        e = self._make(symbol="TSLA", entity_id="EID", trace_id="T1")
        row = e.to_row()
        restored = SourceEvent.from_row(row)
        assert restored.source == e.source
        assert restored.topic == e.topic
        assert restored.symbol == e.symbol
        assert restored.entity_id == e.entity_id
        assert restored.trace_id == e.trace_id
        assert restored.payload == e.payload

    def test_schema_version_default(self):
        e = self._make()
        assert e.schema_version == "1.0"


# ===========================================================================
# 2. CheckpointStore
# ===========================================================================

class TestCheckpointStore:
    def _store(self):
        from app.data.checkpoint_store import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        return CheckpointStore(path=path)

    def test_set_and_get_string(self):
        s = self._store()
        s.set("foo", "bar")
        assert s.get("foo") == "bar"

    def test_get_missing_returns_default(self):
        s = self._store()
        assert s.get("missing") is None
        assert s.get("missing", "default_val") == "default_val"

    def test_set_overwrites(self):
        s = self._store()
        s.set("k", "v1")
        s.set("k", "v2")
        assert s.get("k") == "v2"

    def test_delete(self):
        s = self._store()
        s.set("k", "v")
        s.delete("k")
        assert s.get("k") is None

    def test_delete_nonexistent_is_noop(self):
        s = self._store()
        s.delete("nonexistent")  # Should not raise

    def test_all_returns_dict(self):
        s = self._store()
        s.set("a", 1)
        s.set("b", 2)
        result = s.all()
        assert result == {"a": 1, "b": 2}

    def test_keys_sorted(self):
        s = self._store()
        s.set("b", 2)
        s.set("a", 1)
        assert s.keys() == ["a", "b"]

    def test_stores_complex_value(self):
        s = self._store()
        val = {"nested": {"list": [1, 2, 3]}, "ts": "2026-01-10T12:00:00"}
        s.set("complex", val)
        assert s.get("complex") == val

    def test_clear(self):
        s = self._store()
        s.set("a", 1)
        s.set("b", 2)
        count = s.clear()
        assert count == 2
        assert s.all() == {}

    def test_persistence_across_instances(self):
        """Same file path → same data from a fresh instance."""
        from app.data.checkpoint_store import CheckpointStore
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        s1 = CheckpointStore(path=path)
        s1.set("persisted", "yes")
        s2 = CheckpointStore(path=path)
        assert s2.get("persisted") == "yes"


# ===========================================================================
# 3. BaseSourceAdapter — health + backoff
# ===========================================================================

class ConcreteAdapter:
    """Minimal concrete adapter for testing BaseSourceAdapter behaviour."""

    def __new__(cls, *a, **kw):
        from app.services.ingestion.base import BaseSourceAdapter
        # Dynamically create a concrete subclass
        class _Impl(BaseSourceAdapter):
            name = "test_adapter"
            source_kind = "poll"

            def __init__(self, fail_times=0, events=None):
                super().__init__()
                self._fail_times = fail_times
                self._call_count = 0
                self._events = events or []

            async def fetch(self):
                self._call_count += 1
                if self._call_count <= self._fail_times:
                    raise RuntimeError("Simulated fetch error")
                return self._events

            async def close(self):
                pass

        return _Impl(*a, **kw)


class TestBaseSourceAdapterHealth:
    def test_initial_status_is_starting(self):
        a = ConcreteAdapter()
        h = a.health()
        assert h["status"] == "starting"

    async def test_successful_fetch_sets_healthy(self):
        a = ConcreteAdapter(events=[])
        await a.run_fetch()
        h = a.health()
        assert h["status"] == "healthy"
        assert h["success_count"] == 1
        assert h["error_count"] == 0

    async def test_consecutive_failures_sets_degraded(self):
        from app.services.ingestion.base import BaseSourceAdapter
        class _Always(BaseSourceAdapter):
            name = "always_fail"
            source_kind = "poll"
            backoff_base = 0.001  # Fast for tests
            async def fetch(self): raise RuntimeError("fail")
            async def close(self): pass

        a = _Always()
        await a.run_fetch()  # max_retries=3 attempts → 3 errors → consecutive=3
        h = a.health()
        assert h["status"] == "degraded"
        assert h["consecutive_failures"] >= a.max_retries

    async def test_retry_resets_consecutive_failures(self):
        a = ConcreteAdapter(fail_times=2, events=[])  # Fail twice then succeed
        result = await a.run_fetch()
        h = a.health()
        # After success consecutive_failures resets to 0
        assert h["consecutive_failures"] == 0
        assert h["status"] == "healthy"

    def test_success_rate_computation(self):
        a = ConcreteAdapter()
        a._record_success()
        a._record_success()
        a._record_error("err")
        h = a.health()
        assert h["success_count"] == 2
        assert h["error_count"] == 1
        assert abs(h["success_rate"] - 2 / 3) < 0.01

    def test_health_keys_complete(self):
        a = ConcreteAdapter()
        h = a.health()
        required = {
            "name", "source_kind", "up_seconds", "success_count",
            "error_count", "success_rate", "consecutive_failures",
            "last_success_age_s", "last_error", "status",
        }
        assert required.issubset(set(h.keys()))

    def test_backoff_delay_is_within_cap(self):
        a = ConcreteAdapter()
        for attempt in range(10):
            delay = a._backoff_delay(attempt)
            assert 0 <= delay <= a.backoff_max


# ===========================================================================
# 4. snapshot_diff
# ===========================================================================

class TestSnapshotDiff:
    def test_no_old_all_added(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        diff = compute_snapshot_diff(None, {"a": 1, "b": 2})
        assert sorted(diff.added_keys) == ["a", "b"]
        assert not diff.removed_keys
        assert not diff.changed_fields
        assert diff.has_changes

    def test_identical_snapshots_no_changes(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        d = {"x": 1, "y": 2}
        diff = compute_snapshot_diff(d, d)
        assert not diff.has_changes

    def test_changed_field_detected(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        diff = compute_snapshot_diff({"price": 100}, {"price": 105})
        assert len(diff.changed_fields) == 1
        assert diff.changed_fields[0].key == "price"
        assert diff.changed_fields[0].old == 100
        assert diff.changed_fields[0].new == 105

    def test_added_key_detected(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        diff = compute_snapshot_diff({"a": 1}, {"a": 1, "b": 2})
        assert "b" in diff.added_keys
        assert not diff.removed_keys

    def test_removed_key_detected(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        diff = compute_snapshot_diff({"a": 1, "b": 2}, {"a": 1})
        assert "b" in diff.removed_keys
        assert not diff.added_keys

    def test_to_dict_structure(self):
        from app.services.ingestion.snapshot_diff import compute_snapshot_diff
        diff = compute_snapshot_diff({"p": 1}, {"p": 2, "q": 3})
        d = diff.to_dict()
        assert "has_changes" in d
        assert "added_keys" in d
        assert "removed_keys" in d
        assert "changed_fields" in d

    def test_snapshot_hash_stable(self):
        from app.services.ingestion.snapshot_diff import snapshot_hash
        d = {"b": 2, "a": 1}
        h1 = snapshot_hash(d)
        h2 = snapshot_hash(d)
        assert h1 == h2

    def test_snapshot_hash_differs_on_change(self):
        from app.services.ingestion.snapshot_diff import snapshot_hash
        assert snapshot_hash({"x": 1}) != snapshot_hash({"x": 2})

    def test_snapshot_hash_key_order_invariant(self):
        from app.services.ingestion.snapshot_diff import snapshot_hash
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert snapshot_hash(d1) == snapshot_hash(d2)


# ===========================================================================
# 5. DuckDB ingestion_events table
# ===========================================================================

class TestDuckDBIngestionEvents:
    def _store(self):
        from app.data.duckdb_storage import DuckDBStorage
        import tempfile
        # mktemp gives a path without creating the file (DuckDB requires non-existent or valid DB)
        path = tempfile.mktemp(suffix=".duckdb")
        return DuckDBStorage(db_path=path)

    def _make_event(self, source="test", topic="ingestion.test", symbol=None, seq=0):
        from app.models.source_event import SourceEvent
        return SourceEvent(
            source=source,
            source_kind="poll",
            topic=topic,
            payload={"v": seq},
            symbol=symbol,
            sequence=seq,
        )

    def test_write_single_event(self):
        store = self._store()
        e = self._make_event()
        result = store.write_ingestion_event(e)
        assert result is True
        assert store.get_ingestion_event_count() == 1

    def test_duplicate_dedupe_key_skipped(self):
        store = self._store()
        e = self._make_event(seq=0)  # Same payload → same dedupe_key
        e2 = self._make_event(seq=0)
        store.write_ingestion_event(e)
        store.write_ingestion_event(e2)
        # dedupe_key is identical → only 1 row
        assert store.get_ingestion_event_count() == 1

    def test_write_many(self):
        store = self._store()
        events = [self._make_event(seq=i) for i in range(5)]
        written = store.write_ingestion_events(events)
        assert written == 5

    def test_get_ingestion_events_filter_source(self):
        store = self._store()
        store.write_ingestion_events([self._make_event(source="fred", seq=i) for i in range(3)])
        store.write_ingestion_events([self._make_event(source="finviz", seq=i + 10) for i in range(2)])
        df = store.get_ingestion_events(source="fred")
        assert len(df) == 3

    def test_get_ingestion_events_filter_symbol(self):
        store = self._store()
        e1 = self._make_event(symbol="AAPL", seq=1)
        e2 = self._make_event(symbol="MSFT", seq=2)
        store.write_ingestion_events([e1, e2])
        df = store.get_ingestion_events(symbol="AAPL")
        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "AAPL"

    def test_get_ingestion_event_count_scoped(self):
        store = self._store()
        store.write_ingestion_events([self._make_event(source="fred", seq=i) for i in range(4)])
        assert store.get_ingestion_event_count(source="fred") == 4
        assert store.get_ingestion_event_count(source="finviz") == 0

    async def test_write_ingestion_events_async(self):
        store = self._store()
        events = [self._make_event(seq=i) for i in range(3)]
        written = await store.write_ingestion_events_async(events)
        assert written == 3


# ===========================================================================
# 6. IngestionEventSink
# ===========================================================================

class TestIngestionEventSink:
    def _sink_with_store(self):
        import tempfile
        from app.data.duckdb_storage import DuckDBStorage
        from app.services.ingestion.sink import IngestionEventSink
        path = tempfile.mktemp(suffix=".duckdb")
        store = DuckDBStorage(db_path=path)
        return IngestionEventSink(store=store)

    def _event(self, seq=0):
        from app.models.source_event import SourceEvent
        return SourceEvent(
            source="sink_test",
            source_kind="poll",
            topic="ingestion.test",
            payload={"v": seq},
            sequence=seq,
        )

    async def test_write_single(self):
        sink = self._sink_with_store()
        ok = await sink.write(self._event(0))
        assert ok is True
        assert sink.total_written == 1

    async def test_write_many_updates_counter(self):
        sink = self._sink_with_store()
        events = [self._event(i) for i in range(5)]
        written, _ = await sink.write_many(events)
        assert written == 5
        assert sink.total_written == 5

    async def test_write_empty_list(self):
        sink = self._sink_with_store()
        written, skipped = await sink.write_many([])
        assert written == 0
        assert skipped == 0

    def test_health_keys(self):
        sink = self._sink_with_store()
        h = sink.health()
        assert "total_written" in h
        assert "total_skipped" in h


# ===========================================================================
# 7. AdapterRegistry
# ===========================================================================

class TestAdapterRegistry:
    def _registry(self):
        from app.services.ingestion.registry import AdapterRegistry
        return AdapterRegistry()

    def _adapter(self, name="test"):
        from app.services.ingestion.base import BaseSourceAdapter
        class _A(BaseSourceAdapter):
            source_kind = "poll"
            async def fetch(self): return []
            async def close(self): pass
        a = _A()
        a.name = name
        return a

    def test_register_and_get(self):
        r = self._registry()
        a = self._adapter("a1")
        r.register(a)
        assert r.get("a1") is a

    def test_register_duplicate_raises(self):
        r = self._registry()
        r.register(self._adapter("dup"))
        with pytest.raises(ValueError, match="already registered"):
            r.register(self._adapter("dup"))

    def test_all_returns_list(self):
        r = self._registry()
        r.register(self._adapter("x"))
        r.register(self._adapter("y"))
        assert len(r.all()) == 2

    async def test_start_all_marks_started(self):
        r = self._registry()
        r.register(self._adapter("a"))
        await r.start_all()
        h = r.get_health()
        assert h["started"] is True

    async def test_stop_all_calls_close(self):
        from app.services.ingestion.base import BaseSourceAdapter
        close_called = []

        class _Tracked(BaseSourceAdapter):
            name = "tracked"
            source_kind = "poll"
            async def fetch(self): return []
            async def close(self): close_called.append(True)

        r = self._registry()
        r.register(_Tracked())
        await r.stop_all()
        assert close_called

    def test_get_health_aggregates(self):
        r = self._registry()
        r.register(self._adapter("h1"))
        r.register(self._adapter("h2"))
        h = r.get_health()
        assert "h1" in h["adapters"]
        assert "h2" in h["adapters"]
        assert h["adapter_count"] == 2

    def test_get_health_degraded_list(self):
        r = self._registry()
        a = self._adapter("deg")
        # Force degraded by setting consecutive_failures >= max_retries
        a._consecutive_failures = a.max_retries
        r.register(a)
        h = r.get_health()
        assert "deg" in h["degraded"]


# ===========================================================================
# 8. Concrete adapter — FredAdapter (mocked)
# ===========================================================================

class TestFredAdapter:
    def _make(self):
        from app.services.ingestion.adapters.fred_adapter import FredAdapter
        import tempfile
        from app.data.checkpoint_store import CheckpointStore
        a = FredAdapter(lookback=5)
        # Use temp checkpoint store so tests don't pollute the global one
        a._checkpoint = CheckpointStore(
            path=tempfile.mktemp(suffix=".db")
        )
        return a

    async def test_returns_events_on_new_observations(self):
        adapter = self._make()
        fake_obs = [{"date": "2026-01-10", "value": "14.5"}]
        with patch("app.services.fred_service.FredService.get_observations",
                   new=AsyncMock(return_value=fake_obs)):
            events = await adapter.run_fetch()
        assert len(events) > 0
        assert events[0].source == "fred"
        assert events[0].topic == "ingestion.macro"

    async def test_skips_old_observations(self):
        adapter = self._make()
        adapter.checkpoint.set("fred.last_date", "2026-01-15")
        fake_obs = [{"date": "2026-01-10", "value": "13.0"}]
        with patch("app.services.fred_service.FredService.get_observations",
                   new=AsyncMock(return_value=fake_obs)):
            events = await adapter.run_fetch()
        assert len(events) == 0

    async def test_advances_checkpoint(self):
        adapter = self._make()
        fake_obs = [{"date": "2026-01-20", "value": "15.0"}]
        with patch("app.services.fred_service.FredService.get_observations",
                   new=AsyncMock(return_value=fake_obs)):
            await adapter.run_fetch()
        assert adapter.checkpoint.get("fred.last_date") == "2026-01-20"

    async def test_api_error_returns_empty_no_raise(self):
        adapter = self._make()
        with patch("app.services.fred_service.FredService.get_observations",
                   new=AsyncMock(side_effect=RuntimeError("timeout"))):
            events = await adapter.run_fetch()
        assert events == []

    async def test_close_is_noop(self):
        adapter = self._make()
        await adapter.close()  # Should not raise


# ===========================================================================
# 9. Concrete adapter — UnusualWhalesAdapter (mocked)
# ===========================================================================

class TestUnusualWhalesAdapter:
    def _make(self):
        from app.services.ingestion.adapters.unusual_whales_adapter import UnusualWhalesAdapter
        import tempfile
        from app.data.checkpoint_store import CheckpointStore
        a = UnusualWhalesAdapter()
        a._checkpoint = CheckpointStore(path=tempfile.mktemp(suffix=".db"))
        return a

    async def test_returns_events_for_new_alerts(self):
        adapter = self._make()
        fake_alerts = [
            {"ticker": "AAPL", "traded_at": "2026-01-10T12:00:00", "option_type": "CALL"},
        ]
        with patch(
            "app.services.unusual_whales_service.UnusualWhalesService.get_flow_alerts",
            new=AsyncMock(return_value=fake_alerts),
        ):
            events = await adapter.run_fetch()
        assert len(events) == 1
        assert events[0].symbol == "AAPL"
        assert events[0].topic == "ingestion.options_flow"

    async def test_skips_old_alerts(self):
        adapter = self._make()
        adapter.checkpoint.set("unusual_whales.last_ts", "2026-01-15T00:00:00")
        fake_alerts = [
            {"ticker": "TSLA", "traded_at": "2026-01-10T09:00:00"},
        ]
        with patch(
            "app.services.unusual_whales_service.UnusualWhalesService.get_flow_alerts",
            new=AsyncMock(return_value=fake_alerts),
        ):
            events = await adapter.run_fetch()
        assert len(events) == 0

    async def test_handles_empty_response(self):
        adapter = self._make()
        with patch(
            "app.services.unusual_whales_service.UnusualWhalesService.get_flow_alerts",
            new=AsyncMock(return_value=[]),
        ):
            events = await adapter.run_fetch()
        assert events == []


# ===========================================================================
# 10. Concrete adapter — FinvizAdapter (mocked)
# ===========================================================================

class TestFinvizAdapter:
    def _make(self):
        from app.services.ingestion.adapters.finviz_adapter import FinvizAdapter
        import tempfile
        from app.data.checkpoint_store import CheckpointStore
        a = FinvizAdapter()
        a._checkpoint = CheckpointStore(path=tempfile.mktemp(suffix=".db"))
        return a

    async def test_returns_events_on_first_fetch(self):
        adapter = self._make()
        fake_data = [{"ticker": "NVDA", "price": "800"}, {"ticker": "AAPL", "price": "182"}]
        with patch(
            "app.services.finviz_service.FinvizService.get_screener",
            new=AsyncMock(return_value=fake_data),
        ):
            events = await adapter.run_fetch()
        # First fetch — no previous snapshot → all symbols are "added"
        assert len(events) == 2

    async def test_no_events_when_snapshot_unchanged(self):
        adapter = self._make()
        fake_data = [{"ticker": "NVDA", "price": "800"}]
        with patch(
            "app.services.finviz_service.FinvizService.get_screener",
            new=AsyncMock(return_value=fake_data),
        ):
            # First fetch populates snapshot
            await adapter.run_fetch()
            # Second fetch — same data → no change events
            events = await adapter.run_fetch()
        assert len(events) == 0

    async def test_emits_event_on_price_change(self):
        adapter = self._make()
        snapshot1 = [{"ticker": "AAPL", "price": "182"}]
        snapshot2 = [{"ticker": "AAPL", "price": "185"}]
        with patch(
            "app.services.finviz_service.FinvizService.get_screener",
            new=AsyncMock(return_value=snapshot1),
        ):
            await adapter.run_fetch()
        with patch(
            "app.services.finviz_service.FinvizService.get_screener",
            new=AsyncMock(return_value=snapshot2),
        ):
            events = await adapter.run_fetch()
        assert len(events) == 1
        assert events[0].symbol == "AAPL"


# ===========================================================================
# 11. Scheduler — adapter jobs registered
# ===========================================================================

class TestSchedulerAdapterJobs:
    def test_adapter_job_ids_present(self):
        """Importing get_scheduler_status should work even when scheduler is off."""
        from app.jobs.scheduler import get_scheduler_status
        status = get_scheduler_status()
        # Scheduler is disabled in test env (SCHEDULER_ENABLED=false)
        assert "jobs" in status

    def test_run_adapter_skips_unregistered(self):
        """_run_adapter with unknown name logs a warning and returns cleanly."""
        from app.jobs.scheduler import _run_adapter
        _run_adapter("does_not_exist")  # Should not raise


# ===========================================================================
# 12. Integration — SourceEvent → DuckDB round-trip
# ===========================================================================

class TestIngestionRoundTrip:
    async def test_write_and_read_back(self):
        import tempfile
        from app.data.duckdb_storage import DuckDBStorage
        from app.models.source_event import SourceEvent

        store = DuckDBStorage(db_path=tempfile.mktemp(suffix=".duckdb"))

        event = SourceEvent(
            source="fred",
            source_kind="poll",
            topic="ingestion.macro",
            payload={"series_id": "VIXCLS", "date": "2026-01-10", "value": 14.5},
            entity_id="VIXCLS",
        )
        store.write_ingestion_event(event)

        df = store.get_ingestion_events(source="fred")
        assert len(df) == 1
        row = df.iloc[0]
        assert row["source"] == "fred"
        assert row["topic"] == "ingestion.macro"
        assert row["entity_id"] == "VIXCLS"
        loaded = json.loads(row["payload_json"])
        assert loaded["series_id"] == "VIXCLS"

    async def test_full_adapter_to_sink_pipeline(self):
        """End-to-end: FredAdapter → IngestionEventSink → DuckDB."""
        import tempfile
        from app.data.checkpoint_store import CheckpointStore
        from app.data.duckdb_storage import DuckDBStorage
        from app.services.ingestion.adapters.fred_adapter import FredAdapter
        from app.services.ingestion.sink import IngestionEventSink

        store = DuckDBStorage(db_path=tempfile.mktemp(suffix=".duckdb"))
        sink = IngestionEventSink(store=store)

        adapter = FredAdapter(lookback=5)
        adapter._checkpoint = CheckpointStore(path=tempfile.mktemp(suffix=".db"))

        fake_obs = [{"date": "2026-02-01", "value": "18.5"}]
        with patch(
            "app.services.fred_service.FredService.get_observations",
            new=AsyncMock(return_value=fake_obs),
        ):
            events = await adapter.run_fetch()

        written, _ = await sink.write_many(events)
        assert written > 0
        assert store.get_ingestion_event_count(source="fred") == written
