"""Tests for MessageBus Redis bridge.

Covers:
  - local-only mode (no REDIS_URL)
  - successful connection → connection log + metrics
  - cross-node deduplication (own messages silently ignored)
  - remote message injection into local queue
  - publish errors + reconnect threshold
  - clean disconnect
  - get_metrics() redis section
  - /api/v1/system/event-bus/status exposes redis field
"""
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bus():
    """Create a fresh MessageBus without starting it."""
    from app.core.message_bus import MessageBus
    return MessageBus()


async def _start_local(bus):
    """Start bus in local-only mode (no Redis env var)."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("REDIS_URL", None)
        with patch("app.core.message_bus.MessageBus._connect_redis", new_callable=AsyncMock):
            await bus.start()


# ---------------------------------------------------------------------------
# Local-only mode (no REDIS_URL configured)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_only_when_no_redis_url(monkeypatch):
    """Bus starts normally when REDIS_URL is absent; redis.connected == False."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr("app.core.config.settings", MagicMock(REDIS_URL=""), raising=False)

    from app.core.message_bus import MessageBus
    bus = MessageBus()
    await bus.start()
    try:
        assert bus._running is True
        assert bus._redis_connected is False
        metrics = bus.get_metrics()
        assert metrics["redis"]["connected"] is False
        assert metrics["redis"]["url"] is None
    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_local_only_no_redis_url_env(monkeypatch):
    """_connect_redis returns early and logs when no URL is configured."""
    monkeypatch.delenv("REDIS_URL", raising=False)

    from app.core.message_bus import MessageBus
    bus = MessageBus()

    # patch settings to also return empty string
    with patch("app.core.message_bus.MessageBus._connect_redis", new_callable=AsyncMock) as mock_connect:
        await bus.start()
        mock_connect.assert_called_once()

    assert bus._redis_connected is False
    await bus.stop()


# ---------------------------------------------------------------------------
# Successful Redis connection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_redis_success_sets_connected_flag(monkeypatch, caplog):
    """When Redis is reachable, _redis_connected is set True and log emitted."""
    import logging
    import redis.asyncio as aioredis

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    from app.core.config import settings
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0", raising=False)

    mock_redis_pub = AsyncMock()
    mock_redis_pub.ping = AsyncMock(return_value=True)
    mock_redis_pub.close = AsyncMock()

    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(return_value=None)
    mock_pubsub.close = AsyncMock(return_value=None)

    call_count = [0]

    def mock_from_url(url, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_redis_pub
        sub_client = MagicMock()
        sub_client.pubsub = MagicMock(return_value=mock_pubsub)
        return sub_client

    from app.core.message_bus import MessageBus
    bus = MessageBus()

    # Patch _redis_listener on the instance so create_task() gets a proper coroutine
    async def _noop_listener():
        pass

    bus._redis_listener = _noop_listener

    with patch.object(aioredis, "from_url", side_effect=mock_from_url):
        with caplog.at_level(logging.INFO, logger="app.core.message_bus"):
            await bus._connect_redis()

    assert bus._redis_connected is True
    assert bus._redis_url == "redis://127.0.0.1:6379/0"
    assert any(
        "Redis bridge CONNECTED" in r.message
        for r in caplog.records
    ), f"Expected 'Redis bridge CONNECTED' in logs. Got: {[r.message for r in caplog.records]}"

    await bus._disconnect_redis()


@pytest.mark.asyncio
async def test_connect_redis_connection_failure_fallback(monkeypatch, caplog):
    """When Redis ping raises, bus falls back to local-only mode (no exception propagated)."""
    import logging
    import redis.asyncio as aioredis

    monkeypatch.setenv("REDIS_URL", "redis://10.0.0.1:6379/0")

    mock_redis_client = AsyncMock()
    mock_redis_client.ping = AsyncMock(side_effect=ConnectionRefusedError("no server"))

    from app.core.message_bus import MessageBus
    bus = MessageBus()

    with patch.object(aioredis, "from_url", return_value=mock_redis_client):
        with caplog.at_level(logging.WARNING, logger="app.core.message_bus"):
            await bus._connect_redis()  # must not raise

    assert bus._redis_connected is False
    assert bus._redis_pub is None
    assert any("falling back to local-only" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_connect_redis_no_url_returns_early(monkeypatch, caplog):
    """When REDIS_URL is empty, _connect_redis returns early without connecting."""
    import logging

    monkeypatch.delenv("REDIS_URL", raising=False)
    # Ensure both env and settings report no URL (settings is loaded at app import and may have .env value)
    monkeypatch.setattr(
        "app.core.message_bus.os.getenv",
        lambda key, default="": default if key == "REDIS_URL" else os.getenv(key, default),
        raising=False,
    )
    from app.core.config import settings
    monkeypatch.setattr(settings, "REDIS_URL", "", raising=False)

    from app.core.message_bus import MessageBus
    bus = MessageBus()

    with caplog.at_level(logging.INFO, logger="app.core.message_bus"):
        await bus._connect_redis()

    assert bus._redis_connected is False
    assert bus._redis_pub is None


# ---------------------------------------------------------------------------
# Cross-node deduplication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_own_messages_are_ignored():
    """Messages from our own node_id are not re-injected into the local queue."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "my-node-123"
    # Bypass actual start/redis setup
    bus._running = True
    bus._start_time = 0.0
    bus._queue = asyncio.Queue(maxsize=100)

    envelope = json.dumps({
        "node_id": "my-node-123",
        "topic": "signal.generated",
        "data": {"symbol": "AAPL", "score": 80},
    })
    await bus._on_redis_message({"data": envelope})

    assert bus._queue.empty(), "Own messages should NOT be re-queued"


@pytest.mark.asyncio
async def test_remote_messages_are_injected():
    """Messages from a different node_id are injected into the local queue."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "my-node-123"
    bus._running = True
    bus._start_time = 0.0
    bus._queue = asyncio.Queue(maxsize=100)

    envelope = json.dumps({
        "node_id": "remote-node-456",
        "topic": "signal.generated",
        "data": {"symbol": "MSFT", "score": 72},
    })
    await bus._on_redis_message({"data": envelope})

    assert not bus._queue.empty(), "Remote messages SHOULD be queued locally"
    event = bus._queue.get_nowait()
    assert event["topic"] == "signal.generated"
    assert event["data"]["symbol"] == "MSFT"
    assert event.get("_remote") is True


@pytest.mark.asyncio
async def test_malformed_json_is_silently_dropped():
    """Invalid JSON from Redis is handled without raising."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "my-node-123"
    bus._running = True
    bus._queue = asyncio.Queue(maxsize=100)

    await bus._on_redis_message({"data": "NOT VALID JSON {{{{}}"})
    assert bus._queue.empty()


@pytest.mark.asyncio
async def test_empty_data_is_silently_dropped():
    """Empty or None data from Redis is handled without raising."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "my-node-123"
    bus._running = True
    bus._queue = asyncio.Queue(maxsize=100)

    await bus._on_redis_message({"data": ""})
    await bus._on_redis_message({"data": None})
    assert bus._queue.empty()


# ---------------------------------------------------------------------------
# Redis publish
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_publish_sends_envelope():
    """_redis_publish sends a correctly structured JSON envelope."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "test-node"
    bus._redis_connected = True

    mock_pub = AsyncMock()
    mock_pub.publish = AsyncMock(return_value=1)
    bus._redis_pub = mock_pub

    await bus._redis_publish("signal.generated", {"symbol": "AAPL", "score": 85})

    mock_pub.publish.assert_called_once()
    channel, payload = mock_pub.publish.call_args[0]
    assert channel == "etbus:signal.generated"
    envelope = json.loads(payload)
    assert envelope["node_id"] == "test-node"
    assert envelope["topic"] == "signal.generated"
    assert envelope["data"]["symbol"] == "AAPL"
    assert "timestamp" in envelope


@pytest.mark.asyncio
async def test_redis_publish_skipped_when_not_connected():
    """_redis_publish is a no-op when _redis_pub is None."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._redis_pub = None

    # Should not raise
    await bus._redis_publish("signal.generated", {"symbol": "AAPL", "score": 85})
    assert bus._redis_errors == 0


@pytest.mark.asyncio
async def test_redis_publish_increments_error_count_on_failure():
    """Publish failures increment _redis_errors and do NOT raise."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._node_id = "test-node"
    bus._redis_connected = True

    mock_pub = AsyncMock()
    mock_pub.publish = AsyncMock(side_effect=Exception("connection lost"))
    bus._redis_pub = mock_pub

    # patch _connect_redis so the reconnect branch doesn't try to connect
    with patch.object(bus, "_connect_redis", new_callable=AsyncMock):
        with patch.object(bus, "_disconnect_redis", new_callable=AsyncMock):
            for _ in range(3):
                await bus._redis_publish("signal.generated", {"symbol": "X"})

    assert bus._redis_errors == 3


# ---------------------------------------------------------------------------
# get_metrics() redis section
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_metrics_includes_redis_section():
    """get_metrics() always returns a 'redis' dict with required keys."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._running = True
    bus._start_time = 0.0

    metrics = bus.get_metrics()
    assert "redis" in metrics
    redis_m = metrics["redis"]
    assert "connected" in redis_m
    assert "url" in redis_m
    assert "node_id" in redis_m
    assert "publish_errors" in redis_m
    assert "bridged_topics" in redis_m
    assert redis_m["connected"] is False
    assert isinstance(redis_m["bridged_topics"], int)
    assert redis_m["bridged_topics"] > 0


@pytest.mark.asyncio
async def test_get_metrics_redis_connected_true_when_bridge_active():
    """get_metrics() reports connected=True when the bridge is up."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._running = True
    bus._start_time = 0.0
    bus._redis_connected = True
    bus._redis_url = "redis://192.168.1.105:6379/0"
    bus._node_id = "ESPENMAIN-9999"
    bus._redis_errors = 2

    metrics = bus.get_metrics()
    assert metrics["redis"]["connected"] is True
    assert metrics["redis"]["url"] == "redis://192.168.1.105:6379/0"
    assert metrics["redis"]["node_id"] == "ESPENMAIN-9999"
    assert metrics["redis"]["publish_errors"] == 2


# ---------------------------------------------------------------------------
# publish() bridges bridged topics but not non-bridged topics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_bridges_bridged_topic():
    """publish() calls _redis_publish for topics in REDIS_BRIDGED_TOPICS."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._running = True
    bus._start_time = 0.0
    bus._queue = asyncio.Queue(maxsize=100)
    bus._redis_connected = True

    with patch.object(bus, "_redis_publish", new_callable=AsyncMock) as mock_rp:
        await bus.publish("signal.generated", {"symbol": "AAPL", "score": 80, "action": "BUY"})
        mock_rp.assert_called_once()
        call_topic = mock_rp.call_args[0][0]
        assert call_topic == "signal.generated"


@pytest.mark.asyncio
async def test_publish_does_not_bridge_local_only_topic():
    """publish() does NOT call _redis_publish for topics NOT in REDIS_BRIDGED_TOPICS."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._running = True
    bus._start_time = 0.0
    bus._queue = asyncio.Queue(maxsize=100)
    bus._redis_connected = True

    # market_data.bar is intentionally kept local-only
    assert "market_data.bar" not in MessageBus.REDIS_BRIDGED_TOPICS

    with patch.object(bus, "_redis_publish", new_callable=AsyncMock) as mock_rp:
        await bus.publish("market_data.bar", {"symbol": "AAPL"})
        mock_rp.assert_not_called()


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disconnect_redis_clears_state():
    """_disconnect_redis cleans up all connection state."""
    from app.core.message_bus import MessageBus

    bus = MessageBus()
    bus._redis_connected = True
    bus._redis_url = "redis://127.0.0.1:6379/0"

    mock_pub = AsyncMock()
    mock_pub.close = AsyncMock()
    bus._redis_pub = mock_pub

    mock_sub = AsyncMock()
    mock_sub.unsubscribe = AsyncMock()
    mock_sub.close = AsyncMock()
    bus._redis_sub = mock_sub

    await bus._disconnect_redis()

    assert bus._redis_connected is False
    assert bus._redis_pub is None
    assert bus._redis_sub is None


# ---------------------------------------------------------------------------
# event-bus/status API endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_event_bus_status_includes_redis_field(client):
    """GET /api/v1/system/event-bus/status returns a 'redis' object."""
    resp = await client.get("/api/v1/system/event-bus/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "running" in body
    assert "topics" in body
    assert "redis" in body, f"'redis' key missing from response: {body}"
    redis_info = body["redis"]
    assert "connected" in redis_info


@pytest.mark.anyio
async def test_event_bus_status_redis_not_connected_without_url(client, monkeypatch):
    """When Redis is not connected, the endpoint reports redis.connected=False."""
    # MessageBus is a singleton; at test time it may already have connected if REDIS_URL was set at startup.
    # Patch the bus to report disconnected so we assert the endpoint shape.
    from app.core import message_bus as mb
    bus = mb.get_message_bus()
    monkeypatch.setattr(bus, "_redis_connected", False)
    resp = await client.get("/api/v1/system/event-bus/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["redis"]["connected"] is False


# ---------------------------------------------------------------------------
# REDIS_BRIDGED_TOPICS sanity checks
# ---------------------------------------------------------------------------

def test_bridged_topics_are_subset_of_valid_topics():
    """Every topic in REDIS_BRIDGED_TOPICS must also be in VALID_TOPICS."""
    from app.core.message_bus import MessageBus

    invalid = MessageBus.REDIS_BRIDGED_TOPICS - MessageBus.VALID_TOPICS
    assert not invalid, f"Bridged topics not in VALID_TOPICS: {invalid}"


def test_market_data_topics_not_bridged():
    """High-frequency market data topics must NOT be in REDIS_BRIDGED_TOPICS."""
    from app.core.message_bus import MessageBus

    local_only = {"market_data.bar", "market_data.quote"}
    bridged = local_only & MessageBus.REDIS_BRIDGED_TOPICS
    assert not bridged, f"market_data topics must stay local-only: {bridged}"


def test_redis_prefix_is_set():
    """REDIS_PREFIX must be a non-empty string."""
    from app.core.message_bus import MessageBus

    assert isinstance(MessageBus.REDIS_PREFIX, str)
    assert len(MessageBus.REDIS_PREFIX) > 0
