"""JWT Authentication Endpoints for Live Trading.

Provides authentication endpoints for live trading mode:
- POST /api/v1/auth/login - Login with credentials and get JWT tokens
- POST /api/v1/auth/refresh - Refresh access token using refresh token
- GET /api/v1/auth/me - Get current user information
- GET /api/v1/auth/verify - Verify JWT token validity

In paper mode, these endpoints are available but JWT auth is optional.
In live mode, JWT authentication is required for all state-changing endpoints.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    _is_live_mode,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
_bearer_scheme = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Login request with username and password."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    trading_mode: Optional[str] = Field(None, description="Trading mode (live/paper)")


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="JWT refresh token")


class UserInfo(BaseModel):
    """User information response."""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    trading_mode: str = Field(..., description="Trading mode")
    permissions: list = Field(default_factory=list, description="User permissions")


class VerifyResponse(BaseModel):
    """Token verification response."""
    valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[str] = Field(None, description="User ID from token")
    expires_at: Optional[int] = Field(None, description="Token expiration timestamp")


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login and receive JWT tokens.

    In a production system, this would validate credentials against a user database.
    For now, this is a simplified implementation that accepts any credentials and
    generates tokens for demo/testing purposes.

    In live mode, the trading_mode in the token will be set to 'live'.
    In paper mode, it will be set to 'paper'.
    """
    # TODO: In production, validate username/password against user database
    # For now, accept any credentials for demo/testing

    # Determine trading mode from request or system settings
    trading_mode = request.trading_mode or settings.TRADING_MODE.lower()

    # Create user claims
    user_claims = {
        "user_id": f"user_{request.username}",
        "username": request.username,
        "trading_mode": trading_mode,
        "permissions": ["trade", "view_positions", "view_orders"],
    }

    # Generate tokens
    try:
        access_token = create_access_token(user_claims)
        refresh_token = create_refresh_token(user_claims)

        logger.info(f"User {request.username} logged in successfully (mode: {trading_mode})")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication tokens"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """Refresh access token using refresh token.

    Validates the refresh token and issues a new access token.
    The refresh token remains valid and can be used again.
    """
    try:
        # Decode and validate refresh token
        payload = decode_token(request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Refresh token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract user claims (exclude token-specific fields)
        user_claims = {
            k: v for k, v in payload.items()
            if k not in ["exp", "iat", "type"]
        }

        # Generate new access token
        access_token = create_access_token(user_claims)

        logger.info(f"Access token refreshed for user {payload.get('user_id')}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> UserInfo:
    """Get current user information from JWT token.

    Requires valid JWT token in Authorization header.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode and validate token
        payload = decode_token(credentials.credentials)

        # Verify it's an access token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Access token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserInfo(
            user_id=payload.get("user_id", ""),
            username=payload.get("username", ""),
            trading_mode=payload.get("trading_mode", "paper"),
            permissions=payload.get("permissions", []),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/verify", response_model=VerifyResponse)
async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> VerifyResponse:
    """Verify JWT token validity.

    Returns token validity status and expiration information.
    Does not require a valid token - returns valid=False if token is invalid.
    """
    if not credentials:
        return VerifyResponse(valid=False)

    try:
        # Decode and validate token
        payload = decode_token(credentials.credentials)

        return VerifyResponse(
            valid=True,
            user_id=payload.get("user_id"),
            expires_at=payload.get("exp"),
        )
    except HTTPException:
        # Token is invalid or expired
        return VerifyResponse(valid=False)
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return VerifyResponse(valid=False)
