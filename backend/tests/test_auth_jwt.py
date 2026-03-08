"""
Tests for JWT authentication system.

Covers:
- Token creation (access + refresh) and decoding
- Role-based access control (require_role dependency)
- backward-compatible require_auth (legacy token + JWT both accepted)
- Token issuance endpoint POST /api/v1/auth/token
- Token refresh endpoint POST /api/v1/auth/refresh
- GET /api/v1/auth/me identity endpoint
- WebSocket token verification (verify_ws_jwt / verify_ws_token)
- Error cases: expired tokens, wrong type, bad role, missing secret

NOTE: JWT_SECRET_KEY and API_AUTH_TOKEN are configured in conftest.py.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from httpx import AsyncClient, ASGITransport

from app.core import security
from app.core.config import settings
from app.core.security import (
    ROLE_ADMIN,
    ROLE_READONLY,
    ROLE_TRADER,
    TokenClaims,
    create_access_token,
    create_refresh_token,
    decode_jwt,
    verify_ws_jwt,
)
from app.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test_jwt_secret_key_32chars_xxxxx"
TEST_LEGACY_TOKEN = "test_auth_token_for_tests"

pytestmark = pytest.mark.anyio


def _make_raw_jwt(
    role: str = ROLE_TRADER,
    subject: str = "test-client",
    token_type: str = "access",
    secret: str = TEST_SECRET,
    algorithm: str = "HS256",
    exp_delta: timedelta = timedelta(minutes=30),
    issuer: str = "embodier-trader",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "jti": "test-jti",
        "iss": issuer,
        "iat": now,
        "exp": now + exp_delta,
        "type": token_type,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_LEGACY_TOKEN}"}


@pytest.fixture
def jwt_admin_token():
    return create_access_token(role=ROLE_ADMIN, subject="test-admin")


@pytest.fixture
def jwt_trader_token():
    return create_access_token(role=ROLE_TRADER, subject="test-trader")


@pytest.fixture
def jwt_readonly_token():
    return create_access_token(role=ROLE_READONLY, subject="test-readonly")


# ---------------------------------------------------------------------------
# Unit tests: token creation & decoding
# ---------------------------------------------------------------------------

class TestTokenCreation:
    def test_create_access_token_defaults(self):
        token = create_access_token()
        claims = decode_jwt(token, expected_type="access")
        assert claims.role == ROLE_TRADER
        assert claims.iss == settings.JWT_ISSUER

    def test_create_access_token_admin_role(self):
        token = create_access_token(role=ROLE_ADMIN)
        claims = decode_jwt(token, expected_type="access")
        assert claims.role == ROLE_ADMIN

    def test_create_access_token_readonly_role(self):
        token = create_access_token(role=ROLE_READONLY)
        claims = decode_jwt(token, expected_type="access")
        assert claims.role == ROLE_READONLY

    def test_create_refresh_token(self):
        token = create_refresh_token(role=ROLE_TRADER)
        claims = decode_jwt(token, expected_type="refresh")
        assert claims.role == ROLE_TRADER

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token(role=ROLE_TRADER)
        with pytest.raises(Exception):
            decode_jwt(token, expected_type="refresh")

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token(role=ROLE_TRADER)
        with pytest.raises(Exception):
            decode_jwt(token, expected_type="access")

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="Invalid role"):
            create_access_token(role="superuser")

    def test_expired_token_raises(self):
        expired = _make_raw_jwt(exp_delta=timedelta(seconds=-1))
        with pytest.raises(Exception):
            decode_jwt(expired)

    def test_wrong_secret_raises(self):
        token = jwt.encode(
            {
                "sub": "x", "role": ROLE_TRADER, "jti": "j", "iss": "embodier-trader",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
                "type": "access",
            },
            "wrong_secret",
            algorithm="HS256",
        )
        with pytest.raises(Exception):
            decode_jwt(token)

    def test_token_claims_fields(self):
        token = create_access_token(role=ROLE_ADMIN, subject="my-client")
        claims = decode_jwt(token)
        assert isinstance(claims, TokenClaims)
        assert claims.sub == "my-client"
        assert claims.role == ROLE_ADMIN
        assert claims.jti
        assert claims.iss == settings.JWT_ISSUER
        assert isinstance(claims.exp, datetime)
        assert claims.exp > datetime.now(timezone.utc)

    def test_no_jwt_secret_raises_runtime_error(self):
        with patch("app.core.security._get_jwt_secret", return_value=None):
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                create_access_token()


# ---------------------------------------------------------------------------
# Unit tests: verify_ws_jwt
# ---------------------------------------------------------------------------

class TestVerifyWsJwt:
    def test_valid_jwt_accepted(self):
        token = create_access_token(role=ROLE_TRADER)
        assert verify_ws_jwt(token) is True

    def test_legacy_token_accepted(self):
        assert verify_ws_jwt(TEST_LEGACY_TOKEN) is True

    def test_invalid_token_rejected(self):
        assert verify_ws_jwt("not.a.token") is False

    def test_none_rejected(self):
        assert verify_ws_jwt(None) is False

    def test_empty_string_rejected(self):
        assert verify_ws_jwt("") is False

    def test_expired_jwt_rejected(self):
        expired = _make_raw_jwt(exp_delta=timedelta(seconds=-1))
        assert verify_ws_jwt(expired) is False


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/auth/token
# ---------------------------------------------------------------------------

class TestAuthTokenEndpoint:
    async def test_issue_token_with_valid_secret(self, client):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"client_secret": TEST_LEGACY_TOKEN, "role": "trader"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "trader"
        assert data["expires_in"] > 0

    async def test_issue_token_wrong_secret(self, client):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"client_secret": "wrong_secret", "role": "trader"},
        )
        assert resp.status_code == 403

    async def test_issue_token_invalid_role(self, client):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"client_secret": TEST_LEGACY_TOKEN, "role": "superuser"},
        )
        assert resp.status_code == 422

    async def test_issue_token_all_roles(self, client):
        for role in (ROLE_READONLY, ROLE_TRADER, ROLE_ADMIN):
            resp = await client.post(
                "/api/v1/auth/token",
                json={"client_secret": TEST_LEGACY_TOKEN, "role": role},
            )
            assert resp.status_code == 200, f"Failed for role={role}: {resp.text}"
            assert resp.json()["role"] == role

    async def test_issued_access_token_is_valid_jwt(self, client):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"client_secret": TEST_LEGACY_TOKEN, "role": "admin"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        claims = decode_jwt(token, expected_type="access")
        assert claims.role == "admin"

    async def test_missing_jwt_secret_returns_501(self, client):
        with patch("app.api.v1.auth._get_jwt_secret", return_value=None):
            resp = await client.post(
                "/api/v1/auth/token",
                json={"client_secret": TEST_LEGACY_TOKEN, "role": "trader"},
            )
            assert resp.status_code == 501


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

class TestAuthRefreshEndpoint:
    async def test_refresh_with_valid_token(self, client):
        refresh_tok = create_refresh_token(role=ROLE_TRADER, subject="test-client")
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == ROLE_TRADER

    async def test_refresh_with_access_token_fails(self, client):
        access_tok = create_access_token(role=ROLE_TRADER)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_tok},
        )
        assert resp.status_code == 401

    async def test_refresh_with_expired_token_fails(self, client):
        expired = _make_raw_jwt(token_type="refresh", exp_delta=timedelta(seconds=-1))
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired},
        )
        assert resp.status_code == 401

    async def test_new_access_token_inherits_role(self, client):
        refresh_tok = create_refresh_token(role=ROLE_ADMIN)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert resp.status_code == 200
        claims = decode_jwt(resp.json()["access_token"], expected_type="access")
        assert claims.role == ROLE_ADMIN


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/auth/me
# ---------------------------------------------------------------------------

class TestAuthMeEndpoint:
    async def test_me_with_legacy_token(self, client, auth_headers):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == ROLE_ADMIN
        assert data["token_type"] == "legacy_bearer"

    async def test_me_with_jwt_token(self, client, jwt_trader_token):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == ROLE_TRADER
        assert data["token_type"] == "jwt"

    async def test_me_without_token_returns_401_or_403(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    async def test_me_with_invalid_token_returns_401_or_403(self, client):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Integration tests: require_auth backward compat
# ---------------------------------------------------------------------------

class TestRequireAuthBackwardCompat:
    async def test_legacy_token_accepted_on_protected_route(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/signals/",
            json={"symbol": "AAPL"},
            headers=auth_headers,
        )
        assert resp.status_code not in (401, 403)

    async def test_jwt_token_accepted_on_require_auth_route(self, client, jwt_trader_token):
        resp = await client.post(
            "/api/v1/signals/",
            json={"symbol": "AAPL"},
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code not in (401, 403)

    async def test_no_token_blocked(self, client):
        resp = await client.post("/api/v1/signals/", json={"symbol": "AAPL"})
        assert resp.status_code in (401, 403)

    async def test_wrong_token_blocked(self, client):
        resp = await client.post(
            "/api/v1/signals/",
            json={"symbol": "AAPL"},
            headers={"Authorization": "Bearer wrong_token"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Integration tests: require_role admin enforcement
# ---------------------------------------------------------------------------

class TestRequireRoleAdmin:
    async def test_legacy_token_counts_as_admin(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/orders/emergency-stop",
            headers=auth_headers,
        )
        assert resp.status_code not in (401, 403)

    async def test_admin_jwt_accepted(self, client, jwt_admin_token):
        resp = await client.post(
            "/api/v1/orders/emergency-stop",
            headers={"Authorization": f"Bearer {jwt_admin_token}"},
        )
        assert resp.status_code not in (401, 403)

    async def test_trader_jwt_rejected_on_admin_route(self, client, jwt_trader_token):
        resp = await client.post(
            "/api/v1/orders/emergency-stop",
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 403

    async def test_readonly_jwt_rejected_on_admin_route(self, client, jwt_readonly_token):
        resp = await client.post(
            "/api/v1/orders/emergency-stop",
            headers={"Authorization": f"Bearer {jwt_readonly_token}"},
        )
        assert resp.status_code == 403

    async def test_no_token_blocked_on_admin_route(self, client):
        resp = await client.post("/api/v1/orders/emergency-stop")
        assert resp.status_code in (401, 403)

    async def test_risk_shield_emergency_action_requires_admin(self, client, jwt_trader_token):
        resp = await client.post(
            "/api/v1/risk-shield/emergency-action",
            json={"action": "freeze_entries", "value": True},
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 403

    async def test_risk_shield_admin_jwt_accepted(self, client, jwt_admin_token):
        resp = await client.post(
            "/api/v1/risk-shield/emergency-action",
            json={"action": "freeze_entries", "value": True},
            headers={"Authorization": f"Bearer {jwt_admin_token}"},
        )
        assert resp.status_code not in (401, 403)

    async def test_settings_bulk_update_requires_admin(self, client, jwt_trader_token):
        resp = await client.put(
            "/api/v1/settings",
            json={"trading": {}},
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 403

    async def test_council_weights_reset_requires_admin(self, client, jwt_trader_token):
        resp = await client.post(
            "/api/v1/council/weights/reset",
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 403

    async def test_flatten_all_requires_admin(self, client, jwt_trader_token):
        resp = await client.post(
            "/api/v1/orders/flatten-all",
            headers={"Authorization": f"Bearer {jwt_trader_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# WebSocket auth (unit tests — verify_ws_token function, no real WS connection)
# ---------------------------------------------------------------------------

class TestWebSocketTokenVerification:
    def test_valid_jwt_accepted(self):
        token = create_access_token(role=ROLE_TRADER)
        from app.websocket_manager import verify_ws_token
        assert verify_ws_token(token) is True

    def test_legacy_token_accepted(self):
        from app.websocket_manager import verify_ws_token
        assert verify_ws_token(TEST_LEGACY_TOKEN) is True

    def test_invalid_token_rejected(self):
        from app.websocket_manager import verify_ws_token
        assert verify_ws_token("bad.token") is False

    def test_none_rejected_when_secrets_configured(self):
        from app.websocket_manager import verify_ws_token
        # API_AUTH_TOKEN is set in test env, so anonymous WS is blocked
        assert verify_ws_token(None) is False

    def test_expired_jwt_rejected(self):
        from app.websocket_manager import verify_ws_token
        expired = _make_raw_jwt(exp_delta=timedelta(seconds=-1))
        assert verify_ws_token(expired) is False
