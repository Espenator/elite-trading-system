"""
API Authentication for Embodier Trader.

ENHANCED JWT-based authentication with scope-based authorization.
Backward compatible with legacy API_AUTH_TOKEN for existing deployments.

SECURITY FIX (Audit Task 1):
- Authentication is ALWAYS required on state-changing endpoints
- Paper vs live only changes the broker target URL, NOT auth enforcement
- If API_AUTH_TOKEN is not set, ALL state-changing requests are blocked
- Set API_AUTH_TOKEN in .env to enable the system

JWT AUTHENTICATION:
- Lightweight JWT-based authentication using PyJWT
- Supports scopes for fine-grained access control
- Trading-only scope for /api/v1/orders and /api/v1/risk_shield endpoints
- Access tokens expire after configurable time (default: 60 minutes)

Usage in route files:
    from app.core.security import require_auth, require_trading_scope

    # Basic authentication (legacy and JWT)
    @router.post("/execute", dependencies=[Depends(require_auth)])

    # Trading-only scope required
    @router.post("/orders/advanced", dependencies=[Depends(require_trading_scope)])
"""

import logging
import secrets
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("PyJWT not installed. JWT authentication disabled. Install with: pip install PyJWT")

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bearer token scheme (auto_error=False so we can handle missing tokens ourselves)
_bearer_scheme = HTTPBearer(auto_error=False)

# Auth token loaded from settings (single source of truth)
_AUTH_TOKEN: Optional[str] = None
_AUTH_INITIALIZED = False


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


# ── JWT Token Management ─────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with the given data and optional expiration.

    Args:
        data: Dictionary containing token claims (e.g., {"sub": "user_id", "scopes": ["trading"]})
        expires_delta: Optional expiration time delta. Defaults to JWT_ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        Encoded JWT token string

    Raises:
        RuntimeError: If PyJWT is not installed or JWT_SECRET_KEY is not configured
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT not installed. Install with: pip install PyJWT")

    if not settings.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY not configured in settings")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload as dictionary, or None if invalid/expired
    """
    if not JWT_AVAILABLE:
        logger.warning("PyJWT not installed, cannot decode JWT token")
        return None

    if not settings.JWT_SECRET_KEY:
        logger.warning("JWT_SECRET_KEY not configured, cannot decode JWT token")
        return None

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token: %s", e)
        return None


def verify_token_scopes(token_payload: dict, required_scopes: List[str]) -> bool:
    """Verify that a token has all required scopes.

    Args:
        token_payload: Decoded JWT token payload
        required_scopes: List of required scope strings

    Returns:
        True if token has all required scopes, False otherwise
    """
    token_scopes = token_payload.get("scopes", [])
    return all(scope in token_scopes for scope in required_scopes)


# ── Authentication Dependencies ───────────────────────────────────────────────

async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Dependency that enforces API authentication on ALL protected endpoints.

    SECURITY: Auth is required in ALL modes (paper + live).
    Paper vs live only changes the broker target URL, not auth enforcement.

    Supports both:
    1. Legacy API_AUTH_TOKEN (simple bearer token)
    2. JWT tokens with scopes (if JWT_SECRET_KEY is configured)

    - If API_AUTH_TOKEN is set: requires valid Bearer token OR valid JWT
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

    # Try JWT validation first (if configured)
    if JWT_AVAILABLE and settings.JWT_SECRET_KEY:
        jwt_payload = decode_jwt_token(credentials.credentials)
        if jwt_payload:
            # Valid JWT token - store in request state for scope checking
            request.state.jwt_payload = jwt_payload
            return credentials.credentials

    # Fall back to legacy API_AUTH_TOKEN validation
    if not secrets.compare_digest(credentials.credentials, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def require_trading_scope(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Dependency that enforces 'trading' scope for Alpaca execution endpoints.

    Only requests with the 'trading' scope can hit /api/v1/orders or /api/v1/risk_shield.

    This provides an extra layer of security for the most critical endpoints.
    Legacy API_AUTH_TOKEN grants trading scope implicitly for backward compatibility.
    """
    # First, verify basic authentication
    await require_auth(request, credentials)

    # If using JWT, verify 'trading' scope
    jwt_payload = getattr(request.state, "jwt_payload", None)
    if jwt_payload:
        if not verify_token_scopes(jwt_payload, ["trading"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trading scope required. This token does not have permission to execute trades.",
            )

    # Legacy API_AUTH_TOKEN grants trading scope implicitly
    return credentials.credentials


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Soft auth check — logs warning if no token but doesn't block.
    Useful for read-only endpoints that benefit from auth but don't require it.
    """
    token = _get_auth_token()
    if token and credentials and secrets.compare_digest(credentials.credentials, token):
        return credentials.credentials

    # Also try JWT validation
    if JWT_AVAILABLE and settings.JWT_SECRET_KEY and credentials:
        jwt_payload = decode_jwt_token(credentials.credentials)
        if jwt_payload:
            return credentials.credentials

    return None


def generate_token() -> str:
    """Generate a secure random token for API_AUTH_TOKEN."""
    return secrets.token_urlsafe(32)


# ── Order Signature for MITM Protection ──────────────────────────────────────

def generate_order_signature(order_data: dict) -> str:
    """Generate HMAC signature for an order to prevent MITM attacks.

    This signature is added as X-Signature header on all outgoing orders to Alpaca.

    Args:
        order_data: Order payload dictionary (must be JSON-serializable)

    Returns:
        Hex-encoded HMAC-SHA256 signature

    Raises:
        RuntimeError: If ALPACA_SIGNATURE_SECRET is not configured
    """
    if not settings.ALPACA_SIGNATURE_SECRET:
        raise RuntimeError(
            "ALPACA_SIGNATURE_SECRET not configured. "
            "Set ALPACA_SIGNATURE_SECRET in .env to enable order signature verification."
        )

    # Create canonical representation of order data (sorted keys for consistency)
    canonical = json.dumps(order_data, sort_keys=True, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        settings.ALPACA_SIGNATURE_SECRET.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_order_signature(order_data: dict, signature: str) -> bool:
    """Verify an order signature to detect tampering.

    Args:
        order_data: Order payload dictionary
        signature: Hex-encoded signature to verify

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.ALPACA_SIGNATURE_SECRET:
        logger.warning("ALPACA_SIGNATURE_SECRET not configured, cannot verify signature")
        return False

    try:
        expected_signature = generate_order_signature(order_data)
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error("Error verifying order signature: %s", e)
        return False

