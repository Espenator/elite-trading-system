"""
API Authentication for Embodier Trader.

Uses a shared API key for machine-to-machine auth between
ESPENMAIN / Profit Trader PCs and the backend.

SECURITY FIX (Audit Task 1):
- Authentication is ALWAYS required on state-changing endpoints
- Paper vs live only changes the broker target URL, NOT auth enforcement
- If API_AUTH_TOKEN is not set, ALL state-changing requests are blocked
- Set API_AUTH_TOKEN in .env to enable the system

JWT Authentication for Live Trading:
- JWT tokens are required for live trading endpoints when TRADING_MODE=live
- JWT tokens contain user claims (user_id, exp, trading_mode)
- Tokens are signed with JWT_SECRET_KEY and verified on each request
- Access tokens expire after JWT_ACCESS_TOKEN_EXPIRE_MINUTES (default: 60)
- Refresh tokens expire after JWT_REFRESH_TOKEN_EXPIRE_DAYS (default: 7)

Usage in route files:
    from app.core.security import require_auth, require_jwt_auth

    # Simple bearer token auth (paper + live)
    @router.post("/execute", dependencies=[Depends(require_auth)])

    # JWT auth (only required in live mode)
    @router.post("/live-order", dependencies=[Depends(require_jwt_auth)])
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bearer token scheme (auto_error=False so we can handle missing tokens ourselves)
_bearer_scheme = HTTPBearer(auto_error=False)

# Auth token loaded from settings (single source of truth)
_AUTH_TOKEN: Optional[str] = None
_AUTH_INITIALIZED = False
_JWT_SECRET: Optional[str] = None
_JWT_INITIALIZED = False


def _get_auth_token() -> Optional[str]:
    """Lazy-load the auth token from settings (single source of truth)."""
    global _AUTH_TOKEN, _AUTH_INITIALIZED
    if not _AUTH_INITIALIZED:
        _AUTH_TOKEN = (settings.API_AUTH_TOKEN or "").strip() or None
        _AUTH_INITIALIZED = True
        if _AUTH_TOKEN:
            logger.info("API authentication enabled (token configured)")
        else:
            logger.warning(
                "API_AUTH_TOKEN not set — ALL state-changing endpoints are BLOCKED. "
                "Set API_AUTH_TOKEN in .env to enable the system."
            )
    return _AUTH_TOKEN


def _is_live_mode() -> bool:
    """Use settings singleton as single source of truth (Audit Task 9 fix)."""
    return settings.TRADING_MODE.lower() == "live"


def _get_jwt_secret() -> Optional[str]:
    """Lazy-load JWT secret key from settings."""
    global _JWT_SECRET, _JWT_INITIALIZED
    if not _JWT_INITIALIZED:
        _JWT_SECRET = (settings.JWT_SECRET_KEY or "").strip() or None
        _JWT_INITIALIZED = True
        if _JWT_SECRET:
            logger.info("JWT authentication enabled (secret configured)")
        else:
            logger.debug("JWT_SECRET_KEY not set — JWT auth will be unavailable in live mode")
    return _JWT_SECRET


# ─────────────────────────────────────────────────────────────────────────────
# JWT Token Generation and Validation
# ─────────────────────────────────────────────────────────────────────────────


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional expiration time delta (defaults to settings value)

    Returns:
        Encoded JWT token string

    Raises:
        HTTPException: If JWT_SECRET_KEY is not configured
    """
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY must be configured for JWT authentication"
        )

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token.

    Args:
        data: Dictionary of claims to encode in the token

    Returns:
        Encoded JWT refresh token string

    Raises:
        HTTPException: If JWT_SECRET_KEY is not configured
    """
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY must be configured for JWT authentication"
        )

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary of decoded token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY must be configured for JWT authentication"
        )

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_jwt_secret() -> str:
    """Generate a secure random secret for JWT signing."""
    return secrets.token_urlsafe(64)


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Dependencies
# ─────────────────────────────────────────────────────────────────────────────


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Dependency that enforces API authentication on ALL protected endpoints.

    SECURITY: Auth is required in ALL modes (paper + live).
    Paper vs live only changes the broker target URL, not auth enforcement.

    - If API_AUTH_TOKEN is set: requires valid Bearer token
    - If API_AUTH_TOKEN is NOT set: blocks ALL requests (fail-closed)
    """
    token = _get_auth_token()

    if token is None:
        # No token configured — block everything (fail-closed)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "API_AUTH_TOKEN must be configured. "
                "Set API_AUTH_TOKEN in .env to enable state-changing endpoints."
            ),
        )

    # Token is configured — require valid Bearer auth
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def require_jwt_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """Dependency that enforces JWT authentication on live trading endpoints.

    In live mode: Requires valid JWT token
    In paper mode: Falls back to simple Bearer token auth (for backward compatibility)

    Returns:
        Dict containing decoded JWT claims (user_id, trading_mode, etc.)
    """
    if not _is_live_mode():
        # Paper mode: use simple bearer token auth for backward compatibility
        await require_auth(request, credentials)
        return {"trading_mode": "paper", "auth_type": "bearer"}

    # Live mode: require JWT authentication
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "JWT_SECRET_KEY must be configured for live trading. "
                "Set JWT_SECRET_KEY in .env to enable live trading endpoints."
            ),
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token required for live trading",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate JWT token
    try:
        payload = decode_token(credentials.credentials)

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Access token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate trading mode in token matches current mode
        token_trading_mode = payload.get("trading_mode", "").lower()
        if token_trading_mode and token_trading_mode != "live":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token is for {token_trading_mode} mode, but system is in live mode",
            )

        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Soft auth check — logs warning if no token but doesn't block.
    Useful for read-only endpoints that benefit from auth but don't require it.
    """
    token = _get_auth_token()
    if token and credentials and secrets.compare_digest(credentials.credentials, token):
        return credentials.credentials
    return None


def generate_token() -> str:
    """Generate a secure random token for API_AUTH_TOKEN."""
    return secrets.token_urlsafe(32)

