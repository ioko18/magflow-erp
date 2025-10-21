from datetime import UTC, datetime
from enum import Enum

from fastapi import Form
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
)


class TokenType(str, Enum):
    BEARER = "bearer"
    REFRESH = "refresh"


class TokenBase(BaseModel):
    """Base token schema"""

    token: str
    token_type: TokenType
    expires_in: int = Field(default=3600, description="Token lifetime in seconds")
    refresh_token: str | None = None
    refresh_token_expires_in: int | None = Field(
        default=2592000,
        description="Refresh token lifetime in seconds",  # 30 days
    )


class Token(BaseModel):
    """JWT token response schema"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        default=1800,
        description="Access token lifetime in seconds",
    )


class TokenData(BaseModel):
    """Token payload schema"""

    sub: str = Field(..., description="Subject (user identifier)")
    username: str
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True
    exp: datetime
    iat: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    jti: str = Field(..., description="JWT ID")

    model_config = ConfigDict()

    @field_serializer("exp", "iat", when_used="json")
    def serialize_epoch(self, value: datetime, _info) -> int:
        return int(value.timestamp())


class UserRole(str, Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class RateLimitTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        example="johndoe",
    )
    email: EmailStr = Field(..., example="user@example.com")
    full_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        example="John Doe",
    )
    avatar_url: HttpUrl | None = Field(
        None,
        description="URL to user's avatar image",
    )
    is_active: bool = Field(
        default=True,
        description="Designates whether this user should be treated as active",
    )
    is_verified: bool = Field(
        default=False,
        description="Designates whether this user has verified their email",
    )
    role: UserRole = Field(default=UserRole.USER, description="User's role for RBAC")
    rate_limit_tier: RateLimitTier = Field(
        default=RateLimitTier.FREE,
        description="Rate limiting tier",
    )


class UserInDB(UserBase):
    """User database schema"""

    id: int
    hashed_password: str
    last_login: datetime | None = None
    failed_login_attempts: int = 0
    last_failed_login: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.isoformat()

    @field_serializer(
        "last_login",
        "last_failed_login",
        "password_changed_at",
        when_used="json",
    )
    def serialize_optional_datetime(
        self, value: datetime | None, _info
    ) -> str | None:
        return value.isoformat() if value else None


class User(UserBase):
    """User response schema"""

    id: int
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.isoformat()

    @field_serializer("last_login", when_used="json")
    def serialize_optional_datetime(
        self, value: datetime | None, _info
    ) -> str | None:
        return value.isoformat() if value else None


class UserCreate(BaseModel):
    """User creation schema"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        example="johndoe",
    )
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description=(
            "Must be at least 12 characters long and contain at least one uppercase "
            "letter, one lowercase letter, one number and one special character"
        ),
        example="Str0ngP@ssword!",
    )
    full_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        example="John Doe",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """User update schema"""

    email: EmailStr | None = None
    full_name: str | None = None
    avatar_url: HttpUrl | None = None
    current_password: str | None = None
    new_password: str | None = Field(
        None,
        min_length=12,
        max_length=128,
        description="New password (if changing)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v, values):
        if v is not None and "current_password" not in values:
            raise ValueError("Current password is required to set a new password")
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""

    tier: RateLimitTier
    requests_per_minute: int
    burst_capacity: int

    model_config = ConfigDict(from_attributes=True)


class OAuth2TokenRequestForm:
    """OAuth2 token request form"""

    def __init__(
        self,
        grant_type: str = Form(..., regex="password|refresh_token|client_credentials"),
        username: str | None = Form(None),
        password: str | None = Form(None),
        refresh_token: str | None = Form(None),
        scope: str = Form(""),
        client_id: str | None = Form(None),
        client_secret: str | None = Form(None),
    ):
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.refresh_token = refresh_token
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret
