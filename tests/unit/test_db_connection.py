"""Test database connection with current settings."""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def test_db_connection():
    """Test database connection with current settings."""
    print("Testing database connection...")
    db_url = settings.DB_URI
    print(f"DB URL: {db_url}")

    engine = create_async_engine(db_url)

    try:
        async with engine.connect() as conn:
            # Test the connection
            result = await conn.execute("SELECT 1")
            print("✅ Database connection successful!")
            print(f"Test query result: {result.scalar()}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e!s}")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_db_connection())
