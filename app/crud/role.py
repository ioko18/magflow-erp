"""CRUD operations for roles and permissions."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.role import Permission, Role
from app.schemas.role import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """CRUD operations for Permission model."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Permission | None:
        """Get a permission by name.

        Args:
            db: Database session
            name: Name of the permission to retrieve

        Returns:
            The permission if found, None otherwise

        """
        result = await db.execute(select(Permission).filter(Permission.name == name))
        return result.scalars().first()

    async def get_multi_by_names(
        self,
        db: AsyncSession,
        names: list[str],
    ) -> list[Permission]:
        """Get multiple permissions by names.

        Args:
            db: Database session
            names: List of permission names to retrieve

        Returns:
            List of permissions

        """
        result = await db.execute(select(Permission).filter(Permission.name.in_(names)))
        return result.scalars().all()


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """CRUD operations for Role model."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Role | None:
        """Get a role by name.

        Args:
            db: Database session
            name: Name of the role to retrieve

        Returns:
            The role if found, None otherwise

        """
        result = await db.execute(select(Role).filter(Role.name == name))
        return result.scalars().first()

    async def get_active_roles(self, db: AsyncSession) -> list[Role]:
        """Get all active roles.

        Args:
            db: Database session

        Returns:
            List of active roles

        """
        result = await db.execute(
            select(Role).filter(Role.is_active == True),  # noqa: E712
        )
        return result.scalars().all()

    async def get_role_with_permissions(
        self,
        db: AsyncSession,
        *,
        role_id: int,
    ) -> Role | None:
        """Get a role with its permissions loaded.

        Args:
            db: Database session
            role_id: ID of the role to retrieve

        Returns:
            The role with permissions if found, None otherwise

        """
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .filter(Role.id == role_id),
        )
        return result.scalars().first()


# Create singleton instances
permission = CRUDPermission(Permission)
role = CRUDRole(Role)
