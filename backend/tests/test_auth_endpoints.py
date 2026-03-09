"""
Tests for JWT Authentication Endpoints.

Tests the /api/v1/auth/* endpoints including login, refresh, verify, and user info.
"""

import pytest
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core import jwt_utils
from app.core.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestLoginEndpoint:
    """Test POST /api/v1/auth/login endpoint."""

    def test_login_with_valid_api_key(self, client):
        """Login should succeed with valid API key."""
        with patch.object(settings, "API_AUTH_TOKEN", "test-api-key-123"):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "api_key": "test-api-key-123",
                    "username": "test_user"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

            # Verify tokens are valid
            access_payload = jwt_utils.verify_token(data["access_token"], token_type="access")
            assert access_payload is not None
            assert access_payload["sub"] == "test_user"

            refresh_payload = jwt_utils.verify_token(data["refresh_token"], token_type="refresh")
            assert refresh_payload is not None
            assert refresh_payload["sub"] == "test_user"

    def test_login_with_invalid_api_key(self, client):
        """Login should fail with invalid API key."""
        with patch.object(settings, "API_AUTH_TOKEN", "correct-key"):
            response = client.post(
                "/api/v1/auth/login",
                json={"api_key": "wrong-key"}
            )

            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]

    def test_login_without_api_key(self, client):
        """Login should fail when API key is missing."""
        response = client.post(
            "/api/v1/auth/login",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_login_when_auth_not_configured(self, client):
        """Login should fail gracefully when auth not configured."""
        with patch.object(settings, "API_AUTH_TOKEN", ""):
            response = client.post(
                "/api/v1/auth/login",
                json={"api_key": "any-key"}
            )

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_login_default_username(self, client):
        """Login should use default username if not provided."""
        with patch.object(settings, "API_AUTH_TOKEN", "test-key"):
            response = client.post(
                "/api/v1/auth/login",
                json={"api_key": "test-key"}
            )

            assert response.status_code == 200
            access_token = response.json()["access_token"]

            payload = jwt_utils.verify_token(access_token, token_type="access")
            assert payload["sub"] == "api_user"  # Default username

    def test_login_custom_username(self, client):
        """Login should accept custom username."""
        with patch.object(settings, "API_AUTH_TOKEN", "test-key"):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "api_key": "test-key",
                    "username": "alice"
                }
            )

            assert response.status_code == 200
            access_token = response.json()["access_token"]

            payload = jwt_utils.verify_token(access_token, token_type="access")
            assert payload["sub"] == "alice"


class TestRefreshEndpoint:
    """Test POST /api/v1/auth/refresh endpoint."""

    def test_refresh_with_valid_token(self, client):
        """Refresh should succeed with valid refresh token."""
        # Create valid refresh token
        refresh_token = jwt_utils.create_refresh_token({"sub": "test_user", "type_": "api"})

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # New access token should be valid
        new_access_payload = jwt_utils.verify_token(data["access_token"], token_type="access")
        assert new_access_payload is not None
        assert new_access_payload["sub"] == "test_user"

        # Refresh token should be the same (not rotated)
        assert data["refresh_token"] == refresh_token

    def test_refresh_with_expired_token(self, client):
        """Refresh should fail with expired refresh token."""
        # Create expired refresh token
        expired_delta = timedelta(seconds=-10)
        expired_token = jwt_utils.create_refresh_token(
            {"sub": "test"},
            expires_delta=expired_delta
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]

    def test_refresh_with_access_token(self, client):
        """Refresh should fail when given access token instead of refresh token."""
        # Create access token (wrong type)
        access_token = jwt_utils.create_access_token({"sub": "test"})

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]

    def test_refresh_with_invalid_token(self, client):
        """Refresh should fail with malformed token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )

        assert response.status_code == 401

    def test_refresh_preserves_user_data(self, client):
        """Refresh should preserve user data from original token."""
        refresh_token = jwt_utils.create_refresh_token({
            "sub": "alice",
            "type_": "api",
        })

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        new_access_token = response.json()["access_token"]

        payload = jwt_utils.verify_token(new_access_token, token_type="access")
        assert payload["sub"] == "alice"
        assert payload["type_"] == "api"


class TestMeEndpoint:
    """Test GET /api/v1/auth/me endpoint."""

    def test_me_with_valid_jwt(self, client):
        """Me endpoint should return user info with valid JWT."""
        access_token = jwt_utils.create_access_token({
            "sub": "alice",
            "type_": "api",
        })

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["authenticated"] is True
        assert "user" in data
        assert data["user"]["sub"] == "alice"

    def test_me_with_legacy_token(self, client):
        """Me endpoint should work with legacy bearer token."""
        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "legacy-token-123"

            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer legacy-token-123"}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["authenticated"] is True
            assert data["user"]["type"] == "legacy"

    def test_me_without_auth(self, client):
        """Me endpoint should reject unauthenticated requests."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_me_with_expired_token(self, client):
        """Me endpoint should reject expired tokens."""
        expired_token = jwt_utils.create_access_token(
            {"sub": "test"},
            expires_delta=timedelta(seconds=-10)
        )

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = None  # No legacy fallback

            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"}
            )

            assert response.status_code == 401

    def test_me_with_invalid_token(self, client):
        """Me endpoint should reject invalid tokens."""
        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = None

            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )

            assert response.status_code == 401


class TestVerifyEndpoint:
    """Test GET /api/v1/auth/verify endpoint."""

    def test_verify_with_valid_jwt(self, client):
        """Verify should succeed with valid JWT."""
        access_token = jwt_utils.create_access_token({"sub": "test"})

        response = client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "user_type" in data

    def test_verify_with_legacy_token(self, client):
        """Verify should succeed with legacy token."""
        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "legacy-token"

            response = client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": "Bearer legacy-token"}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is True
            assert data["user_type"] == "legacy"

    def test_verify_with_expired_token(self, client):
        """Verify should reject expired token."""
        expired_token = jwt_utils.create_access_token(
            {"sub": "test"},
            expires_delta=timedelta(seconds=-10)
        )

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = None

            response = client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {expired_token}"}
            )

            assert response.status_code == 401

    def test_verify_without_auth(self, client):
        """Verify should reject unauthenticated requests."""
        response = client.get("/api/v1/auth/verify")

        assert response.status_code == 401


class TestAuthEndpointIntegration:
    """Integration tests for auth endpoint workflows."""

    def test_full_auth_workflow(self, client):
        """Test complete login → verify → refresh → use token workflow."""
        with patch.object(settings, "API_AUTH_TOKEN", "test-key"):
            # Step 1: Login
            login_response = client.post(
                "/api/v1/auth/login",
                json={"api_key": "test-key", "username": "alice"}
            )
            assert login_response.status_code == 200
            tokens = login_response.json()

            access_token = tokens["access_token"]
            refresh_token = tokens["refresh_token"]

            # Step 2: Verify access token
            verify_response = client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert verify_response.status_code == 200
            assert verify_response.json()["valid"] is True

            # Step 3: Get user info
            me_response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert me_response.status_code == 200
            assert me_response.json()["user"]["sub"] == "alice"

            # Step 4: Refresh token
            refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            assert refresh_response.status_code == 200
            new_tokens = refresh_response.json()

            # Step 5: Use new access token
            new_verify_response = client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
            )
            assert new_verify_response.status_code == 200

    def test_multiple_refreshes(self, client):
        """Test that refresh token can be used multiple times."""
        refresh_token = jwt_utils.create_refresh_token({"sub": "test"})

        # First refresh
        response1 = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response1.status_code == 200

        # Second refresh with same token
        response2 = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response2.status_code == 200

        # Both should succeed (no token rotation)
        assert response2.json()["refresh_token"] == refresh_token
