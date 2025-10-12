#!/usr/bin/env python3
"""Create admin user for MagFlow ERP."""

import asyncio
import sys

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User


async def create_admin():
    """Create admin user if not exists."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin exists
            result = await session.execute(
                select(User).where(User.email == 'admin@magflow.com')
            )
            user = result.scalar_one_or_none()

            if user:
                print('✅ Admin user already exists: admin@magflow.com')
                print('   Password: admin123')
                return

            # Create admin role if not exists
            role_result = await session.execute(
                select(Role).where(Role.name == 'admin')
            )
            role = role_result.scalar_one_or_none()

            if not role:
                role = Role(
                    name='admin',
                    description='Administrator role',
                    is_system_role=True
                )
                session.add(role)
                await session.flush()
                print('✅ Created admin role')

            # Create admin user
            user = User(
                email='admin@magflow.com',
                hashed_password=get_password_hash('admin123'),
                full_name='Admin User',
                is_active=True,
                is_superuser=True,
                email_verified=True
            )
            session.add(user)
            await session.commit()

            print('✅ Admin user created successfully!')
            print('   Email: admin@magflow.com')
            print('   Password: admin123')
            print('')
            print('🔐 You can now login at: http://localhost:5173')

        except Exception as e:
            print(f'❌ Error creating admin user: {e}')
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(create_admin())
