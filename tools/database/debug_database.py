#!/usr/bin/env python3
"""Debug database connection and check user creation."""

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

    async def debug_database():
        """Debug database connection and check what's actually in the database."""
        # Database connection string
        db_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

        print(f"Connecting to database: {db_url}")
        print(f"Schema: {settings.DB_SCHEMA}")

        # Create async engine
        engine = create_async_engine(db_url, echo=True)

        async with engine.connect() as conn:
            # Check current database
            result = await conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            print(f"Current database: {current_db}")

            # Check current schema
            result = await conn.execute(text("SELECT current_schema"))
            current_schema = result.scalar()
            print(f"Current schema: {current_schema}")

            # List all tables in the app schema
            result = await conn.execute(text("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = :schema
                ORDER BY tablename
            """), {"schema": settings.DB_SCHEMA})

            tables = result.fetchall()
            print(f"Tables in schema '{settings.DB_SCHEMA}':")
            for table in tables:
                print(f"  - {table.tablename}")

            # Check if users table exists and count users
            try:
                result = await conn.execute(text("""
                    SELECT COUNT(*) FROM app.users
                """))
                user_count = result.scalar()
                print(f"Users in app.users table: {user_count}")
            except Exception as e:
                print(f"Error querying users table: {e}")

            # Check if any users exist at all
            result = await conn.execute(text("""
                SELECT email, full_name, is_superuser
                FROM app.users
                LIMIT 5
            """))
            users = result.fetchall()
            print("All users found:")
            for user in users:
                print(f"  - {user.email} ({user.full_name}) - Superuser: {user.is_superuser}")

        await engine.dispose()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(debug_database())

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please ensure all dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
