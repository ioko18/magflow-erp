from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.config import settings
from ..security.jwt import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    verify_password,
    get_password_hash,
    decode_token,
)
from ..security.schemas import Token, User, UserInDB

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests.

    - **username**: Username for authentication
    - **password**: Password for authentication

    Returns:
    - **access_token**: JWT access token (RS256)
    - **refresh_token**: JWT refresh token (long-lived)
    - **token_type**: Always "bearer"
    - **expires_in**: Token expiration in seconds
    """
    # In a real app, you would validate the username and password against your database
    # For now, we'll use a hardcoded user
    fake_db: Dict[str, Dict[str, Any]] = {
        "admin": {
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "Admin User",
            "hashed_password": get_password_hash("secret"),
            "is_active": True,
            "role": "admin",
        }
    }

    user_data = fake_db.get(form_data.username)
    if not user_data or not verify_password(
        form_data.password, user_data["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        subject=user_data["username"],
        expires_delta=access_token_expires,
        additional_claims={
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "type": "access",
        },
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        subject=user_data["username"],
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    # Log the login attempt (in a real app, you might want to store this in a database)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"User {user_data['username']} logged in from {request.client.host}",
        extra={"user": user_data["username"], "ip": request.client.host},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    refresh_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Refresh an access token using a refresh token.

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
        #     expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        # )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Or new_refresh_token if rotating
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
    """
    Get current user information.

    - **Requires authentication**
    """
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Log out the current user (invalidate token).

    In a real implementation, you would add the token to a blacklist
    or mark it as revoked in your database.
    """
    # In a real app, you would add the token to a blacklist
    # token = request.headers.get("Authorization").split(" ")[1]
    # await add_token_to_blacklist(token)

    return {"message": "Successfully logged out"}
