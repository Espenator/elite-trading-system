"""Tests for JWT authentication and scope-based authorization."""
import os
import pytest
from datetime import timedelta
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["TRADING_MODE"] = "paper"
os.environ["ALPACA_API_KEY"] = "test_key"
os.environ["ALPACA_SECRET_KEY"] = "test_secret"
os.environ["API_AUTH_TOKEN"] = "test_auth_token_for_tests"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_only"
os.environ["ALPACA_SIGNATURE_SECRET"] = "test_signature_secret_for_testing"

from app.main import app  # noqa: E402
from app.core.security import (  # noqa: E402
    create_access_token,
    decode_jwt_token,
    verify_token_scopes,
    generate_order_signature,
    verify_order_signature,
)


# ── JWT Token Management Tests ──────────────────────────────────────────────


def test_create_access_token():
    """Test JWT token creation with custom data."""
    data = {"sub": "test_user", "scopes": ["trading", "read"]}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_jwt_token():
    """Test JWT token decoding and validation."""
    data = {"sub": "test_user", "scopes": ["trading"]}
    token = create_access_token(data)

    payload = decode_jwt_token(token)

    assert payload is not None
    assert payload["sub"] == "test_user"
    assert "trading" in payload["scopes"]
    assert "exp" in payload
    assert "iat" in payload


def test_decode_invalid_token():
    """Test that invalid tokens return None."""
    payload = decode_jwt_token("invalid_token_here")
    assert payload is None


def test_token_expiration():
    """Test that expired tokens are rejected."""
    data = {"sub": "test_user", "scopes": ["trading"]}
    # Create token that expires immediately
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))

    payload = decode_jwt_token(token)
    assert payload is None  # Should be expired


def test_verify_token_scopes_success():
    """Test scope verification with valid scopes."""
    payload = {"scopes": ["trading", "read", "write"]}

    assert verify_token_scopes(payload, ["trading"]) is True
    assert verify_token_scopes(payload, ["read"]) is True
    assert verify_token_scopes(payload, ["trading", "read"]) is True


def test_verify_token_scopes_failure():
    """Test scope verification with missing scopes."""
    payload = {"scopes": ["read"]}

    assert verify_token_scopes(payload, ["trading"]) is False
    assert verify_token_scopes(payload, ["write"]) is False
    assert verify_token_scopes(payload, ["read", "trading"]) is False


def test_verify_token_scopes_empty():
    """Test scope verification with no scopes."""
    payload = {"scopes": []}

    assert verify_token_scopes(payload, ["trading"]) is False
    assert verify_token_scopes(payload, []) is True  # Empty required scopes


# ── Order Signature Tests ────────────────────────────────────────────────────


def test_generate_order_signature():
    """Test order signature generation."""
    order_data = {
        "symbol": "AAPL",
        "qty": "10",
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
    }

    signature = generate_order_signature(order_data)

    assert signature is not None
    assert isinstance(signature, str)
    assert len(signature) == 64  # HMAC-SHA256 hex digest length


def test_verify_order_signature_success():
    """Test order signature verification with valid signature."""
    order_data = {
        "symbol": "AAPL",
        "qty": "10",
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
    }

    signature = generate_order_signature(order_data)
    assert verify_order_signature(order_data, signature) is True


def test_verify_order_signature_failure():
    """Test order signature verification with invalid signature."""
    order_data = {
        "symbol": "AAPL",
        "qty": "10",
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
    }

    # Use wrong signature
    assert verify_order_signature(order_data, "invalid_signature") is False


def test_order_signature_tamper_detection():
    """Test that signature detects data tampering."""
    order_data = {
        "symbol": "AAPL",
        "qty": "10",
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
    }

    signature = generate_order_signature(order_data)

    # Tamper with the order data
    order_data["qty"] = "100"

    # Signature should fail
    assert verify_order_signature(order_data, signature) is False


def test_order_signature_canonical_representation():
    """Test that signature is consistent regardless of key order."""
    order_data_1 = {"symbol": "AAPL", "qty": "10", "side": "buy"}
    order_data_2 = {"qty": "10", "symbol": "AAPL", "side": "buy"}

    sig1 = generate_order_signature(order_data_1)
    sig2 = generate_order_signature(order_data_2)

    # Should produce same signature (canonical JSON with sorted keys)
    assert sig1 == sig2


# ── API Endpoint Tests with JWT ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_legacy_token_still_works():
    """Test that legacy API_AUTH_TOKEN still works for backward compatibility."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test_auth_token_for_tests"}

        # Follow redirects
        resp = await client.get("/api/v1/signals", headers=headers, follow_redirects=True)
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_jwt_token_authentication():
    """Test that JWT tokens work for authentication."""
    # Create a JWT token with trading scope
    token = create_access_token({"sub": "test_user", "scopes": ["trading"]})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Follow redirects
        resp = await client.get("/api/v1/signals", headers=headers, follow_redirects=True)
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_trading_scope_required_for_orders():
    """Test that trading scope is required for order endpoints."""
    # Create token WITHOUT trading scope
    token = create_access_token({"sub": "test_user", "scopes": ["read"]})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Try to cancel all orders (requires trading scope)
        resp = await client.delete("/api/v1/orders/", headers=headers)
        assert resp.status_code == 403
        assert "trading scope" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_trading_scope_allows_orders():
    """Test that trading scope allows access to order endpoints."""
    # Create token WITH trading scope
    token = create_access_token({"sub": "test_user", "scopes": ["trading"]})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Try to get orders (should work even without real Alpaca keys)
        resp = await client.get("/api/v1/orders/", headers=headers)
        # Might return 200 with empty list or 502 if Alpaca fails, both acceptable
        assert resp.status_code in (200, 502)


@pytest.mark.anyio
async def test_trading_scope_required_for_risk_shield():
    """Test that trading scope is required for risk shield emergency actions."""
    # Create token WITHOUT trading scope
    token = create_access_token({"sub": "test_user", "scopes": ["read"]})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Try to execute emergency action (requires trading scope)
        resp = await client.post("/api/v1/risk-shield/emergency-action", json={
            "action": "freeze_entries",
            "value": True
        }, headers=headers)
        assert resp.status_code == 403
        assert "trading scope" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_no_auth_header_blocked():
    """Test that requests without auth header are blocked."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to cancel orders without auth
        resp = await client.delete("/api/v1/orders/")
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_invalid_jwt_token_blocked():
    """Test that invalid JWT tokens are blocked."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid_jwt_token_here"}

        # Should fall back to legacy token check and fail
        resp = await client.delete("/api/v1/orders/", headers=headers)
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_expired_jwt_token_blocked():
    """Test that expired JWT tokens are blocked."""
    # Create expired token
    token = create_access_token(
        {"sub": "test_user", "scopes": ["trading"]},
        expires_delta=timedelta(seconds=-10)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete("/api/v1/orders/", headers=headers)
        assert resp.status_code == 401
