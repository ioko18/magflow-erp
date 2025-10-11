"""Test authentication endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_access_token
from app.security.jwt import oauth2_scheme

router = APIRouter()


@router.post("/test-token", response_model=dict[str, Any])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate a test token for development."""
    # In a real app, you would validate the username and password against your database
    if form_data.username == "admin" and form_data.password == "secret":
        access_token = create_access_token(
            subject=form_data.username,
            expires_delta=settings.access_token_expire_minutes,
        )
        return {"access_token": access_token, "token_type": "bearer"}

    # For development, always return a valid token
    if settings.ENVIRONMENT == "development":
        access_token = create_access_token(
            subject="admin",
            expires_delta=settings.access_token_expire_minutes,
        )
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/test-auth")
async def test_auth(token: str = Depends(oauth2_scheme)):
    """Test authentication."""
    return {
        "message": "You are authenticated!",
        "token": token,
    }
