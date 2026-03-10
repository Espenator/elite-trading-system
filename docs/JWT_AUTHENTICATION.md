# JWT Authentication for Live Trading

## Overview

The Elite Trading System now supports JWT (JSON Web Token) authentication for live trading mode. This provides secure, token-based authentication for all state-changing endpoints when the system is running in live trading mode.

## Features

- **Time-limited Access Tokens**: Short-lived tokens (default: 60 minutes) for accessing protected endpoints
- **Long-lived Refresh Tokens**: Long-lived tokens (default: 7 days) for obtaining new access tokens
- **Backward Compatibility**: Falls back to simple bearer token authentication in paper mode
- **Trading Mode Validation**: Tokens include trading mode claims to prevent accidental live trading
- **Secure Signing**: Uses HS256 algorithm with configurable secret keys

## Architecture

### Token Types

1. **Access Token**
   - Used for authenticating API requests
   - Expires after 60 minutes (configurable)
   - Contains user claims: user_id, username, trading_mode, permissions
   - Type: `access`

2. **Refresh Token**
   - Used for obtaining new access tokens
   - Expires after 7 days (configurable)
   - Contains same user claims as access token
   - Type: `refresh`

### Authentication Flow

```
1. User logs in via POST /api/v1/auth/login
   ↓
2. Server validates credentials and issues tokens
   ↓
3. Client stores both access and refresh tokens
   ↓
4. Client uses access token for API requests
   ↓
5. When access token expires, use refresh token
   ↓
6. POST /api/v1/auth/refresh with refresh token
   ↓
7. Receive new access token
```

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# JWT Authentication (REQUIRED for live trading)
JWT_SECRET_KEY=your-secure-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Generate a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**IMPORTANT**: Keep your JWT_SECRET_KEY secret and never commit it to version control!

## API Endpoints

All authentication endpoints are available at `/api/v1/auth/*`:

### POST /api/v1/auth/login

Login and receive JWT tokens.

**Request:**
```json
{
  "username": "your_username",
  "password": "your_password",
  "trading_mode": "live"  // optional, defaults to system trading mode
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /api/v1/auth/refresh

Refresh your access token using a refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### GET /api/v1/auth/me

Get current user information from your token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "user_id": "user_123",
  "username": "trader",
  "trading_mode": "live",
  "permissions": ["trade", "view_positions", "view_orders"]
}
```

### GET /api/v1/auth/verify

Verify if a token is valid.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "valid": true,
  "user_id": "user_123",
  "expires_at": 1709145600
}
```

## Using JWT Authentication

### In Paper Mode

In paper mode, the system falls back to simple bearer token authentication for backward compatibility:

```bash
curl -X POST http://localhost:8000/api/v1/orders/advanced \
  -H "Authorization: Bearer your_api_auth_token" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", ...}'
```

### In Live Mode

In live mode, you must use JWT authentication:

1. **Login to get tokens:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

2. **Use access token for requests:**
```bash
curl -X POST http://localhost:8000/api/v1/orders/advanced \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", ...}'
```

3. **Refresh token when it expires:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Protected Endpoints

The following endpoints require JWT authentication in live mode:

### Order Management
- `POST /api/v1/orders/advanced` - Create advanced order
- `PATCH /api/v1/orders/{order_id}` - Replace/amend order
- `DELETE /api/v1/orders/{order_id}` - Cancel single order
- `DELETE /api/v1/orders/` - Cancel all orders
- `POST /api/v1/orders/close` - Close position
- `POST /api/v1/orders/adjust` - Adjust position
- `POST /api/v1/orders/flatten-all` - Flatten all positions
- `POST /api/v1/orders/emergency-stop` - Emergency stop

## Security Best Practices

1. **Keep Secrets Secure**
   - Never commit JWT_SECRET_KEY to version control
   - Use environment variables for all secrets
   - Rotate secrets periodically

2. **Token Storage**
   - Store tokens securely on the client side
   - Use httpOnly cookies when possible
   - Clear tokens on logout

3. **Token Expiration**
   - Access tokens should be short-lived (default: 60 minutes)
   - Refresh tokens should be longer (default: 7 days)
   - Implement token refresh before expiration

4. **HTTPS Only**
   - Always use HTTPS in production
   - Never send tokens over unencrypted connections

5. **Validation**
   - All tokens are validated on every request
   - Expired tokens are rejected
   - Tampered tokens are rejected

## Testing

### Run JWT Authentication Tests

```bash
cd backend
python -m pytest tests/test_jwt_auth.py -v
python -m pytest tests/test_auth_endpoints.py -v
```

### Test Coverage

- 26 JWT utility tests (test_jwt_auth.py)
- 23 endpoint integration tests (test_auth_endpoints.py)
- Tests cover token generation, validation, endpoints, and workflows

## Implementation Details

### Files Added/Modified

1. **backend/app/core/security.py** - JWT utilities (create_access_token, create_refresh_token, decode_token, require_jwt_auth)
2. **backend/app/core/config.py** - JWT configuration settings
3. **backend/app/api/v1/auth.py** - Authentication endpoints
4. **backend/app/api/v1/orders.py** - Updated to use require_jwt_auth
5. **backend/app/main.py** - Mounted auth router
6. **.env.example** - JWT configuration examples
7. **backend/tests/test_jwt_auth.py** - JWT utility tests
8. **backend/tests/test_auth_endpoints.py** - Endpoint integration tests

### Token Claims

Access and refresh tokens include the following claims:

```python
{
  "user_id": "string",        # Unique user identifier
  "username": "string",       # Username
  "trading_mode": "string",   # "live" or "paper"
  "permissions": ["string"],  # List of permissions
  "exp": int,                 # Expiration timestamp
  "iat": int,                 # Issued at timestamp
  "type": "string"            # "access" or "refresh"
}
```

### Authentication Priority

1. **Live Mode**: JWT authentication required (require_jwt_auth)
2. **Paper Mode**: Simple bearer token (backward compatible with require_auth)

## Troubleshooting

### "JWT_SECRET_KEY must be configured"

Set the JWT_SECRET_KEY in your `.env` file:
```bash
JWT_SECRET_KEY=your_secure_secret_here
```

### "Invalid token" or "Token has expired"

1. Check token expiration time
2. Use refresh token to get a new access token
3. Verify JWT_SECRET_KEY matches between token creation and validation

### "Invalid token type"

- Use access tokens for API requests
- Use refresh tokens only for the /auth/refresh endpoint

## Future Enhancements

1. **User Database Integration**: Currently accepts any credentials for demo purposes
2. **Token Revocation**: Implement token blacklist for logout
3. **Role-Based Access Control**: Expand permissions system
4. **Multi-Factor Authentication**: Add 2FA support
5. **Token Rotation**: Automatic refresh token rotation

## References

- [JWT.io](https://jwt.io/) - JWT introduction and debugger
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
