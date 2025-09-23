#!/usr/bin/env python3
"""Create test user for authentication testing."""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, app_dir)

# Add user site-packages to path
user_site = "/Users/macos/Library/Python/3.9/lib/python/site-packages"
sys.path.insert(0, user_site)

try:
    import asyncpg
    import sqlalchemy
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from passlib.hash import bcrypt

    from app.core.config import settings

    async def create_test_user():
        """Create test user in database using direct SQL."""
        # Database connection string
        db_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

        # Create async engine
        engine = create_async_engine(db_url, echo=False)

        async with engine.connect() as conn:
            # Set search path to ensure we're working in the right schema
            await conn.execute(text(f'SET search_path TO {settings.DB_SCHEMA}, public'))

            # Create admin user with hashed password
            hashed_password = bcrypt.hash("secret")

            # Insert user directly using SQL
            result = await conn.execute(text("""
                INSERT INTO app.users (email, hashed_password, full_name, is_superuser, email_verified)
                VALUES (:email, :password, :name, :is_superuser, :verified)
                ON CONFLICT (email) DO UPDATE SET
                    hashed_password = EXCLUDED.hashed_password,
                    full_name = EXCLUDED.full_name,
                    is_superuser = EXCLUDED.is_superuser,
                    email_verified = EXCLUDED.email_verified
                RETURNING id
            """), {
                "email": "admin@magflow.local",
                "password": hashed_password,
                "name": "Test Admin User",
                "is_superuser": True,
                "verified": True
            })

            user = result.fetchone()
            user_id = user.id if user else None

            # Create admin role if it doesn't exist
            await conn.execute(text("""
                INSERT INTO app.roles (name, description, is_active)
                VALUES (:name, :description, :is_active)
                ON CONFLICT (name) DO NOTHING
            """), {
                "name": "admin",
                "description": "Administrator role",
                "is_active": True
            })

            # Get role ID
            result = await conn.execute(text("""
                SELECT id FROM app.roles WHERE name = :name
            """), {"name": "admin"})
            role = result.fetchone()
            role_id = role.id if role else None

            # Assign role to user if both exist
            if user_id and role_id:
                await conn.execute(text("""
                    INSERT INTO app.user_role (user_id, role_id)
                    VALUES (:user_id, :role_id)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                """), {
                    "user_id": user_id,
                    "role_id": role_id
                })

            await conn.commit()

            # Verify user was created
            result = await conn.execute(text("""
                SELECT u.email, u.is_superuser, r.name as role_name
                FROM app.users u
                LEFT JOIN app.user_role ur ON u.id = ur.user_id
                LEFT JOIN app.roles r ON ur.role_id = r.id
                WHERE u.email = :email
            """), {"email": "admin@magflow.local"})

            user_info = result.fetchone()

            if user_info:
                print("✅ Test user created successfully!")
                print("   Email: admin@magflow.local")
                print("   Password: secret")
                print("   Is Superuser: {}".format(user_info.is_superuser))
                print("   Role: {}".format(user_info.role_name or "None"))
            else:
                print("❌ Failed to create or verify user")

        await engine.dispose()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(create_test_user())

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please ensure all dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
