"""JWT Authentication Tests for Live Trading Endpoints.

Tests JWT token generation, validation, and authentication flows
for live trading endpoints. Verifies that:
- JWT tokens are correctly generated with proper claims
- JWT tokens are validated and decoded correctly
- Live trading endpoints require JWT auth when TRADING_MODE=live
- Paper trading endpoints fall back to bearer token auth
- Invalid or expired tokens are rejected
"""
import os
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["TRADING_MODE"] = "paper"
os.environ["ALPACA_API_KEY"] = "test_key"
os.environ["ALPACA_SECRET_KEY"] = "test_secret"
os.environ["API_AUTH_TOKEN"] = "test_auth_token_for_tests"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_tests_1234567890"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from app.main import app
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_jwt_secret,
)
from app.core.config import settings

# Force reload settings to pick up environment variables
settings.JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
settings.JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"])

# Reset the JWT initialization flag so the secret gets reloaded
import app.core.security as sec_module
sec_module._JWT_INITIALIZED = False
sec_module._JWT_SECRET = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_user_claims():
    """Sample user claims for JWT token testing."""
    return {
        "user_id": "test_user_123",
        "username": "test_trader",
        "trading_mode": "live",
        "permissions": ["trade", "view_positions"],
    }


@pytest.fixture
def valid_jwt_token(sample_user_claims):
    """Generate a valid JWT access token for testing."""
    return create_access_token(sample_user_claims)


@pytest.fixture
def expired_jwt_token(sample_user_claims):
    """Generate an expired JWT token for testing."""
    return create_access_token(
        sample_user_claims,
        expires_delta=timedelta(seconds=-60)  # Expired 60 seconds ago
    )


# ─────────────────────────────────────────────────────────────────────────────
# JWT Token Generation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTTokenGeneration:
    """Test JWT token creation and structure."""

    def test_create_access_token(self, sample_user_claims):
        """Test access token creation with valid claims."""
        token = create_access_token(sample_user_claims)
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify claims
        payload = decode_token(token)
        assert payload["user_id"] == sample_user_claims["user_id"]
        assert payload["username"] == sample_user_claims["username"]
        assert payload["trading_mode"] == sample_user_claims["trading_mode"]
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self, sample_user_claims):
        """Test refresh token creation with valid claims."""
        token = create_refresh_token(sample_user_claims)
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify claims
        payload = decode_token(token)
        assert payload["user_id"] == sample_user_claims["user_id"]
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiration_time(self, sample_user_claims):
        """Test that token expiration is set correctly."""
        token = create_access_token(sample_user_claims)
        payload = decode_token(token)

        # Check expiration is in the future
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        assert exp_time > iat_time

        # Check expiration is approximately correct (within 1 minute tolerance)
        expected_exp = iat_time + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        assert abs((exp_time - expected_exp).total_seconds()) < 60

    def test_custom_expiration_delta(self, sample_user_claims):
        """Test token creation with custom expiration time."""
        custom_delta = timedelta(minutes=30)
        token = create_access_token(sample_user_claims, expires_delta=custom_delta)
        payload = decode_token(token)

        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        expected_exp = iat_time + custom_delta

        # Check expiration is approximately correct (within 1 minute tolerance)
        assert abs((exp_time - expected_exp).total_seconds()) < 60

    def test_generate_jwt_secret(self):
        """Test JWT secret generation."""
        secret = generate_jwt_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

        # Generate multiple secrets and ensure they're unique
        secret2 = generate_jwt_secret()
        assert secret != secret2


# ─────────────────────────────────────────────────────────────────────────────
# JWT Token Validation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTTokenValidation:
    """Test JWT token decoding and validation."""

    def test_decode_valid_token(self, valid_jwt_token, sample_user_claims):
        """Test decoding a valid JWT token."""
        payload = decode_token(valid_jwt_token)
        assert payload["user_id"] == sample_user_claims["user_id"]
        assert payload["username"] == sample_user_claims["username"]
        assert payload["type"] == "access"

    def test_decode_expired_token(self, expired_jwt_token):
        """Test that expired tokens are rejected."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_jwt_token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_token(self):
        """Test that invalid tokens are rejected."""
        from fastapi import HTTPException

        invalid_token = "invalid.jwt.token"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    def test_decode_malformed_token(self):
        """Test that malformed tokens are rejected."""
        from fastapi import HTTPException

        malformed_token = "not-a-valid-jwt"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(malformed_token)

        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# JWT Authentication Dependency Tests (Paper Mode)
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTAuthPaperMode:
    """Test JWT authentication in paper trading mode."""

    @pytest.mark.anyio
    async def test_paper_mode_accepts_bearer_token(self, client):
        """Test that paper mode accepts simple bearer tokens."""
        # Paper mode should fall back to bearer token auth
        headers = {"Authorization": "Bearer test_auth_token_for_tests"}

        # This endpoint doesn't exist but will test the auth middleware
        # We expect a 404 (not found) rather than 401 (unauthorized)
        # indicating that auth passed
        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # 404 means auth passed, endpoint not found
        # 401 or 403 would mean auth failed
        assert response.status_code in [404, 405]

    @pytest.mark.anyio
    async def test_paper_mode_rejects_invalid_bearer_token(self, client):
        """Test that paper mode rejects invalid bearer tokens."""
        headers = {"Authorization": "Bearer invalid_token"}

        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # Should get 401 unauthorized for invalid token
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_paper_mode_rejects_missing_auth(self, client):
        """Test that paper mode requires authentication."""
        # No auth header
        response = await client.post("/api/v1/orders/test-endpoint")
        # Should get 401 unauthorized
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# JWT Authentication Dependency Tests (Live Mode)
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTAuthLiveMode:
    """Test JWT authentication in live trading mode."""

    @pytest.fixture(autouse=True)
    def set_live_mode(self):
        """Set TRADING_MODE to live for these tests."""
        original_mode = settings.TRADING_MODE
        settings.TRADING_MODE = "live"
        yield
        settings.TRADING_MODE = original_mode

    @pytest.mark.anyio
    async def test_live_mode_accepts_valid_jwt(self, client, valid_jwt_token):
        """Test that live mode accepts valid JWT tokens."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # 404 or 405 means auth passed, endpoint not found or method not allowed
        # 401 or 403 would mean auth failed
        assert response.status_code in [404, 405]

    @pytest.mark.anyio
    async def test_live_mode_rejects_expired_jwt(self, client, expired_jwt_token):
        """Test that live mode rejects expired JWT tokens."""
        headers = {"Authorization": f"Bearer {expired_jwt_token}"}

        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # Should get 401 unauthorized for expired token
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_live_mode_rejects_bearer_token(self, client):
        """Test that live mode rejects simple bearer tokens (requires JWT)."""
        # Try to use simple bearer token in live mode
        headers = {"Authorization": "Bearer test_auth_token_for_tests"}

        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # Should get 401 because simple bearer tokens are not valid JWTs
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_live_mode_rejects_missing_auth(self, client):
        """Test that live mode requires authentication."""
        # No auth header
        response = await client.post("/api/v1/orders/test-endpoint")
        # Should get 401 unauthorized
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_live_mode_validates_trading_mode_claim(self, client, sample_user_claims):
        """Test that live mode validates trading_mode claim in token."""
        # Create token with paper trading mode claim
        paper_claims = sample_user_claims.copy()
        paper_claims["trading_mode"] = "paper"
        paper_token = create_access_token(paper_claims)

        headers = {"Authorization": f"Bearer {paper_token}"}
        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # Should get 403 forbidden because token is for paper mode
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_live_mode_validates_token_type(self, client, sample_user_claims):
        """Test that live mode validates token type (access vs refresh)."""
        # Create refresh token and try to use it for access
        refresh_token = create_refresh_token(sample_user_claims)

        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = await client.post("/api/v1/orders/test-endpoint", headers=headers)
        # Should get 401 because refresh tokens can't be used for access
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests with Real Endpoints
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTAuthRealEndpoints:
    """Test JWT authentication with real order endpoints."""

    @pytest.mark.anyio
    async def test_orders_endpoint_requires_auth(self, client):
        """Test that order creation endpoint requires authentication."""
        order_data = {
            "symbol": "AAPL",
            "qty": "1",
            "side": "buy",
            "type": "market",
            "time_in_force": "day"
        }

        # No auth header
        response = await client.post("/api/v1/orders/advanced", json=order_data)
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_orders_endpoint_paper_mode_bearer_auth(self, client):
        """Test order creation with bearer token in paper mode."""
        headers = {"Authorization": "Bearer test_auth_token_for_tests"}
        order_data = {
            "symbol": "AAPL",
            "qty": "1",
            "side": "buy",
            "type": "market",
            "time_in_force": "day"
        }

        response = await client.post("/api/v1/orders/advanced", json=order_data, headers=headers)
        # Auth should pass; may get different error (broker, alignment, etc.)
        assert response.status_code not in [401, 403]

    @pytest.mark.anyio
    async def test_cancel_order_requires_auth(self, client):
        """Test that cancel order endpoint requires authentication."""
        # No auth header
        response = await client.delete("/api/v1/orders/fake-order-id")
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_emergency_stop_requires_auth(self, client):
        """Test that emergency stop endpoint requires authentication."""
        # No auth header
        response = await client.post("/api/v1/orders/emergency-stop")
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Security Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestJWTSecurity:
    """Test JWT security features."""

    def test_token_signatures_differ(self, sample_user_claims):
        """Test that different tokens have different signatures."""
        token1 = create_access_token(sample_user_claims)
        token2 = create_access_token(sample_user_claims)

        # Tokens should be different due to different iat times
        assert token1 != token2

    def test_token_tamper_detection(self, valid_jwt_token):
        """Test that tampered tokens are rejected."""
        from fastapi import HTTPException

        # Tamper with the token by changing a character
        tampered_token = valid_jwt_token[:-5] + "XXXXX"

        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered_token)

        assert exc_info.value.status_code == 401

    def test_token_without_secret_fails(self, sample_user_claims):
        """Test that tokens can't be created without JWT secret."""
        from fastapi import HTTPException

        # Temporarily clear JWT secret
        original_secret = settings.JWT_SECRET_KEY
        settings.JWT_SECRET_KEY = ""

        try:
            with pytest.raises(HTTPException) as exc_info:
                create_access_token(sample_user_claims)
            assert exc_info.value.status_code == 500
        finally:
            settings.JWT_SECRET_KEY = original_secret

    def test_decode_without_secret_fails(self, valid_jwt_token):
        """Test that tokens can't be decoded without JWT secret."""
        from fastapi import HTTPException

        # Temporarily clear JWT secret
        original_secret = settings.JWT_SECRET_KEY
        settings.JWT_SECRET_KEY = ""

        try:
            with pytest.raises(HTTPException) as exc_info:
                decode_token(valid_jwt_token)
            assert exc_info.value.status_code == 500
        finally:
            settings.JWT_SECRET_KEY = original_secret
