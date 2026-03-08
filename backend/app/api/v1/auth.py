"""
auth.py — JWT Token Issuance and Refresh Endpoints

POST /api/v1/auth/token
    Exchange the legacy API_AUTH_TOKEN (or client_secret) for a JWT
    access + refresh token pair.  Supports role selection so that
    operators can issue scoped tokens (readonly, trader, admin).

POST /api/v1/auth/refresh
    Exchange a valid refresh token for a new access token.
    The new access token inherits the role from the refresh token.

GET /api/v1/auth/me
    Inspect the claims of the current bearer token (JWT or legacy).
    Useful for debugging and confirming which role is in effect.

Security design:
- Token issuance requires a valid API_AUTH_TOKEN (shared secret) as the
  client_secret field.  This keeps the issuance gate behind the existing
  machine-to-machine credential.
- JWT_SECRET_KEY must be configured to enable this endpoint.  If it is
  absent, token issuance returns 501 Not Implemented.
- No weak dev shortcuts: same validation rules apply in paper and live.
- Refresh tokens are single-use by convention (clients should discard the
  old one after obtaining a new access token).  Server-side revocation is
  out of scope for Phase 1 (single-instance deployment has no shared store).
"""

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    ROLE_ADMIN,
    ROLE_READONLY,
    ROLE_TRADER,
    TokenClaims,
    _bearer_scheme,
    _get_auth_token,
    _get_jwt_secret,
    create_access_token,
    create_refresh_token,
    decode_jwt,
    require_auth,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class TokenRequest(BaseModel):
    """Credentials required to obtain a JWT token pair."""

    client_secret: str = Field(
        ...,
        description="The shared API_AUTH_TOKEN value from the server's .env file.",
    )
    role: str = Field(
        default=ROLE_TRADER,
        description=(
            "Requested role for the issued token. "
            f"One of: {ROLE_READONLY!r}, {ROLE_TRADER!r}, {ROLE_ADMIN!r}."
        ),
    )
    subject: str = Field(
        default="embodier-trader-client",
        description="Arbitrary identifier for the requesting client (for audit logs).",
        max_length=128,
    )


class TokenResponse(BaseModel):
    """JWT token pair returned on successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds.")
    role: str
    subject: str


class RefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str = Field(..., description="A valid JWT refresh token.")


class MeResponse(BaseModel):
    """Current caller's identity and active role."""

    sub: str
    role: str
    jti: str
    iss: str
    token_type: str
    expires_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ROLES = {ROLE_READONLY, ROLE_TRADER, ROLE_ADMIN}


def _require_jwt_configured() -> None:
    """Raise 501 if JWT_SECRET_KEY is not set."""
    if not _get_jwt_secret():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "JWT authentication is not configured on this server. "
                "Set JWT_SECRET_KEY in .env to enable token issuance."
            ),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Issue a JWT access + refresh token pair",
    description=(
        "Exchange the shared API_AUTH_TOKEN for a scoped JWT token pair. "
        "The legacy bearer token continues to work on all protected endpoints; "
        "this endpoint enables finer-grained role-based access control."
    ),
)
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Issue a JWT access + refresh token pair.

    Validates the client_secret against API_AUTH_TOKEN using constant-time
    comparison to prevent timing attacks.  Returns 403 if the secret is wrong.
    """
    _require_jwt_configured()

    legacy_token = _get_auth_token()
    if not legacy_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "API_AUTH_TOKEN must be configured on the server before "
                "JWT tokens can be issued."
            ),
        )

    if not secrets.compare_digest(body.client_secret, legacy_token):
        logger.warning("Token issuance rejected: invalid client_secret from subject=%s", body.subject)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid client_secret.",
        )

    if body.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid role '{body.role}'. "
                f"Must be one of: {sorted(_VALID_ROLES)}."
            ),
        )

    access = create_access_token(role=body.role, subject=body.subject)
    refresh = create_refresh_token(role=body.role, subject=body.subject)

    logger.info("JWT token issued: subject=%s role=%s", body.subject, body.role)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=body.role,
        subject=body.subject,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
    description=(
        "Exchange a valid (non-expired) refresh token for a new access token. "
        "The new access token inherits the role from the refresh token."
    ),
)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Obtain a new access token using a refresh token."""
    _require_jwt_configured()

    claims = decode_jwt(body.refresh_token, expected_type="refresh")

    access = create_access_token(role=claims.role, subject=claims.sub)
    new_refresh = create_refresh_token(role=claims.role, subject=claims.sub)

    logger.info("JWT token refreshed: subject=%s role=%s", claims.sub, claims.role)

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=claims.role,
        subject=claims.sub,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Inspect the current bearer token's claims",
    description=(
        "Returns identity and role for the token in the Authorization header. "
        "Accepts both JWT access tokens and the legacy API_AUTH_TOKEN."
    ),
)
async def me(
    _auth: Optional[str] = Depends(require_auth),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> MeResponse:
    """Return the authenticated caller's identity and role."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No credentials provided.",
        )

    raw = credentials.credentials

    # Try JWT first
    if _get_jwt_secret():
        try:
            claims = decode_jwt(raw, expected_type="access")
            return MeResponse(
                sub=claims.sub,
                role=claims.role,
                jti=claims.jti,
                iss=claims.iss,
                token_type="jwt",
                expires_at=claims.exp.isoformat(),
            )
        except HTTPException:
            pass  # Fall through to legacy token response

    # Legacy bearer token (already validated by require_auth above)
    return MeResponse(
        sub="legacy-api-token",
        role=ROLE_ADMIN,
        jti="legacy",
        iss=settings.JWT_ISSUER,
        token_type="legacy_bearer",
        expires_at="",
    )
