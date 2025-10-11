import logging
import os
import re
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.auth import TokenPayload

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token

    """
    now = datetime.now(tz=UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": int(expire.timestamp()),
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "jti": uuid4().hex,
        "type": "access",
        "scopes": [],
    }

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token.

    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT refresh token

    """
    now = datetime.now(tz=UTC)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

    to_encode = {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": int(expire.timestamp()),
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "jti": uuid4().hex,
        "type": "refresh",
        "scopes": [],
    }

    return jwt.encode(
        to_encode,
        settings.refresh_secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str, *, is_refresh: bool = False) -> TokenPayload:
    """Verify a JWT token and return its payload.

    Args:
        token: The JWT token to verify
        is_refresh: Whether this is a refresh token

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If the token is invalid or expired

    """
    secret_key = settings.refresh_secret_key if is_refresh else settings.JWT_SECRET_KEY

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        token_data = TokenPayload(**payload)

        # Additional validation for token type
        if (is_refresh and token_data.type != "refresh") or (
            not is_refresh and token_data.type != "access"
        ):
            raise JWTError("Invalid token type")

    except (JWTError, ValidationError) as e:
        raise ValueError("Could not validate credentials") from e

    return token_data


def generate_password_reset_token(email: str) -> str:
    """Generate a password reset token.

    Args:
        email: User's email address

    Returns:
        JWT token for password reset

    """
    expires = datetime.now(tz=UTC) + timedelta(
        hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
    )
    to_encode = {
        "exp": expires,
        "sub": email,
        "type": "password_reset",
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_public_key() -> str:
    """Get the current public key for JWT verification.

    Returns:
        The public key as a string

    Raises:
        RuntimeError: If the public key file is not found

    """
    # Look for the public key in the configured directory
    keys_dir = Path(settings.JWT_KEYSET_DIR)
    if not keys_dir.exists() or not keys_dir.is_dir():
        raise RuntimeError(f"JWT keys directory not found: {keys_dir}")

    # Find the most recent public key
    public_keys = list(keys_dir.glob("*.pub"))
    if not public_keys:
        raise RuntimeError(f"No public key files found in {keys_dir}")

    # Get the most recent key (by modification time)
    latest_key = max(public_keys, key=os.path.getmtime)
    return latest_key.read_text()


def verify_password_reset_token(token: str) -> str | None:
    """Verify a password reset token.

    Args:
        token: The JWT token to verify

    Returns:
        The email address if the token is valid, None otherwise

    """
    try:
        # Get the public key for verification
        public_key = get_public_key()

        # Decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"verify_exp": True},
        )

        # Verify this is a password reset token
        if payload.get("type") != "password_reset":
            return None

        return payload.get("sub")

    except JWTError:
        return None


def decode_token(token: str) -> dict:
    """Decode a JWT token and return its payload.

    This is a lower-level function that just decodes the token without
    performing all the validations done in verify_token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If the token is invalid or expired

    """
    # Use the appropriate secret key based on token type
    try:
        # First try to decode as access token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False, "verify_exp": False},
        )

        # Check if it's a refresh token and use refresh secret if needed
        if payload.get("type") == "refresh":
            payload = jwt.decode(
                token,
                settings.refresh_secret_key,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False, "verify_exp": False},
            )

        return payload

    except JWTError:
        # If decoding fails with secret keys, try with refresh secret for refresh tokens
        try:
            return jwt.decode(
                token,
                settings.refresh_secret_key,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False, "verify_exp": False},
            )
        except JWTError:
            # If both fail, re-raise the original error
            raise


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Security validation utilities
logger = logging.getLogger(__name__)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> UserModel:
    """
    Get the current user from the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(username=username)
    except JWTError:
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(UserModel).where(UserModel.email == token_data.username)
    )
    user = result.scalars().first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Get the current active user.

    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class SecurityValidator:
    """Security validation utilities for input sanitization and validation."""

    @staticmethod
    def validate_sql_injection(input_string: str, max_length: int = 1000) -> bool:
        """Basic SQL injection pattern detection.

        Args:
            input_string: The string to validate
            max_length: Maximum allowed length

        Returns:
            True if safe, False if potentially malicious

        """
        if not isinstance(input_string, str):
            return False

        if len(input_string) > max_length:
            logger.warning(
                f"Input string exceeds max length: {len(input_string)} > {max_length}"
            )
            return False

        # Check for parameterized queries first (these are safe)
        if re.search(r"\?|\$\d+|:\w+", input_string):
            # This appears to be a parameterized query, check for actual injection patterns
            dangerous_patterns = [
                r"(\bor\s+1\s*=\s*1|\band\s+1\s*=\s*1)",
                r"(\bunion\s+select|\bunion\s+all\s+select)",
                r"(\-\-[^\?]|\#[^\?]|\/\*[^\?]|\*\/[^\?])",  # Comments not in parameters
                r"(\bEXEC\b|\bEXECUTE\b|\bxp_|\bsp_)",
                r"(\bdrop\s+table|\bdrop\s+database|\btruncate\s+table)",
                r"(\bSCRIPT\b|\bJAVASCRIPT\b|\bVBSCRIPT\b)",
                r"(\bALERT\b|\bCONFIRM\b|\bPROMPT\b)",
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, input_string, re.IGNORECASE):
                    logger.warning(
                        f"Potential security threat detected in parameterized query: {input_string[:100]}..."
                    )
                    return False

            # Parameterized query with no dangerous patterns is safe
            return True

        # Non-parameterized queries - check for SQL keywords and injection patterns
        sql_patterns = [
            r"(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b)",
            r"(\bEXEC\b|\bEXECUTE\b|\bCAST\b|\bDECLARE\b)",
            r"(\-\-|\#|\/\*|\*\/)",
            r"(\bor\s+1=1|\band\s+1=1)",
            r"(\bSCRIPT\b|\bJAVASCRIPT\b|\bVBSCRIPT\b)",
            r"(\bALERT\b|\bCONFIRM\b|\bPROMPT\b)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                logger.warning(
                    f"Potential security threat detected: {input_string[:100]}..."
                )
                return False

        return True

    @staticmethod
    def validate_sql_injection_risk(input_string: str, max_length: int = 1000) -> bool:
        """Check if a SQL query is safe from injection attacks.

        Returns True if the query appears safe, False if it contains dangerous patterns.
        This is different from validate_sql_injection which rejects all SQL keywords.
        """
        if not isinstance(input_string, str):
            return False

        if len(input_string) > max_length:
            return False

        # Check for dangerous SQL injection patterns
        dangerous_patterns = [
            r";\s*(DROP|DELETE|TRUNCATE|ALTER)\s+",  # Multiple statements with dangerous commands
            r"\b(OR|AND)\s+1\s*=\s*1\b",  # Classic injection pattern
            r"\bWHERE\s+1\s*=\s*1\b",  # WHERE 1=1 pattern
            r"\bUNION\s+(ALL\s+)?SELECT\b",  # UNION-based injection
            r"--\s*$",  # Comment at end (suspicious)
            r"/\*.*\*/",  # SQL comments
            r"\bEXEC(UTE)?\s*\(",  # Execute commands
            r"\bxp_\w+",  # Extended stored procedures
            r"\bsp_\w+",  # System stored procedures
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                logger.warning(
                    f"Potential security threat detected: {input_string[:100]}..."
                )
                return False

        return True

    @staticmethod
    def validate_password_strength(password: str) -> dict[str, Any]:
        """Validate password strength.

        Checks for minimum length and inclusion of uppercase, lowercase, digits, and special characters.
        Returns a dictionary with score and feedback.
        """
        if not isinstance(password, str):
            return {"score": 0, "feedback": "Password must be a string", "valid": False}

        score = 0
        feedback = []

        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password must be at least 8 characters long")

        if re.search(r"[A-Z]", password):
            score += 1
        else:
            feedback.append("Password must contain at least one uppercase letter")

        if re.search(r"[a-z]", password):
            score += 1
        else:
            feedback.append("Password must contain at least one lowercase letter")

        if re.search(r"[0-9]", password):
            score += 1
        else:
            feedback.append("Password must contain at least one digit")

        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1
        else:
            feedback.append("Password must contain at least one special character")

        is_acceptable = score >= 4
        return {
            "score": score,
            "feedback": feedback,
            "valid": is_acceptable,
            "is_acceptable": is_acceptable,  # Add for backward compatibility
        }

    @staticmethod
    def sanitize_html(
        html: str, allowed_tags: list[str] | None = None, max_length: int = 1000
    ) -> str:
        """Basic HTML sanitization.

        Strips potentially dangerous tags and attributes. For simplicity, this implementation
        removes script/style tags and any event-handler attributes.

        Args:
            html: The HTML string to sanitize
            allowed_tags: List of allowed HTML tags (optional)
            max_length: Maximum length of the cleaned HTML
        """
        if not isinstance(html, str):
            return ""

        # Remove script and style tags
        cleaned = re.sub(
            r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove on* event attributes
        cleaned = re.sub(
            r"\s+on\w+\s*=\s*['\"]?[^'\"]+['\"]?", "", cleaned, flags=re.IGNORECASE
        )

        # If allowed_tags is specified, remove all other tags
        if allowed_tags is not None:
            # Create pattern to match all tags except allowed ones
            allowed_pattern = "|".join(re.escape(tag) for tag in allowed_tags)
            if allowed_pattern:
                # Remove tags that are not in the allowed list
                cleaned = re.sub(
                    rf"<(?!/?(?:{allowed_pattern})\b)[^>]*>",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                )

        # Optionally truncate
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]

        return cleaned

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and allowed schemes.

        Args:
            url: The URL to validate

        Returns:
            True if valid and safe, False otherwise

        """
        if not isinstance(url, str):
            return False

        try:
            parsed = urlparse(url)
            allowed_schemes = {"http", "https", "postgresql", "redis", "mongodb"}
            if parsed.scheme not in allowed_schemes:
                logger.warning(f"Disallowed URL scheme: {parsed.scheme}")
                return False

            if not parsed.netloc:
                return False

            # Basic validation for localhost access
            if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                return True

            # For external URLs, could add whitelist validation here
            return True

        except Exception as e:
            logger.warning(f"URL validation error: {e}")
            return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation with length and format checks.

        Args:
            email: The email to validate

        Returns:
            True if valid, False otherwise

        """
        if not isinstance(email, str):
            return False

        if len(email) > 254:  # RFC 5321 limit
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    @staticmethod
    def validate_file_path(path: str) -> bool:
        """Validate file path for security.

        Args:
            path: The file path to validate

        Returns:
            True if safe, False if potentially dangerous

        """
        if not isinstance(path, str):
            return False

        # Prevent directory traversal
        if ".." in path or path.startswith(("/", "\\")):
            logger.warning(f"Directory traversal attempt detected: {path}")
            return False

        # Check for dangerous characters
        dangerous_chars = ["<", ">", "|", "&", ";", "`", "$", "\x00"]
        if any(char in path for char in dangerous_chars):
            logger.warning(f"Dangerous characters in path: {path}")
            return False

        return True

    @staticmethod
    def sanitize_input(input_data: Any, max_length: int = 1000) -> Any:
        """Sanitize input data to prevent XSS and injection attacks.

        Args:
            input_data: The data to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized data

        """
        if isinstance(input_data, str):
            # Remove null bytes and control characters
            sanitized = input_data.replace("\x00", "").strip()
            # Basic HTML escaping (could be enhanced with a proper HTML escaper)
            sanitized = (
                sanitized.replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
                .replace("/", "&#x2F;")
            )
            return sanitized[:max_length] if len(sanitized) > max_length else sanitized
        if isinstance(input_data, dict):
            return {
                k: SecurityValidator.sanitize_input(v, max_length)
                for k, v in input_data.items()
            }
        if isinstance(input_data, list):
            return [
                SecurityValidator.sanitize_input(item, max_length)
                for item in input_data
            ]
        return input_data


def security_check(func):
    """Decorator for security validation on function inputs.

    Args:
        func: The function to wrap

    Returns:
        Wrapped function with security validation

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Validate all string arguments
        for arg in args:
            if isinstance(arg, str):
                if not SecurityValidator.validate_sql_injection(arg):
                    logger.warning(
                        f"Potential security issue detected in argument: {arg[:50]}..."
                    )
                    raise ValueError(
                        "Invalid input detected - potential security threat"
                    )

        for key, value in kwargs.items():
            if isinstance(value, str):
                if not SecurityValidator.validate_sql_injection(value):
                    logger.warning(
                        f"Potential security issue detected in kwarg {key}: {value[:50]}..."
                    )
                    raise ValueError(
                        f"Invalid input detected in {key} - potential security threat"
                    )

        return func(*args, **kwargs)

    return wrapper


def validate_environment_variables():
    """Validate critical environment variables for security.

    Raises:
        EnvironmentError: If required variables are missing or invalid

    """
    required_vars = [
        "SECRET_KEY",
        "DATABASE_URL",
        "EMAG_API_BASE_URL",
        "EMAG_API_USERNAME",
        "EMAG_API_PASSWORD",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise OSError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Validate database URL format
    db_url = os.getenv("DATABASE_URL", "")
    if not SecurityValidator.validate_url(db_url):
        raise OSError("Invalid DATABASE_URL format")

    # Check for weak secret key (basic check)
    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        logger.warning("SECRET_KEY appears to be weak (less than 32 characters)")

    logger.info("Environment variables validation passed")
