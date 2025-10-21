#!/usr/bin/env python3
"""Apply database migrations manually."""

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

    from app.core.config import settings

    async def apply_migration():
        """Apply the user auth migration."""
        # Database connection string
        db_url = (
            "postgresql+asyncpg://"
            f"{settings.DB_USER}:{settings.DB_PASS}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )

        # Create async engine
        engine = create_async_engine(db_url, echo=True)

        async with engine.connect() as conn:
            # Create schema if it doesn't exist
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}'))
            await conn.commit()

            # Set search path
            await conn.execute(text(f'SET search_path TO {settings.DB_SCHEMA}, public'))

            # Create roles table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app.roles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    description VARCHAR(255),
                    is_active BOOLEAN DEFAULT true NOT NULL,
                    created_at TIMESTAMP DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP DEFAULT now() NOT NULL
                )
            """))

            # Create users table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app.users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT true NOT NULL,
                    is_superuser BOOLEAN DEFAULT false NOT NULL,
                    last_login TIMESTAMP WITH TIME ZONE,
                    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
                    last_failed_login TIMESTAMP WITH TIME ZONE,
                    email_verified BOOLEAN DEFAULT false NOT NULL,
                    avatar_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP DEFAULT now() NOT NULL
                )
            """))

            # Create refresh_tokens table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app.refresh_tokens (
                    id SERIAL PRIMARY KEY,
                    token VARCHAR(512) UNIQUE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_revoked BOOLEAN DEFAULT false NOT NULL,
                    user_agent VARCHAR(255),
                    ip_address VARCHAR(45),
                    user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP DEFAULT now() NOT NULL
                )
            """))

            # Create user_role association table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app.user_role (
                    user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
                    role_id INTEGER NOT NULL REFERENCES app.roles(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT now() NOT NULL,
                    PRIMARY KEY (user_id, role_id)
                )
            """))

            # Create indexes
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_users_email "
                    "ON app.users(email)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_users_is_active "
                    "ON app.users(is_active)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_users_is_superuser "
                    "ON app.users(is_superuser)"
                )
            )

            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token "
                    "ON app.refresh_tokens(token)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id "
                    "ON app.refresh_tokens(user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at "
                    "ON app.refresh_tokens(expires_at)"
                )
            )

            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_roles_name "
                    "ON app.roles(name)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_roles_is_active "
                    "ON app.roles(is_active)"
                )
            )

            await conn.commit()
            print("✅ Database migration applied successfully!")

            # Create a default admin user
            result = await conn.execute(
                text(
                    """
                    INSERT INTO app.users (
                        email,
                        hashed_password,
                        full_name,
                        is_superuser,
                        email_verified
                    )
                    VALUES (
                        'admin@magflow.local',
                        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCa3B5K/8N4lU3jK',
                        'Admin User',
                        true,
                        true
                    )
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id
                    """
                )
            )
            user = result.fetchone()

            if user:
                # Create admin role if it doesn't exist
                await conn.execute(text("""
                    INSERT INTO app.roles (name, description, is_active)
                    VALUES ('admin', 'Administrator role', true)
                    ON CONFLICT (name) DO NOTHING
                """))

                # Get admin role id
                result = await conn.execute(text("SELECT id FROM app.roles WHERE name = 'admin'"))
                role = result.fetchone()

                if role:
                    # Assign admin role to user
                    await conn.execute(text("""
                        INSERT INTO app.user_role (user_id, role_id)
                        VALUES (:user_id, :role_id)
                        ON CONFLICT (user_id, role_id) DO NOTHING
                    """), {"user_id": user.id, "role_id": role.id})

                # Create permissions table
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS app.permissions (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        description VARCHAR(255),
                        created_at TIMESTAMP DEFAULT now() NOT NULL,
                        updated_at TIMESTAMP DEFAULT now() NOT NULL
                    )
                """))

                # Insert permissions
                await conn.execute(
                    text(
                        """
                        INSERT INTO app.permissions (name, description, created_at, updated_at)
                        VALUES
                            (
                                'view_dashboard',
                                'View dashboard metrics and reports',
                                now(),
                                now()
                            ),
                            (
                                'manage_users',
                                'Create, update, and deactivate users',
                                now(),
                                now()
                            ),
                            (
                                'view_orders',
                                'View order data and export reports',
                                now(),
                                now()
                            ),
                            (
                                'manage_orders',
                                'Update order status and manage order workflow',
                                now(),
                                now()
                            ),
                            (
                                'manage_products',
                                'Create and update product catalog data',
                                now(),
                                now()
                            ),
                            (
                                'manage_inventory',
                                'Adjust inventory levels and stock settings',
                                now(),
                                now()
                            ),
                            (
                                'manage_settings',
                                'Update system configuration and integrations',
                                now(),
                                now()
                            )
                        ON CONFLICT (name) DO NOTHING
                        """
                    )
                )

                await conn.commit()
                print(
                    "✅ Default admin user created (email: admin@magflow.local, "
                    "password: secret)"
                )
            else:
                print("ℹ️  Admin user already exists")

        await engine.dispose()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(apply_migration())

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please install required packages:")
    print("pip install asyncpg sqlalchemy")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
