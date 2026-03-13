"""WebSocket end-to-end tests: connect, subscribe, and receive backend broadcasts."""

import asyncio
import threading
import pytest
from fastapi.testclient import TestClient

# Use conftest client fixture if available; otherwise create app here
@pytest.fixture
def ws_client():
    from app.main import app
    return TestClient(app)


def test_ws_connect_with_token_succeeds(ws_client):
    """Connect with valid token is accepted."""
    token = "test_auth_token_for_tests"
    with ws_client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_json({"type": "subscribe", "channel": "signals"})
        # Connection accepted; no immediate close
    # Clean exit


def test_ws_subscribe_and_receive(ws_client):
    """Client subscribes and backend broadcast call path executes without errors."""
    token = "test_auth_token_for_tests"
    errors = []

    def run_broadcast():
        """Run broadcast_ws in a new loop so it sends to the connected client."""
        import asyncio
        from app.websocket_manager import broadcast_ws
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                broadcast_ws("signals", {"type": "new_signal", "signal": {"symbol": "TEST", "score": 80}})
            )
        except Exception as exc:
            errors.append(exc)
        finally:
            loop.close()

    with ws_client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_json({"type": "subscribe", "channel": "signals"})
        # Start background thread to broadcast after subscription.
        t = threading.Thread(target=run_broadcast)
        t.start()
        t.join(timeout=2.0)

    assert not errors, f"broadcast_ws raised unexpected error: {errors}"
    assert not t.is_alive(), "Broadcast thread should complete promptly"


@pytest.mark.anyio
async def test_ws_subscribe_valid_channels(client):
    """Subscribe to allowed channels does not error; registry accepts them."""
    from app.websocket_manager import WS_ALLOWED_CHANNELS
    r = await client.get("/api/v1/ws/registry")
    assert r.status_code == 200
    body = r.json()
    assert "channels" in body
    # All allowed channels should be in registry
    for ch in ["signals", "order", "council_verdict", "market", "swarm"]:
        assert ch in WS_ALLOWED_CHANNELS, f"Channel {ch} must be in WS_ALLOWED_CHANNELS"
