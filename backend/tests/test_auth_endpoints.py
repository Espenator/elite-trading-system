"""Tests for JWT Authentication Endpoints.

Tests the /api/v1/auth/* endpoints:
- POST /auth/login - Login and get JWT tokens
- POST /auth/refresh - Refresh access token
- GET /auth/me - Get current user information
- GET /auth/verify - Verify token validity
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
from app.core.security import create_access_token, create_refresh_token
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
    """Sample user claims for testing."""
    return {
        "user_id": "test_user_123",
        "username": "test_trader",
        "trading_mode": "live",
        "permissions": ["trade", "view_positions"],
    }


@pytest.fixture
def valid_access_token(sample_user_claims):
    """Generate a valid access token."""
    return create_access_token(sample_user_claims)


@pytest.fixture
def valid_refresh_token(sample_user_claims):
    """Generate a valid refresh token."""
    return create_refresh_token(sample_user_claims)


@pytest.fixture
def expired_access_token(sample_user_claims):
    """Generate an expired access token."""
    return create_access_token(
        sample_user_claims,
        expires_delta=timedelta(seconds=-60)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Login Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoginEndpoint:
    """Test POST /api/v1/auth/login endpoint."""

    async def test_login_success(self, client):
        """Test successful login returns JWT tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_trader",
                "password": "test_password",
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

        # Verify tokens are not empty
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    async def test_login_with_trading_mode(self, client):
        """Test login with explicit trading mode."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_trader",
                "password": "test_password",
                "trading_mode": "live",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_missing_username(self, client):
        """Test login with missing username."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "test_password"}
        )
        assert response.status_code == 422  # Validation error

    async def test_login_missing_password(self, client):
        """Test login with missing password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_trader"}
        )
        assert response.status_code == 422  # Validation error

    async def test_login_empty_credentials(self, client):
        """Test login with empty credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": ""}
        )
        # Should still succeed (we don't validate credentials yet)
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Refresh Token Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRefreshEndpoint:
    """Test POST /api/v1/auth/refresh endpoint."""

    async def test_refresh_success(self, client, valid_refresh_token):
        """Test successful token refresh."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": valid_refresh_token}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

        # Verify new access token is returned
        assert len(data["access_token"]) > 0
        # Refresh token should be the same
        assert data["refresh_token"] == valid_refresh_token

    async def test_refresh_with_access_token_fails(self, client, valid_access_token):
        """Test that using access token for refresh fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": valid_access_token}
        )
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]

    async def test_refresh_with_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token_xyz"}
        )
        assert response.status_code == 401

    async def test_refresh_with_expired_token(self, client, sample_user_claims):
        """Test refresh with expired token."""
        # Create an expired refresh token
        expired_refresh = create_refresh_token(
            {**sample_user_claims, "exp": datetime.utcnow() - timedelta(days=1)}
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_refresh}
        )
        assert response.status_code == 401

    async def test_refresh_missing_token(self, client):
        """Test refresh with missing token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={}
        )
        assert response.status_code == 422  # Validation error


# ─────────────────────────────────────────────────────────────────────────────
# Get Current User Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCurrentUserEndpoint:
    """Test GET /api/v1/auth/me endpoint."""

    async def test_get_current_user_success(self, client, valid_access_token):
        """Test getting current user info with valid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify user info structure
        assert "user_id" in data
        assert "username" in data
        assert "trading_mode" in data
        assert "permissions" in data

        # Verify user info matches token claims
        assert data["user_id"] == "test_user_123"
        assert data["username"] == "test_trader"
        assert data["trading_mode"] == "live"
        assert isinstance(data["permissions"], list)

    async def test_get_current_user_no_auth_header(self, client):
        """Test getting current user without auth header."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]

    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 401

    async def test_get_current_user_expired_token(self, client, expired_access_token):
        """Test getting current user with expired token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_access_token}"}
        )
        assert response.status_code == 401

    async def test_get_current_user_with_refresh_token_fails(self, client, valid_refresh_token):
        """Test that using refresh token for /me fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {valid_refresh_token}"}
        )
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Verify Token Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVerifyEndpoint:
    """Test GET /api/v1/auth/verify endpoint."""

    async def test_verify_valid_token(self, client, valid_access_token):
        """Test verifying a valid token."""
        response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {valid_access_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "user_id" in data
        assert "expires_at" in data
        assert data["user_id"] == "test_user_123"
        assert data["expires_at"] > 0

    async def test_verify_invalid_token(self, client):
        """Test verifying an invalid token."""
        response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert data.get("user_id") is None
        assert data.get("expires_at") is None

    async def test_verify_expired_token(self, client, expired_access_token):
        """Test verifying an expired token."""
        response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {expired_access_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False

    async def test_verify_no_auth_header(self, client):
        """Test verify without auth header."""
        response = await client.get("/api/v1/auth/verify")
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False

    async def test_verify_refresh_token(self, client, valid_refresh_token):
        """Test verifying a refresh token (should work since it's still a valid JWT)."""
        response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {valid_refresh_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify endpoint doesn't check token type, just validity
        assert data["valid"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthWorkflow:
    """Test complete authentication workflow."""

    async def test_login_and_use_token(self, client):
        """Test login, then use token to access /me."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_trader", "password": "test_password"}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # Use access token to get user info
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert me_response.status_code == 200
        user_info = me_response.json()
        assert user_info["username"] == "test_trader"

    async def test_login_refresh_and_use_new_token(self, client):
        """Test login, refresh token, then use new access token."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_trader", "password": "test_password"}
        )
        tokens = login_response.json()

        # Refresh token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()

        # Use new access token
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )
        assert me_response.status_code == 200

    async def test_verify_token_lifecycle(self, client):
        """Test token verification throughout lifecycle."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_trader", "password": "test_password"}
        )
        tokens = login_response.json()

        # Verify access token
        verify_response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

        # Verify refresh token
        verify_refresh_response = await client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
        )
        assert verify_refresh_response.status_code == 200
        assert verify_refresh_response.json()["valid"] is True
