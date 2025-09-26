import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool


async def test_connection():
    """Test database connection using SQLite."""
    # Create an in-memory SQLite database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=True,
        future=True,
    )
    
    async with engine.connect() as conn:
        # Use text() for raw SQL queries
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("Successfully connected to SQLite database")


if __name__ == "__main__":
    asyncio.run(test_connection())
