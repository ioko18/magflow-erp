"""Pydantic models for user data validation and serialization."""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: Optional[EmailStr] = None
    is_active: bool = True
    full_name: Optional[str] = None
    is_superuser: bool = False

class UserCreate(UserBase):
    """Schema for creating a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)

    @validator('password')
    def password_must_be_strong(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

class UserUpdate(UserBase):
    """Schema for updating a user."""
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)

class UserInDBBase(UserBase):
    """Base schema for user data in the database."""
    id: Optional[int] = None

    class Config:
        orm_mode = True

class User(UserInDBBase):
    """Schema for user data returned to clients."""
    pass

class UserInDB(UserInDBBase):
    """Schema for user data stored in the database."""
    hashed_password: str
