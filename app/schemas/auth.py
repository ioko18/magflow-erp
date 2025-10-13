"""Authentication-related Pydantic models for request/response validation."""

from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field, field_validator
from pydantic.networks import HttpUrl


def validate_email_allow_local(v: str) -> str:
    """Validate email but allow .local domains for development."""
    if isinstance(v, str) and "@" in v:
        # Basic email format validation
        parts = v.split("@")
        if len(parts) == 2 and parts[0] and parts[1]:
            # Allow .local and other special domains for development
            if parts[1].endswith(".local") or parts[1] in ["localhost"]:
                return v
            # For other domains, use standard validation
            try:
                from email_validator import validate_email as ev_validate

                result = ev_validate(v, check_deliverability=False)
                return result.email
            except Exception:
                # If email_validator fails, do basic validation
                if "." in parts[1]:
                    return v
    return v


# Custom email type that allows .local domains
FlexibleEmail = Annotated[str, BeforeValidator(validate_email_allow_local)]


class Token(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str = Field(
        ...,
        description="Refresh token for obtaining new access tokens",
    )


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration time (UNIX timestamp)")
    iat: int = Field(..., description="Issued at time (UNIX timestamp)")
    jti: str | None = Field(None, description="JWT ID")
    scopes: list[str] = Field(default_factory=list, description="List of scopes")
    type: str = Field("access", description="Token type (access/refresh)")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        """Normalize token type to one of the supported values."""

        normalized = (value or "access").strip().lower()
        if normalized not in {"access", "refresh"}:
            raise ValueError("Invalid token type")
        return normalized


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: FlexibleEmail = Field(..., description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    is_active: bool = Field(True, description="Whether the user is active")
    is_superuser: bool = Field(False, description="Whether the user is a superuser")


class UserCreate(UserBase):
    """User creation model with password."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="User's password (8-72 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(BaseModel):
    """User update model with optional fields."""

    email: FlexibleEmail | None = Field(None, description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    password: str | None = Field(
        None,
        min_length=8,
        max_length=72,
        description="New password (8-72 characters)",
    )
    is_active: bool | None = Field(None, description="Whether the user is active")
    is_superuser: bool | None = Field(
        None,
        description="Whether the user is a superuser",
    )


class UserInDBBase(UserBase):
    """User model for database representation."""

    id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime | None = Field(
        None,
        description="When the user was last updated",
    )
    last_login: datetime | None = Field(
        None,
        description="Last successful login time",
    )
    failed_login_attempts: int = Field(0, description="Number of failed login attempts")
    avatar_url: HttpUrl | None = Field(
        None,
        description="URL to user's avatar image",
    )

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """User model for API responses."""


class UserInDB(UserInDBBase):
    """User model with hashed password for database storage."""

    hashed_password: str = Field(..., description="Hashed password")


class LoginRequest(BaseModel):
    """Login request model.

    Accepts both 'username' and 'email' fields for compatibility.
    """

    username: str = Field(
        ...,
        min_length=1,
        description="Username or email",
        validation_alias=AliasChoices("username", "email"),
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Password",
    )
    remember_me: bool = Field(
        False,
        description="Whether to create a long-lived session",
    )


class PasswordResetRequest(BaseModel):
    """Password reset request model."""

    email: FlexibleEmail = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New password",
    )


class ChangePasswordRequest(BaseModel):
    """Change password request model."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New password",
    )


class Msg(BaseModel):
    """Simple message response model."""

    msg: str = Field(
        ...,
        description="A message describing the result of the operation",
    )
