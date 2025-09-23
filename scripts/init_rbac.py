"""Script to initialize default roles and permissions."""

import asyncio
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.role import Role, Permission
from app.security.rbac import Permission as PermissionEnum, DEFAULT_ROLES

logger = logging.getLogger(__name__)


async def create_default_permissions(session: AsyncSession) -> List[Permission]:
    """Create default permissions if they don't exist."""
    permissions = []

    for perm_enum in PermissionEnum:
        # Check if permission already exists
        result = await session.execute(
            select(Permission).where(Permission.name == perm_enum.value)
        )
        existing = result.scalars().first()

        if existing:
            permissions.append(existing)
        else:
            permission = Permission(
                name=perm_enum.value,
                description=f"Permission to {perm_enum.value.replace(':', ' ')}"
            )
            session.add(permission)
            permissions.append(permission)

    await session.commit()
    return permissions


async def create_default_roles(session: AsyncSession, permissions: List[Permission]) -> List[Role]:
    """Create default roles with their permissions."""
    roles = []

    # Create permission lookup dict
    perm_dict = {p.name: p for p in permissions}

    for role_name, role_config in DEFAULT_ROLES.items():
        # Check if role already exists
        result = await session.execute(
            select(Role).where(Role.name == role_name)
        )
        existing = result.scalars().first()

        if existing:
            roles.append(existing)
            continue

        role = Role(
            name=role_name,
            description=role_config["description"],
            is_active=role_config["is_active"]
        )

        # Add permissions to role
        for perm_name in role_config["permissions"]:
            if perm_name in perm_dict:
                role.permissions.append(perm_dict[perm_name])

        session.add(role)
        roles.append(role)

    await session.commit()
    return roles


async def initialize_rbac():
    """Initialize RBAC system with default roles and permissions."""
    logger.info("Initializing RBAC system...")

    async with AsyncSessionFactory() as session:
        try:
            # Create permissions
            logger.info("Creating default permissions...")
            permissions = await create_default_permissions(session)

            # Create roles
            logger.info("Creating default roles...")
            roles = await create_default_roles(session, permissions)

            logger.info(f"RBAC initialization completed: {len(permissions)} permissions, {len(roles)} roles")

        except Exception as e:
            logger.error(f"Failed to initialize RBAC: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    """Run RBAC initialization."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(initialize_rbac())
