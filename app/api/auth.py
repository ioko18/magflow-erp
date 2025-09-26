import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_async_session
from ..db.models import User as UserModel
from ..middleware.correlation_id import get_correlation_id
from ..schemas.auth import LoginRequest, Token, User, UserInDB
from ..services.cache_service import CacheManager, get_cache_service
from ..services.rbac_service import AuditService

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_str}/auth/login",
    auto_error=False,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes,
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access",
        "email": str(subject),
        "full_name": "Test User",
        "role": "admin",
        "roles": ["admin"],
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    return jwt.encode(
        to_encode,
        settings.REFRESH_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
    cache: CacheManager = Depends(get_cache_service),
) -> UserInDB:
    """Get current active user from JWT token and database.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        UserInDB: The authenticated user from database

    Raises:
        HTTPException: If authentication fails or user not found

    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode and verify the token
        payload = decode_token(token)
        username: str = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Try to get user from cache first
        cache_key = f"user:{username}"
        cached_user_data = await cache.get(cache_key, "users")

        if cached_user_data:
            # Return cached user data
            return UserInDB(**cached_user_data)

        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.email == username))
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Check if user is active
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        # Create UserInDB object from database data
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

        # Cache user data for future requests (10 minutes)
        await cache.set(cache_key, user_data.dict(), ttl=600, namespace="users")

        return user_data

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
    cache: CacheManager = Depends(get_cache_service),
) -> Dict[str, Any]:
    """OAuth2 compatible token login, get an access token for future requests.

    - **username**: Username for authentication
    - **password**: Password for authentication

    Returns:
      - **access_token**: JWT access token (RS256)
      - **refresh_token**: JWT refresh token (long-lived)
      - **token_type**: Always "bearer"
      - **expires_in**: Token expiration in seconds

    """
    try:
        logger.info("Authentication endpoint called for user: %s", login_data.username)

        # Initialize audit service for logging
        audit_service = AuditService(db)

        # Log login attempt
        await audit_service.log_action(
            user=None,
            action="login_attempt",
            resource="auth",
            details={"email": login_data.username, "ip": request.client.host},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=False,  # Will be updated on successful login
        )

        # Try to get user from cache first
        cache_key = f"user:{login_data.username}"
        cached_user_data = await cache.get(cache_key, "users")

        if cached_user_data:
            # Use cached user data
            user_obj = UserInDB(**cached_user_data)
            logger.info("User found in cache: %s", user_obj.email)
        else:
            # Get user from database by email using SQLAlchemy model
            result = await db.execute(
                select(UserModel).where(UserModel.email == login_data.username),
            )
            db_user = result.scalar_one_or_none()
            logger.debug("Database query result: %s", db_user)

            if db_user:
                # Create a user object from database data
                user_obj = UserInDB(
                    id=db_user.id,
                    email=db_user.email,
                    hashed_password=db_user.hashed_password,
                    full_name=db_user.full_name,
                    is_active=db_user.is_active,
                    is_superuser=db_user.is_superuser,
                    created_at=db_user.created_at,
                    updated_at=db_user.updated_at,
                    last_login=db_user.last_login,
                    failed_login_attempts=db_user.failed_login_attempts,
                    avatar_url=db_user.avatar_url,
                )

                # Cache user data for future requests (10 minutes)
                await cache.set(cache_key, user_obj.dict(), ttl=600, namespace="users")
                logger.info("User found and cached: %s", user_obj.email)
            else:
                user_obj = None
                logger.warning("No user found with email: %s", login_data.username)

        # Check if user exists
        if not user_obj:
            logger.warning(
                "User not found, returning 401 for user: %s",
                login_data.username,
            )
            await audit_service.log_action(
                user=None,
                action="login_failed",
                resource="auth",
                details={"reason": "user_not_found", "email": login_data.username},
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                success=False,
            )
            correlation_id = get_correlation_id()
            headers = {"WWW-Authenticate": "Bearer"}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers=headers,
            )

        # Check if user is active
        if not user_obj.is_active:
            logger.warning(
                "User inactive, returning 400 for user: %s",
                login_data.username,
            )
            await audit_service.log_action(
                user=None,  # We don't have the user object from cache
                action="login_failed",
                resource="auth",
                details={"reason": "user_inactive"},
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        # Verify password
        if not verify_password(login_data.password, user_obj.hashed_password):
            logger.warning("Password verification failed for user: %s", user_obj.email)

            # If we got user from cache, we need to get the actual user from DB to update failed attempts
            if cached_user_data:
                result = await db.execute(
                    select(UserModel).where(UserModel.email == login_data.username),
                )
                db_user = result.scalar_one_or_none()
                if db_user:
                    # Increment failed login attempts
                    db_user.failed_login_attempts += 1
                    await db.commit()

                    # Invalidate user cache since data changed
                    await cache.invalidate_user_cache(db_user.id)

            await audit_service.log_action(
                user=None,  # We don't have the user object from cache
                action="login_failed",
                resource="auth",
                details={"reason": "invalid_password", "email": login_data.username},
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                success=False,
            )
            correlation_id = get_correlation_id()
            headers = {"WWW-Authenticate": "Bearer"}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers=headers,
            )

        # Password verified successfully
        logger.info("Password verification successful for user: %s", user_obj.email)

        # Get the actual user from database to update login info
        result = await db.execute(
            select(UserModel).where(UserModel.email == login_data.username),
        )
        db_user = result.scalar_one_or_none()

        if db_user:
            # Reset failed login attempts
            db_user.failed_login_attempts = 0
            db_user.last_login = datetime.utcnow()
            await db.commit()

            # Invalidate user cache since data changed
            await cache.invalidate_user_cache(db_user.id)

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            subject=user_obj.email,
            expires_delta=access_token_expires,
        )
        logger.info("Access token created successfully for user: %s", user_obj.email)

        # Create refresh token
        refresh_token = create_refresh_token(
            subject=user_obj.email,
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )
        logger.info("Refresh token created successfully for user: %s", user_obj.email)

        # Log successful login
        await audit_service.log_action(
            user=db_user,
            action="login_success",
            resource="auth",
            details={"email": user_obj.email},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=True,
        )

        logger.info("Authentication successful for user: %s", user_obj.email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other exceptions and log them
        logger.error("Unexpected error in auth endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/simple-login")
async def simple_login_test(
    request: Request,
    login_data: LoginRequest,
) -> Dict[str, Any]:
    """Simple synchronous login test - no database, no dependencies."""
    print(f"🚀 SIMPLE LOGIN CALLED with username: {login_data.username}")

    # Create a fake successful response
    if login_data.username == "admin@magflow.local" and login_data.password == "secret":
        return {
            "access_token": "fake_access_token",
            "refresh_token": "fake_refresh_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "message": "Login successful (fake)",
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/test-db")
async def test_database(
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Test database connection."""
    try:
        # Simple query to test database connection
        result = await db.execute(
            text(f"SELECT COUNT(*) FROM {settings.DB_SCHEMA}.users"),
        )
        user_count = result.scalar()
        return {"status": "success", "users_count": user_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    refresh_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Refresh an access token using a refresh token.

    - **refresh_token**: The refresh token received during login

    Returns:
    - **access_token**: New JWT access token
    - **refresh_token**: New refresh token (optional, if rotating refresh tokens is enabled)
    - **token_type**: Always "bearer"
    - **expires_in**: Token expiration in seconds

    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required",
        )

    try:
        # Verify the refresh token
        payload = decode_token(refresh_token)

        # Ensure this is a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )

        # In a real app, you would validate the user still exists and is active
        username = payload.get("sub")

        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            subject=username,
            expires_delta=access_token_expires,
            additional_claims={
                "type": "access",
            },
        )

        # Optionally rotate refresh tokens (uncomment if you want to rotate refresh tokens)
        # new_refresh_token = create_refresh_token(
        #     subject=username,
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserInDB:
    """Get current user information.

    - **Requires authentication**
    """
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, str]:
    """Log out the current user (invalidate token).

    In a real implementation, you would add the token to a blacklist
    or mark it as revoked in your database.
    """
    # In a real app, you would add the token to a blacklist
    # token = request.headers.get("Authorization").split(" ")[1]
    # await add_token_to_blacklist(token)


@router.get("/cache/stats")
async def get_cache_stats(
    cache: CacheManager = Depends(get_cache_service),
) -> Dict[str, Any]:
    """Get cache service statistics.

    Returns cache connection status, memory usage, and other metrics.
    """
    stats = await cache.cache.get_cache_stats()
    return stats


@router.delete("/cache/user/{user_id}")
async def invalidate_user_cache(
    user_id: int,
    cache: CacheManager = Depends(get_cache_service),
) -> Dict[str, str]:
    """Invalidate all cache entries for a specific user.

    - **user_id**: User ID to invalidate cache for
    """
    success = await cache.invalidate_user_cache(user_id)
    if success:
        return {"message": f"Cache invalidated for user {user_id}"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to invalidate user cache",
    )


@router.delete("/cache/flush")
async def flush_cache(
    cache: CacheManager = Depends(get_cache_service),
) -> Dict[str, str]:
    """Flush all cache entries. Use with caution!"""
    # This would require implementing a flush method in CacheService
    # For now, return a message indicating this feature is not implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Cache flush not implemented",
    )
