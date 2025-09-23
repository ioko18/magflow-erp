#!/usr/bin/env python3
"""Test database connection script."""

import asyncio
import sys
from app.core.database import get_async_session


async def test_db_connection():
    """Test database connection."""
    try:
        async with get_async_session() as session:
            print("✅ Database connection successful!")
            print(f"Session type: {type(session)}")

            # Try a simple query to verify the database is working
            result = await session.execute("SELECT 1 as test")
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database query test passed!")
            else:
                print("❌ Database query test failed!")

            return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    sys.exit(0 if success else 1)
