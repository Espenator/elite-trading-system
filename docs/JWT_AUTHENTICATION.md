# JWT Authentication Guide

## Overview

The Elite Trading System now supports JWT (JSON Web Token) authentication, providing a secure, time-limited authentication mechanism with user context tracking. This guide explains how to configure, use, and test the JWT authentication system.

## Features

- **Time-Limited Tokens**: Access tokens expire after 30 minutes (configurable)
- **Refresh Tokens**: Long-lived tokens (7 days) for obtaining new access tokens
- **Dual Auth Mode**: Supports both JWT and legacy bearer tokens
- **Auto-Generation**: Secret key auto-generated in development if not configured
- **User Context**: Tokens carry user information (username, role, etc.)
- **Type Safety**: Separate access and refresh token types with validation

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# JWT Authentication (Optional — recommended for multi-user)
JWT_SECRET_KEY=your-secret-key-here  # Generate with command below
JWT_ALGORITHM=HS256                   # Signing algorithm
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30    # Access token expiration
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7       # Refresh token expiration

# Legacy API Authentication (backward compatibility)
API_AUTH_TOKEN=your-api-token-here
```

### Generate Secure Keys

Generate a secure JWT secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## API Endpoints

### 1. Login (Exchange API Key for JWT Tokens)

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```json
{
  "api_key": "your-api-auth-token",
  "username": "alice"  // Optional, defaults to "api_user"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800  // seconds (30 minutes)
}
```

### 2. Refresh Access Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // New token
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // Same token
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Get Current User Info

**Endpoint**: `GET /api/v1/auth/me`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "user": {
    "sub": "alice",
    "type_": "api",
    "type": "access",
    "exp": 1234567890,
    "iat": 1234567890
  },
  "authenticated": true
}
```

### 4. Verify Token

**Endpoint**: `GET /api/v1/auth/verify`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "valid": true,
  "user_type": "jwt"
}
```

## Usage Examples

### Python Client

```python
import requests

# 1. Login and get tokens
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "api_key": "your-api-key",
        "username": "alice"
    }
)
tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# 2. Use access token for API calls
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
print(response.json())

# 3. Refresh when token expires
response = requests.post(
    "http://localhost:8000/api/v1/auth/refresh",
    json={"refresh_token": refresh_token}
)
new_tokens = response.json()
access_token = new_tokens["access_token"]
```

### JavaScript/TypeScript

```typescript
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    api_key: 'your-api-key',
    username: 'alice'
  })
});
const tokens = await loginResponse.json();

// 2. Store tokens (use secure storage in production)
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);

// 3. Use access token
const meResponse = await fetch('http://localhost:8000/api/v1/auth/me', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
const user = await meResponse.json();

// 4. Refresh token when needed
const refreshResponse = await fetch('http://localhost:8000/api/v1/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: localStorage.getItem('refresh_token')
  })
});
const newTokens = await refreshResponse.json();
localStorage.setItem('access_token', newTokens.access_token);
```

### cURL

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key", "username": "alice"}'

# Use access token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Protected Routes

The following routes require authentication (JWT or legacy token):

### State-Changing Endpoints (Protected)
- `POST /api/v1/agents/*` - Agent creation/updates
- `POST /api/v1/training/*` - Training operations
- `POST /api/v1/signals/*` - Signal creation
- `POST /api/v1/backtest/*` - Backtest execution
- `POST /api/v1/alignment/*` - Alignment operations
- `DELETE /api/v1/alpaca/positions/*` - Position deletions
- `POST /api/v1/risk-shield/*` - Risk operations

### Authentication Endpoints (Public)
- `POST /api/v1/auth/login` - Login (requires API key)
- `POST /api/v1/auth/refresh` - Refresh (requires refresh token)
- `GET /api/v1/auth/me` - User info (requires access token)
- `GET /api/v1/auth/verify` - Verify (requires access token)

## Security Best Practices

### Production Deployment

1. **Always set JWT_SECRET_KEY in production**:
   ```bash
   JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Use HTTPS**: JWT tokens should never be transmitted over HTTP in production.

3. **Secure Token Storage**:
   - Frontend: Use httpOnly cookies or secure storage (not localStorage in production)
   - Mobile: Use secure keychain/keystore
   - Backend: Never log tokens

4. **Token Rotation**: Implement token rotation strategy for refresh tokens in high-security environments.

5. **Short Expiration**: Keep access token expiration short (15-30 minutes).

### Development vs Production

**Development** (auto-generated secret, warnings logged):
```bash
# .env
# Leave JWT_SECRET_KEY empty - auto-generates
JWT_SECRET_KEY=
```

**Production** (explicit configuration required):
```bash
# .env
JWT_SECRET_KEY=<strong-random-secret>
API_AUTH_TOKEN=<strong-random-token>
```

## Backward Compatibility

The system supports both JWT tokens and legacy bearer tokens:

**Priority Order**:
1. Try JWT token validation first
2. Fall back to legacy `API_AUTH_TOKEN` if JWT fails
3. Block request if both fail

**Example**:
```python
# Both work:
headers1 = {"Authorization": f"Bearer {jwt_access_token}"}  # JWT
headers2 = {"Authorization": f"Bearer {API_AUTH_TOKEN}"}     # Legacy
```

## Testing

### Run JWT Tests

```bash
# Run all JWT tests
pytest tests/test_jwt_auth.py -v

# Run endpoint tests
pytest tests/test_auth_endpoints.py -v

# Run specific test
pytest tests/test_jwt_auth.py::TestJWTTokenGeneration::test_create_access_token_default_expiry -v
```

### Manual Testing

```bash
# Start the backend
cd backend
uvicorn app.main:app --reload

# In another terminal, test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-key", "username": "test"}'
```

## Troubleshooting

### "Authentication required" Error

**Cause**: No authentication configured.

**Solution**: Set `API_AUTH_TOKEN` or `JWT_SECRET_KEY` in `.env`:
```bash
API_AUTH_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### "Invalid or expired token" Error

**Cause**: Token expired or invalid.

**Solution**: Use refresh token to get new access token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your_refresh_token>"}'
```

### Token Expiration Too Short/Long

**Cause**: Default expiration doesn't fit your use case.

**Solution**: Adjust in `.env`:
```bash
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60   # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30     # 30 days
```

### "JWT secret auto-generated" Warning

**Cause**: `JWT_SECRET_KEY` not set in `.env`.

**Solution**:
- Development: Ignore (auto-generation is fine)
- Production: Set explicit key:
  ```bash
  JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
  ```

## Architecture

### Components

1. **jwt_utils.py**: Token generation and validation
   - `create_access_token()`: Create access tokens
   - `create_refresh_token()`: Create refresh tokens
   - `verify_token()`: Validate and decode tokens

2. **security.py**: FastAPI dependencies
   - `require_auth()`: Enforce authentication
   - `optional_auth()`: Optional authentication
   - `get_current_user()`: Extract user context

3. **auth.py**: API endpoints
   - `/auth/login`: Login endpoint
   - `/auth/refresh`: Refresh endpoint
   - `/auth/me`: User info endpoint
   - `/auth/verify`: Verify endpoint

### Token Structure

**Access Token Payload**:
```json
{
  "sub": "alice",           // Subject (username)
  "type_": "api",           // User type
  "type": "access",         // Token type
  "exp": 1234567890,        // Expiration timestamp
  "iat": 1234567890         // Issued-at timestamp
}
```

**Refresh Token Payload**:
```json
{
  "sub": "alice",
  "type_": "api",
  "type": "refresh",        // Token type (refresh)
  "exp": 1234567890,
  "iat": 1234567890
}
```

## Migration from Legacy Auth

If you're currently using `API_AUTH_TOKEN` only:

1. **No changes required**: System is backward compatible
2. **Optional migration**: Add JWT for enhanced security:
   ```bash
   # .env
   API_AUTH_TOKEN=<existing-token>    # Keep for backward compat
   JWT_SECRET_KEY=<new-secret>        # Add JWT support
   ```
3. **Gradual rollout**: Update clients to use JWT over time
4. **Full migration**: Eventually remove `API_AUTH_TOKEN` once all clients use JWT

## Reference

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | Auto-generated | Secret key for JWT signing |
| `JWT_ALGORITHM` | HS256 | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token expiration |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token expiration |
| `API_AUTH_TOKEN` | - | Legacy bearer token |

### Supported Algorithms

- HS256 (HMAC SHA-256) - Default
- HS384 (HMAC SHA-384)
- HS512 (HMAC SHA-512)
- RS256 (RSA SHA-256)
- RS384 (RSA SHA-384)
- RS512 (RSA SHA-512)

**Note**: For asymmetric algorithms (RS*), you need to configure public/private keys.

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (no auth configured) |
| 422 | Validation error (malformed request) |
| 503 | Service unavailable (auth not configured) |

## Future Enhancements

Planned improvements:
- [ ] Token revocation/blacklist system
- [ ] OAuth2 integration
- [ ] Multi-user management with roles/permissions
- [ ] Rate limiting on auth endpoints
- [ ] Audit logging for auth events
- [ ] Token rotation strategy
- [ ] Session management

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test files: `tests/test_jwt_auth.py`, `tests/test_auth_endpoints.py`
3. Check logs for authentication errors
4. Open an issue on GitHub
