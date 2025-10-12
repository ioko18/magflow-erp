"""Script to check database connection and list all tables in the app schema."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


async def check_database():
    """Check database connection and list all tables in the app schema."""
    # Create an async engine
    engine = create_async_engine(settings.DB_URI, echo=True)

    # Create a session
    sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Get database inspector
    async with engine.connect() as conn:
        # Check if the app schema exists
        result = await conn.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
            {"schema": settings.DB_SCHEMA}
        )
        schema_exists = result.scalar() is not None

        if not schema_exists:
            print(f"Schema '{settings.DB_SCHEMA}' does not exist. Creating...")
            await conn.execute(text(f"CREATE SCHEMA {settings.DB_SCHEMA}"))
            await conn.commit()
            print(f"Schema '{settings.DB_SCHEMA}' created successfully.")

        # Get all tables in the app schema
        result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                """
            ),
            {"schema": settings.DB_SCHEMA}
        )

        tables = result.fetchall()

        if tables:
            print(f"\nTables in schema '{settings.DB_SCHEMA}':")
            for table in tables:
                print(f"- {table[0]}")
        else:
            print(f"No tables found in schema '{settings.DB_SCHEMA}'.")

    await engine.dispose()

if __name__ == "__main__":
    print(f"Checking database connection to: {settings.DB_URI}")
    print(f"Using schema: {settings.DB_SCHEMA}")
    asyncio.run(check_database())
