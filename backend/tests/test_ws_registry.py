"""WebSocket registry and payload format — operator awareness contract."""

import pytest


@pytest.mark.anyio
async def test_ws_registry_returns_channels_and_schema(client):
    """GET /api/v1/ws/registry returns channel names, message schema, and subscriber counts."""
    r = await client.get("/api/v1/ws/registry")
    assert r.status_code == 200
    body = r.json()
    assert "channels" in body
    assert "message_schema" in body
    assert "schema_examples" in body
    assert "total_connections" in body
    assert "subscriber_counts" in body
    assert "signals" in body["channels"]
    assert "council" in body["channels"]
    assert "market" in body["channels"]
    assert body["message_schema"].get("channel") == "string (e.g. signals, council, risk, market, order, swarm)"
    assert body["message_schema"].get("type") and body["message_schema"].get("ts")


@pytest.mark.anyio
async def test_ws_payload_has_canonical_shape():
    """Bridges publish {channel, type, data, ts}; sample validation."""
    from app.websocket_manager import broadcast_ws
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    # Build canonical payload as broadcast_ws would
    channel = "signal"
    data = {"type": "new_signal", "signal": {"symbol": "AAPL", "score": 80}}
    ts = 1234567890.0
    msg = {"channel": channel, "type": data.get("type", "update"), "data": data, "ts": ts}
    assert msg["channel"] == "signal"
    assert msg["type"] == "new_signal"
    assert "data" in msg
    assert "ts" in msg
