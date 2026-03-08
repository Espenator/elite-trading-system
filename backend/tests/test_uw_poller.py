"""Tests for the UnusualWhalesPoller incremental polling layer.

Covers:
- Dedupe: events already in the seen-IDs set are not re-published.
- Resume: checkpoint is loaded on start so the poller resumes correctly.
- Cursor advancement: last_ts advances to the max timestamp in a batch.
- Partial overlap: only genuinely new events in a batch are emitted.
- Empty response: no crash or spurious publishes.
- Error resilience: fetch errors increment error counter, do not crash.
- Checkpoint persistence: seen_ids + last_ts are saved after each poll.
- SourceEvent schema: emitted payloads have the expected keys.
- _event_id determinism: same content always yields same ID.
- _event_id native ID preference: native id field wins over hash.
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.checkpoint_store import CheckpointStore
from app.models.source_event import SourceEvent
from app.services.unusual_whales_service import (
    UnusualWhalesPoller,
    _event_id,
    _event_timestamp,
    _extract_alerts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(
    ticker: str = "AAPL",
    option_type: str = "CALL",
    strike: str = "200",
    expiry: str = "2026-03-21",
    traded_at: str = "2026-03-08T10:00:00Z",
    native_id: str = None,
) -> Dict:
    alert = {
        "ticker": ticker,
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry,
        "traded_at": traded_at,
        "volume": 1000,
        "premium": 50000,
    }
    if native_id is not None:
        alert["id"] = native_id
    return alert


def _make_store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(path=tmp_path / "checkpoints.json")


def _make_poller(store: CheckpointStore, service_mock=None) -> UnusualWhalesPoller:
    if service_mock is None:
        service_mock = AsyncMock()
        service_mock.get_flow_alerts = AsyncMock(return_value=[])
    poller = UnusualWhalesPoller(
        poll_interval=60.0,
        checkpoint_store=store,
        service=service_mock,
    )
    return poller


# ---------------------------------------------------------------------------
# _event_id unit tests
# ---------------------------------------------------------------------------


class TestEventId:
    def test_native_id_used_when_present(self):
        alert = _make_alert(native_id="abc-123")
        assert _event_id(alert) == "abc-123"

    def test_hash_computed_when_no_id(self):
        alert = _make_alert()
        eid = _event_id(alert)
        assert len(eid) == 32  # 32-char hex digest

    def test_same_content_same_id(self):
        a1 = _make_alert()
        a2 = _make_alert()
        assert _event_id(a1) == _event_id(a2)

    def test_different_content_different_id(self):
        a1 = _make_alert(ticker="AAPL")
        a2 = _make_alert(ticker="TSLA")
        assert _event_id(a1) != _event_id(a2)

    def test_type_field_also_accepted(self):
        """Alerts using 'type' instead of 'option_type' still get stable IDs."""
        a = {"ticker": "AAPL", "type": "CALL", "strike": "200",
             "expiry": "2026-03-21", "traded_at": "2026-03-08T10:00:00Z"}
        eid = _event_id(a)
        assert len(eid) == 32


# ---------------------------------------------------------------------------
# _event_timestamp unit tests
# ---------------------------------------------------------------------------


class TestEventTimestamp:
    def test_iso_string_parsed(self):
        alert = {"traded_at": "2026-03-08T10:00:00Z"}
        ts = _event_timestamp(alert)
        assert ts > 0

    def test_numeric_passthrough(self):
        now = 1741430000.0
        alert = {"traded_at": now}
        assert _event_timestamp(alert) == now

    def test_fallback_to_now_when_missing(self):
        before = time.time()
        ts = _event_timestamp({})
        after = time.time()
        assert before <= ts <= after


# ---------------------------------------------------------------------------
# _extract_alerts unit tests
# ---------------------------------------------------------------------------


class TestExtractAlerts:
    def test_list_passthrough(self):
        data = [{"ticker": "AAPL"}]
        assert _extract_alerts(data) == data

    def test_dict_with_data_key(self):
        data = {"data": [{"ticker": "AAPL"}]}
        assert _extract_alerts(data) == data["data"]

    def test_dict_with_items_key(self):
        data = {"items": [{"ticker": "TSLA"}]}
        assert _extract_alerts(data) == data["items"]

    def test_empty_response(self):
        assert _extract_alerts({}) == []
        assert _extract_alerts([]) == []


# ---------------------------------------------------------------------------
# CheckpointStore unit tests
# ---------------------------------------------------------------------------


class TestCheckpointStore:
    def test_set_get(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("key", "value")
        assert store.get("key") == "value"

    def test_default_when_missing(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.get("missing", "default") == "default"

    def test_persistence_across_instances(self, tmp_path):
        store1 = CheckpointStore(path=tmp_path / "cp.json")
        store1.set("ts", 12345.0)

        store2 = CheckpointStore(path=tmp_path / "cp.json")
        assert store2.get("ts") == 12345.0

    def test_delete(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("k", 1)
        store.delete("k")
        assert store.get("k") is None

    def test_all_keys(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("a", 1)
        store.set("b", 2)
        assert set(store.all_keys()) == {"a", "b"}


# ---------------------------------------------------------------------------
# SourceEvent unit tests
# ---------------------------------------------------------------------------


class TestSourceEvent:
    def test_to_bus_payload_keys(self):
        evt = SourceEvent(
            source="unusual_whales",
            event_type="flow_alert",
            event_id="abc123",
            timestamp=1741430000.0,
            symbol="AAPL",
            payload={"volume": 100},
        )
        p = evt.to_bus_payload()
        assert p["source"] == "unusual_whales"
        assert p["event_type"] == "flow_alert"
        assert p["event_id"] == "abc123"
        assert p["symbol"] == "AAPL"
        assert p["payload"] == {"volume": 100}

    def test_symbol_is_optional(self):
        evt = SourceEvent(
            source="unusual_whales",
            event_type="flow_alert",
            event_id="x",
            timestamp=0.0,
        )
        assert evt.symbol is None
        assert evt.to_bus_payload()["symbol"] is None


# ---------------------------------------------------------------------------
# UnusualWhalesPoller.poll_once — dedupe tests
# ---------------------------------------------------------------------------


class TestPollerDedupe:
    @pytest.mark.anyio
    async def test_same_event_not_published_twice(self, tmp_path):
        """Polling the same list twice must publish events only once."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        alert = _make_alert()
        svc.get_flow_alerts = AsyncMock(return_value=[alert])

        published: List[Dict] = []

        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda topic, payload: published.append(payload))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            new1 = await poller.poll_once()
            new2 = await poller.poll_once()

        assert new1 == 1
        assert new2 == 0
        assert len(published) == 1
        assert poller.stats["duplicate_events"] == 1

    @pytest.mark.anyio
    async def test_different_events_both_published(self, tmp_path):
        store = _make_store(tmp_path)
        svc = AsyncMock()
        a1 = _make_alert(ticker="AAPL", traded_at="2026-03-08T10:00:00Z")
        a2 = _make_alert(ticker="TSLA", traded_at="2026-03-08T10:01:00Z")
        svc.get_flow_alerts = AsyncMock(return_value=[a1, a2])

        published: List[Dict] = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            new = await poller.poll_once()

        assert new == 2
        assert len(published) == 2

    @pytest.mark.anyio
    async def test_partial_overlap_only_new_published(self, tmp_path):
        """Second poll returns one old + one new alert — only new is emitted."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        old = _make_alert(ticker="AAPL", traded_at="2026-03-08T10:00:00Z")
        new_alert = _make_alert(ticker="MSFT", traded_at="2026-03-08T10:02:00Z")

        svc.get_flow_alerts = AsyncMock(return_value=[old])

        published: List[Dict] = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            await poller.poll_once()  # first poll — emits old

            svc.get_flow_alerts = AsyncMock(return_value=[old, new_alert])
            new_count = await poller.poll_once()  # second poll — old is dupe

        assert new_count == 1
        symbols = [p["symbol"] for p in published]
        assert "MSFT" in symbols
        assert symbols.count("AAPL") == 1  # only once

    @pytest.mark.anyio
    async def test_native_id_dedupe(self, tmp_path):
        """Events with a native 'id' field dedupe correctly."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        alert = _make_alert(native_id="native-001")
        svc.get_flow_alerts = AsyncMock(return_value=[alert])

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            n1 = await poller.poll_once()
            n2 = await poller.poll_once()

        assert n1 == 1 and n2 == 0
        assert len(published) == 1
        assert published[0]["event_id"] == "native-001"


# ---------------------------------------------------------------------------
# UnusualWhalesPoller.poll_once — resume/checkpoint tests
# ---------------------------------------------------------------------------


class TestPollerCheckpoint:
    @pytest.mark.anyio
    async def test_checkpoint_saved_after_poll(self, tmp_path):
        """After a poll the checkpoint file contains last_ts and seen_ids."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        alert = _make_alert()
        svc.get_flow_alerts = AsyncMock(return_value=[alert])

        bus = MagicMock()
        bus._running = False  # no publish needed for this test

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            await poller.poll_once()

        saved_ts = store.get("unusual_whales:last_ts")
        saved_ids = store.get("unusual_whales:seen_ids")
        assert saved_ts > 0
        assert isinstance(saved_ids, list)
        assert len(saved_ids) == 1

    @pytest.mark.anyio
    async def test_resume_skips_already_seen_events(self, tmp_path):
        """A new poller instance with a pre-loaded checkpoint skips seen events."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        alert = _make_alert()
        eid = _event_id(alert)

        # Pre-populate checkpoint as if a previous run already saw this alert
        store.set("unusual_whales:last_ts", 1_000_000.0)
        store.set("unusual_whales:seen_ids", [eid])

        svc.get_flow_alerts = AsyncMock(return_value=[alert])
        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            poller._load_checkpoint()  # explicitly load saved state
            new = await poller.poll_once()

        assert new == 0
        assert published == []

    @pytest.mark.anyio
    async def test_resume_emits_events_newer_than_cursor(self, tmp_path):
        """Events with timestamps newer than the saved cursor are emitted."""
        store = _make_store(tmp_path)
        old_ts = 1_700_000_000.0  # some past epoch
        store.set("unusual_whales:last_ts", old_ts)
        store.set("unusual_whales:seen_ids", [])

        # Create a fresh alert with a newer timestamp
        new_alert = {
            "ticker": "NVDA",
            "option_type": "CALL",
            "strike": "500",
            "expiry": "2026-04-18",
            "traded_at": 1_700_000_100.0,  # 100 s after cursor
            "volume": 500,
        }
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value=[new_alert])

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            poller._load_checkpoint()
            new = await poller.poll_once()

        assert new == 1
        assert published[0]["symbol"] == "NVDA"

    @pytest.mark.anyio
    async def test_last_ts_advances_after_poll(self, tmp_path):
        """last_ts must advance to the max timestamp seen in a batch."""
        store = _make_store(tmp_path)
        ts1 = 1_700_000_100.0
        ts2 = 1_700_000_200.0
        alerts = [
            {**_make_alert(ticker="AAPL"), "traded_at": ts1},
            {**_make_alert(ticker="MSFT"), "traded_at": ts2},
        ]
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value=alerts)

        bus = MagicMock()
        bus._running = False

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            await poller.poll_once()

        assert poller._last_ts == ts2

    @pytest.mark.anyio
    async def test_checkpoint_survives_restart(self, tmp_path):
        """Two poller instances sharing a checkpoint store behave correctly."""
        store = _make_store(tmp_path)
        alert = _make_alert()

        svc1 = AsyncMock()
        svc1.get_flow_alerts = AsyncMock(return_value=[alert])
        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        # First instance — polls once, saves checkpoint
        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            p1 = _make_poller(store, svc1)
            await p1.poll_once()

        # Second instance loads from same file — same event is already seen
        store2 = CheckpointStore(path=tmp_path / "checkpoints.json")
        svc2 = AsyncMock()
        svc2.get_flow_alerts = AsyncMock(return_value=[alert])

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            p2 = _make_poller(store2, svc2)
            p2._load_checkpoint()
            new = await p2.poll_once()

        assert new == 0  # duplicate — seen by first instance


# ---------------------------------------------------------------------------
# UnusualWhalesPoller — error handling tests
# ---------------------------------------------------------------------------


class TestPollerErrorHandling:
    @pytest.mark.anyio
    async def test_fetch_error_increments_counter(self, tmp_path):
        store = _make_store(tmp_path)
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(side_effect=Exception("network error"))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=MagicMock()):
            poller = _make_poller(store, svc)
            result = await poller.poll_once()

        assert result == 0
        assert poller.stats["errors"] == 1

    @pytest.mark.anyio
    async def test_missing_api_key_not_counted_as_error(self, tmp_path):
        """ValueError from missing API key should not increment error counter."""
        store = _make_store(tmp_path)
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(side_effect=ValueError("UNUSUAL_WHALES_API_KEY is not set"))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=MagicMock()):
            poller = _make_poller(store, svc)
            result = await poller.poll_once()

        assert result == 0
        assert poller.stats["errors"] == 0

    @pytest.mark.anyio
    async def test_empty_response_no_publish(self, tmp_path):
        store = _make_store(tmp_path)
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value=[])

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            result = await poller.poll_once()

        assert result == 0
        assert published == []

    @pytest.mark.anyio
    async def test_dict_response_shape_handled(self, tmp_path):
        """UW API can return {'data': [...]} — poller must handle it."""
        store = _make_store(tmp_path)
        alert = _make_alert(ticker="AMD")
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value={"data": [alert]})

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            result = await poller.poll_once()

        assert result == 1
        assert published[0]["symbol"] == "AMD"


# ---------------------------------------------------------------------------
# UnusualWhalesPoller — emitted payload schema tests
# ---------------------------------------------------------------------------


class TestPollerPayloadSchema:
    @pytest.mark.anyio
    async def test_published_payload_has_required_keys(self, tmp_path):
        store = _make_store(tmp_path)
        alert = _make_alert(ticker="AAPL", native_id="schema-test-001")
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value=[alert])

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append((t, p)))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            await poller.poll_once()

        assert len(published) == 1
        topic, payload = published[0]
        assert topic == "perception.unusualwhales"
        for key in ("source", "event_type", "event_id", "timestamp", "symbol", "payload"):
            assert key in payload, f"Missing key: {key}"
        assert payload["source"] == "unusual_whales"
        assert payload["event_type"] == "flow_alert"
        assert payload["event_id"] == "schema-test-001"
        assert payload["symbol"] == "AAPL"

    @pytest.mark.anyio
    async def test_symbol_normalised_to_uppercase(self, tmp_path):
        store = _make_store(tmp_path)
        alert = {**_make_alert(), "ticker": "nvda"}
        svc = AsyncMock()
        svc.get_flow_alerts = AsyncMock(return_value=[alert])

        published = []
        bus = MagicMock()
        bus._running = True
        bus.publish = AsyncMock(side_effect=lambda t, p: published.append(p))

        with patch("app.services.unusual_whales_service.get_message_bus", return_value=bus):
            poller = _make_poller(store, svc)
            await poller.poll_once()

        assert published[0]["symbol"] == "NVDA"
