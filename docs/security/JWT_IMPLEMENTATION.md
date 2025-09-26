---
title: JWT Authentication Implementation
last_reviewed: 2025-09-25
owner: security-team
---

# JWT Authentication Implementation

## Overview

This document outlines the JWT (JSON Web Token) authentication implementation for the MagFlow API, supporting both RS256 and EdDSA algorithms.

## Features

- Dual algorithm support (RS256 and EdDSA)
- Automatic key rotation with N-1 active keys
- Short-lived access tokens and long-lived refresh tokens
- Comprehensive security validations
- JWKS endpoint for public key discovery
- Token revocation support

## Configuration

### Environment Variables

```env
# JWT Settings
JWT_ALGORITHM=RS256  # or EdDSA
JWT_ISSUER=magflow-service
JWT_AUDIENCE=magflow-api
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_LEEWAY=60  # seconds
JWT_KEY_EXPIRE_DAYS=30
JWT_ROTATE_DAYS=7
JWT_MAX_ACTIVE_KEYS=2
JWKS_CACHE_MAX_AGE=3600
```

## Key Management

### Key Generation

1. **RSA Keys (RS256)**

   ```bash
   mkdir -p jwt-keys
   openssl genrsa -out jwt-keys/private-rsa.pem 4096
   openssl rsa -in jwt-keys/private-rsa.pem -pubout -out jwt-keys/public-rsa.pem
   ```

1. **EdDSA Keys**

   ```bash
   openssl genpkey -algorithm Ed25519 -out jwt-keys/private-ed25519.pem
   openssl pkey -in jwt-keys/private-ed25519.pem -pubout -out jwt-keys/public-ed25519.pem
   ```

### Key Rotation

Keys are automatically rotated based on the following rules:

- New keys are generated when the current key is within `JWT_ROTATE_DAYS` of expiration
- Up to `JWT_MAX_ACTIVE_KEYS` - 1 keys are kept for verification
- Expired keys are automatically removed

## Token Types

### Access Token

- Short-lived (15 minutes by default)
- Contains user claims and permissions
- Used for API authentication

### Refresh Token

- Long-lived (7 days by default)
- Used to obtain new access tokens
- Can be revoked

## Security Considerations

### Token Validation

1. Signature verification
1. Algorithm validation (prevents algorithm substitution attacks)
1. Expiration check with leeway
1. Issuer validation
1. Audience validation
1. Key ID (kid) validation

### Best Practices

- Always use HTTPS
- Store private keys securely with restricted permissions
- Set appropriate token expiration times
- Implement token revocation
- Rotate keys regularly
- Monitor for suspicious activity

## API Endpoints

### Authentication

- `POST /auth/login` - Obtain access and refresh tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Revoke refresh token

### Public Keys

- `GET /.well-known/jwks.json` - JSON Web Key Set (JWKS) endpoint

## Testing

### Unit Tests

Run the test suite:

```bash
pytest tests/security/test_jwt.py -v
```

### Manual Testing

1. Get an access token:

   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user@example.com", "password": "password"}'
   ```

1. Use the access token:

   ```bash
   curl http://localhost:8000/api/protected \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## Troubleshooting

### Common Issues

#### Invalid Token

- Verify token hasn't expired
- Check token signature
- Validate token claims

#### Key Rotation Issues

- Check key files exist and are readable
- Verify key permissions (600 for private keys)
- Check logs for key rotation errors

#### Performance Issues

- Monitor key generation time
- Check token validation performance
- Review cache settings

## Monitoring and Logging

- Monitor token generation and validation metrics
- Log authentication failures
- Track key rotation events
- Monitor token usage patterns

## References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [JWS RFC 7515](https://tools.ietf.org/html/rfc7515)
- [JWA RFC 7518](https://tools.ietf.org/html/rfc7518)
- [JWK RFC 7517](https://tools.ietf.org/html/rfc7517)
