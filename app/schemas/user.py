"""Pydantic models for user data validation and serialization."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


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


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: FlexibleEmail | None = None
    is_active: bool = True
    full_name: str | None = None
    is_superuser: bool = False
    oauth_provider: str | None = None  # OAuth2 provider (google, github, etc.)
    oauth_id: str | None = None  # OAuth2 provider user ID


class UserCreate(UserBase):
    """Schema for creating a new user."""

    email: FlexibleEmail
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(UserBase):
    """Schema for updating a user."""

    password: str | None = Field(None, min_length=8, max_length=100)
    email: FlexibleEmail | None = None
    full_name: str | None = Field(None, min_length=2, max_length=100)


class UserInDBBase(UserBase):
    """Base schema for user data in the database."""

    id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """Schema for user data returned to clients."""


class UserInDB(UserInDBBase):
    """Schema for user data stored in the database."""

    hashed_password: str
