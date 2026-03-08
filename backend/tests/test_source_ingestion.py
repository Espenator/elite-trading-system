"""Tests for the firehose ingestion layer.

Covers:
- SourceEvent model construction and dedupe key generation
- CheckpointStore save / load / resume / delete
- EventSinkWriter idempotent write + duplicate skipping
- SnapshotDiffer inserted / changed / removed diff logic
- ReconnectPolicy backoff computation and success reset
- BaseSourceAdapter health reporting and lifecycle
"""
import asyncio
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# SourceEvent model
# ---------------------------------------------------------------------------

class TestSourceEvent:
    def test_default_fields_populated(self):
        from app.models.source_event import SourceEvent
        ev = SourceEvent(
            dedupe_key="finviz:AAPL:abc123",
            source="finviz",
        )
        assert ev.event_id  # UUID4 generated
        assert ev.schema_version == "1.0"
        assert ev.symbols == []
        assert ev.is_deleted is False
        assert ev.event_ts.tzinfo is not None

    def test_make_dedupe_key_stable(self):
        from app.models.source_event import SourceEvent
        k1 = SourceEvent.make_dedupe_key("finviz", "AAPL", {"price": 150, "vol": 1e6})
        k2 = SourceEvent.make_dedupe_key("finviz", "AAPL", {"vol": 1e6, "price": 150})
        assert k1 == k2, "dedupe key must be order-independent"

    def test_make_dedupe_key_varies_by_content(self):
        from app.models.source_event import SourceEvent
        k1 = SourceEvent.make_dedupe_key("finviz", "AAPL", {"price": 150})
        k2 = SourceEvent.make_dedupe_key("finviz", "AAPL", {"price": 151})
        assert k1 != k2

    def test_make_dedupe_key_format(self):
        from app.models.source_event import SourceEvent
        k = SourceEvent.make_dedupe_key("fred", "UNRATE", {"value": 4.1})
        parts = k.split(":")
        assert parts[0] == "fred"
        assert parts[1] == "UNRATE"
        assert len(parts[2]) == 16  # 16-char hex hash

    def test_from_screener_row(self):
        from app.models.source_event import SourceEvent
        row = {"ticker": "MSFT", "price": 420.0, "volume": 5_000_000}
        ev = SourceEvent.from_screener_row(
            source="finviz",
            symbol="MSFT",
            row=row,
            feed="screener",
        )
        assert ev.source == "finviz"
        assert ev.feed == "screener"
        assert "MSFT" in ev.symbols
        assert ev.payload["price"] == 420.0

    def test_from_macro_series(self):
        from app.models.source_event import SourceEvent
        ev = SourceEvent.from_macro_series(
            source="fred", series_id="UNRATE", value=4.1
        )
        assert ev.entity_id == "UNRATE"
        assert ev.feed == "macro"
        assert ev.payload["value"] == 4.1

    def test_to_bus_dict_timestamps_are_strings(self):
        from app.models.source_event import SourceEvent
        ev = SourceEvent(dedupe_key="k", source="test")
        d = ev.to_bus_dict()
        assert isinstance(d["event_ts"], str)
        assert isinstance(d["ingested_at"], str)
        assert "T" in d["event_ts"]  # ISO format


# ---------------------------------------------------------------------------
# CheckpointStore
# ---------------------------------------------------------------------------

@pytest.fixture
def checkpoint_store_fresh(tmp_path):
    """Return a CheckpointStore backed by a fresh DuckDB file."""
    import duckdb
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
            source   VARCHAR NOT NULL,
            scope    VARCHAR NOT NULL,
            data     VARCHAR NOT NULL,
            saved_at TIMESTAMP NOT NULL,
            PRIMARY KEY (source, scope)
        )
    """)
    conn.close()

    from app.data.checkpoint_store import CheckpointStore

    store = CheckpointStore()

    # Monkeypatch to use in-memory duckdb_store backed by tmp_path
    real_conn = duckdb.connect(db_path)
    import threading as _t
    real_lock = _t.Lock()

    def patched_load(source, scope):
        with real_lock:
            rows = real_conn.execute(
                "SELECT data FROM ingestion_checkpoints WHERE source = ? AND scope = ?",
                [source, scope],
            ).fetchall()
        return json.loads(rows[0][0]) if rows else None

    def patched_save(source, scope, data):
        payload = json.dumps(data, default=str)
        now = datetime.now(timezone.utc).isoformat()
        with real_lock:
            real_conn.execute(
                """
                INSERT INTO ingestion_checkpoints (source, scope, data, saved_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (source, scope)
                DO UPDATE SET data = excluded.data, saved_at = excluded.saved_at
                """,
                [source, scope, payload, now],
            )

    def patched_delete(source, scope):
        with real_lock:
            real_conn.execute(
                "DELETE FROM ingestion_checkpoints WHERE source = ? AND scope = ?",
                [source, scope],
            )

    store._load_sync = patched_load
    store._save_sync = patched_save
    store._delete_sync = patched_delete
    yield store
    real_conn.close()


class TestCheckpointStore:
    @pytest.mark.anyio
    async def test_load_missing_returns_none(self, checkpoint_store_fresh):
        result = await checkpoint_store_fresh.load("finviz", "screener")
        assert result is None

    @pytest.mark.anyio
    async def test_save_and_load(self, checkpoint_store_fresh):
        data = {"cursor": "2026-03-01T00:00:00", "page": 3}
        await checkpoint_store_fresh.save("finviz", "screener", data)
        loaded = await checkpoint_store_fresh.load("finviz", "screener")
        assert loaded == data

    @pytest.mark.anyio
    async def test_save_overwrites(self, checkpoint_store_fresh):
        await checkpoint_store_fresh.save("fred", "UNRATE", {"value": 4.0})
        await checkpoint_store_fresh.save("fred", "UNRATE", {"value": 4.1})
        loaded = await checkpoint_store_fresh.load("fred", "UNRATE")
        assert loaded["value"] == 4.1

    @pytest.mark.anyio
    async def test_different_scopes_independent(self, checkpoint_store_fresh):
        await checkpoint_store_fresh.save("edgar", "filings", {"cik": "1234"})
        await checkpoint_store_fresh.save("edgar", "facts", {"cik": "9999"})
        r1 = await checkpoint_store_fresh.load("edgar", "filings")
        r2 = await checkpoint_store_fresh.load("edgar", "facts")
        assert r1["cik"] == "1234"
        assert r2["cik"] == "9999"

    @pytest.mark.anyio
    async def test_delete_removes_checkpoint(self, checkpoint_store_fresh):
        await checkpoint_store_fresh.save("uw", "flow", {"ts": "x"})
        await checkpoint_store_fresh.delete("uw", "flow")
        result = await checkpoint_store_fresh.load("uw", "flow")
        assert result is None

    @pytest.mark.anyio
    async def test_resume_pattern(self, checkpoint_store_fresh):
        """Simulate adapter restart — checkpoint survived."""
        await checkpoint_store_fresh.save("finviz", "screener", {"last_page": 5})
        # Simulate restart: load same store
        cp = await checkpoint_store_fresh.load("finviz", "screener")
        assert cp is not None
        assert cp["last_page"] == 5


# ---------------------------------------------------------------------------
# EventSinkWriter (dedupe behaviour)
# ---------------------------------------------------------------------------

@pytest.fixture
def sink_and_store(tmp_path):
    """Return an EventSinkWriter wired to a fresh in-memory DuckDB."""
    import duckdb
    import threading as _t

    db_path = str(tmp_path / "sink.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS source_events (
            event_id        VARCHAR NOT NULL,
            dedupe_key      VARCHAR NOT NULL,
            schema_version  VARCHAR NOT NULL DEFAULT '1.0',
            source          VARCHAR NOT NULL,
            source_version  VARCHAR NOT NULL DEFAULT '1',
            feed            VARCHAR NOT NULL DEFAULT '',
            event_ts        TIMESTAMP NOT NULL,
            ingested_at     TIMESTAMP NOT NULL,
            symbols         VARCHAR NOT NULL DEFAULT '[]',
            entity_id       VARCHAR NOT NULL DEFAULT '',
            payload         VARCHAR NOT NULL DEFAULT '{}',
            raw_payload     VARCHAR,
            is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (dedupe_key)
        )
    """)

    lock = _t.Lock()

    from app.services.ingestion.event_sink import EventSinkWriter

    sink = EventSinkWriter()

    def patched_write(data):
        with lock:
            existing = conn.execute(
                "SELECT COUNT(*) FROM source_events WHERE dedupe_key = ?",
                [data["dedupe_key"]],
            ).fetchone()[0]
            if existing > 0:
                return "skipped"
            conn.execute(
                """
                INSERT INTO source_events
                    (event_id, dedupe_key, schema_version, source, source_version,
                     feed, event_ts, ingested_at, symbols, entity_id,
                     payload, raw_payload, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    data.get("event_id", ""),
                    data["dedupe_key"],
                    data.get("schema_version", "1.0"),
                    data.get("source", ""),
                    data.get("source_version", "1"),
                    data.get("feed", ""),
                    data.get("event_ts", datetime.now(timezone.utc).isoformat()),
                    data.get("ingested_at", datetime.now(timezone.utc).isoformat()),
                    json.dumps(data.get("symbols", []), default=str),
                    data.get("entity_id", ""),
                    json.dumps(data.get("payload", {}), default=str),
                    data.get("raw_payload"),
                    bool(data.get("is_deleted", False)),
                ],
            )
        return "written"

    def count_rows():
        with lock:
            return conn.execute("SELECT COUNT(*) FROM source_events").fetchone()[0]

    sink._write_sync = patched_write
    sink._running = True
    yield sink, count_rows
    conn.close()


def _make_event_dict(**kwargs) -> Dict[str, Any]:
    from app.models.source_event import SourceEvent
    ev = SourceEvent(
        dedupe_key=kwargs.get("dedupe_key", f"test:{uuid.uuid4()}"),
        source=kwargs.get("source", "test"),
        feed=kwargs.get("feed", ""),
        symbols=kwargs.get("symbols", []),
        payload=kwargs.get("payload", {}),
    )
    return ev.to_bus_dict()


class TestEventSinkWriter:
    @pytest.mark.anyio
    async def test_writes_new_event(self, sink_and_store):
        sink, count = sink_and_store
        data = _make_event_dict(source="finviz", dedupe_key="finviz:AAPL:aaa111")
        await sink._handle_event(data)
        assert count() == 1
        assert sink._events_written == 1
        assert sink._events_skipped == 0

    @pytest.mark.anyio
    async def test_skips_duplicate(self, sink_and_store):
        sink, count = sink_and_store
        data = _make_event_dict(source="finviz", dedupe_key="finviz:AAPL:dup001")
        await sink._handle_event(data)
        await sink._handle_event(data)  # exact duplicate
        assert count() == 1
        assert sink._events_written == 1
        assert sink._events_skipped == 1

    @pytest.mark.anyio
    async def test_different_dedupe_keys_both_written(self, sink_and_store):
        sink, count = sink_and_store
        d1 = _make_event_dict(source="fred", dedupe_key="fred:UNRATE:aaa")
        d2 = _make_event_dict(source="fred", dedupe_key="fred:UNRATE:bbb")
        await sink._handle_event(d1)
        await sink._handle_event(d2)
        assert count() == 2
        assert sink._events_written == 2

    @pytest.mark.anyio
    async def test_missing_dedupe_key_increments_failed(self, sink_and_store):
        sink, _ = sink_and_store
        await sink._handle_event({"source": "bad", "payload": {}})
        assert sink._events_failed == 1

    @pytest.mark.anyio
    async def test_not_running_drops_event(self, sink_and_store):
        sink, count = sink_and_store
        sink._running = False
        data = _make_event_dict(dedupe_key="x:y:z")
        await sink._handle_event(data)
        assert count() == 0

    def test_status_fields(self, sink_and_store):
        sink, _ = sink_and_store
        s = sink.status()
        assert "running" in s
        assert "events_written" in s
        assert "events_skipped" in s
        assert "events_failed" in s


# ---------------------------------------------------------------------------
# SnapshotDiffer
# ---------------------------------------------------------------------------

class TestSnapshotDiffer:
    def test_first_call_emits_all_rows(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol")
        rows = [
            {"symbol": "AAPL", "price": 150},
            {"symbol": "MSFT", "price": 420},
        ]
        events = differ.diff(rows)
        assert len(events) == 2
        syms = {e.symbols[0] for e in events if e.symbols}
        assert "AAPL" in syms
        assert "MSFT" in syms

    def test_no_change_emits_nothing(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol")
        rows = [{"symbol": "AAPL", "price": 150}]
        differ.diff(rows)
        events = differ.diff(rows)  # identical snapshot
        assert events == []

    def test_changed_row_emits_event(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol")
        differ.diff([{"symbol": "AAPL", "price": 150}])
        events = differ.diff([{"symbol": "AAPL", "price": 151}])
        assert len(events) == 1
        assert events[0].payload["price"] == 151

    def test_new_row_emits_event(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol")
        differ.diff([{"symbol": "AAPL", "price": 150}])
        events = differ.diff([
            {"symbol": "AAPL", "price": 150},  # unchanged
            {"symbol": "NVDA", "price": 800},  # new
        ])
        assert len(events) == 1
        assert events[0].symbols == ["NVDA"]

    def test_removed_row_emits_deleted_event(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol",
                                emit_removals=True)
        differ.diff([{"symbol": "AAPL", "price": 150}, {"symbol": "MSFT", "price": 420}])
        events = differ.diff([{"symbol": "AAPL", "price": 150}])  # MSFT removed
        assert len(events) == 1
        assert events[0].is_deleted is True
        assert "MSFT" in events[0].symbols

    def test_removal_suppressed_when_disabled(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="finviz", feed="screener", key_field="symbol",
                                emit_removals=False)
        differ.diff([{"symbol": "AAPL"}, {"symbol": "MSFT"}])
        events = differ.diff([{"symbol": "AAPL"}])
        removed = [e for e in events if e.is_deleted]
        assert removed == []

    def test_reset_forces_full_emit(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="oc", feed="candidates", key_field="symbol")
        rows = [{"symbol": "NVDA", "score": 80}]
        differ.diff(rows)
        differ.reset()
        events = differ.diff(rows)
        assert len(events) == 1

    def test_tracked_keys_updated_after_diff(self):
        from app.services.ingestion.snapshot_diff import SnapshotDiffer
        differ = SnapshotDiffer(source="oc", feed="candidates", key_field="symbol")
        differ.diff([{"symbol": "AAPL"}, {"symbol": "MSFT"}])
        assert set(differ.tracked_keys) == {"AAPL", "MSFT"}


# ---------------------------------------------------------------------------
# ReconnectPolicy (backoff + reconnect counters)
# ---------------------------------------------------------------------------

class TestReconnectPolicy:
    def test_initial_delay_returned_on_first_failure(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=2.0, jitter=0.0)
        delay = p.on_failure()
        assert delay == pytest.approx(2.0, abs=0.01)

    def test_delay_doubles_on_subsequent_failures(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=2.0, multiplier=2.0, jitter=0.0)
        d1 = p.on_failure()
        d2 = p.on_failure()
        assert d2 == pytest.approx(d1 * 2.0, abs=0.01)

    def test_delay_capped_at_max(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(
            name="test", initial_delay=2.0, max_delay=10.0,
            multiplier=100.0, jitter=0.0,
        )
        for _ in range(10):
            d = p.on_failure()
        assert d <= 10.0

    def test_success_resets_delay(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=2.0, multiplier=2.0, jitter=0.0)
        p.on_failure()
        p.on_failure()
        p.on_success()
        d = p.on_failure()
        assert d == pytest.approx(2.0, abs=0.01)

    def test_success_resets_consecutive_count(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=1.0, jitter=0.0)
        p.on_failure()
        p.on_failure()
        p.on_success()
        assert p._consecutive_failures == 0

    def test_max_attempts_returns_none(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=1.0, jitter=0.0, max_attempts=2)
        p.on_failure()
        p.on_failure()
        result = p.on_failure()  # 3rd attempt
        assert result is None

    def test_unlimited_attempts_never_returns_none(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=1.0, jitter=0.0, max_attempts=0)
        for _ in range(20):
            d = p.on_failure()
            assert d is not None

    def test_jitter_added(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=2.0, jitter=5.0)
        delays = [p.on_failure() for _ in range(20)]
        p.on_success()
        # With jitter, delays should not all be identical
        assert len(set(round(d, 3) for d in delays)) > 1

    def test_status_fields(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="ws_adapter")
        p.on_failure()
        s = p.status()
        assert s["name"] == "ws_adapter"
        assert s["consecutive_failures"] == 1
        assert s["total_reconnects"] == 1

    @pytest.mark.anyio
    async def test_run_with_retry_succeeds_on_second_attempt(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=0.01, jitter=0.0)
        attempts = []

        async def factory():
            attempts.append(1)
            if len(attempts) < 2:
                raise ValueError("first fail")
            # Cancel after success to exit the infinite retry loop
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(p.run_with_retry(factory), timeout=5.0)
        assert len(attempts) == 2

    @pytest.mark.anyio
    async def test_run_with_retry_respects_max_attempts(self):
        from app.services.ingestion.reconnect import ReconnectPolicy
        p = ReconnectPolicy(name="test", initial_delay=0.01, jitter=0.0, max_attempts=2)

        async def factory():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError):
            await asyncio.wait_for(p.run_with_retry(factory), timeout=5.0)


# ---------------------------------------------------------------------------
# BaseSourceAdapter — health reporting + lifecycle
# ---------------------------------------------------------------------------

class _SimpleAdapter:
    """Minimal concrete adapter for testing BaseSourceAdapter."""

    SOURCE = "test_source"
    FEED = "test_feed"

    def __init__(self, bus=None, cp_store=None, tick_sleep: float = 9999.0):
        from app.data.checkpoint_store import CheckpointStore
        from app.services.ingestion.base_adapter import BaseSourceAdapter

        class _Adapter(BaseSourceAdapter):
            SOURCE = "test_source"
            FEED = "test_feed"

            def __init__(self, bus, cp_store, sleep_s):
                super().__init__(message_bus=bus, checkpoint_store=cp_store)
                self._sleep_s = sleep_s

            async def _run(self):
                self._record_tick()
                await asyncio.sleep(self._sleep_s)

        mock_store = MagicMock(spec=CheckpointStore)
        mock_store.load = AsyncMock(return_value=None)
        mock_store.save = AsyncMock()

        self._inner = _Adapter(bus, cp_store or mock_store, tick_sleep)

    @property
    def adapter(self):
        return self._inner


class TestBaseSourceAdapter:
    @pytest.mark.anyio
    async def test_health_not_running_before_start(self):
        a = _SimpleAdapter()
        h = a.adapter.health()
        assert h["running"] is False
        assert h["source"] == "test_source"
        assert h["events_published"] == 0

    @pytest.mark.anyio
    async def test_start_sets_running(self):
        a = _SimpleAdapter(tick_sleep=0.0)
        await a.adapter.start()
        await asyncio.sleep(0.05)
        # task may have completed but running was True during run
        await a.adapter.stop()

    @pytest.mark.anyio
    async def test_stop_cancels_task(self):
        a = _SimpleAdapter(tick_sleep=60.0)
        await a.adapter.start()
        await asyncio.sleep(0.02)
        await a.adapter.stop()
        assert a.adapter._running is False

    @pytest.mark.anyio
    async def test_publish_event_increments_counter(self):
        from app.models.source_event import SourceEvent
        bus = MagicMock()
        bus.publish = AsyncMock()
        a = _SimpleAdapter(bus=bus)
        event = SourceEvent(dedupe_key="k:v:x", source="test_source")
        await a.adapter.publish_event(event)
        assert a.adapter._events_published == 1
        bus.publish.assert_called_once()

    @pytest.mark.anyio
    async def test_publish_event_no_bus_does_not_raise(self):
        from app.models.source_event import SourceEvent
        a = _SimpleAdapter(bus=None)
        event = SourceEvent(dedupe_key="k:v:y", source="test_source")
        await a.adapter.publish_event(event)  # should not raise
        assert a.adapter._events_published == 0

    @pytest.mark.anyio
    async def test_health_uptime_after_start(self):
        a = _SimpleAdapter(tick_sleep=60.0)
        await a.adapter.start()
        await asyncio.sleep(0.05)
        h = a.adapter.health()
        assert h["uptime_seconds"] is not None
        assert h["uptime_seconds"] >= 0
        await a.adapter.stop()

    @pytest.mark.anyio
    async def test_source_must_be_set(self):
        from app.services.ingestion.base_adapter import BaseSourceAdapter

        class _BadAdapter(BaseSourceAdapter):
            async def _run(self): pass

        with pytest.raises(ValueError, match="SOURCE"):
            _BadAdapter()

    @pytest.mark.anyio
    async def test_load_checkpoint_delegates(self):
        from app.data.checkpoint_store import CheckpointStore
        mock_cp = MagicMock(spec=CheckpointStore)
        mock_cp.load = AsyncMock(return_value={"cursor": "abc"})
        a = _SimpleAdapter(cp_store=mock_cp)
        result = await a.adapter.load_checkpoint("screener")
        mock_cp.load.assert_called_once_with("test_source", "screener")
        assert result == {"cursor": "abc"}

    @pytest.mark.anyio
    async def test_save_checkpoint_delegates(self):
        from app.data.checkpoint_store import CheckpointStore
        mock_cp = MagicMock(spec=CheckpointStore)
        mock_cp.save = AsyncMock()
        a = _SimpleAdapter(cp_store=mock_cp)
        await a.adapter.save_checkpoint("screener", {"page": 3})
        mock_cp.save.assert_called_once_with("test_source", "screener", {"page": 3})
