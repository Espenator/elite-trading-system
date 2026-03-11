"""
API Authentication for Embodier Trader.

Uses a shared API key for machine-to-machine auth between
ESPENMAIN / Profit Trader PCs and the backend.

SECURITY FIX (Audit Task 1):
- Authentication is ALWAYS required on state-changing endpoints
- Paper vs live only changes the broker target URL, NOT auth enforcement
- If API_AUTH_TOKEN is not set, ALL state-changing requests are blocked
- Set API_AUTH_TOKEN in .env to enable the system

Usage in route files:
    from app.core.security import require_auth
    @router.post("/execute", dependencies=[Depends(require_auth)])
"""

import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bearer token scheme (auto_error=False so we can handle missing tokens ourselves)
_bearer_scheme = HTTPBearer(auto_error=False)

# Auth token loaded from settings (single source of truth)
_AUTH_TOKEN: Optional[str] = None
_AUTH_INITIALIZED = False


def reset_auth_cache():
    """Reset the auth token cache. Useful for tests that set API_AUTH_TOKEN dynamically."""
    global _AUTH_TOKEN, _AUTH_INITIALIZED
    _AUTH_TOKEN = None
    _AUTH_INITIALIZED = False


def _get_auth_token() -> Optional[str]:
    """Lazy-load the auth token. Env var overrides settings (supports test injection)."""
    global _AUTH_TOKEN, _AUTH_INITIALIZED
    if not _AUTH_INITIALIZED:
        import os
        env_token = os.environ.get("API_AUTH_TOKEN", "").strip()
        _AUTH_TOKEN = env_token or (settings.API_AUTH_TOKEN or "").strip() or None
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
