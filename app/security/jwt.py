from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Sequence, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from passlib.context import CryptContext

from app.schemas.user import UserInDB

from ..core.config import settings
from .keys import get_key_manager

# Supported JWT algorithms (normalised to uppercase)
SUPPORTED_ALGORITHMS = sorted({alg.upper() for alg in settings.jwt_supported_algorithms})

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mock user for development
MOCK_USER = UserInDB(
    id=1,
    username="admin",
    email="admin@magflow.com",
    full_name="Admin User",
    is_active=True,
    is_superuser=True,
    hashed_password="$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"  # password = "secret"
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_str}/auth/login",
    auto_error=False,
)

# Key manager for JWT signing and verification
key_manager = get_key_manager()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def _normalize_alg(algorithm: Optional[str]) -> str:
    alg = (algorithm or settings.jwt_algorithm).upper()
    if alg not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported JWT algorithm '{alg}'. Supported algorithms: {', '.join(SUPPORTED_ALGORITHMS)}",
        )
    return alg


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
    algorithm: Optional[str] = None,
) -> str:
    """Create a JWT access token with the specified subject and claims.

    Args:
        subject: The subject of the token (usually a user ID or username)
        expires_delta: Optional timedelta for token expiration
        additional_claims: Additional claims to include in the token
        algorithm: JWT signing algorithm (default: settings.jwt_algorithm)

    Returns:
        str: Encoded JWT token

    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    # Use provided algorithm or default from settings
    alg = _normalize_alg(algorithm)

    # Prepare the token claims
    to_encode = {
        "iss": settings.jwt_issuer,
        "sub": str(subject),
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "nbf": int(now.timestamp() - 60),  # Not before 1 minute ago (clock skew)
        "jti": f"{now.timestamp()}-{subject}",
    }

    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)

    try:
        if alg == "HS256":
            return jwt.encode(
                to_encode,
                settings.secret_key,
                algorithm=alg,
                headers={"alg": alg, "typ": "JWT"},
            )

        key_manager.ensure_active_key(alg)
        key = key_manager.get_active_key(alg)
        headers = {"kid": key.kid, "alg": alg, "typ": "JWT"}
        return jwt.encode(
            to_encode,
            key.private_key,
            algorithm=alg,
            headers=headers,
        )
    except JWTError as e:
        raise ValueError(f"Failed to encode token: {e}") from e


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a refresh token for the specified subject.

    Args:
        subject: The subject of the token (usually a user ID or username)
        expires_delta: Optional timedelta for token expiration

    Returns:
        str: Encoded refresh token

    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return create_access_token(
        subject=subject,
        expires_delta=expires_delta,
        additional_claims={"type": "refresh"},
    )


def decode_token(
    token: str,
    algorithms: Optional[Sequence[str]] = None,
    options: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """Decode and verify a JWT token using the key manager.

    Args:
        token: The JWT token to decode
        algorithms: List of allowed algorithms (default: settings.jwt_algorithm)
        options: JWT decode options (default: verify signature, expiration, issuer)

    Returns:
        The decoded token payload

    Raises:
        JWTError: If the token is invalid, expired, or verification fails

    """
    if not token:
        raise JWTError("No token provided")

    # Set default algorithms if not provided
    if algorithms is None:
        algorithms = [settings.jwt_algorithm]

    normalized_algorithms = [alg.upper() for alg in algorithms]

    # Verify that all specified algorithms are supported
    unsupported_algs = set(normalized_algorithms) - set(SUPPORTED_ALGORITHMS)
    if unsupported_algs:
        raise JWTError(f"Unsupported JWT algorithms: {', '.join(unsupported_algs)}")

    # Get the key ID and algorithm from the token header
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")
        if alg:
            alg = alg.upper()

        if not alg:
            raise JWTError("Missing 'alg' in token header")

        # Use appropriate key based on algorithm
        # Determine verification key based on algorithm
        if alg == "HS256":
            # Use secret key for HMAC-SHA256
            verification_key = settings.secret_key
        else:
            # Use RSA keys for other algorithms
            if not kid:
                raise JWTError("Token header missing 'kid' claim for RSA algorithm")
            # Get the public key for verification
            try:
                key = key_manager.get_key(kid)
                verification_key = key.public_key
            except KeyError:
                raise JWTError(f"No public key found for kid: {kid}")

        # Set default options if not provided
        if options is None:
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "require": ["exp", "iat", "nbf", "iss", "aud"],
            }

        # Decode and verify the token
        payload = jwt.decode(
            token,
            verification_key,
            algorithms=normalized_algorithms,
            options=options,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )

        # Additional validation
        current_time = datetime.now(timezone.utc).timestamp()
        if "exp" in payload:
            if payload["exp"] < current_time - 60:  # 60 seconds leeway
                raise ExpiredSignatureError("Token has expired")

        # Check not before time
        if "nbf" in payload and payload["nbf"] > current_time + 60:  # 60 seconds leeway
            raise JWTClaimsError(f"Token not valid before {payload['nbf']}")

        # Check issued at time
        if "iat" in payload and payload["iat"] > current_time + 60:  # 60 seconds leeway
            raise JWTClaimsError("Token issued in the future")

        return payload

    except JWTError:
        # Re-raise JWT-specific exceptions
        raise
    except Exception as e:
        # Wrap other exceptions in JWTError
        raise JWTError(f"Token validation failed: {e}") from e


def get_user(db, username: str):
    # For development, return mock user
    if username == "admin":
        return MOCK_USER
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


async def get_current_user(
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme),
    ) -> UserInDB:
        """Dependency to get the current user from a JWT token.

        Args:
            request: The FastAPI request object
            token: The JWT token from the Authorization header

        Returns:
            UserInDB: The authenticated user

        Raises:
            HTTPException: If authentication fails

        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Decode and verify the JWT token
            payload = decode_token(token)
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # For development, return mock user if username is "admin"
            if username == "admin":
                return MOCK_USER

            # Look up user in database
            from app.db.session import AsyncSessionLocal
            from app.models.user import User as UserModel
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(UserModel).where(UserModel.email == username)
                )
                db_user = result.scalar_one_or_none()

                if not db_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                # Create UserInDB object from database user
                user_data = UserInDB(
                    id=db_user.id,
                    email=db_user.email,
                    full_name=db_user.full_name,
                    is_active=db_user.is_active,
                    is_superuser=db_user.is_superuser,
                    hashed_password=db_user.hashed_password,
                    created_at=db_user.created_at,
                    updated_at=db_user.updated_at,
                    last_login=db_user.last_login,
                    failed_login_attempts=db_user.failed_login_attempts,
                    avatar_url=db_user.avatar_url,
                )

                return user_data

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error",
            )


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Dependency to check if the current user is active.

    Args:
        current_user: The current authenticated user

    Returns:
        UserInDB: The active user

    Raises:
        HTTPException: If the user is inactive

    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_active_superuser(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Dependency to check if the current user is a superuser.

    Args:
        current_user: The current authenticated user

    Returns:
        UserInDB: The superuser

    Raises:
        HTTPException: If the user is not a superuser

    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
