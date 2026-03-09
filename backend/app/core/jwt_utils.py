"""
JWT Token Management for Embodier Trader.

Provides JWT token generation, validation, and refresh functionality.
Supports both JWT tokens and legacy bearer tokens for backward compatibility.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Auto-generate JWT secret if not configured
_JWT_SECRET: Optional[str] = None
_JWT_INITIALIZED = False


def _get_jwt_secret() -> str:
    """Get or generate JWT secret key."""
    global _JWT_SECRET, _JWT_INITIALIZED

    if not _JWT_INITIALIZED:
        if settings.JWT_SECRET_KEY:
            _JWT_SECRET = settings.JWT_SECRET_KEY
            logger.info("JWT authentication enabled (secret key configured)")
        else:
            # Auto-generate a secure secret for development
            _JWT_SECRET = secrets.token_urlsafe(32)
            logger.warning(
                "JWT_SECRET_KEY not set — auto-generated temporary key. "
                "Set JWT_SECRET_KEY in .env for production use."
            )
        _JWT_INITIALIZED = True

    return _JWT_SECRET


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        _get_jwt_secret(),
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        _get_jwt_secret(),
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging/inspection only).

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload (unverified)
    """
    try:
        return jwt.decode(
            token,
            options={"verify_signature": False}
        )
    except Exception as e:
        logger.debug(f"Failed to decode token: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired without full validation.

    Args:
        token: JWT token string

    Returns:
        True if expired, False otherwise
    """
    payload = decode_token_without_verification(token)
    if not payload:
        return True

    exp = payload.get("exp")
    if not exp:
        return True

    return datetime.now(timezone.utc).timestamp() > exp


def generate_api_token() -> str:
    """Generate a secure random API token (for legacy bearer auth)."""
    return secrets.token_urlsafe(32)
