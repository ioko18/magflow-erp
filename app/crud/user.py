"""CRUD operations for users."""

from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            db: Database session
            email: Email of the user to retrieve

        Returns:
            The user if found, None otherwise

        """
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user with hashed password.

        Args:
            db: Database session
            obj_in: User creation schema with email and password

        Returns:
            The created user

        """
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_superuser=obj_in.is_superuser,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]],
    ) -> User:
        """Update a user's information.

        Args:
            db: Database session
            db_obj: The user model instance to update
            obj_in: The data to update the user with

        Returns:
            The updated user

        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate a user.

        Args:
            db: Database session
            email: User's email
            password: Plain text password

        Returns:
            The authenticated user if successful, None otherwise

        """
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Check if a user is active."""
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        """Check if a user is a superuser."""
        return user.is_superuser


# Create a singleton instance
user = CRUDUser(User)
