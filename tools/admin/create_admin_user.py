#!/usr/bin/env python3
"""Create admin user for testing authentication."""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, app_dir)

# Add user site-packages to path
user_site = "/Users/macos/Library/Python/3.9/lib/python/site-packages"
sys.path.insert(0, user_site)

try:
    from passlib.hash import bcrypt
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    async def create_admin_user():
        """Create admin user in database."""
        # Database connection string
        db_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

        # Create async engine
        engine = create_async_engine(db_url, echo=False)

        async with engine.connect() as conn:
            # Set search path
            await conn.execute(text(f'SET search_path TO {settings.DB_SCHEMA}, public'))

            # Create admin user
            hashed_password = bcrypt.hash("secret")

            # Check if user already exists
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM app.users WHERE email = 'admin@magflow.local'
            """))
            user_exists = result.scalar()

            if user_exists:
                print("✅ Admin user already exists")
                return

            # Insert admin user
            await conn.execute(text("""
                INSERT INTO app.users (
                    email,
                    hashed_password,
                    full_name,
                    is_superuser,
                    email_verified
                )
                VALUES (
                    :email,
                    :password,
                    :name,
                    :is_superuser,
                    :verified
                )
            """), {
                "email": "admin@magflow.local",
                "password": hashed_password,
                "name": "Admin User",
                "is_superuser": True,
                "verified": True
            })

            # Create admin role
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
                SELECT id FROM app.roles WHERE name = 'admin'
            """))
            role_id = result.scalar()

            # Get user ID
            result = await conn.execute(text("""
                SELECT id FROM app.users WHERE email = 'admin@magflow.local'
            """))
            user_id = result.scalar()

            # Assign role to user
            if role_id and user_id:
                await conn.execute(text("""
                    INSERT INTO app.user_role (user_id, role_id)
                    VALUES (:user_id, :role_id)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                """), {
                    "user_id": user_id,
                    "role_id": role_id
                })

            await conn.commit()
            print("✅ Admin user created successfully!")
            print("   Email: admin@magflow.local")
            print("   Password: secret")
            print("   Role: admin")

        await engine.dispose()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(create_admin_user())

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please install required packages:")
    print("pip install asyncpg sqlalchemy passlib")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
