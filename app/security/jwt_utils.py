"""JWT utility functions for token creation, validation, and verification."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from ..core.config import settings
from .keys import get_key_manager

# Supported JWT algorithms
SUPPORTED_ALGORITHMS = ["RS256", "EdDSA"]

# Get key manager instance
key_manager = get_key_manager()


class JWTValidationError(JWTError):
    """Raised when JWT validation fails."""


def create_token(
    subject: str | Any,
    token_type: str = "access",
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
    algorithm: str | None = None,
) -> str:
    """Create a JWT token with the specified subject and claims.

    Args:
        subject: The subject of the token (usually a user ID or username)
        token_type: Type of token (access or refresh)
        expires_delta: Optional timedelta for token expiration
        additional_claims: Additional claims to include in the token
        algorithm: JWT signing algorithm (default: settings.JWT_ALGORITHM)

    Returns:
        str: Encoded JWT token

    """
    now = datetime.now(UTC)

    # Set expiration time based on token type
    if expires_delta:
        expire = now + expires_delta
    elif token_type == "refresh":
        expire = now + timedelta(days=settings.refresh_token_expire_days)
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    # Get the active key for signing
    key = key_manager.get_active_key()

    # Use provided algorithm or default from settings
    alg = algorithm or settings.jwt_algorithm
    if alg not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported JWT algorithm: {alg}")

    # Prepare the token claims
    to_encode = {
        "iss": settings.jwt_issuer,
        "sub": str(subject),
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "nbf": int(
            now.timestamp() - settings.jwt_leeway,
        ),  # Not before with leeway for clock skew
        "jti": f"{now.timestamp()}-{subject}",
        "kid": key.kid,
        "typ": token_type,
    }

    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)

    try:
        # Encode the token with the private key
        return jwt.encode(
            to_encode,
            key.private_key,
            algorithm=alg,
            headers={
                "kid": key.kid,
                "alg": alg,
                "typ": "JWT",
            },
        )
    except JWTError as e:
        raise JWTError(f"Failed to encode token: {e}")


def decode_token(
    token: str,
    algorithms: list[str] | None = None,
    options: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Decode and verify a JWT token using the key manager.

    Args:
        token: The JWT token to decode
        algorithms: List of allowed algorithms (default: settings.JWT_ALGORITHM)
        options: JWT decode options (default: verify signature, expiration, issuer)

    Returns:
        The decoded token payload

    Raises:
        JWTValidationError: If the token is invalid, expired, or verification fails

    """
    if options is None:
        options = {
            "verify_signature": True,
            "verify_aud": True,
            "verify_iat": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iss": True,
            "verify_sub": False,
            "verify_jti": True,
            "leeway": settings.JWT_LEEWAY,
        }

    # Get the key ID and algorithm from the token header
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")

        if not kid or not alg:
            raise JWTValidationError("Missing 'kid' or 'alg' in token header")

        # Get the key for verification
        key = key_manager.get_key(kid)
        if not key:
            raise JWTValidationError(f"Key not found: {kid}")

        # Verify the key algorithm matches the token algorithm
        if key.algorithm != alg:
            raise JWTValidationError(
                f"Key algorithm mismatch: expected {key.algorithm}, got {alg}",
            )

        # Decode and verify the token
        payload = jwt.decode(
            token,
            key.public_key,
            algorithms=algorithms or [alg],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )

        # Additional validation for token type if present
        if "typ" in payload and payload["typ"] not in ["access", "refresh"]:
            raise JWTValidationError("Invalid token type")

        return payload

    except ExpiredSignatureError as e:
        raise JWTValidationError("Token has expired") from e
    except JWTClaimsError as e:
        raise JWTValidationError(f"Invalid token claims: {e}") from e
    except JWTError as e:
        raise JWTValidationError(f"Invalid token: {e}") from e


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
    algorithm: str | None = None,
) -> str:
    """Create an access token with the specified subject and claims."""
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=expires_delta,
        additional_claims=additional_claims,
        algorithm=algorithm,
    )


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
    algorithm: str | None = None,
) -> str:
    """Create a refresh token with the specified subject and claims."""
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=expires_delta
        or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        additional_claims=additional_claims,
        algorithm=algorithm,
    )
