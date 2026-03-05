"""
API Authentication for Elite Trading System.

Uses a shared API key for machine-to-machine auth between
ESPENMAIN / Profit Trader PCs and the backend.

- All state-changing endpoints (POST/PUT/DELETE) require auth
- Read-only GET endpoints for market data are open
- In development mode (TRADING_MODE != "live"), auth is optional
- Set API_AUTH_TOKEN in .env to enable authentication

Usage in route files:
    from app.core.security import require_auth
    @router.post("/execute", dependencies=[Depends(require_auth)])
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Bearer token scheme (auto_error=False so we can handle missing tokens ourselves)
_bearer_scheme = HTTPBearer(auto_error=False)

# Auth token loaded from environment
_AUTH_TOKEN: Optional[str] = None
_AUTH_INITIALIZED = False


def _get_auth_token() -> Optional[str]:
    """Lazy-load the auth token from environment."""
    global _AUTH_TOKEN, _AUTH_INITIALIZED
    if not _AUTH_INITIALIZED:
        _AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "").strip() or None
        _AUTH_INITIALIZED = True
        if _AUTH_TOKEN:
            logger.info("API authentication enabled (token configured)")
        else:
            logger.warning(
                "API_AUTH_TOKEN not set. Auth is DISABLED in paper mode, "
                "BLOCKED in live mode. Set API_AUTH_TOKEN in .env for security."
            )
    return _AUTH_TOKEN


def _is_live_mode() -> bool:
    return os.getenv("TRADING_MODE", "live") == "live"


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Dependency that enforces API authentication on protected endpoints.

    - If API_AUTH_TOKEN is set: requires valid Bearer token
    - If API_AUTH_TOKEN is NOT set and TRADING_MODE=live: blocks all requests
    - If API_AUTH_TOKEN is NOT set and TRADING_MODE!=live: allows (dev mode)
    """
    token = _get_auth_token()

    if token is None:
        # No token configured
        if _is_live_mode():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API_AUTH_TOKEN must be configured for live trading mode",
            )
        # Dev/paper mode - allow without auth
        return None

    # Token is configured - require valid Bearer auth
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
    """Soft auth check - logs warning if no token but doesn't block.
    Useful for read-only endpoints that benefit from auth but don't require it.
    """
    token = _get_auth_token()
    if token and credentials and secrets.compare_digest(credentials.credentials, token):
        return credentials.credentials
    return None


def generate_token() -> str:
    """Generate a secure random token for API_AUTH_TOKEN."""
    return secrets.token_urlsafe(32)
