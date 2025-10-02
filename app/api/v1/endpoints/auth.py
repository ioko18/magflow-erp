"""Authentication endpoints for API v1.

These endpoints provide a thin wrapper around the core security helpers so the
test-suite can exercise the typical login → fetch profile → refresh token flow
using the `/api/v1/auth/*` routes.
"""

from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models import User
from app.schemas.auth import LoginRequest, Token, User as UserSchema


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

router = APIRouter()
users_router = APIRouter()


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as exc:  # pragma: no cover - defensive branch
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await _get_user_by_email(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def _extract_login_credentials(
    request: Request, payload: LoginRequest | None
) -> tuple[str | None, str | None]:
    """Normalize login credentials from either JSON payloads or form submissions."""

    if payload is not None:
        return payload.username, payload.password

    content_type = request.headers.get("content-type", "").lower()

    if content_type.startswith(
        "application/x-www-form-urlencoded"
    ) or content_type.startswith("multipart/form-data"):
        form = await request.form()
        return form.get("username"), form.get("password")

    try:
        body = await request.json()
    except Exception:  # pragma: no cover - malformed or empty bodies fall through
        body = None

    if isinstance(body, dict):
        return body.get("username"), body.get("password")

    return None, None


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    payload: LoginRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate a user and issue access and refresh tokens."""

    username, password = await _extract_login_credentials(request, payload)

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    user = await _get_user_by_email(db, username)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        subject=user.email,
        expires_delta=refresh_token_expires,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    refresh_token: str = Depends(oauth2_scheme),
) -> Token:
    """Rotate the access token using a refresh token."""

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required",
        )

    try:
        token_payload = verify_token(refresh_token, is_refresh=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = token_payload.sub

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_access_token = create_access_token(
        subject=subject,
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(
        subject=subject,
        expires_delta=refresh_token_expires,
    )

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@users_router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(_get_current_user)) -> UserSchema:
    return UserSchema.model_validate(current_user)


@users_router.post(
    "/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED
)
async def register_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    existing = await _get_user_by_email(db, form_data.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    user = User(
        email=form_data.username,
        hashed_password=get_password_hash(form_data.password),
        full_name=form_data.username,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserSchema.model_validate(user)


# uncompyle6 version 3.9.2
# Python bytecode version base 3.11 (3495)
# Decompiled from: Python 3.13.2 (main, Mar 15 2025, 22:36:18) [Clang 14.0.0 (clang-1400.0.29.202)]
# Embedded file name: /Users/macos/anaconda3/envs/MagFlow/app/api/v1/endpoints/auth.py
# Compiled at: 2025-09-19 00:52:20
# Size of source mod 2**32: 122 bytes
