"""
Comprehensive JWT Authentication Tests for Embodier Trader.

Tests JWT token generation, validation, refresh, and authentication endpoints.
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.core import jwt_utils
from app.core.config import settings
from app.core.security import require_auth, optional_auth, get_current_user


class TestJWTTokenGeneration:
    """Test JWT token creation and encoding."""

    def test_create_access_token_default_expiry(self):
        """Access token should expire in JWT_ACCESS_TOKEN_EXPIRE_MINUTES."""
        data = {"sub": "test_user", "role": "trader"}
        token = jwt_utils.create_access_token(data)

        # Decode without verification to inspect payload
        payload = jwt_utils.decode_token_without_verification(token)

        assert payload["sub"] == "test_user"
        assert payload["role"] == "trader"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

        # Verify expiration is approximately correct (within 1 minute tolerance)
        expected_exp = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert abs((actual_exp - expected_exp).total_seconds()) < 60

    def test_create_access_token_custom_expiry(self):
        """Access token should accept custom expiration time."""
        data = {"sub": "test_user"}
        custom_delta = timedelta(minutes=5)
        token = jwt_utils.create_access_token(data, expires_delta=custom_delta)

        payload = jwt_utils.decode_token_without_verification(token)

        expected_exp = datetime.now(timezone.utc) + custom_delta
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert abs((actual_exp - expected_exp).total_seconds()) < 5

    def test_create_refresh_token_default_expiry(self):
        """Refresh token should expire in JWT_REFRESH_TOKEN_EXPIRE_DAYS."""
        data = {"sub": "test_user"}
        token = jwt_utils.create_refresh_token(data)

        payload = jwt_utils.decode_token_without_verification(token)

        assert payload["sub"] == "test_user"
        assert payload["type"] == "refresh"
        assert "exp" in payload

        expected_exp = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert abs((actual_exp - expected_exp).total_seconds()) < 60

    def test_create_refresh_token_custom_expiry(self):
        """Refresh token should accept custom expiration time."""
        data = {"sub": "test_user"}
        custom_delta = timedelta(days=1)
        token = jwt_utils.create_refresh_token(data, expires_delta=custom_delta)

        payload = jwt_utils.decode_token_without_verification(token)

        expected_exp = datetime.now(timezone.utc) + custom_delta
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert abs((actual_exp - expected_exp).total_seconds()) < 60

    def test_token_contains_iat(self):
        """Tokens should contain issued-at timestamp."""
        token = jwt_utils.create_access_token({"sub": "test"})
        payload = jwt_utils.decode_token_without_verification(token)

        assert "iat" in payload
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert abs((now - iat).total_seconds()) < 5


class TestJWTTokenVerification:
    """Test JWT token validation and verification."""

    def test_verify_valid_access_token(self):
        """Valid access token should be verified successfully."""
        data = {"sub": "test_user", "role": "admin"}
        token = jwt_utils.create_access_token(data)

        payload = jwt_utils.verify_token(token, token_type="access")

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_verify_valid_refresh_token(self):
        """Valid refresh token should be verified successfully."""
        data = {"sub": "test_user"}
        token = jwt_utils.create_refresh_token(data)

        payload = jwt_utils.verify_token(token, token_type="refresh")

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["type"] == "refresh"

    def test_verify_token_type_mismatch(self):
        """Access token verified as refresh should fail."""
        access_token = jwt_utils.create_access_token({"sub": "test"})

        # Try to verify access token as refresh token
        payload = jwt_utils.verify_token(access_token, token_type="refresh")

        assert payload is None

    def test_verify_expired_token(self):
        """Expired token should fail verification."""
        data = {"sub": "test_user"}
        # Create token that expires in -1 second (already expired)
        expired_delta = timedelta(seconds=-1)
        token = jwt_utils.create_access_token(data, expires_delta=expired_delta)

        payload = jwt_utils.verify_token(token, token_type="access")

        assert payload is None

    def test_verify_invalid_signature(self):
        """Token with invalid signature should fail verification."""
        # Create valid token
        token = jwt_utils.create_access_token({"sub": "test"})

        # Tamper with token (change last character)
        tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")

        payload = jwt_utils.verify_token(tampered_token, token_type="access")

        assert payload is None

    def test_verify_malformed_token(self):
        """Malformed token should fail verification gracefully."""
        malformed_tokens = [
            "not.a.token",
            "invalid",
            "",
            "a.b",  # Too few segments
            "a.b.c.d.e",  # Too many segments
        ]

        for bad_token in malformed_tokens:
            payload = jwt_utils.verify_token(bad_token, token_type="access")
            assert payload is None, f"Expected None for token: {bad_token}"

    def test_is_token_expired_valid_token(self):
        """Non-expired token should return False."""
        token = jwt_utils.create_access_token({"sub": "test"})
        assert jwt_utils.is_token_expired(token) is False

    def test_is_token_expired_expired_token(self):
        """Expired token should return True."""
        expired_delta = timedelta(seconds=-10)
        token = jwt_utils.create_access_token({"sub": "test"}, expires_delta=expired_delta)
        assert jwt_utils.is_token_expired(token) is True

    def test_is_token_expired_malformed_token(self):
        """Malformed token should be considered expired."""
        assert jwt_utils.is_token_expired("invalid") is True


class TestSecurityDependencies:
    """Test FastAPI security dependencies."""

    @pytest.mark.asyncio
    async def test_require_auth_with_valid_jwt(self):
        """require_auth should accept valid JWT token."""
        # Create valid JWT token
        token = jwt_utils.create_access_token({"sub": "test_user"})

        # Mock request and credentials
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Should not raise exception
        result = await require_auth(request, credentials)

        assert result == token
        assert hasattr(request.state, "user")
        assert request.state.user["sub"] == "test_user"

    @pytest.mark.asyncio
    async def test_require_auth_with_valid_legacy_token(self):
        """require_auth should accept valid legacy bearer token."""
        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "legacy-token-123"

            request = Mock(spec=Request)
            request.state = Mock()
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="legacy-token-123"
            )

            result = await require_auth(request, credentials)

            assert result == "legacy-token-123"
            assert request.state.user["type"] == "legacy"

    @pytest.mark.asyncio
    async def test_require_auth_with_expired_jwt(self):
        """require_auth should reject expired JWT token."""
        # Create expired token
        expired_delta = timedelta(seconds=-10)
        token = jwt_utils.create_access_token({"sub": "test"}, expires_delta=expired_delta)

        request = Mock(spec=Request)
        request.state = Mock()
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = None  # No legacy token fallback

            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request, credentials)

            assert exc_info.value.status_code == 401
            assert "Invalid or expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_auth_no_credentials(self):
        """require_auth should reject missing credentials."""
        request = Mock(spec=Request)

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "some-token"  # Legacy token configured

            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request, credentials=None)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_invalid_token(self):
        """require_auth should reject invalid token."""
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "different-token"

            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request, credentials)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_optional_auth_with_valid_jwt(self):
        """optional_auth should accept valid JWT token."""
        token = jwt_utils.create_access_token({"sub": "test_user"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await optional_auth(credentials)

        assert result == token

    @pytest.mark.asyncio
    async def test_optional_auth_with_invalid_token(self):
        """optional_auth should return None for invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        with patch("app.core.security._get_auth_token") as mock_auth:
            mock_auth.return_value = "different-token"

            result = await optional_auth(credentials)

            assert result is None

    @pytest.mark.asyncio
    async def test_optional_auth_no_credentials(self):
        """optional_auth should return None when no credentials provided."""
        result = await optional_auth(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_with_jwt(self):
        """get_current_user should return user from JWT token."""
        token = jwt_utils.create_access_token({"sub": "alice", "role": "trader"})

        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"sub": "alice", "role": "trader", "type": "access"}

        user = await get_current_user(request, token)

        assert user["sub"] == "alice"
        assert user["role"] == "trader"

    @pytest.mark.asyncio
    async def test_get_current_user_with_legacy(self):
        """get_current_user should return legacy user object."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"type": "legacy", "authenticated": True}

        user = await get_current_user(request, "legacy-token")

        assert user["type"] == "legacy"
        assert user["authenticated"] is True


class TestJWTUtilities:
    """Test JWT utility functions."""

    def test_generate_api_token(self):
        """generate_api_token should create secure random tokens."""
        token1 = jwt_utils.generate_api_token()
        token2 = jwt_utils.generate_api_token()

        # Tokens should be different
        assert token1 != token2

        # Tokens should be URL-safe strings
        assert isinstance(token1, str)
        assert len(token1) > 32  # URL-safe base64 encoding

    def test_decode_token_without_verification(self):
        """decode_token_without_verification should decode any valid JWT structure."""
        data = {"sub": "test", "custom": "value"}
        token = jwt_utils.create_access_token(data)

        payload = jwt_utils.decode_token_without_verification(token)

        assert payload["sub"] == "test"
        assert payload["custom"] == "value"

    def test_decode_invalid_token_without_verification(self):
        """decode_token_without_verification should return None for invalid tokens."""
        payload = jwt_utils.decode_token_without_verification("not-a-token")
        assert payload is None


class TestJWTSecretManagement:
    """Test JWT secret key initialization."""

    def test_jwt_secret_auto_generation(self):
        """JWT secret should be auto-generated if not configured."""
        # Reset initialization state
        jwt_utils._JWT_INITIALIZED = False
        jwt_utils._JWT_SECRET = None

        with patch.object(settings, "JWT_SECRET_KEY", ""):
            secret = jwt_utils._get_jwt_secret()

            assert secret is not None
            assert len(secret) > 32
            assert jwt_utils._JWT_INITIALIZED is True

    def test_jwt_secret_from_config(self):
        """JWT secret should use configured value if available."""
        jwt_utils._JWT_INITIALIZED = False
        jwt_utils._JWT_SECRET = None

        configured_secret = "my-custom-secret-key-12345"
        with patch.object(settings, "JWT_SECRET_KEY", configured_secret):
            secret = jwt_utils._get_jwt_secret()

            assert secret == configured_secret


class TestTokenEdgeCases:
    """Test edge cases and security scenarios."""

    def test_token_with_special_characters_in_payload(self):
        """Token should handle special characters in payload."""
        data = {
            "sub": "user@example.com",
            "name": "Test User 日本語",
            "special": "!@#$%^&*()",
        }
        token = jwt_utils.create_access_token(data)
        payload = jwt_utils.verify_token(token, token_type="access")

        assert payload["sub"] == "user@example.com"
        assert payload["name"] == "Test User 日本語"
        assert payload["special"] == "!@#$%^&*()"

    def test_token_with_empty_subject(self):
        """Token should handle empty subject."""
        data = {"sub": ""}
        token = jwt_utils.create_access_token(data)
        payload = jwt_utils.verify_token(token, token_type="access")

        assert payload["sub"] == ""

    def test_token_with_nested_data(self):
        """Token should handle nested data structures."""
        data = {
            "sub": "test",
            "metadata": {
                "role": "admin",
                "permissions": ["read", "write"],
            },
        }
        token = jwt_utils.create_access_token(data)
        payload = jwt_utils.verify_token(token, token_type="access")

        assert payload["metadata"]["role"] == "admin"
        assert payload["metadata"]["permissions"] == ["read", "write"]

    def test_very_long_payload(self):
        """Token should handle large payloads."""
        data = {
            "sub": "test",
            "data": "x" * 1000,  # 1KB of data
        }
        token = jwt_utils.create_access_token(data)
        payload = jwt_utils.verify_token(token, token_type="access")

        assert len(payload["data"]) == 1000

    def test_token_algorithm_consistency(self):
        """Tokens should use configured algorithm."""
        token = jwt_utils.create_access_token({"sub": "test"})

        # Decode header to check algorithm
        header = jwt.get_unverified_header(token)
        assert header["alg"] == settings.JWT_ALGORITHM
