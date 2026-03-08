"""
API Authentication for Embodier Trader.

Supports two authentication schemes (both may be used simultaneously):

1. Legacy Bearer Token (API_AUTH_TOKEN):
   Machine-to-machine shared secret.  Treated as role="admin" when valid.
   All existing callers continue to work unchanged.

2. JWT Bearer Token (JWT_SECRET_KEY):
   Signed JSON Web Tokens with role-based access control.
   Issued by POST /api/v1/auth/token (requires API_AUTH_TOKEN as credential).
   Roles: admin | trader | readonly

SECURITY PRINCIPLES (Audit Task 1 + Phase-2 JWT extension):
- Auth is ALWAYS required on state-changing endpoints (paper AND live).
- Paper vs live only changes the broker target URL, not auth enforcement.
- If API_AUTH_TOKEN is not set, ALL state-changing requests are BLOCKED (fail-closed).
- JWT_SECRET_KEY must be set to enable JWT issuance in production.
- No secrets are hardcoded; all come from environment / .env.

Usage in route files:
    from app.core.security import require_auth, require_role

    # Backward-compatible (legacy token or any valid JWT):
    @router.post("/execute", dependencies=[Depends(require_auth)])

    # Role-gated (legacy token treated as admin, or JWT with matching role):
    @router.post("/emergency-stop", dependencies=[Depends(require_role("admin"))])
    @router.post("/order", dependencies=[Depends(require_role("trader"))])
"""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import jwt as _jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared bearer scheme — auto_error=False so we control error messages
# ---------------------------------------------------------------------------
_bearer_scheme = HTTPBearer(auto_error=False)

# Valid roles (ordered least → most privileged)
ROLE_READONLY = "readonly"
ROLE_TRADER = "trader"
ROLE_ADMIN = "admin"

_ROLE_RANK: dict[str, int] = {
    ROLE_READONLY: 0,
    ROLE_TRADER: 1,
    ROLE_ADMIN: 2,
}

# ---------------------------------------------------------------------------
# Legacy bearer token (lazy-loaded from settings once)
# ---------------------------------------------------------------------------
_AUTH_TOKEN: Optional[str] = None
_AUTH_INITIALIZED = False


def _get_auth_token() -> Optional[str]:
    """Lazy-load the legacy API_AUTH_TOKEN from settings."""
    global _AUTH_TOKEN, _AUTH_INITIALIZED
    if not _AUTH_INITIALIZED:
        _AUTH_TOKEN = (settings.API_AUTH_TOKEN or "").strip() or None
        _AUTH_INITIALIZED = True
        if _AUTH_TOKEN:
            logger.info("API authentication enabled (legacy token configured)")
        else:
            logger.warning(
                "API_AUTH_TOKEN not set — ALL state-changing endpoints are BLOCKED. "
                "Set API_AUTH_TOKEN in .env to enable the system."
            )
    return _AUTH_TOKEN


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
@dataclass
class TokenClaims:
    """Decoded, validated claims from a JWT bearer token."""
    sub: str
    role: str
    jti: str
    iss: str
    iat: datetime
    exp: datetime


def _get_jwt_secret() -> Optional[str]:
    """Return the JWT signing secret from settings (None if not configured)."""
    return (settings.JWT_SECRET_KEY or "").strip() or None


def create_access_token(role: str = ROLE_TRADER, subject: str = "embodier-trader-client") -> str:
    """Create a signed JWT access token.

    Args:
        role: One of "readonly", "trader", "admin".
        subject: Identifier for the requesting client (informational).

    Returns:
        Signed JWT string.

    Raises:
        RuntimeError: If JWT_SECRET_KEY is not configured.
    """
    secret = _get_jwt_secret()
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. "
            "Set JWT_SECRET_KEY in .env to enable JWT issuance."
        )
    if role not in _ROLE_RANK:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {list(_ROLE_RANK)}")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return _jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(role: str = ROLE_TRADER, subject: str = "embodier-trader-client") -> str:
    """Create a longer-lived JWT refresh token.

    The refresh token carries the same role as the original access token and is
    used exclusively at POST /api/v1/auth/refresh to obtain a new access token.
    It MUST NOT be accepted as a general-purpose auth token.
    """
    secret = _get_jwt_secret()
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. "
            "Set JWT_SECRET_KEY in .env to enable JWT issuance."
        )
    if role not in _ROLE_RANK:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {list(_ROLE_RANK)}")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    return _jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str, expected_type: str = "access") -> TokenClaims:
    """Decode and validate a JWT bearer token.

    Args:
        token: Raw JWT string (without "Bearer " prefix).
        expected_type: Token type claim that must match ("access" or "refresh").

    Returns:
        TokenClaims with validated fields.

    Raises:
        HTTPException 401: If the token is invalid, expired, or has wrong type/issuer.
    """
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT authentication is not configured on this server.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["sub", "role", "jti", "iss", "iat", "exp", "type"]},
        )
    except _jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except _jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Wrong token type (expected '{expected_type}').",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role", "")
    if role not in _ROLE_RANK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown role '{role}' in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenClaims(
        sub=payload["sub"],
        role=role,
        jti=payload["jti"],
        iss=payload["iss"],
        iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


def verify_ws_jwt(token: Optional[str]) -> bool:
    """Verify a JWT or legacy token for WebSocket connections.

    Returns True if the token is valid (either JWT access token or legacy bearer).
    Returns False for any invalid or missing token.
    """
    if not token:
        return False

    # Try JWT first
    secret = _get_jwt_secret()
    if secret:
        try:
            decode_jwt(token, expected_type="access")
            return True
        except HTTPException:
            pass  # Fall through to legacy check

    # Fall back to legacy bearer token comparison
    legacy = _get_auth_token()
    if legacy and secrets.compare_digest(token, legacy):
        return True

    return False


# ---------------------------------------------------------------------------
# FastAPI dependency functions
# ---------------------------------------------------------------------------

def _is_live_mode() -> bool:
    """Use settings singleton as single source of truth (Audit Task 9 fix)."""
    return settings.TRADING_MODE.lower() == "live"


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Backward-compatible auth dependency.

    Accepts EITHER a valid legacy API_AUTH_TOKEN bearer string OR a valid JWT
    access token (any role).  Existing callers that already pass the legacy
    token continue to work without any changes.

    Fail-closed: if API_AUTH_TOKEN is not set, all requests are blocked.
    """
    legacy_token = _get_auth_token()

    if legacy_token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "API_AUTH_TOKEN must be configured. "
                "Set API_AUTH_TOKEN in .env to enable state-changing endpoints."
            ),
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw = credentials.credentials

    # 1. Check legacy bearer token (constant-time comparison)
    if secrets.compare_digest(raw, legacy_token):
        return raw

    # 2. Try JWT (any valid role accepted)
    secret = _get_jwt_secret()
    if secret:
        try:
            decode_jwt(raw, expected_type="access")
            return raw
        except HTTPException:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: str) -> Callable:
    """Dependency factory: require a minimum JWT role (or legacy admin token).

    The legacy API_AUTH_TOKEN is always treated as role="admin", so existing
    machine-to-machine callers using the legacy token retain full access.

    Usage:
        @router.post("/emergency-stop", dependencies=[Depends(require_role("admin"))])
        @router.post("/order", dependencies=[Depends(require_role("trader"))])

    Role hierarchy (least → most privileged):
        readonly < trader < admin
    """
    if required_role not in _ROLE_RANK:
        raise ValueError(f"Invalid required_role '{required_role}'. Must be one of: {list(_ROLE_RANK)}")

    async def _check(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    ) -> TokenClaims:
        legacy_token = _get_auth_token()

        if legacy_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "API_AUTH_TOKEN must be configured. "
                    "Set API_AUTH_TOKEN in .env to enable state-changing endpoints."
                ),
            )

        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        raw = credentials.credentials

        # Legacy token → treat as admin (full backward compatibility)
        if secrets.compare_digest(raw, legacy_token):
            now = datetime.now(timezone.utc)
            return TokenClaims(
                sub="legacy-api-token",
                role=ROLE_ADMIN,
                jti="legacy",
                iss=settings.JWT_ISSUER,
                iat=now,
                exp=now + timedelta(hours=1),
            )

        # JWT path
        secret = _get_jwt_secret()
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT authentication is not configured on this server.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        claims = decode_jwt(raw, expected_type="access")

        if _ROLE_RANK.get(claims.role, -1) < _ROLE_RANK[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. Required role: '{required_role}', "
                    f"token role: '{claims.role}'."
                ),
            )

        return claims

    # Give the inner function a unique name per role so FastAPI's dependency
    # cache correctly distinguishes require_role("admin") from require_role("trader").
    _check.__name__ = f"require_role_{required_role}"
    return _check


# Convenience pre-built dependencies
require_trader = require_role(ROLE_TRADER)
require_admin = require_role(ROLE_ADMIN)


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Soft auth check — does not block; returns the raw token if valid.

    Useful for read-only endpoints that benefit from auth but don't require it.
    Accepts both legacy bearer token and JWT access tokens.
    """
    if credentials is None:
        return None
    raw = credentials.credentials
    legacy = _get_auth_token()
    if legacy and secrets.compare_digest(raw, legacy):
        return raw
    if _get_jwt_secret():
        try:
            decode_jwt(raw, expected_type="access")
            return raw
        except HTTPException:
            pass
    return None


def generate_token() -> str:
    """Generate a secure random token for API_AUTH_TOKEN."""
    return secrets.token_urlsafe(32)
