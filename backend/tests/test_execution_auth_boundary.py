"""Security/reality boundary: execution routes require auth; shadow mode default."""

import pytest


@pytest.mark.anyio
async def test_orders_advanced_requires_auth(client):
    """POST /api/v1/orders/advanced returns 401 without Authorization header (when API_AUTH_TOKEN set)."""
    # When API_AUTH_TOKEN is configured, missing Bearer yields 401
    r = await client.post(
        "/api/v1/orders/advanced",
        json={"symbol": "AAPL", "side": "buy", "type": "market", "qty": "1"},
    )
    # Either 401 (auth required, no header) or 403 (API_AUTH_TOKEN not set — fail closed)
    assert r.status_code in (401, 403)


@pytest.mark.anyio
async def test_orders_advanced_rejects_invalid_bearer(client):
    """POST /api/v1/orders/advanced with invalid Bearer returns 401."""
    r = await client.post(
        "/api/v1/orders/advanced",
        json={"symbol": "AAPL", "side": "buy", "type": "market", "qty": "1"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code in (401, 403)


def test_shadow_mode_default():
    """AUTO_EXECUTE_TRADES defaults to False (shadow mode) in config."""
    from app.core.config import Settings
    default = Settings.model_fields["AUTO_EXECUTE_TRADES"].default
    assert default is False
