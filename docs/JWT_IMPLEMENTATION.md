# JWT Authentication with RS256, EdDSA, and Key Rotation

This document outlines the JWT authentication implementation with support for multiple signing algorithms (RS256 and EdDSA) and key rotation with JWKS endpoint support.

## Overview

The JWT authentication system supports multiple signing algorithms and provides robust key management:

1. **Multiple Algorithms**: Support for both RS256 (RSA with SHA-256) and EdDSA (Ed25519) signing algorithms
2. **Key Management**: Secure key storage and automatic key rotation
3. **N-1 Key Rotation**: Maintains previous key during rotation to prevent token invalidation
4. **JWKS Endpoint**: Public key discovery endpoint for token verification
5. **Refresh Tokens**: Long-lived refresh tokens for better security

## Key Components

### 1. Key Management

- **Key Storage**: Keys are stored in the configured directory (`JWT_KEYSET_DIR`)
- **Key Rotation**: Automatic key rotation based on configuration
- **N-1 Strategy**: Maintains one previous active key during rotation
- **Key Formats**: Keys are stored in PEM format
- **Supported Algorithms**:
  - RS256: RSA with SHA-256 (recommended for compatibility)
  - EdDSA: Ed25519 (recommended for performance and security)

### 2. JWT Tokens

- **Algorithms**:
  - RS256 (RSA with SHA-256)
  - EdDSA (Ed25519)
- **Token Types**:
  - Access Token: Short-lived (default 15 minutes)
  - Refresh Token: Long-lived (default 7 days)
- **Claims**:
  - Standard JWT claims (iss, sub, aud, exp, nbf, iat, jti)
  - Custom claims for user roles and permissions
  - `kid` (Key ID) for key identification
  - `typ` to distinguish between token types (access/refresh)

### 3. JWKS Endpoint

- **Endpoint**: `/.well-known/jwks.json`
- **Purpose**: Provides public keys for token verification
- **Caching**: Responses include `Cache-Control` headers (default: 1 hour)
- **Key Types**: Includes public keys for all active keys of both algorithms
- **Security**: Only public keys are exposed (no private key material)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_ALGORITHM` | Default algorithm for new tokens | `RS256` |
| `JWT_ISSUER` | Token issuer | `magflow` |
| `JWT_AUDIENCE` | Token audience | `magflow-api` |
| `JWT_LEEWAY` | Clock skew leeway (seconds) | `60` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `JWT_KEY_EXPIRE_DAYS` | Key expiration period | `30` |
| `JWT_ROTATE_DAYS` | Rotate keys when this many days left | `5` |
| `JWT_MAX_ACTIVE_KEYS` | Maximum active keys per algorithm | `2` |
| `JWKS_CACHE_MAX_AGE` | Cache TTL for JWKS endpoint | `3600` |
| `JWT_KEYSET_DIR` | Directory to store key files | `./jwt-keys` |

## Key Rotation

The system implements an N-1 key rotation strategy:

1. **Key Generation**: New keys are generated when:
   - No active keys exist for an algorithm
   - The current key is within `JWT_ROTATE_DAYS` of expiration

2. **Rotation Process**:
   - When a new key is generated, it becomes the active key
   - The previous active key is kept for verification of existing tokens
   - Up to `JWT_MAX_ACTIVE_KEYS` keys per algorithm are maintained
   - Expired keys are automatically cleaned up

3. **Verification**:
   - Tokens are verified using the key ID (`kid`) in the header
   - The system will try all active keys if the specified key is not found
   - Expired keys are never used for verification

## Security Considerations

1. **Algorithm Security**:
   - RS256 is widely supported and recommended for compatibility
   - EdDSA (Ed25519) offers better performance and security
   - The system prevents algorithm substitution attacks

2. **Key Security**:
   - Private keys are stored with restricted file permissions (600)
   - Keys are rotated regularly to limit the impact of key compromise
   - Only public keys are exposed via the JWKS endpoint

3. **Token Security**:
   - Access tokens are short-lived (15 minutes by default)
   - Refresh tokens can be used to obtain new access tokens
   - Tokens include standard security claims (iss, aud, exp, nbf, iat, jti)

## Usage Example

### Creating Tokens

```python
from datetime import timedelta
from app.security.jwt_utils import create_access_token, create_refresh_token

# Create access token (RS256 by default)
access_token = create_access_token(
    subject="user123",
    expires_delta=timedelta(minutes=15),
    additional_claims={"role": "admin"}
)

# Create refresh token with EdDSA
refresh_token = create_refresh_token(
    subject="user123",
    algorithm="EdDSA"
)
```

### Verifying Tokens

```python
from app.security.jwt_utils import decode_token

try:
    payload = decode_token(token)
    user_id = payload["sub"]
    role = payload.get("role")
    # Process the token...
except JWTError as e:
    # Handle invalid token
    pass
```

### Using the JWKS Endpoint

Clients can verify tokens using the JWKS endpoint:

```python
import requests
from jose import jwt
from jose.utils import base64url_decode

def verify_token(token: str) -> dict:
    # Get the key ID from the token header
    header = jwt.get_unverified_header(token)
    kid = header["kid"]

    # Fetch the JWKS
    jwks_url = "https://your-api.com/.well-known/jwks.json"
    jwks = requests.get(jwks_url).json()

    # Find the key with matching kid
    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if not key:
        raise ValueError("Key not found in JWKS")

    # Verify and decode the token
    return jwt.decode(
        token,
        key,
        algorithms=["RS256", "EdDSA"],
        audience="magflow-api",
        issuer="magflow"
    )
```

## Monitoring and Maintenance

1. **Key Rotation**: Monitor key rotation logs to ensure keys are rotated as expected
2. **Expired Keys**: The system automatically cleans up expired keys
3. **Performance**: Monitor token verification performance, especially with large numbers of active keys
4. **Security**: Regularly audit key permissions and access patterns
3. Create a symlink to the active key

### 2. Environment Variables

Update your `.env` file with these variables:

```ini
# JWT Configuration
JWT_ALGORITHM=RS256
JWT_KEYSET_DIR=./jwt-keys
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_KEY_EXPIRE_DAYS=30
JWT_ROTATE_DAYS=7
JWKS_CACHE_MAX_AGE=3600
JWT_ISSUER=magflow-service
```

### 3. Database Migration

Run the database migration to create the required tables:

```bash
alembic upgrade head
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Get access and refresh tokens
- `POST /api/v1/auth/refresh` - Get a new access token using a refresh token
- `POST /api/v1/auth/logout` - Invalidate the current token

### JWKS

- `GET /.well-known/jwks.json` - Get public keys for token verification
- `GET /.well-known/openid-configuration` - OpenID Connect configuration

## Usage Examples

### 1. Login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=testuser&password=testpassword
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Access Protected Endpoint

```http
GET /api/v1/protected
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Key Rotation

Key rotation is handled automatically based on the configuration:

1. New keys are generated when the current key is about to expire
2. Old keys are kept for a grace period to allow token verification
3. The JWKS endpoint always returns the active public keys

## Security Considerations

1. **Private Keys**: Keep private keys secure and never commit them to version control
2. **Key Rotation**: Regularly rotate keys according to your security policy
3. **Token Expiration**: Keep access token lifetimes short and use refresh tokens for long-lived sessions
4. **HTTPS**: Always use HTTPS in production to prevent token interception

## Troubleshooting

### Token Validation Fails

1. Verify the token signature using the public key from the JWKS endpoint
2. Check the token expiration time
3. Verify the token issuer matches your configuration

### JWKS Endpoint Not Working

1. Ensure the `JWT_KEYSET_DIR` is correctly configured and readable
2. Check that the key files have the correct permissions
3. Verify the service has read access to the key files

## Testing

Run the test suite to verify the JWT implementation:

```bash
pytest tests/test_jwt_implementation.py -v
```

## Monitoring

Monitor the following metrics:

- Token validation success/failure rates
- Key rotation events
- Token expiration and revocation events
- JWKS endpoint response times

## Future Enhancements

1. Support for multiple key algorithms
2. Key revocation and key rollover events
3. More granular token scopes and permissions
4. Integration with OAuth 2.0 and OpenID Connect
