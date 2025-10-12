#!/usr/bin/env python3
"""Create admin user with direct SQL."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.core.database import get_async_session
from app.core.security import get_password_hash


async def create_admin_user():
    """Create admin user using direct SQL."""
    print("🔧 Creating admin user with SQL...")

    try:
        async for session in get_async_session():
            # Check if admin user exists
            result = await session.execute(
                text("SELECT COUNT(*) FROM app.users WHERE email = :email"),
                {"email": "admin@magflow.local"},
            )
            user_count = result.scalar()

            if user_count > 0:
                print("✅ Admin user already exists")
                return

            # Create hashed password
            hashed_password = get_password_hash("secret")

            # Insert admin user
            await session.execute(
                text(
                    """
                    INSERT INTO app.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
                    VALUES (:email, :password, :name, :is_superuser, :is_active, :verified)
                """
                ),
                {
                    "email": "admin@magflow.local",
                    "password": hashed_password,
                    "name": "Admin User",
                    "is_superuser": True,
                    "is_active": True,
                    "verified": True,
                },
            )

            # Create admin role if it doesn't exist
            await session.execute(
                text(
                    """
                    INSERT INTO app.roles (name, description, is_system_role)
                    VALUES (:name, :description, :is_system_role)
                    ON CONFLICT (name) DO NOTHING
                """
                ),
                {
                    "name": "admin",
                    "description": "Administrator role",
                    "is_system_role": True,
                },
            )

            # Get user and role IDs
            user_result = await session.execute(
                text("SELECT id FROM app.users WHERE email = :email"),
                {"email": "admin@magflow.local"},
            )
            user_id = user_result.scalar()

            role_result = await session.execute(
                text("SELECT id FROM app.roles WHERE name = :name"), {"name": "admin"}
            )
            role_id = role_result.scalar()

            # Assign role to user
            if user_id and role_id:
                await session.execute(
                    text(
                        """
                        INSERT INTO app.user_roles (user_id, role_id)
                        VALUES (:user_id, :role_id)
                        ON CONFLICT (user_id, role_id) DO NOTHING
                    """
                    ),
                    {"user_id": user_id, "role_id": role_id},
                )

            await session.commit()

            print("✅ Admin user created successfully!")
            print("   Email: admin@magflow.local")
            print("   Password: secret")
            print("   Role: admin")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
