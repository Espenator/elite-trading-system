"""
Authentication endpoints for Embodier Trader.

Provides JWT token generation and refresh endpoints.
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request/Response Models ──


class LoginRequest(BaseModel):
    """Login request with API key."""

    api_key: str = Field(..., description="API key for authentication")
    username: Optional[str] = Field(None, description="Optional username for JWT payload")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


# ── Endpoints ──


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Generate JWT tokens using API key authentication.

    This endpoint allows clients to exchange their API key for JWT tokens.
    The API key is validated against API_AUTH_TOKEN from settings.

    Returns:
        - access_token: Short-lived token for API requests (30 min default)
        - refresh_token: Long-lived token for getting new access tokens (7 days default)
    """
    # Validate API key
    if not settings.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set API_AUTH_TOKEN in .env.",
        )

    if request.api_key != settings.API_AUTH_TOKEN:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Create JWT tokens
    token_data = {
        "sub": request.username or "api_user",
        "type_": "api",
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(f"JWT tokens generated for user: {token_data['sub']}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using a refresh token.

    Validates the refresh token and generates a new access token.
    The refresh token itself is NOT rotated (remains valid).

    Returns:
        New access token with the same expiration time as the original.
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Create new access token with the same user data
    token_data = {
        "sub": payload.get("sub", "api_user"),
        "type_": payload.get("type_", "api"),
    }

    access_token = create_access_token(token_data)

    logger.info(f"Access token refreshed for user: {token_data['sub']}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.

    This endpoint can be used to verify token validity and inspect user context.
    Works with both JWT tokens and legacy bearer tokens.

    Returns:
        User information from the token payload.
    """
    return {
        "user": user,
        "authenticated": True,
    }


@router.get("/verify")
async def verify_token_endpoint(user: dict = Depends(get_current_user)):
    """
    Verify token validity.

    Simple endpoint to check if the provided token is valid.
    Returns 200 OK if valid, 401 Unauthorized if invalid.
    """
    return {
        "valid": True,
        "user_type": user.get("type", "jwt"),
    }
