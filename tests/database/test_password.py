#!/usr/bin/env python3
"""Test password verification directly."""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, app_dir)

# Add user site-packages to path
user_site = "/Users/macos/Library/Python/3.9/lib/python/site-packages"
sys.path.insert(0, user_site)

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from passlib.hash import bcrypt

    from app.core.config import settings

    async def test_password():
        """Test password verification directly against database."""
        # Database connection string
        db_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

        print(f"Connecting to database: {db_url}")

        # Create async engine
        engine = create_async_engine(db_url, echo=False)

        async with engine.connect() as conn:
            # Set search path
            await conn.execute(text(f'SET search_path TO {settings.DB_SCHEMA}, public'))

            # Check if users table exists
            table_exists = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE  table_schema = :schema
                    AND    table_name   = 'users'
                )
            """), {"schema": settings.DB_SCHEMA})
            
            if not table_exists.scalar():
                print("❌ Users table does not exist in the test database")
                return
                
            # Get the hashed password from database
            result = await conn.execute(text(f"""
                SELECT hashed_password FROM {settings.DB_SCHEMA}.users WHERE email = :email
            """), {"email": "admin@magflow.local"})

            db_password = result.scalar()

            if db_password:
                print(f"Database hashed password: {db_password}")

                # Test password verification
                plain_password = "secret"
                is_valid = bcrypt.verify(plain_password, db_password)

                print(f"Password verification result: {is_valid}")

                # Also test with wrong password
                is_wrong_valid = bcrypt.verify("wrongpassword", db_password)
                print(f"Wrong password verification: {is_wrong_valid}")

                # Test hashing a new password
                new_hash = bcrypt.hash(plain_password)
                print(f"New hash for 'secret': {new_hash}")

                is_new_valid = bcrypt.verify(plain_password, new_hash)
                print(f"New hash verification: {is_new_valid}")
            else:
                print("❌ No user found with email admin@magflow.local")

        await engine.dispose()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(test_password())

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please ensure all dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
