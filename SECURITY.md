# Security Policy

## Overview

This document describes the security measures implemented in the Elite Trading System to protect sensitive data, prevent unauthorized access, and ensure safe operation in production environments.

## Security Features

### 1. API Authentication

**Bearer Token Authentication**
- All state-changing endpoints (POST, PUT, PATCH, DELETE) require Bearer token authentication
- Token configured via `API_AUTH_TOKEN` environment variable
- Uses constant-time comparison (`secrets.compare_digest`) to prevent timing attacks
- Enforced in production and live trading modes

**Configuration:**
```bash
# Generate a secure token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
API_AUTH_TOKEN=your-generated-token-here
```

### 2. WebSocket Security

**Authentication**
- WebSocket connections require token authentication
- Fail-closed design: rejects connections if no token configured
- Token must match `API_AUTH_TOKEN` from environment
- Uses constant-time comparison to prevent timing attacks

**Connection Flow:**
1. Client connects to `/ws?token=YOUR_TOKEN`
2. Server validates token on connection
3. Invalid tokens result in immediate rejection (code 4001)

### 3. Credential Encryption

**Fernet Symmetric Encryption**
- All API keys and secrets stored in database are encrypted using Fernet
- `FERNET_KEY` environment variable required in production
- Application fails to start if `FERNET_KEY` is missing in production mode

**Key Generation:**
```bash
# Generate Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
FERNET_KEY=your-generated-key-here
```

**Protected Credentials:**
- Alpaca API keys and secrets
- External API keys (Finviz, Unusual Whales, etc.)
- OAuth tokens
- Discord/Slack tokens

### 4. CORS Protection

**Production Configuration**
- CORS `allow_credentials=True` only when:
  - Single explicit origin configured (not localhost)
  - In non-production environments
- Multiple origins or localhost origins disable credentials in production
- Prevents credential leakage to unauthorized origins

**Configuration:**
```bash
# Production - single origin, enables credentials
CORS_ORIGINS=https://yourdomain.com

# Development - multiple origins, disables credentials in production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 5. Logging Security

**Automatic Secret Redaction**
- All log messages automatically redact sensitive data
- Patterns detected and replaced with `[REDACTED]`:
  - API keys (`api_key`, `api-key`)
  - Secret keys (`secret_key`, `secret-key`)
  - Tokens (`token`, `bearer`)
  - Passwords (`password`)
  - Authorization headers

**Examples:**
```
# Before: "API call failed: api_key=sk_live_abc123xyz"
# After:  "API call failed: api_key=[REDACTED]"

# Before: "Bearer sk_test_xyz789abc in request"
# After:  "Bearer [REDACTED] in request"
```

### 6. Rate Limiting

**SlowAPI Integration**
- Default: 100 requests per minute per IP
- Prevents brute force attacks
- Returns HTTP 429 when limit exceeded

### 7. Security Headers

All HTTP responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Correlation-ID: <unique-id>` (for request tracing)

### 8. Production Validation

**Startup Checks**
- Live trading mode requires:
  - `ALPACA_API_KEY`
  - `ALPACA_SECRET_KEY`
  - `API_AUTH_TOKEN`
- Production environment requires:
  - `FERNET_KEY`
- Missing keys cause automatic fallback or startup failure

## Security Best Practices

### For Development

1. **Never commit secrets** to version control
2. Use `.env` files (gitignored) for local development
3. Generate unique tokens per environment
4. Set `ENVIRONMENT=development` to enable dev-friendly logging

### For Production

1. **Required Environment Variables:**
   ```bash
   ENVIRONMENT=production
   TRADING_MODE=paper  # or "live" for real trading
   API_AUTH_TOKEN=<secure-token>
   FERNET_KEY=<fernet-key>
   CORS_ORIGINS=https://yourdomain.com  # single origin only
   ```

2. **Use HTTPS/TLS:**
   - Frontend should use `https://` URLs
   - WebSocket should use `wss://` protocol
   - Configure reverse proxy (nginx/caddy) with SSL certificates

3. **Secure Database:**
   - Restrict file system access to database files
   - Consider OS-level encryption for data at rest
   - Regular backups with encrypted storage

4. **Monitor Logs:**
   - Review logs for authentication failures
   - Set up alerts for repeated auth failures (potential attacks)
   - Use correlation IDs to trace suspicious requests

5. **Rotate Credentials:**
   - Regularly rotate `API_AUTH_TOKEN`
   - Rotate external API keys per provider policies
   - Update `FERNET_KEY` requires re-encryption of stored data

### Network Security

**Firewall Rules:**
- Restrict backend port (8000) to trusted networks
- Use VPN or IP whitelisting for remote access
- Separate production and development networks

**Two-PC Setup:**
- PC1 (ESPENMAIN): Primary backend on 192.168.1.105
- PC2 (ProfitTrader): Secondary services on 192.168.1.116
- LAN-only access by default
- External access requires proper network security

## Incident Response

### Security Issue Detected

1. **Immediate Actions:**
   - Rotate compromised credentials immediately
   - Review logs for unauthorized access
   - Check database for data modifications

2. **Mitigation:**
   - Update `API_AUTH_TOKEN` in all environments
   - Regenerate `FERNET_KEY` and re-encrypt data if necessary
   - Block suspicious IPs at firewall level

3. **Investigation:**
   - Use correlation IDs to trace attack vector
   - Review authentication logs
   - Check for data exfiltration

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please:

1. **Do NOT** open a public GitHub issue
2. Report privately via GitHub Security Advisories
3. Include:
   - Vulnerability description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Checklist

Before deploying to production:

- [ ] `ENVIRONMENT=production` set
- [ ] `API_AUTH_TOKEN` configured (32+ character random string)
- [ ] `FERNET_KEY` configured (Fernet-generated key)
- [ ] `CORS_ORIGINS` set to single production domain (no localhost)
- [ ] SSL/TLS certificates installed and configured
- [ ] Firewall rules configured
- [ ] Database file permissions restricted
- [ ] Log monitoring configured
- [ ] Backup strategy implemented
- [ ] All external API keys validated and working
- [ ] WebSocket uses `wss://` in production
- [ ] Rate limiting configured appropriately

## Security Updates

This security policy was last updated: **March 9, 2026**

Major security improvements:
- **v3.5.1**: WebSocket authentication enforcement, FERNET_KEY validation, CORS restrictions, log redaction
- Previous versions may have security gaps - upgrade recommended

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Fernet Specification](https://github.com/fernet/spec/)
