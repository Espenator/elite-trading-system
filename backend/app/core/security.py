"""
API Authentication for Embodier Trader.

Supports both JWT tokens and legacy bearer tokens for backward compatibility.

SECURITY:
- Authentication is ALWAYS required on state-changing endpoints
- Paper vs live only changes the broker target URL, NOT auth enforcement
- JWT tokens are preferred (time-limited, can include user context)
- Legacy bearer tokens (API_AUTH_TOKEN) are still supported for backward compatibility

Usage in route files:
    from app.core.security import require_auth, get_current_user
    @router.post("/execute", dependencies=[Depends(require_auth)])

    # Or to get user context from JWT:
    @router.get("/profile")
    async def profile(user = Depends(get_current_user)):
        return {"user": user}
"""

import logging
import secrets
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.jwt_utils import verify_token

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


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Dependency that enforces API authentication on ALL protected endpoints.

    SECURITY: Auth is required in ALL modes (paper + live).
    Supports both JWT tokens and legacy bearer tokens.

    Priority:
    1. Try to verify as JWT token (preferred)
    2. Fall back to legacy bearer token comparison
    3. Block if neither is valid

    Returns:
        The validated token string
    """
    if credentials is None:
        # Try to get legacy token - if not configured, block everything
        legacy_token = _get_auth_token()
        if legacy_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Authentication required. "
                    "Set JWT_SECRET_KEY or API_AUTH_TOKEN in .env."
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token_str = credentials.credentials

    # Try JWT token first (preferred)
    jwt_payload = verify_token(token_str, token_type="access")
    if jwt_payload:
        # Valid JWT token - store user context in request state
        request.state.user = jwt_payload
        return token_str

    # Fall back to legacy bearer token
    legacy_token = _get_auth_token()
    if legacy_token and secrets.compare_digest(token_str, legacy_token):
        # Valid legacy token - mark as legacy user
        request.state.user = {"type": "legacy", "authenticated": True}
        return token_str

    # Neither JWT nor legacy token is valid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Soft auth check — logs warning if no token but doesn't block.
    Useful for read-only endpoints that benefit from auth but don't require it.
    Supports both JWT and legacy tokens.
    """
    if not credentials:
        return None

    token_str = credentials.credentials

    # Try JWT first
    jwt_payload = verify_token(token_str, token_type="access")
    if jwt_payload:
        return token_str

    # Try legacy token
    legacy_token = _get_auth_token()
    if legacy_token and secrets.compare_digest(token_str, legacy_token):
        return token_str

    return None


async def get_current_user(
    request: Request,
    _: str = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get the current authenticated user from the request.

    This dependency REQUIRES authentication and returns the user context.
    For JWT tokens, returns the full JWT payload.
    For legacy tokens, returns a minimal user object.

    Usage:
        @router.get("/profile")
        async def get_profile(user = Depends(get_current_user)):
            return {"username": user.get("sub"), ...}
    """
    # User context was set by require_auth
    return getattr(request.state, "user", {"type": "unknown"})


def generate_token() -> str:
    """Generate a secure random token for API_AUTH_TOKEN."""
    return secrets.token_urlsafe(32)
